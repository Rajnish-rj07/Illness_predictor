"""
Database connection management for PostgreSQL and Redis.
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
import redis
from typing import Generator
from config.settings import settings
from config.logging_config import get_logger

logger = get_logger(__name__)


# PostgreSQL Engine
engine = create_engine(
    settings.database_url,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=settings.debug
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for getting database sessions.
    Yields a database session and ensures it's closed after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Redis Connection
redis_client = None


def get_redis() -> redis.Redis:
    """
    Get Redis client instance.
    Creates a connection pool for efficient connection management.
    """
    global redis_client
    
    if redis_client is None:
        redis_client = redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True
        )
        logger.info("Redis connection established")
    
    return redis_client


def init_db():
    """
    Initialize database tables.
    Creates all tables defined in models.py if they don't exist.
    """
    from src.database.models import Base
    
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database tables: {e}")
        raise


def check_db_connection() -> bool:
    """
    Check if database connection is working.
    Returns True if connection is successful, False otherwise.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection check: OK")
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False


def check_redis_connection() -> bool:
    """
    Check if Redis connection is working.
    Returns True if connection is successful, False otherwise.
    """
    try:
        client = get_redis()
        client.ping()
        logger.info("Redis connection check: OK")
        return True
    except Exception as e:
        logger.error(f"Redis connection check failed: {e}")
        return False
