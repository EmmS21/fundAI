"""
The Engineer AI Tutor - Database Operations
CRUD operations and specialized queries for programming education
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy import create_engine, and_, or_, func, desc
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError

from .models import (
    Base, User, Problem, ProblemCategory, Submission, Assessment,
    CodeAnalysis, LearningPath, UserProgress,
    DifficultyLevel, ProgrammingLanguage, EngineeringDomain
)
from ...config.settings import DATABASE_CONFIG

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages database connections and operations for The Engineer"""
    
    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize database connection and create tables"""
        try:
            self.engine = create_engine(
                DATABASE_CONFIG["url"],
                echo=DATABASE_CONFIG["echo"],
                pool_pre_ping=DATABASE_CONFIG["pool_pre_ping"],
            )
            
            # Create tables
            Base.metadata.create_all(self.engine)
            
            # Create session factory
            self.SessionLocal = sessionmaker(bind=self.engine)
            
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def get_session(self) -> Session:
        """Get a database session"""
        return self.SessionLocal()
    
    def close_session(self, session: Session):
        """Close a database session"""
        try:
            session.close()
        except Exception as e:
            logger.error(f"Error closing session: {e}")

class UserOperations:
    """User-related database operations"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def create_user(self, username: str, email: str, **kwargs) -> Optional[User]:
        """Create a new user"""
        session = self.db.get_session()
        try:
            user = User(
                username=username,
                email=email,
                **kwargs
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            
            logger.info(f"Created user: {username}")
            return user
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Failed to create user {username}: {e}")
            return None
        finally:
            self.db.close_session(session)
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        session = self.db.get_session()
        try:
            user = session.query(User).filter(User.username == username).first()
            return user
        except SQLAlchemyError as e:
            logger.error(f"Failed to get user {username}: {e}")
            return None
        finally:
            self.db.close_session(session)
    
    def update_user_progress(self, user_id: int, problems_solved: int = None, 
                           current_streak: int = None, skill_level: float = None) -> bool:
        """Update user progress metrics"""
        session = self.db.get_session()
        try:
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                return False
            
            if problems_solved is not None:
                user.total_problems_solved = problems_solved
            
            if current_streak is not None:
                user.current_streak = current_streak
                if current_streak > user.best_streak:
                    user.best_streak = current_streak
            
            if skill_level is not None:
                user.current_skill_level = skill_level
            
            user.last_active = datetime.utcnow()
            session.commit()
            
            logger.info(f"Updated progress for user {user_id}")
            return True
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Failed to update user progress: {e}")
            return False
        finally:
            self.db.close_session(session)

class ProblemOperations:
    """Problem-related database operations"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def create_problem(self, title: str, description: str, difficulty: DifficultyLevel,
                      language: ProgrammingLanguage, domain: EngineeringDomain, **kwargs) -> Optional[Problem]:
        """Create a new programming problem"""
        session = self.db.get_session()
        try:
            problem = Problem(
                title=title,
                description=description,
                difficulty=difficulty,
                primary_language=language,
                domain=domain,
                **kwargs
            )
            session.add(problem)
            session.commit()
            session.refresh(problem)
            
            logger.info(f"Created problem: {title}")
            return problem
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Failed to create problem {title}: {e}")
            return None
        finally:
            self.db.close_session(session)
    
    def get_problems_by_difficulty(self, difficulty: DifficultyLevel, 
                                  language: ProgrammingLanguage = None,
                                  domain: EngineeringDomain = None,
                                  limit: int = 10) -> List[Problem]:
        """Get problems filtered by difficulty and optional criteria"""
        session = self.db.get_session()
        try:
            query = session.query(Problem).filter(
                and_(
                    Problem.difficulty == difficulty,
                    Problem.is_active == True
                )
            )
            
            if language:
                query = query.filter(Problem.primary_language == language)
            
            if domain:
                query = query.filter(Problem.domain == domain)
            
            problems = query.limit(limit).all()
            return problems
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get problems by difficulty: {e}")
            return []
        finally:
            self.db.close_session(session)
    
    def get_recommended_problems(self, user_id: int, count: int = 5) -> List[Problem]:
        """Get recommended problems based on user's skill level and progress"""
        session = self.db.get_session()
        try:
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                return []
            
            # Get problems slightly above user's current level
            target_difficulties = [user.current_level]
            if user.current_level != DifficultyLevel.STAFF:
                # Include next difficulty level
                levels = list(DifficultyLevel)
                current_index = levels.index(user.current_level)
                if current_index < len(levels) - 1:
                    target_difficulties.append(levels[current_index + 1])
            
            # Get problems user hasn't solved yet
            solved_problem_ids = session.query(Submission.problem_id).filter(
                and_(
                    Submission.user_id == user_id,
                    Submission.is_correct == True
                )
            ).subquery()
            
            problems = session.query(Problem).filter(
                and_(
                    Problem.difficulty.in_(target_difficulties),
                    Problem.domain == user.primary_domain,
                    Problem.is_active == True,
                    ~Problem.id.in_(solved_problem_ids)
                )
            ).limit(count).all()
            
            return problems
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get recommended problems: {e}")
            return []
        finally:
            self.db.close_session(session)
    
    def update_problem_analytics(self, problem_id: int, success: bool, completion_time: int):
        """Update problem analytics after a submission"""
        session = self.db.get_session()
        try:
            problem = session.query(Problem).filter(Problem.id == problem_id).first()
            if not problem:
                return False
            
            problem.total_attempts += 1
            
            if success:
                # Recalculate success rate
                successful_submissions = session.query(Submission).filter(
                    and_(
                        Submission.problem_id == problem_id,
                        Submission.is_correct == True
                    )
                ).count()
                
                problem.success_rate = successful_submissions / problem.total_attempts
            
            # Update average completion time
            if completion_time > 0:
                if problem.average_completion_time == 0:
                    problem.average_completion_time = completion_time
                else:
                    # Weighted average
                    problem.average_completion_time = (
                        (problem.average_completion_time * (problem.total_attempts - 1) + completion_time) 
                        / problem.total_attempts
                    )
            
            session.commit()
            return True
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Failed to update problem analytics: {e}")
            return False
        finally:
            self.db.close_session(session)

class SubmissionOperations:
    """Submission-related database operations"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def create_submission(self, user_id: int, problem_id: int, code: str, 
                         language: ProgrammingLanguage, **kwargs) -> Optional[Submission]:
        """Create a new code submission"""
        session = self.db.get_session()
        try:
            submission = Submission(
                user_id=user_id,
                problem_id=problem_id,
                code=code,
                language=language,
                **kwargs
            )
            session.add(submission)
            session.commit()
            session.refresh(submission)
            
            logger.info(f"Created submission for user {user_id}, problem {problem_id}")
            return submission
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Failed to create submission: {e}")
            return None
        finally:
            self.db.close_session(session)
    
    def update_submission_results(self, submission_id: int, is_correct: bool,
                                 ai_feedback: Dict[str, Any], ai_grade: float,
                                 execution_results: Dict[str, Any] = None) -> bool:
        """Update submission with evaluation results"""
        session = self.db.get_session()
        try:
            submission = session.query(Submission).filter(Submission.id == submission_id).first()
            if not submission:
                return False
            
            submission.is_correct = is_correct
            submission.ai_feedback = ai_feedback
            submission.ai_grade = ai_grade
            submission.evaluation_completed_at = datetime.utcnow()
            
            if execution_results:
                submission.passed_test_cases = execution_results.get('passed_test_cases', 0)
                submission.total_test_cases = execution_results.get('total_test_cases', 0)
                submission.execution_time = execution_results.get('execution_time')
                submission.memory_usage = execution_results.get('memory_usage')
            
            # Extract specific scores from AI feedback
            if isinstance(ai_feedback, dict):
                submission.code_quality_score = self._extract_score(ai_feedback.get('Code Quality', ''))
                submission.efficiency_score = self._extract_score(ai_feedback.get('Efficiency', ''))
            
            session.commit()
            
            logger.info(f"Updated submission {submission_id} with results")
            return True
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Failed to update submission results: {e}")
            return False
        finally:
            self.db.close_session(session)
    
    def _extract_score(self, score_text: str) -> float:
        """Extract numeric score from text description"""
        score_mapping = {
            'Excellent': 10.0,
            'Good': 8.0,
            'Fair': 6.0,
            'Poor': 4.0,
        }
        
        for key, value in score_mapping.items():
            if key.lower() in score_text.lower():
                return value
        
        # Try to extract numeric score
        import re
        match = re.search(r'(\d+(?:\.\d+)?)', score_text)
        if match:
            return float(match.group(1))
        
        return 5.0  # Default score
    
    def get_user_submissions(self, user_id: int, limit: int = 50) -> List[Submission]:
        """Get recent submissions for a user"""
        session = self.db.get_session()
        try:
            submissions = session.query(Submission).filter(
                Submission.user_id == user_id
            ).order_by(desc(Submission.submitted_at)).limit(limit).all()
            
            return submissions
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get user submissions: {e}")
            return []
        finally:
            self.db.close_session(session)
    
    def get_submission_analytics(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """Get submission analytics for a user over specified days"""
        session = self.db.get_session()
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            submissions = session.query(Submission).filter(
                and_(
                    Submission.user_id == user_id,
                    Submission.submitted_at >= start_date
                )
            ).all()
            
            analytics = {
                'total_submissions': len(submissions),
                'successful_submissions': sum(1 for s in submissions if s.is_correct),
                'success_rate': 0.0,
                'average_grade': 0.0,
                'languages_used': set(),
                'problems_attempted': set(),
                'average_time_spent': 0.0,
            }
            
            if submissions:
                analytics['success_rate'] = analytics['successful_submissions'] / analytics['total_submissions'] * 100
                
                grades = [s.ai_grade for s in submissions if s.ai_grade is not None]
                if grades:
                    analytics['average_grade'] = sum(grades) / len(grades)
                
                for submission in submissions:
                    analytics['languages_used'].add(submission.language.value)
                    analytics['problems_attempted'].add(submission.problem_id)
                
                time_spent = [s.time_spent for s in submissions if s.time_spent is not None]
                if time_spent:
                    analytics['average_time_spent'] = sum(time_spent) / len(time_spent)
            
            # Convert sets to lists for JSON serialization
            analytics['languages_used'] = list(analytics['languages_used'])
            analytics['problems_attempted'] = list(analytics['problems_attempted'])
            
            return analytics
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get submission analytics: {e}")
            return {}
        finally:
            self.db.close_session(session)

class AssessmentOperations:
    """Assessment-related database operations"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def create_assessment(self, user_id: int, assessment_type: str,
                         target_level: DifficultyLevel, domain: EngineeringDomain,
                         language: ProgrammingLanguage, problem_ids: List[int]) -> Optional[Assessment]:
        """Create a new assessment"""
        session = self.db.get_session()
        try:
            assessment = Assessment(
                user_id=user_id,
                assessment_type=assessment_type,
                target_level=target_level,
                domain=domain,
                language=language,
                problem_ids=problem_ids,
                total_problems=len(problem_ids)
            )
            session.add(assessment)
            session.commit()
            session.refresh(assessment)
            
            logger.info(f"Created assessment for user {user_id}")
            return assessment
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Failed to create assessment: {e}")
            return None
        finally:
            self.db.close_session(session)
    
    def update_assessment_results(self, assessment_id: int, results: Dict[str, Any]) -> bool:
        """Update assessment with results"""
        session = self.db.get_session()
        try:
            assessment = session.query(Assessment).filter(Assessment.id == assessment_id).first()
            if not assessment:
                return False
            
            # Update basic results
            assessment.problems_attempted = results.get('problems_attempted', 0)
            assessment.problems_solved = results.get('problems_solved', 0)
            assessment.total_score = results.get('total_score', 0.0)
            assessment.time_taken = results.get('time_taken', 0)
            
            # Update skill breakdown
            assessment.algorithm_score = results.get('algorithm_score', 0.0)
            assessment.data_structure_score = results.get('data_structure_score', 0.0)
            assessment.code_quality_score = results.get('code_quality_score', 0.0)
            assessment.system_design_score = results.get('system_design_score', 0.0)
            
            # Update recommendations
            assessment.recommended_level = results.get('recommended_level')
            assessment.focus_areas = results.get('focus_areas', [])
            assessment.study_plan = results.get('study_plan', {})
            
            assessment.completed_at = datetime.utcnow()
            assessment.is_completed = True
            
            session.commit()
            
            logger.info(f"Updated assessment {assessment_id} with results")
            return True
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Failed to update assessment results: {e}")
            return False
        finally:
            self.db.close_session(session)

# Initialize global database manager
db_manager = DatabaseManager()

# Initialize operation handlers
user_ops = UserOperations(db_manager)
problem_ops = ProblemOperations(db_manager)
submission_ops = SubmissionOperations(db_manager)
assessment_ops = AssessmentOperations(db_manager) 