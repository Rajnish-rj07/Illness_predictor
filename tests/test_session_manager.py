"""
Unit tests for SessionManager class.

Tests session lifecycle management, persistence, expiration, and immutability.

Validates: Requirements 10.1, 10.2, 10.3, 10.4, 10.5
"""

import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from src.session.session_manager import SessionManager
from src.models.data_models import (
    Session, SessionStatus, ConversationContext, SymptomVector,
    SymptomInfo, Message
)
from src.database.models import SessionModel


class TestSessionManagerStartSession:
    """Test SessionManager.start_session() method."""
    
    def test_start_session_creates_unique_id(self):
        """Test that start_session generates a unique UUID session ID."""
        manager = SessionManager()
        
        session1 = manager.start_session('web', 'user-123', 'en')
        session2 = manager.start_session('web', 'user-456', 'en')
        
        # Session IDs should be unique
        assert session1.session_id != session2.session_id
        
        # Should be valid UUIDs
        uuid.UUID(session1.session_id)
        uuid.UUID(session2.session_id)
        
        # Cleanup
        manager.delete_session(session1.session_id)
        manager.delete_session(session2.session_id)
    
    def test_start_session_sets_correct_fields(self):
        """Test that start_session sets all required fields correctly."""
        manager = SessionManager()
        
        session = manager.start_session('sms', 'user-789', 'es')
        
        assert session.session_id is not None
        assert session.user_id == 'user-789'
        assert session.channel == 'sms'
        assert session.language == 'es'
        assert session.status == SessionStatus.ACTIVE
        assert isinstance(session.created_at, datetime)
        assert isinstance(session.last_active, datetime)
        assert isinstance(session.conversation_context, ConversationContext)
        assert isinstance(session.symptom_vector, SymptomVector)
        
        # Cleanup
        manager.delete_session(session.session_id)
    
    def test_start_session_persists_to_redis(self):
        """Test that start_session saves session to Redis."""
        manager = SessionManager()
        
        session = manager.start_session('web', 'user-111', 'en')
        
        # Should be able to load from Redis
        redis_key = manager._get_redis_key(session.session_id)
        redis_data = manager.redis.get(redis_key)
        
        assert redis_data is not None
        
        # Cleanup
        manager.delete_session(session.session_id)
    
    def test_start_session_persists_to_database(self):
        """Test that start_session saves session to PostgreSQL."""
        manager = SessionManager()
        
        session = manager.start_session('whatsapp', 'user-222', 'fr')
        
        # Should be able to load from database
        loaded = manager._load_from_db(session.session_id)
        
        assert loaded is not None
        assert loaded.session_id == session.session_id
        assert loaded.user_id == 'user-222'
        assert loaded.channel == 'whatsapp'
        assert loaded.language == 'fr'
        
        # Cleanup
        manager.delete_session(session.session_id)
    
    def test_start_session_with_default_language(self):
        """Test that start_session uses default language when not specified."""
        manager = SessionManager()
        
        session = manager.start_session('web', 'user-333')
        
        assert session.language == 'en'  # Default language
        
        # Cleanup
        manager.delete_session(session.session_id)


