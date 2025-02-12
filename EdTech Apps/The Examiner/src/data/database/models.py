from sqlalchemy import Column, Integer, String, Date, DateTime, Enum, Float, ForeignKey, Table, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import enum

Base = declarative_base()

class SyncStatus(enum.Enum):
    PENDING = "pending"
    SYNCED = "synced"
    FAILED = "failed"

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    hardware_id = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    birthday = Column(Date)
    country = Column(String)
    school_level = Column(String)  
    grade = Column(String)  
    
    # New fields for profile
    profile_picture = Column(String, nullable=True)  
    city = Column(String, nullable=True)
    subjects = Column(JSON, default=dict) 
    medals = Column(JSON, default={'gold': 0, 'silver': 0, 'bronze': 0})
    
    # Sync-related columns
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    sync_status = Column(Enum(SyncStatus), default=SyncStatus.PENDING)
    sync_attempts = Column(Integer, default=0)
    last_sync_attempt = Column(DateTime, nullable=True)

    # Relationships
    exam_results = relationship("ExamResult", back_populates="user")

    def __repr__(self):
        return f"<User(name='{self.full_name}', school_level='{self.school_level}', grade='{self.grade}')>"

class ExamResult(Base):
    __tablename__ = 'exam_results'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    subject = Column(String, nullable=False)
    exam_date = Column(DateTime, default=datetime.now)
    grade = Column(Float)  # Actual grade achieved
    total_possible = Column(Float)  # What the grade is out of
    level = Column(String)  # Difficulty level
    topics = Column(JSON)  # Store topics as JSON array
    
    # Sync-related columns
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    sync_status = Column(Enum(SyncStatus), default=SyncStatus.PENDING)
    sync_attempts = Column(Integer, default=0)
    last_sync_attempt = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="exam_results")
    question_responses = relationship("QuestionResponse", back_populates="exam_result")

class QuestionResponse(Base):
    __tablename__ = 'question_responses'
    
    id = Column(Integer, primary_key=True)
    exam_result_id = Column(Integer, ForeignKey('exam_results.id'))
    question_text = Column(String, nullable=False)
    student_answer = Column(String, nullable=False)
    correct_answer = Column(String, nullable=False)
    is_correct = Column(Boolean, nullable=False)
    feedback = Column(String)  # Teacher/AI feedback on the answer
    marks_achieved = Column(Float)
    marks_possible = Column(Float)
    
    # Sync-related columns
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    sync_status = Column(Enum(SyncStatus), default=SyncStatus.PENDING)
    sync_attempts = Column(Integer, default=0)
    last_sync_attempt = Column(DateTime, nullable=True)
    
    # Relationships
    exam_result = relationship("ExamResult", back_populates="question_responses")
