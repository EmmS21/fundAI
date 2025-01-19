"""
database.py

Purpose: Database connection management and session handling.
Provides SQLAlchemy setup and connection pooling.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool
from ..core.config import settings

# Create SQLAlchemy engine with connection pooling
engine = create_engine(
    settings.compute_db_url(),
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30
)

# Create sessionmaker
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for SQLAlchemy models
Base = declarative_base()

def get_db():
    """Dependency for FastAPI endpoints to get DB session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