class TestSessionManagerResumeSession:
    """Test SessionManager.resume_session() method."""
    
    def test_resume_session_loads_from_redis(self):
        """Test that resume_session loads from Redis (fast path)."""
        manager = SessionManager()
        
        # Create session
        original = manager.start_session('web', 'user-444', 'en')
        session_id = original.session_id
        
        # Resume session
        resumed = manager.resume_session(session_id)
        
        assert resumed is not None
        assert resumed.session_id == session_id
        assert resumed.user_id == 'user-444'
        
        # Cleanup
        manager.delete_session(session_id)
    
    def test_resume_session_falls_back_to_database(self):
        """Test that resume_session falls back to PostgreSQL if not in Redis."""
        manager = SessionManager()
        
        # Create session
        original = manager.start_session('sms', 'user-555', 'en')
        session_id = original.session_id
        
        # Remove from Redis
        manager._delete_from_redis(session_id)
        
        # Resume should still work (from database)
        resumed = manager.resume_session(session_id)
        
        assert resumed is not None
        assert resumed.session_id == session_id
        assert resumed.user_id == 'user-555'
        
        # Cleanup
        manager.delete_session(session_id)
    
    def test_resume_session_returns_none_for_nonexistent(self):
        """Test that resume_session returns None for non-existent session."""
        manager = SessionManager()
        
        fake_id = str(uuid.uuid4())
        resumed = manager.resume_session(fake_id)
        
        assert resumed is None
    
    def test_resume_session_updates_last_active(self):
        """Test that resume_session updates last_active timestamp."""
        manager = SessionManager()
        
        # Create session
        original = manager.start_session('web', 'user-666', 'en')
        session_id = original.session_id
        original_last_active = original.last_active
        
        # Wait a moment
        import time
        time.sleep(0.1)
        
        # Resume session
        resumed = manager.resume_session(session_id)
        
        assert resumed.last_active > original_last_active
        
        # Cleanup
        manager.delete_session(session_id)
    
    def test_resume_session_rejects_expired(self):
        """Test that resume_session returns None for expired sessions."""
        manager = SessionManager()
        
        # Create session with old timestamp
        session = manager.start_session('web', 'user-777', 'en')
        session_id = session.session_id
        
        # Manually set last_active to >24 hours ago
        old_time = datetime.utcnow() - timedelta(hours=25)
        session.last_active = old_time
        manager._save_to_db(session)
        manager._save_to_redis(session)
        
        # Resume should return None (expired)
        resumed = manager.resume_session(session_id)
        
        assert resumed is None
        
        # Session should be marked as expired in database
        db_session = manager._load_from_db(session_id)
        assert db_session.status == SessionStatus.EXPIRED
        
        # Cleanup
        manager.delete_session(session_id)
    
    def test_resume_session_allows_completed(self):
        """Test that resume_session returns completed sessions."""
        manager = SessionManager()
        
        # Create and complete session
        session = manager.start_session('web', 'user-888', 'en')
        session_id = session.session_id
        manager.end_session(session_id)
        
        # Resume should return the completed session
        resumed = manager.resume_session(session_id)
        
        assert resumed is not None
        assert resumed.status == SessionStatus.COMPLETED
        
        # Cleanup
        manager.delete_session(session_id)


class TestSessionManagerEndSession:
    """Test SessionManager.end_session() method."""
    
    def test_end_session_marks_as_completed(self):
        """Test that end_session marks session as completed."""
        manager = SessionManager()
        
        # Create session
        session = manager.start_session('web', 'user-999', 'en')
        session_id = session.session_id
        
        # End session
        result = manager.end_session(session_id)
        
        assert result is True
        
        # Load from database
        db_session = manager._load_from_db(session_id)
        assert db_session.status == SessionStatus.COMPLETED
        
        # Cleanup
        manager.delete_session(session_id)
    
    def test_end_session_removes_from_redis(self):
        """Test that end_session removes session from Redis."""
        manager = SessionManager()
        
        # Create session
        session = manager.start_session('web', 'user-1010', 'en')
        session_id = session.session_id
        
        # Verify in Redis
        redis_key = manager._get_redis_key(session_id)
        assert manager.redis.get(redis_key) is not None
        
        # End session
        manager.end_session(session_id)
        
        # Should be removed from Redis
        assert manager.redis.get(redis_key) is None
        
        # Cleanup
        manager.delete_session(session_id)
    
    def test_end_session_keeps_in_database(self):
        """Test that end_session keeps session in PostgreSQL."""
        manager = SessionManager()
        
        # Create session
        session = manager.start_session('web', 'user-1111', 'en')
        session_id = session.session_id
        
        # End session
        manager.end_session(session_id)
        
        # Should still be in database
        db_session = manager._load_from_db(session_id)
        assert db_session is not None
        assert db_session.status == SessionStatus.COMPLETED
        
        # Cleanup
        manager.delete_session(session_id)
    
    def test_end_session_returns_false_for_nonexistent(self):
        """Test that end_session returns False for non-existent session."""
        manager = SessionManager()
        
        fake_id = str(uuid.uuid4())
        result = manager.end_session(fake_id)
        
        assert result is False
    
    def test_end_session_idempotent(self):
        """Test that end_session can be called multiple times."""
        manager = SessionManager()
        
        # Create session
        session = manager.start_session('web', 'user-1212', 'en')
        session_id = session.session_id
        
        # End session twice
        result1 = manager.end_session(session_id)
        result2 = manager.end_session(session_id)
        
        assert result1 is True
        assert result2 is True
        
        # Cleanup
        manager.delete_session(session_id)


