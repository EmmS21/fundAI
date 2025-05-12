import os
import sys
import logging
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.data.database.models import Base

logger = logging.getLogger(__name__)

def init_database():
    """Initialize the database and create all tables"""
    try:
        # Create database directory if it doesn't exist
        db_dir = os.path.expanduser('~/.examiner/data')
        os.makedirs(db_dir, exist_ok=True)
        
        # Full path to database file
        db_path = os.path.join(db_dir, 'student_profile.db')
        logger.info(f"Database path: {db_path}")
        
        # Create SQLite database engine with verbose logging
        engine = create_engine(f'sqlite:///{db_path}', 
                             echo=True,
                             pool_pre_ping=True)
        
        try:
            # Test database connection
            connection = engine.connect()
            connection.close()
            logger.info("Database connection test successful")
        except Exception as conn_error:
            logger.error(f"Database connection test failed: {conn_error}")
            raise
        
        try:
            # Create all tables
            Base.metadata.create_all(engine)
            logger.info("Database tables created successfully")
        except Exception as table_error:
            logger.error(f"Failed to create database tables: {table_error}")
            raise
        
        # Create session factory
        Session = sessionmaker(bind=engine)
        
        return engine, Session
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        logger.error(f"Current working directory: {os.getcwd()}")
        logger.error(f"Python path: {sys.path}")
        raise

# Initialize database and create global engine and Session
try:
    engine, Session = init_database()
except Exception as e:
    logger.critical(f"Failed to initialize database: {e}")
    sys.exit(1)

@contextmanager
def get_db_session():
    session = Session()
    try:
        yield session
        session.commit()
    except Exception as e:
        logger.error(f"Database session error: {e}")
        session.rollback()
        raise
    finally:
        session.close()
