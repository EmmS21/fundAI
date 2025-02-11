from sqlalchemy import Column, Integer, String, Date
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    full_name = Column(String, nullable=False)
    birthday = Column(Date)
    country = Column(String)
    grade = Column(String)
    
    def __repr__(self):
        return f"<User(name='{self.full_name}', country='{self.country}')>"