class TestSessionManagerUpdateSession:
    """Test SessionManager.update_session() method."""
    
    def test_update_session_saves_changes(self):
        """Test that update_session persists changes."""
        manager = SessionManager()
        
        # Create session
        session = manager.start_session('web', 'user-1313', 'en')
        session_id = session.session_id
        
        # Modify session
        session.symptom_vector.symptoms['fever'] = SymptomInfo(
            present=True, severity=8, duration='1-3d'
        )
        session.symptom_vector.question_count = 3
        
        # Update session
        result = manager.update_session(session)
        
        assert result is True
        
        # Load and verify changes
        loaded = manager.resume_session(session_id)
        assert 'fever' in loaded.symptom_vector.symptoms
        assert loaded.symptom_vector.question_count == 3
        
        # Cleanup
        manager.delete_session(session_id)
    
    def test_update_session_rejects_completed(self):
        """Test that update_session rejects completed sessions."""
        manager = SessionManager()
        
        # Create and complete session
        session = manager.start_session('web', 'user-1414', 'en')
        session_id = session.session_id
        manager.end_session(session_id)
        
        # Try to update completed session
        session.status = SessionStatus.COMPLETED
        session.symptom_vector.question_count = 5
        
        result = manager.update_session(session)
        
        assert result is False
        
        # Cleanup
        manager.delete_session(session_id)
    
    def test_update_session_validates_data(self):
        """Test that update_session validates session data."""
        manager = SessionManager()
        
        # Create session
        session = manager.start_session('web', 'user-1515', 'en')
        session_id = session.session_id
        
        # Make session invalid
        session.symptom_vector.question_count = 20  # Exceeds max of 15
        
        # Update should fail validation
        result = manager.update_session(session)
        
        assert result is False
        
        # Cleanup
        manager.delete_session(session_id)
    
    def test_update_session_updates_last_active(self):
        """Test that update_session updates last_active timestamp."""
        manager = SessionManager()
        
        # Create session
        session = manager.start_session('web', 'user-1616', 'en')
        session_id = session.session_id
        original_last_active = session.last_active
        
        # Wait a moment
        import time
        time.sleep(0.1)
        
        # Update session
        session.symptom_vector.question_count = 1
        manager.update_session(session)
        
        # Load and check timestamp
        loaded = manager.resume_session(session_id)
        assert loaded.last_active > original_last_active
        
        # Cleanup
        manager.delete_session(session_id)


class TestSessionManagerDeleteSession:
    """Test SessionManager.delete_session() method."""
    
    def test_delete_session_removes_from_redis(self):
        """Test that delete_session removes from Redis."""
        manager = SessionManager()
        
        # Create session
        session = manager.start_session('web', 'user-1717', 'en')
        session_id = session.session_id
        
        # Verify in Redis
        redis_key = manager._get_redis_key(session_id)
        assert manager.redis.get(redis_key) is not None
        
        # Delete session
        result = manager.delete_session(session_id)
        
        assert result is True
        assert manager.redis.get(redis_key) is None
    
    def test_delete_session_removes_from_database(self):
        """Test that delete_session removes from PostgreSQL."""
        manager = SessionManager()
        
        # Create session
        session = manager.start_session('web', 'user-1818', 'en')
        session_id = session.session_id
        
        # Delete session
        result = manager.delete_session(session_id)
        
        assert result is True
        
        # Should not be in database
        db_session = manager._load_from_db(session_id)
        assert db_session is None
    
    def test_delete_session_returns_false_for_nonexistent(self):
        """Test that delete_session returns False for non-existent session."""
        manager = SessionManager()
        
        fake_id = str(uuid.uuid4())
        result = manager.delete_session(fake_id)
        
        assert result is False


