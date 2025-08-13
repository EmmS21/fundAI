"""
The Engineer AI Tutor - Database Models
Programming and engineering education focused data models
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, 
    JSON, ForeignKey, Float, Enum as SQLEnum
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum

Base = declarative_base()

class DifficultyLevel(enum.Enum):
    """Engineering difficulty levels"""
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"
    STAFF = "staff"

class ProgrammingLanguage(enum.Enum):
    """Supported programming languages"""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    JAVA = "java"
    CPP = "cpp"
    GO = "go"
    RUST = "rust"
    TYPESCRIPT = "typescript"

class EngineeringDomain(enum.Enum):
    """Engineering specialization domains"""
    SOFTWARE = "software"
    DATA = "data"
    SYSTEMS = "systems"
    SECURITY = "security"
    FRONTEND = "frontend"
    BACKEND = "backend"
    FULLSTACK = "fullstack"

class User(Base):
    """User model for The Engineer AI Tutor"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    
    # Engineering profile
    current_level = Column(SQLEnum(DifficultyLevel), default=DifficultyLevel.JUNIOR)
    target_level = Column(SQLEnum(DifficultyLevel), default=DifficultyLevel.MID)
    primary_domain = Column(SQLEnum(EngineeringDomain), default=EngineeringDomain.SOFTWARE)
    preferred_languages = Column(JSON, default=list)  # List of programming languages
    
    # Progress tracking
    total_problems_solved = Column(Integer, default=0)
    problems_by_difficulty = Column(JSON, default=dict)  # {difficulty: count}
    current_streak = Column(Integer, default=0)
    best_streak = Column(Integer, default=0)
    
    # Assessment results
    initial_assessment_score = Column(Float, nullable=True)
    current_skill_level = Column(Float, default=0.0)  # 0-100 skill rating
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    submissions = relationship("Submission", back_populates="user")
    assessments = relationship("Assessment", back_populates="user")

class ProblemCategory(Base):
    """Categories for organizing programming problems"""
    __tablename__ = "problem_categories"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    domain = Column(SQLEnum(EngineeringDomain), nullable=False)
    
    # Relationships
    problems = relationship("Problem", back_populates="category")

class Problem(Base):
    """Programming problems and challenges"""
    __tablename__ = "problems"
    
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    
    # Problem metadata
    difficulty = Column(SQLEnum(DifficultyLevel), nullable=False)
    primary_language = Column(SQLEnum(ProgrammingLanguage), nullable=False)
    supported_languages = Column(JSON, default=list)  # Multiple language support
    domain = Column(SQLEnum(EngineeringDomain), nullable=False)
    
    # Problem content
    problem_statement = Column(Text, nullable=False)
    constraints = Column(Text)
    examples = Column(JSON, default=list)  # Input/output examples
    hints = Column(JSON, default=list)  # Progressive hints
    
    # Solution data
    expected_solution = Column(Text)  # Reference solution
    test_cases = Column(JSON, default=list)  # Test cases for validation
    time_complexity = Column(String(50))  # Expected time complexity
    space_complexity = Column(String(50))  # Expected space complexity
    
    # Tagging and organization
    topics = Column(JSON, default=list)  # Algorithm/concept tags
    skills_assessed = Column(JSON, default=list)  # Skills this problem tests
    
    # Metadata
    created_by = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Analytics
    total_attempts = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)
    average_completion_time = Column(Integer, default=0)  # in seconds
    
    # Foreign keys
    category_id = Column(Integer, ForeignKey("problem_categories.id"))
    
    # Relationships
    category = relationship("ProblemCategory", back_populates="problems")
    submissions = relationship("Submission", back_populates="problem")

