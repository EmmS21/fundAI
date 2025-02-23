from sqlalchemy.orm import Session, sessionmaker, joinedload
from sqlalchemy import create_engine, select
from .models import User, Subject, UserSubject, ExamResult
from src.utils.db import engine, Session, get_db_session
from src.utils.hardware_identifier import HardwareIdentifier
from src.core.queue_manager import QueueManager, QueuePriority
from typing import Dict, List, Optional

class UserOperations:
    @staticmethod
    def create_user(user_data: dict):
        # Get hardware ID
        hardware_id = HardwareIdentifier.get_hardware_id()[0]
        
        # Add hardware_id to user_data
        user_data['hardware_id'] = hardware_id
        
        with get_db_session() as session:
            try:
                # Check if user already exists
                existing_user = session.query(User).filter_by(hardware_id=hardware_id).first()
                
                if existing_user:
                    # Update existing user
                    for key, value in user_data.items():
                        setattr(existing_user, key, value)
                    user = existing_user
                else:
                    # Create new user
                    user = User(**user_data)
                    session.add(user)
                
                session.commit()
                
                # Refresh the user object with a new session
                return UserOperations.get_current_user()  # This will return a fresh, session-bound user
                
            except Exception as e:
                print(f"Error creating user: {e}")
                session.rollback()
                return None

    @staticmethod
    def get_current_user():
        """Get current user based on hardware ID"""
        with Session() as session:
            # Get hardware ID from system
            hardware_id = HardwareIdentifier.get_hardware_id()[0]
            
            # Query user with subjects relationship loaded
            user = session.query(User).options(
                joinedload(User.subjects)
            ).filter_by(hardware_id=hardware_id).first()
            
            return user

    @classmethod
    def update_user_profile_picture(cls, user_id: str, image_data: bytes):
        with Session() as session:  # Now Session knows which database to connect to
            user = session.query(User).filter(User.id == user_id).first()
            if user:
                user.profile_picture = image_data
                session.commit()

    @classmethod
    def update_field(cls, user_id: str, field_name: str, value: str):
        with get_db_session() as session:
            user = session.query(User).filter(User.id == user_id).first()
            if user:
                setattr(user, field_name, value)
                session.commit()

    @staticmethod
    def add_subject(user_id: int, subject_name: str, levels: Dict[str, bool] = None) -> bool:
        """
        Add a subject to a user's profile with optional level selections
        
        Args:
            user_id: The user's ID
            subject_name: Name of the subject
            levels: Dictionary containing level selections e.g.
                   {'grade_7': True, 'o_level': False, 'a_level': True}
        """
        if levels is None:
            levels = {'grade_7': False, 'o_level': False, 'a_level': False}
            
        with Session() as session:
            try:
                # Get or create the subject
                subject = session.query(Subject).filter_by(name=subject_name).first()
                if not subject:
                    subject = Subject(name=subject_name)
                    session.add(subject)
                    session.flush()  # Get the subject ID
                
                # Create user-subject association with level selections
                user_subject = UserSubject(
                    user_id=user_id,
                    subject_id=subject.id,
                    grade_7=levels.get('grade_7', False),
                    o_level=levels.get('o_level', False),
                    a_level=levels.get('a_level', False)
                )
                session.add(user_subject)
                session.commit()
                return True
            except Exception as e:
                print(f"Error adding subject: {e}")
                session.rollback()
                return False

    @staticmethod
    def update_subject_levels(user_id: int, subject_name: str, levels: Dict[str, bool]) -> bool:
        """
        Update the level selections for a user's subject
        
        Args:
            user_id: The user's ID
            subject_name: Name of the subject
            levels: Dictionary containing level selections to update
        """
        with Session() as session:
            try:
                # Find the user-subject association
                user_subject = session.query(UserSubject)\
                    .join(Subject)\
                    .filter(
                        UserSubject.user_id == user_id,
                        Subject.name == subject_name
                    ).first()
                
                if user_subject:
                    # Update only the provided levels
                    for level, value in levels.items():
                        if hasattr(user_subject, level):
                            setattr(user_subject, level, value)
                    
                    session.commit()
                    return True
                return False
            except Exception as e:
                print(f"Error updating subject levels: {e}")
                session.rollback()
                return False

    @staticmethod
    def get_user_subjects(user_id: int) -> List[Dict]:
        """
        Get all subjects and their level selections for a user
        
        Returns:
            List of dictionaries containing subject info and level selections
        """
        with Session() as session:
            try:
                results = session.query(
                    Subject.name,
                    UserSubject.grade_7,
                    UserSubject.o_level,
                    UserSubject.a_level,
                    UserSubject.created_at
                ).join(UserSubject)\
                 .filter(UserSubject.user_id == user_id)\
                 .all()
                
                return [
                    {
                        'name': r.name,
                        'levels': {
                            'grade_7': r.grade_7,
                            'o_level': r.o_level,
                            'a_level': r.a_level
                        },
                        'created_at': r.created_at
                    }
                    for r in results
                ]
            except Exception as e:
                print(f"Error getting subjects: {e}")
                return []

    @staticmethod
    def remove_subject(user_id: int, subject_name: str) -> bool:
        """Remove a subject from a user's profile"""
        with Session() as session:
            try:
                # Find and remove the user-subject association
                user_subject = session.query(UserSubject)\
                    .join(Subject)\
                    .filter(
                        UserSubject.user_id == user_id,
                        Subject.name == subject_name
                    ).first()
                
                if user_subject:
                    # Check for related exam results
                    exam_results = session.query(ExamResult)\
                        .filter(ExamResult.user_subject_id == user_subject.id)\
                        .all()
                    
                    # Delete related exam results first
                    for result in exam_results:
                        session.delete(result)
                    
                    # Then delete the user-subject association
                    session.delete(user_subject)
                    session.commit()
                    return True
                return False
            except Exception as e:
                print(f"Error removing subject: {e}")
                session.rollback()
                return False

    @staticmethod
    def get_subject_levels(user_id: int, subject_name: str) -> Optional[Dict[str, bool]]:
        """Get level selections for a specific subject"""
        with Session() as session:
            try:
                result = session.query(
                    UserSubject.grade_7,
                    UserSubject.o_level,
                    UserSubject.a_level
                ).join(Subject)\
                 .filter(
                     UserSubject.user_id == user_id,
                     Subject.name == subject_name
                 ).first()
                
                if result:
                    return {
                        'grade_7': result.grade_7,
                        'o_level': result.o_level,
                        'a_level': result.a_level
                    }
                return None
            except Exception as e:
                print(f"Error getting subject levels: {e}")
                return None