class TestSessionManagerCleanupExpired:
    """Test SessionManager.cleanup_expired_sessions() method."""
    
    def test_cleanup_expired_marks_as_expired(self):
        """Test that cleanup marks expired sessions as expired."""
        manager = SessionManager()
        
        # Create session with old timestamp
        session = manager.start_session('web', 'user-1919', 'en')
        session_id = session.session_id
        
        # Manually set last_active to >24 hours ago
        old_time = datetime.utcnow() - timedelta(hours=25)
        session.last_active = old_time
        manager._save_to_db(session)
        
        # Run cleanup
        count = manager.cleanup_expired_sessions()
        
        assert count >= 1
        
        # Session should be marked as expired
        db_session = manager._load_from_db(session_id)
        assert db_session.status == SessionStatus.EXPIRED
        
        # Cleanup
        manager.delete_session(session_id)
    
    def test_cleanup_expired_removes_from_redis(self):
        """Test that cleanup removes expired sessions from Redis."""
        manager = SessionManager()
        
        # Create session with old timestamp
        session = manager.start_session('web', 'user-2020', 'en')
        session_id = session.session_id
        
        # Manually set last_active to >24 hours ago
        old_time = datetime.utcnow() - timedelta(hours=25)
        session.last_active = old_time
        manager._save_to_db(session)
        manager._save_to_redis(session)
        
        # Verify in Redis
        redis_key = manager._get_redis_key(session_id)
        assert manager.redis.get(redis_key) is not None
        
        # Run cleanup
        manager.cleanup_expired_sessions()
        
        # Should be removed from Redis
        assert manager.redis.get(redis_key) is None
        
        # Cleanup
        manager.delete_session(session_id)
    
    def test_cleanup_expired_ignores_active(self):
        """Test that cleanup doesn't affect active sessions."""
        manager = SessionManager()
        
        # Create active session
        session = manager.start_session('web', 'user-2121', 'en')
        session_id = session.session_id
        
        # Run cleanup
        count_before = manager.cleanup_expired_sessions()
        
        # Session should still be active
        loaded = manager.resume_session(session_id)
        assert loaded is not None
        assert loaded.status == SessionStatus.ACTIVE
        
        # Cleanup
        manager.delete_session(session_id)
    
    def test_cleanup_expired_ignores_completed(self):
        """Test that cleanup doesn't affect completed sessions."""
        manager = SessionManager()
        
        # Create and complete session
        session = manager.start_session('web', 'user-2222', 'en')
        session_id = session.session_id
        manager.end_session(session_id)
        
        # Manually set old timestamp
        old_time = datetime.utcnow() - timedelta(hours=25)
        session = manager._load_from_db(session_id)
        session.last_active = old_time
        manager._save_to_db(session)
        
        # Run cleanup
        manager.cleanup_expired_sessions()
        
        # Session should still be completed (not changed to expired)
        db_session = manager._load_from_db(session_id)
        assert db_session.status == SessionStatus.COMPLETED
        
        # Cleanup
        manager.delete_session(session_id)


class TestSessionManagerPersistence:
    """Test SessionManager persistence round-trip."""
    
    def test_session_round_trip_preserves_data(self):
        """Test that session data is preserved through save/load cycle."""
        manager = SessionManager()
        
        # Create session with complex data
        session = manager.start_session('whatsapp', 'user-2323', 'es')
        session_id = session.session_id
        
        # Add conversation context
        session.conversation_context.messages.append(
            Message(role='user', content='Tengo fiebre', timestamp=datetime.utcnow())
        )
        session.conversation_context.extracted_symptoms.append('fever')
        
        # Add symptom vector
        session.symptom_vector.symptoms['fever'] = SymptomInfo(
            present=True,
            severity=8,
            duration='1-3d',
            description='High fever'
        )
        session.symptom_vector.question_count = 2
        
        # Update session
        manager.update_session(session)
        
        # Load from database (bypassing Redis)
        manager._delete_from_redis(session_id)
        loaded = manager.resume_session(session_id)
        
        # Verify all data preserved
        assert loaded.session_id == session_id
        assert loaded.user_id == 'user-2323'
        assert loaded.channel == 'whatsapp'
        assert loaded.language == 'es'
        assert len(loaded.conversation_context.messages) == 1
        assert loaded.conversation_context.messages[0].content == 'Tengo fiebre'
        assert 'fever' in loaded.conversation_context.extracted_symptoms
        assert 'fever' in loaded.symptom_vector.symptoms
        assert loaded.symptom_vector.symptoms['fever'].severity == 8
        assert loaded.symptom_vector.question_count == 2
        
        # Cleanup
        manager.delete_session(session_id)


