from sqlalchemy import Column, Integer, String, Date, DateTime, Enum, Float, ForeignKey, Table, JSON, Boolean, LargeBinary, Text
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import enum
from sqlalchemy.sql import func
from typing import Optional, List, Dict, Any

Base = declarative_base()

class SyncStatus(enum.Enum):
    PENDING = "pending"
    SYNCED = "synced"
    FAILED = "failed"

class ReportVersion(enum.Enum):
    PRELIMINARY = "preliminary"
    FINAL = "final"

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    hardware_id = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    birthday = Column(Date)
    country = Column(String)
    school_level = Column(String)  
    grade = Column(String)  
    school = Column(String, nullable=True)
    
    # New fields for profile
    profile_picture = Column(LargeBinary, nullable=True)  
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
    subjects = relationship("UserSubject", back_populates="user")

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
    
    # New fields
    report_version = Column(Enum(ReportVersion), default=ReportVersion.PRELIMINARY)
    last_ai_sync = Column(DateTime, nullable=True)
    
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
    
    # Link to the specific question in the cache, if this response originated from one.
    # Made nullable=True initially for flexibility, but ideally should be set for cached questions.
    cached_question_id = Column(Text, ForeignKey('cached_questions.question_id'), nullable=True)
    
    # Relationships
    exam_result = relationship("ExamResult", back_populates="question_responses")
    cached_question = relationship("CachedQuestion")

# Many-to-many association table for user subjects with level selections
class UserSubject(Base):
    __tablename__ = 'user_subjects'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    subject_id = Column(Integer, ForeignKey('subjects.id'), nullable=False)
    
    # Level selections
    grade_7 = Column(Boolean, default=False)
    o_level = Column(Boolean, default=False)
    a_level = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="subjects")
    subject = relationship("Subject", back_populates="users")
    cached_papers = relationship("PaperCache", back_populates="user_subject")

class Subject(Base):
    __tablename__ = 'subjects'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    users = relationship("UserSubject", back_populates="subject")

class PaperCache(Base):
    __tablename__ = 'paper_cache'
    
    id = Column(Integer, primary_key=True)
    # Link to UserSubject for subject/level relationship
    user_subject_id = Column(Integer, ForeignKey('user_subjects.id'), nullable=False)
    year = Column(Integer, nullable=False)
    
    # Binary storage for paper content
    paper_content = Column(LargeBinary)
    
    # Simple completion tracking
    is_completed = Column(Boolean, default=False)
    
    # Basic timestamps
    created_at = Column(DateTime, default=datetime.now)
    last_accessed = Column(DateTime, nullable=True)
    
    # Relationship
    user_subject = relationship("UserSubject", back_populates="cached_papers")

class CachedQuestion(Base):
    __tablename__ = 'cached_questions'

    question_id = Column(Text, primary_key=True)
    paper_id = Column(Text, nullable=False)
    paper_year = Column(Integer, nullable=False)
    paper_number = Column(Text, nullable=False)
    subject = Column(Text, nullable=False)
    level = Column(Text, nullable=False)
    topic = Column(Text)
    content = Column(Text, nullable=False)
    marks = Column(Integer, nullable=False)
    cached_at = Column(DateTime, nullable=False, default=func.now())
    last_accessed = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    # Relationship back to responses (optional but can be useful)
    # responses = relationship("QuestionResponse", back_populates="cached_question")
