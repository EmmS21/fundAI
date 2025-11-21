"""
Database Operations
CRUD operations and database utilities

NOTE: Operations are intentionally minimal/placeholder.
See tasks.md Task 2.1 for database schema design discussion.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from src.config.settings import Settings
from src.data.database.models import Base


def get_engine():
    """Create and return database engine"""
    database_url = f"sqlite:///{Settings.DATABASE_PATH}"
    return create_engine(database_url, echo=False)


def init_database():
    """Initialize database tables"""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)


def get_session() -> Session:
    """Get database session"""
    engine = get_engine()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


# TODO: Implement CRUD operations once models are defined 