class TestSessionManagerConcurrency:
    """Test SessionManager behavior with concurrent operations."""
    
    def test_multiple_sessions_independent(self):
        """Test that multiple sessions are independent."""
        manager = SessionManager()
        
        # Create multiple sessions
        session1 = manager.start_session('web', 'user-2424', 'en')
        session2 = manager.start_session('sms', 'user-2525', 'es')
        session3 = manager.start_session('whatsapp', 'user-2626', 'fr')
        
        # Modify session1
        session1.symptom_vector.question_count = 5
        manager.update_session(session1)
        
        # Verify other sessions unaffected
        loaded2 = manager.resume_session(session2.session_id)
        loaded3 = manager.resume_session(session3.session_id)
        
        assert loaded2.symptom_vector.question_count == 0
        assert loaded3.symptom_vector.question_count == 0
        
        # Cleanup
        manager.delete_session(session1.session_id)
        manager.delete_session(session2.session_id)
        manager.delete_session(session3.session_id)


class TestSessionManagerEdgeCases:
    """Test SessionManager edge cases and error handling."""
    
    def test_session_with_empty_symptom_vector(self):
        """Test session with no symptoms."""
        manager = SessionManager()
        
        session = manager.start_session('web', 'user-2727', 'en')
        session_id = session.session_id
        
        # Symptom vector should be empty but valid
        assert len(session.symptom_vector.symptoms) == 0
        assert session.symptom_vector.question_count == 0
        
        # Should be able to resume
        loaded = manager.resume_session(session_id)
        assert loaded is not None
        
        # Cleanup
        manager.delete_session(session_id)
    
    def test_session_with_max_symptoms(self):
        """Test session with many symptoms."""
        manager = SessionManager()
        
        session = manager.start_session('web', 'user-2828', 'en')
        session_id = session.session_id
        
        # Add many symptoms
        for i in range(20):
            session.symptom_vector.symptoms[f'symptom_{i}'] = SymptomInfo(
                present=True, severity=5
            )
        
        manager.update_session(session)
        
        # Should be able to resume with all symptoms
        loaded = manager.resume_session(session_id)
        assert len(loaded.symptom_vector.symptoms) == 20
        
        # Cleanup
        manager.delete_session(session_id)
    
    def test_session_with_special_characters(self):
        """Test session with special characters in data."""
        manager = SessionManager()
        
        session = manager.start_session('web', 'user-2929', 'en')
        session_id = session.session_id
        
        # Add symptom with special characters
        session.symptom_vector.symptoms['test'] = SymptomInfo(
            present=True,
            description='Pain with "quotes" and \'apostrophes\' and émojis 😷'
        )
        
        manager.update_session(session)
        
        # Should preserve special characters
        loaded = manager.resume_session(session_id)
        assert '😷' in loaded.symptom_vector.symptoms['test'].description
        
        # Cleanup
        manager.delete_session(session_id)



# ============================================================================
# Property-Based Tests
# ============================================================================

from hypothesis import given, strategies as st, settings
from hypothesis.strategies import composite


# Custom strategies for generating test data
@composite
def session_channels(draw):
    """Generate valid session channels."""
    return draw(st.sampled_from(['sms', 'whatsapp', 'web']))


@composite
def session_languages(draw):
    """Generate valid session languages."""
    return draw(st.sampled_from(['en', 'es', 'fr', 'hi', 'zh']))


@composite
def user_ids(draw):
    """Generate anonymized user IDs."""
    return draw(st.text(min_size=5, max_size=20, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'), 
        whitelist_characters='-_'
    )))