class Submission(Base):
    """Code submissions for problems"""
    __tablename__ = "submissions"
    
    id = Column(Integer, primary_key=True)
    
    # Submission content
    code = Column(Text, nullable=False)
    language = Column(SQLEnum(ProgrammingLanguage), nullable=False)
    approach_description = Column(Text)  # Student's explanation of their approach
    
    # Execution results
    is_correct = Column(Boolean, default=False)
    passed_test_cases = Column(Integer, default=0)
    total_test_cases = Column(Integer, default=0)
    execution_time = Column(Float)  # Execution time in seconds
    memory_usage = Column(Float)  # Memory usage in MB
    
    # AI evaluation results
    ai_grade = Column(Float)  # 0-10 grade from AI
    code_quality_score = Column(Float)  # 0-10 code quality
    efficiency_score = Column(Float)  # 0-10 efficiency
    ai_feedback = Column(JSON)  # Structured AI feedback
    raw_ai_response = Column(Text)  # Raw AI response for debugging
    
    # Metadata
    submitted_at = Column(DateTime, default=datetime.utcnow)
    evaluation_completed_at = Column(DateTime)
    time_spent = Column(Integer)  # Time spent coding in seconds
    
    # Foreign keys
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    problem_id = Column(Integer, ForeignKey("problems.id"), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="submissions")
    problem = relationship("Problem", back_populates="submissions")

class Assessment(Base):
    """Initial and periodic skill assessments"""
    __tablename__ = "assessments"
    
    id = Column(Integer, primary_key=True)
    assessment_type = Column(String(50), nullable=False)  # 'initial', 'periodic', 'domain_specific'
    
    # Assessment configuration
    target_level = Column(SQLEnum(DifficultyLevel), nullable=False)
    domain = Column(SQLEnum(EngineeringDomain), nullable=False)
    language = Column(SQLEnum(ProgrammingLanguage), nullable=False)
    
    # Problems included
    problem_ids = Column(JSON, default=list)  # List of problem IDs
    total_problems = Column(Integer, default=0)
    
    # Results
    problems_attempted = Column(Integer, default=0)
    problems_solved = Column(Integer, default=0)
    total_score = Column(Float, default=0.0)
    time_taken = Column(Integer, default=0)  # Total time in seconds
    
    # Skill breakdown
    algorithm_score = Column(Float, default=0.0)
    data_structure_score = Column(Float, default=0.0)
    code_quality_score = Column(Float, default=0.0)
    system_design_score = Column(Float, default=0.0)
    
    # Recommendations
    recommended_level = Column(SQLEnum(DifficultyLevel))
    focus_areas = Column(JSON, default=list)  # Areas needing improvement
    study_plan = Column(JSON, default=dict)  # Suggested learning path
    
    # Metadata
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    is_completed = Column(Boolean, default=False)
    
    # Foreign keys
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="assessments")

class CodeAnalysis(Base):
    """Detailed code analysis results"""
    __tablename__ = "code_analysis"
    
    id = Column(Integer, primary_key=True)
    
    # Analysis metadata
    analysis_type = Column(String(50), nullable=False)  # 'submission', 'review', 'optimization'
    language = Column(SQLEnum(ProgrammingLanguage), nullable=False)
    code_snippet = Column(Text, nullable=False)
    
    # Complexity analysis
    time_complexity = Column(String(50))
    space_complexity = Column(String(50))
    cyclomatic_complexity = Column(Integer)
    
    # Quality metrics
    readability_score = Column(Float, default=0.0)
    maintainability_score = Column(Float, default=0.0)
    testability_score = Column(Float, default=0.0)
    
    # Code issues
    syntax_errors = Column(JSON, default=list)
    logical_errors = Column(JSON, default=list)
    style_violations = Column(JSON, default=list)
    security_issues = Column(JSON, default=list)
    performance_issues = Column(JSON, default=list)
    
    # Suggestions
    optimization_suggestions = Column(JSON, default=list)
    refactoring_suggestions = Column(JSON, default=list)
    alternative_approaches = Column(JSON, default=list)
    
    # Pattern recognition
    design_patterns_used = Column(JSON, default=list)
    anti_patterns_detected = Column(JSON, default=list)
    
    # Metadata
    analyzed_at = Column(DateTime, default=datetime.utcnow)
    analyzer_version = Column(String(20))
    
    # Foreign keys (optional - can be standalone analysis)
    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

