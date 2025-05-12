import os
import sys
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_database():
    try:
        # Create database directory
        db_dir = os.path.expanduser('~/.examiner/data')
        os.makedirs(db_dir, exist_ok=True)
        
        # Database path
        db_path = os.path.join(db_dir, 'student_profile.db')
        logger.info(f"Testing database at: {db_path}")
        
        # Create engine
        engine = create_engine(f'sqlite:///{db_path}', echo=True)
        
        # Test connection
        connection = engine.connect()
        logger.info("Successfully connected to database")
        connection.close()
        
        return True
    except Exception as e:
        logger.error(f"Database test failed: {e}")
        return False

if __name__ == "__main__":
    if test_database():
        print("Database test passed")
        sys.exit(0)
    else:
        print("Database test failed")
        sys.exit(1)
