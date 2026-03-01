"""
Database initialization script.
Run this to create all database tables.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.logging_config import setup_logging
from src.database.connection import init_db, check_db_connection, check_redis_connection

logger = setup_logging()


def main():
    """Initialize database and check connections."""
    logger.info("Starting database initialization...")
    
    # Check PostgreSQL connection
    logger.info("Checking PostgreSQL connection...")
    if not check_db_connection():
        logger.error("PostgreSQL connection failed. Please check your configuration.")
        sys.exit(1)
    
    # Check Redis connection
    logger.info("Checking Redis connection...")
    if not check_redis_connection():
        logger.error("Redis connection failed. Please check your configuration.")
        sys.exit(1)
    
    # Initialize database tables
    logger.info("Creating database tables...")
    try:
        init_db()
        logger.info("Database initialization completed successfully!")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