class LearningPath(Base):
    """Personalized learning paths for users"""
    __tablename__ = "learning_paths"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    
    # Path configuration
    target_level = Column(SQLEnum(DifficultyLevel), nullable=False)
    domain = Column(SQLEnum(EngineeringDomain), nullable=False)
    estimated_duration = Column(Integer)  # Estimated duration in days
    
    # Content structure
    modules = Column(JSON, default=list)  # List of learning modules
    problem_sequence = Column(JSON, default=list)  # Ordered problem IDs
    milestones = Column(JSON, default=list)  # Progress checkpoints
    
    # Prerequisites and outcomes
    prerequisites = Column(JSON, default=list)  # Required skills/knowledge
    learning_outcomes = Column(JSON, default=list)  # Skills gained
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Foreign keys
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

class UserProgress(Base):
    """Track user progress through learning paths and topics"""
    __tablename__ = "user_progress"
    
    id = Column(Integer, primary_key=True)
    
    # Progress tracking
    current_module = Column(Integer, default=0)
    completed_problems = Column(JSON, default=list)  # List of completed problem IDs
    current_problem_id = Column(Integer)
    
    # Performance metrics
    completion_percentage = Column(Float, default=0.0)
    average_score = Column(Float, default=0.0)
    time_invested = Column(Integer, default=0)  # Total time in seconds
    
    # Streak and consistency
    current_streak = Column(Integer, default=0)
    last_activity = Column(DateTime, default=datetime.utcnow)
    
    # Metadata
    started_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Foreign keys
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    path_id = Column(Integer, ForeignKey("learning_paths.id"), nullable=False)

class Project(Base):
    """AI-generated projects for hands-on learning"""
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    
    # Project configuration
    language = Column(String(50), nullable=False)  # Programming language
    difficulty_level = Column(SQLEnum(DifficultyLevel), nullable=False)
    domain = Column(SQLEnum(EngineeringDomain), nullable=False)
    
    # AI-generated content
    project_description = Column(Text, nullable=False)  
    task_headers = Column(Text)  
    
    # Project status
    status = Column(String(50), default='active')  
    current_task_number = Column(Integer, default=1)
    total_tasks = Column(Integer, default=4)
    
    # User progress
    progress_percentage = Column(Float, default=0.0)
    time_spent = Column(Integer, default=0)  # Time spent in seconds
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_accessed = Column(DateTime, default=datetime.utcnow)
    
    # User context from assessment
    user_scores = Column(JSON, default=dict)  # Assessment scores when project was created
    
    # Foreign keys
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Relationships
    tasks = relationship("ProjectTask", back_populates="project", cascade="all, delete-orphan")

class ProjectTask(Base):
    """Individual tasks within AI-generated projects"""
    __tablename__ = "project_tasks"
    
    id = Column(Integer, primary_key=True)
    task_number = Column(Integer, nullable=False)
    title = Column(String(200), nullable=False)
    
    # AI-generated task content
    task_content = Column(Text)  # Detailed task instructions from AI
    
    # Task status
    status = Column(String(50), default='pending')  # pending, in_progress, completed, skipped
    
    # Progress tracking
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    time_spent = Column(Integer, default=0)  # Time spent on this task in seconds
    
    # User work tracking
    notes = Column(Text)  # User's notes about this task
    cursor_evaluations = Column(JSON, default=list)  # Cursor AI evaluations
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Foreign keys
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    
    # Relationships
    project = relationship("Project", back_populates="tasks")

def create_tables(engine):
    """Create all database tables"""
    Base.metadata.create_all(engine)

def get_model_by_name(model_name: str):
    """Get model class by name"""
    models = {
        'User': User,
        'Problem': Problem,
        'ProblemCategory': ProblemCategory,
        'Submission': Submission,
        'Assessment': Assessment,
        'CodeAnalysis': CodeAnalysis,
        'LearningPath': LearningPath,
        'UserProgress': UserProgress,
    }
    return models.get(model_name) 