@composite
def symptom_infos(draw):
    """Generate valid SymptomInfo objects."""
    return SymptomInfo(
        present=draw(st.booleans()),
        severity=draw(st.one_of(st.none(), st.integers(min_value=1, max_value=10))),
        duration=draw(st.one_of(st.none(), st.sampled_from(['<1d', '1-3d', '3-7d', '>7d']))),
        description=draw(st.text(min_size=0, max_size=200))
    )


@composite
def symptom_vectors(draw):
    """Generate valid SymptomVector objects."""
    num_symptoms = draw(st.integers(min_value=0, max_value=20))
    symptoms = {}
    
    for i in range(num_symptoms):
        symptom_name = draw(st.text(min_size=3, max_size=30, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll'), 
            whitelist_characters=' -_'
        )))
        symptoms[symptom_name] = draw(symptom_infos())
    
    return SymptomVector(
        symptoms=symptoms,
        question_count=draw(st.integers(min_value=0, max_value=15)),
        confidence_threshold_met=draw(st.booleans())
    )


@composite
def messages(draw):
    """Generate valid Message objects."""
    return Message(
        role=draw(st.sampled_from(['user', 'assistant'])),
        content=draw(st.text(min_size=1, max_size=500)),
        timestamp=datetime.utcnow()
    )


@composite
def conversation_contexts(draw):
    """Generate valid ConversationContext objects."""
    num_messages = draw(st.integers(min_value=0, max_value=20))
    msgs = [draw(messages()) for _ in range(num_messages)]
    
    num_symptoms = draw(st.integers(min_value=0, max_value=20))
    extracted = [draw(st.text(min_size=3, max_size=30)) for _ in range(num_symptoms)]
    
    return ConversationContext(
        messages=msgs,
        extracted_symptoms=extracted
    )


