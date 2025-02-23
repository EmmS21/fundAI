from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.data.database.models import Base

# Create SQLite database engine - change to student_profile.db
engine = create_engine('sqlite:///student_profile.db', echo=True)

# Create all tables
Base.metadata.create_all(engine)

# Create session factory
Session = sessionmaker(bind=engine)

@contextmanager
def get_db_session():
    session = Session()
    try:
        yield session
    finally:
        session.close()
