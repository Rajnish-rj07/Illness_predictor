"""
SessionManager for managing user conversation sessions.

Implements session lifecycle management with persistence to both Redis (fast access)
and PostgreSQL (durable storage).

Validates: Requirements 10.1, 10.2, 10.3, 10.4, 10.5
"""

import uuid
import json
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session as DBSession

from config.settings import settings
from config.logging_config import get_logger
from src.models.data_models import (
    Session, SessionStatus, ConversationContext, SymptomVector
)
from src.database.models import SessionModel
from src.database.connection import get_db, get_redis

logger = get_logger(__name__)


class SessionManager:
    """
    Manages user conversation sessions with dual persistence (Redis + PostgreSQL).
    
    Redis is used for fast session access during active conversations.
    PostgreSQL provides durable storage and historical data.
    """
    
    def __init__(self):
        """Initialize SessionManager with Redis and database connections."""
        self.redis = get_redis()
        self.session_ttl = settings.redis_session_ttl  # 24 hours
        
    def _get_redis_key(self, session_id: str) -> str:
        """Generate Redis key for session."""
        return f"session:{session_id}"
    
    def start_session(
        self,
        channel: str,
        user_id: str,
        language: str = "en"
    ) -> Session:
        """
        Start a new conversation session.
        
        Generates a unique session ID (UUID) and persists to both Redis and PostgreSQL.
        
        Args:
            channel: Communication channel ('sms', 'whatsapp', 'web')
            user_id: Anonymized user identifier
            language: User's preferred language (default: 'en')
            
        Returns:
            Session: Newly created session object
            
        Validates: Requirements 10.1, 10.2
        """
        # Generate unique session ID
        session_id = str(uuid.uuid4())
        
        # Create session object
        now = datetime.utcnow()
        session = Session(
            session_id=session_id,
            user_id=user_id,
            channel=channel,
            language=language,
            created_at=now,
            last_active=now,
            status=SessionStatus.ACTIVE,
            conversation_context=ConversationContext(),
            symptom_vector=SymptomVector()
        )
        
        # Validate session
        session.validate()
        
        # Persist to Redis for fast access
        self._save_to_redis(session)
        
        # Persist to PostgreSQL for durability
        self._save_to_db(session)
        
        logger.info(
            f"Started new session: {session_id} "
            f"(channel={channel}, user={user_id}, language={language})"
        )
        
        return session
    
    def resume_session(self, session_id: str) -> Optional[Session]:
        """
        Resume an existing session.
        
        Attempts to load from Redis first (fast), falls back to PostgreSQL if needed.
        Checks for expiration and updates last_active timestamp.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            Session: Restored session object, or None if not found/expired
            
        Validates: Requirements 10.3, 10.4
        """
        # Try Redis first (fast path)
        session = self._load_from_redis(session_id)
        
        # Fall back to PostgreSQL if not in Redis
        if session is None:
            session = self._load_from_db(session_id)
            
            # If found in DB, restore to Redis
            if session is not None:
                self._save_to_redis(session)
        
        # Check if session exists
        if session is None:
            logger.warning(f"Session not found: {session_id}")
            return None
        
        # Check if session is expired (>24 hours inactive)
        if session.is_expired():
            logger.info(f"Session expired: {session_id}")
            # Update status to expired
            session.status = SessionStatus.EXPIRED
            self._save_to_db(session)
            self._delete_from_redis(session_id)
            return None
        
        # Check if session is completed
        if session.is_completed():
            logger.info(f"Session already completed: {session_id}")
            return session
        
        # Update last_active timestamp
        session.last_active = datetime.utcnow()
        
        # Save updated session
        self._save_to_redis(session)
        self._save_to_db(session)
        
        logger.info(f"Resumed session: {session_id}")
        
        return session
    
    def end_session(self, session_id: str) -> bool:
        """
        End a conversation session.
        
        Marks session as completed and prevents further modifications.
        Removes from Redis but keeps in PostgreSQL for historical data.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            bool: True if session was successfully ended, False otherwise
            
        Validates: Requirements 10.5
        """
        # Load session
        session = self.resume_session(session_id)
        
        if session is None:
            logger.warning(f"Cannot end session - not found: {session_id}")
            return False
        
        # Check if already completed
        if session.is_completed():
            logger.info(f"Session already completed: {session_id}")
            return True
        
        # Mark as completed
        session.status = SessionStatus.COMPLETED
        
        # Save to database with completed status
        self._save_to_db(session)
        
        # Remove from Redis (no longer active)
        self._delete_from_redis(session_id)
        
        logger.info(f"Ended session: {session_id}")
        
        return True
    
    def update_session(self, session: Session) -> bool:
        """
        Update an existing session.
        
        Validates that session is not completed before allowing updates.
        
        Args:
            session: Session object to update
            
        Returns:
            bool: True if update successful, False otherwise
            
        Validates: Requirements 10.5
        """
        # Check if session is completed (immutable)
        if session.is_completed():
            logger.warning(
                f"Cannot update completed session: {session.session_id}"
            )
            return False
        
        # Validate session
        try:
            session.validate()
        except ValueError as e:
            logger.error(f"Session validation failed: {e}")
            return False
        
        # Update last_active timestamp
        session.last_active = datetime.utcnow()
        
        # Save to both Redis and PostgreSQL
        self._save_to_redis(session)
        self._save_to_db(session)
        
        logger.debug(f"Updated session: {session.session_id}")
        
        return True
    
    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session completely (for data deletion requests).
        
        Removes from both Redis and PostgreSQL.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            bool: True if deletion successful, False otherwise
            
        Validates: Requirements 9.5
        """
        # Delete from Redis
        self._delete_from_redis(session_id)
        
        # Delete from PostgreSQL
        deleted = self._delete_from_db(session_id)
        
        if deleted:
            logger.info(f"Deleted session: {session_id}")
        else:
            logger.warning(f"Session not found for deletion: {session_id}")
        
        return deleted
    
    def _save_to_redis(self, session: Session) -> None:
        """
        Save session to Redis for fast access.
        
        Args:
            session: Session object to save
        """
        try:
            redis_key = self._get_redis_key(session.session_id)
            session_json = session.to_json()
            
            # Set with TTL (24 hours)
            self.redis.setex(
                redis_key,
                self.session_ttl,
                session_json
            )
            
            logger.debug(f"Saved session to Redis: {session.session_id}")
        except Exception as e:
            logger.error(f"Failed to save session to Redis: {e}")
            # Don't raise - PostgreSQL is the source of truth
    
    def _load_from_redis(self, session_id: str) -> Optional[Session]:
        """
        Load session from Redis.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            Session object or None if not found
        """
        try:
            redis_key = self._get_redis_key(session_id)
            session_json = self.redis.get(redis_key)
            
            if session_json is None:
                return None
            
            session = Session.from_json(session_json)
            logger.debug(f"Loaded session from Redis: {session_id}")
            return session
            
        except Exception as e:
            logger.error(f"Failed to load session from Redis: {e}")
            return None
    
    def _delete_from_redis(self, session_id: str) -> None:
        """
        Delete session from Redis.
        
        Args:
            session_id: Unique session identifier
        """
        try:
            redis_key = self._get_redis_key(session_id)
            self.redis.delete(redis_key)
            logger.debug(f"Deleted session from Redis: {session_id}")
        except Exception as e:
            logger.error(f"Failed to delete session from Redis: {e}")
    
    def _save_to_db(self, session: Session) -> None:
        """
        Save session to PostgreSQL for durable storage.
        
        Args:
            session: Session object to save
        """
        db = next(get_db())
        try:
            # Check if session exists
            existing = db.query(SessionModel).filter(
                SessionModel.session_id == session.session_id
            ).first()
            
            if existing:
                # Update existing session
                existing.user_id = session.user_id
                existing.channel = session.channel
                existing.language = session.language
                existing.status = session.status
                existing.last_active = session.last_active
                existing.conversation_context = session.conversation_context.to_dict()
                existing.symptom_vector = session.symptom_vector.to_dict()
                
                if session.is_completed():
                    existing.completed_at = datetime.utcnow()
            else:
                # Create new session
                db_session = SessionModel(
                    session_id=session.session_id,
                    user_id=session.user_id,
                    channel=session.channel,
                    language=session.language,
                    status=session.status,
                    created_at=session.created_at,
                    last_active=session.last_active,
                    conversation_context=session.conversation_context.to_dict(),
                    symptom_vector=session.symptom_vector.to_dict()
                )
                db.add(db_session)
            
            db.commit()
            logger.debug(f"Saved session to database: {session.session_id}")
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to save session to database: {e}")
            raise
        finally:
            db.close()
    
    def _load_from_db(self, session_id: str) -> Optional[Session]:
        """
        Load session from PostgreSQL.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            Session object or None if not found
        """
        db = next(get_db())
        try:
            db_session = db.query(SessionModel).filter(
                SessionModel.session_id == session_id
            ).first()
            
            if db_session is None:
                return None
            
            # Convert database model to application model
            session = Session(
                session_id=db_session.session_id,
                user_id=db_session.user_id,
                channel=db_session.channel,
                language=db_session.language,
                created_at=db_session.created_at,
                last_active=db_session.last_active,
                status=SessionStatus(db_session.status.value),
                conversation_context=ConversationContext.from_dict(
                    db_session.conversation_context
                ),
                symptom_vector=SymptomVector.from_dict(
                    db_session.symptom_vector
                )
            )
            
            logger.debug(f"Loaded session from database: {session_id}")
            return session
            
        except Exception as e:
            logger.error(f"Failed to load session from database: {e}")
            return None
        finally:
            db.close()
    
    def _delete_from_db(self, session_id: str) -> bool:
        """
        Delete session from PostgreSQL.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            bool: True if deleted, False if not found
        """
        db = next(get_db())
        try:
            db_session = db.query(SessionModel).filter(
                SessionModel.session_id == session_id
            ).first()
            
            if db_session is None:
                return False
            
            db.delete(db_session)
            db.commit()
            logger.debug(f"Deleted session from database: {session_id}")
            return True
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to delete session from database: {e}")
            return False
        finally:
            db.close()
    
    def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions from Redis and mark as expired in PostgreSQL.
        
        This should be run periodically (e.g., via cron job).
        
        Returns:
            int: Number of sessions cleaned up
        """
        db = next(get_db())
        try:
            # Find expired sessions (>24 hours inactive, still marked as active)
            expiration_time = datetime.utcnow() - timedelta(hours=24)
            
            expired_sessions = db.query(SessionModel).filter(
                SessionModel.status == SessionStatus.ACTIVE,
                SessionModel.last_active < expiration_time
            ).all()
            
            count = 0
            for db_session in expired_sessions:
                # Mark as expired
                db_session.status = SessionStatus.EXPIRED
                
                # Remove from Redis
                self._delete_from_redis(db_session.session_id)
                
                count += 1
            
            db.commit()
            
            if count > 0:
                logger.info(f"Cleaned up {count} expired sessions")
            
            return count
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to cleanup expired sessions: {e}")
            return 0
        finally:
            db.close()