class TestSessionManagerPropertyTests:
    """Property-based tests for SessionManager."""
    
    @given(
        channel=session_channels(),
        user_id=user_ids(),
        language=session_languages()
    )
    @settings(max_examples=100, deadline=None)
    def test_property_23_session_identifier_uniqueness(self, channel, user_id, language):
        """
        Property 23: Session identifier uniqueness
        **Validates: Requirements 10.1**
        
        Test that any two sessions have unique identifiers.
        
        For any two sessions created at different times or for different users,
        their session identifiers should be unique.
        """
        manager = SessionManager()
        
        # Create two sessions
        session1 = manager.start_session(channel, user_id, language)
        session2 = manager.start_session(channel, user_id, language)
        
        try:
            # Session IDs must be unique
            assert session1.session_id != session2.session_id, \
                f"Session IDs are not unique: {session1.session_id} == {session2.session_id}"
            
            # Both should be valid UUIDs
            uuid.UUID(session1.session_id)
            uuid.UUID(session2.session_id)
            
        finally:
            # Cleanup
            manager.delete_session(session1.session_id)
            manager.delete_session(session2.session_id)
    
    @given(
        channel=session_channels(),
        user_id=user_ids(),
        language=session_languages(),
        symptom_vector=symptom_vectors(),
        conversation_context=conversation_contexts()
    )
    @settings(max_examples=100, deadline=None)
    def test_property_24_session_state_round_trip(
        self, channel, user_id, language, symptom_vector, conversation_context
    ):
        """
        Property 24: Session state round-trip
        **Validates: Requirements 10.2, 10.3**
        
        Test that persisting and restoring any session preserves state.
        
        For any active session, persisting the session and then restoring it
        should produce an equivalent session state (Conversation_Context and
        Symptom_Vector preserved).
        """
        manager = SessionManager()
        
        # Create session
        session = manager.start_session(channel, user_id, language)
        session_id = session.session_id
        
        try:
            # Set complex state
            session.symptom_vector = symptom_vector
            session.conversation_context = conversation_context
            
            # Validate before saving
            try:
                session.validate()
            except ValueError:
                # Skip invalid test cases
                return
            
            # Update session (persist)
            result = manager.update_session(session)
            
            if not result:
                # Skip if update failed (e.g., validation error)
                return
            
            # Remove from Redis to force database load
            manager._delete_from_redis(session_id)
            
            # Restore session
            restored = manager.resume_session(session_id)
            
            # Verify session was restored
            assert restored is not None, "Session should be restorable"
            
            # Verify all fields preserved
            assert restored.session_id == session_id
            assert restored.user_id == user_id
            assert restored.channel == channel
            assert restored.language == language
            assert restored.status == SessionStatus.ACTIVE
            
            # Verify symptom vector preserved
            assert restored.symptom_vector.question_count == symptom_vector.question_count
            assert restored.symptom_vector.confidence_threshold_met == symptom_vector.confidence_threshold_met
            assert len(restored.symptom_vector.symptoms) == len(symptom_vector.symptoms)
            
            # Verify each symptom preserved
            for symptom_name, symptom_info in symptom_vector.symptoms.items():
                assert symptom_name in restored.symptom_vector.symptoms, \
                    f"Symptom {symptom_name} not preserved"
                restored_info = restored.symptom_vector.symptoms[symptom_name]
                assert restored_info.present == symptom_info.present
                assert restored_info.severity == symptom_info.severity
                assert restored_info.duration == symptom_info.duration
                assert restored_info.description == symptom_info.description
            
            # Verify conversation context preserved
            assert len(restored.conversation_context.messages) == len(conversation_context.messages)
            assert len(restored.conversation_context.extracted_symptoms) == len(conversation_context.extracted_symptoms)
            
            # Verify messages preserved
            for i, msg in enumerate(conversation_context.messages):
                restored_msg = restored.conversation_context.messages[i]
                assert restored_msg.role == msg.role
                assert restored_msg.content == msg.content
            
            # Verify extracted symptoms preserved
            for symptom in conversation_context.extracted_symptoms:
                assert symptom in restored.conversation_context.extracted_symptoms
            
        finally:
            # Cleanup
            manager.delete_session(session_id)
    
    @given(
        channel=session_channels(),
        user_id=user_ids(),
        language=session_languages(),
        hours_old=st.floats(min_value=24.1, max_value=72.0)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_25_session_expiration_correctness(
        self, channel, user_id, language, hours_old
    ):
        """
        Property 25: Session expiration correctness
        **Validates: Requirements 10.4**
        
        Test that sessions older than 24 hours are marked expired.
        
        For any session with last_active timestamp more than 24 hours in the past,
        the session should be marked as expired and not restorable.
        """
        manager = SessionManager()
        
        # Create session
        session = manager.start_session(channel, user_id, language)
        session_id = session.session_id
        
        try:
            # Set last_active to more than 24 hours ago
            old_time = datetime.utcnow() - timedelta(hours=hours_old)
            session.last_active = old_time
            
            # Save with old timestamp
            manager._save_to_db(session)
            manager._save_to_redis(session)
            
            # Try to resume session
            resumed = manager.resume_session(session_id)
            
            # Session should not be restorable (returns None)
            assert resumed is None, \
                f"Session should be expired after {hours_old} hours, but was resumed"
            
            # Verify session is marked as expired in database
            db_session = manager._load_from_db(session_id)
            assert db_session is not None, "Session should still exist in database"
            assert db_session.status == SessionStatus.EXPIRED, \
                f"Session status should be EXPIRED, got {db_session.status}"
            
            # Verify session is removed from Redis
            redis_key = manager._get_redis_key(session_id)
            redis_data = manager.redis.get(redis_key)
            assert redis_data is None, "Expired session should be removed from Redis"
            
        finally:
            # Cleanup
            manager.delete_session(session_id)
    
    @given(
        channel=session_channels(),
        user_id=user_ids(),
        language=session_languages(),
        symptom_vector=symptom_vectors()
    )
    @settings(max_examples=100, deadline=None)
    def test_property_26_completed_session_immutability(
        self, channel, user_id, language, symptom_vector
    ):
        """
        Property 26: Completed session immutability
        **Validates: Requirements 10.5**
        
        Test that completed sessions reject modifications.
        
        For any session marked as completed, attempts to modify the Symptom_Vector
        or add messages should be rejected.
        """
        manager = SessionManager()
        
        # Create session
        session = manager.start_session(channel, user_id, language)
        session_id = session.session_id
        
        try:
            # Set initial state
            session.symptom_vector.question_count = 5
            manager.update_session(session)
            
            # Complete the session
            result = manager.end_session(session_id)
            assert result is True, "Session should be successfully completed"
            
            # Load completed session
            completed_session = manager._load_from_db(session_id)
            assert completed_session is not None
            assert completed_session.status == SessionStatus.COMPLETED
            
            # Try to modify completed session
            completed_session.symptom_vector = symptom_vector
            completed_session.symptom_vector.question_count = 10
            
            # Attempt to update should be rejected
            update_result = manager.update_session(completed_session)
            
            assert update_result is False, \
                "Update should be rejected for completed session"
            
            # Verify original state is preserved
            reloaded = manager._load_from_db(session_id)
            assert reloaded.symptom_vector.question_count == 5, \
                "Completed session state should not be modified"
            assert reloaded.status == SessionStatus.COMPLETED, \
                "Session should remain completed"
            
        finally:
            # Cleanup
            manager.delete_session(session_id)


class TestSessionManagerPropertyEdgeCases:
    """Property-based tests for edge cases."""
    
    @given(
        channel=session_channels(),
        user_id=user_ids(),
        language=session_languages()
    )
    @settings(max_examples=50, deadline=None)
    def test_property_session_uniqueness_same_user(self, channel, user_id, language):
        """
        Test that multiple sessions for the same user have unique IDs.
        
        This is a specific case of Property 23 focusing on same-user sessions.
        """
        manager = SessionManager()
        
        # Create multiple sessions for the same user
        sessions = []
        try:
            for _ in range(5):
                session = manager.start_session(channel, user_id, language)
                sessions.append(session)
            
            # All session IDs should be unique
            session_ids = [s.session_id for s in sessions]
            assert len(session_ids) == len(set(session_ids)), \
                "All session IDs should be unique even for the same user"
            
        finally:
            # Cleanup
            for session in sessions:
                manager.delete_session(session.session_id)
    
    @given(
        channel=session_channels(),
        user_id=user_ids(),
        language=session_languages(),
        hours_old=st.floats(min_value=0.0, max_value=23.9)
    )
    @settings(max_examples=50, deadline=None)
    def test_property_session_not_expired_before_24h(
        self, channel, user_id, language, hours_old
    ):
        """
        Test that sessions less than 24 hours old are NOT expired.
        
        This is the inverse case of Property 25.
        """
        manager = SessionManager()
        
        # Create session
        session = manager.start_session(channel, user_id, language)
        session_id = session.session_id
        
        try:
            # Set last_active to less than 24 hours ago
            recent_time = datetime.utcnow() - timedelta(hours=hours_old)
            session.last_active = recent_time
            
            # Save with recent timestamp
            manager._save_to_db(session)
            manager._save_to_redis(session)
            
            # Try to resume session
            resumed = manager.resume_session(session_id)
            
            # Session should be restorable (not expired)
            assert resumed is not None, \
                f"Session should NOT be expired after {hours_old} hours"
            assert resumed.status == SessionStatus.ACTIVE, \
                f"Session should be ACTIVE, got {resumed.status}"
            
        finally:
            # Cleanup
            manager.delete_session(session_id)
    
    @given(
        channel=session_channels(),
        user_id=user_ids(),
        language=session_languages()
    )
    @settings(max_examples=50, deadline=None)
    def test_property_empty_session_round_trip(self, channel, user_id, language):
        """
        Test that empty sessions (no symptoms, no messages) round-trip correctly.
        
        This is a specific case of Property 24 for minimal sessions.
        """
        manager = SessionManager()
        
        # Create session with empty state
        session = manager.start_session(channel, user_id, language)
        session_id = session.session_id
        
        try:
            # Verify empty state
            assert len(session.symptom_vector.symptoms) == 0
            assert len(session.conversation_context.messages) == 0
            
            # Remove from Redis to force database load
            manager._delete_from_redis(session_id)
            
            # Restore session
            restored = manager.resume_session(session_id)
            
            # Verify empty state preserved
            assert restored is not None
            assert len(restored.symptom_vector.symptoms) == 0
            assert len(restored.conversation_context.messages) == 0
            assert restored.symptom_vector.question_count == 0
            
        finally:
            # Cleanup
            manager.delete_session(session_id)
