from sqlalchemy.orm import Session, sessionmaker, joinedload
from sqlalchemy import create_engine, select
from .models import User, Subject, UserSubject, ExamResult, PaperCache
from src.utils.db import engine, Session, get_db_session
from src.utils.hardware_identifier import HardwareIdentifier
from src.core.queue_manager import QueueManager, QueuePriority
from typing import Dict, List, Optional
from datetime import datetime
import os
import tempfile
import logging

class UserOperations:
    @staticmethod
    def create_user(user_data: dict):
        """Create or update a user in the database"""
        logger = logging.getLogger(__name__)
        
        # Get hardware ID
        hardware_id_info = HardwareIdentifier.get_hardware_id()
        hardware_id = hardware_id_info[0] if hardware_id_info else "default-id"
        
        logger.info(f"Creating/updating user with hardware ID: {hardware_id}")
        
        # Add hardware_id to user_data
        user_data['hardware_id'] = hardware_id
        
        with get_db_session() as session:
            try:
                # Check if user already exists with this hardware ID
                existing_user = session.query(User).filter_by(hardware_id=hardware_id).first()
                
                # If no user with this hardware ID, check if we have any user (might be first run after ID change)
                if not existing_user:
                    existing_user = session.query(User).first()
                    if existing_user:
                        logger.info(f"Found existing user with different hardware ID. Updating ID from {existing_user.hardware_id} to {hardware_id}")
                
                if existing_user:
                    # Update existing user
                    for key, value in user_data.items():
                        setattr(existing_user, key, value)
                    user = existing_user
                    logger.info(f"Updated existing user: {user.full_name} (ID: {user.id})")
                else:
                    # Create new user
                    user = User(**user_data)
                    session.add(user)
                    logger.info(f"Created new user with data: {user_data}")
                
                # Commit changes directly here (don't rely on context manager in this case)
                session.commit()
                logger.info("User data committed to database")
                
                # Return the user directly rather than calling get_current_user again
                return user
                
            except Exception as e:
                logger.error(f"Error creating user: {e}", exc_info=True)
                session.rollback()
                return None

    @staticmethod
    def get_current_user():
        """Get the current user based on hardware ID, with fallback to first user"""
        from src.utils.hardware_identifier import HardwareIdentifier
        from src.utils.db import get_db_session
        from src.data.database.models import User
        
        logger = logging.getLogger(__name__)
        
        try:
            # Get the current hardware ID
            hardware_id_info = HardwareIdentifier.get_hardware_id()
            hardware_id = hardware_id_info[0] if hardware_id_info else None
            
            with get_db_session() as session:
                # Try to find user by hardware ID first
                if hardware_id:
                    logger.debug(f"Looking for user with hardware ID: {hardware_id}")
                    user = session.query(User).filter(User.hardware_id == hardware_id).first()
                    
                    if user:
                        logger.info(f"Found user by hardware ID: {user.full_name} (ID: {user.id})")
                        # Create a simple dictionary with all the attributes we need
                        user_dict = {
                            'id': user.id,
                            'full_name': user.full_name,
                            'hardware_id': user.hardware_id,
                            'country': user.country,
                            'school_level': user.school_level,
                            'grade': user.grade
                        }
                        return user_dict
                    
                    logger.warning(f"No user found for hardware ID: {hardware_id}, falling back to first user")
                
                # Fallback: Get the first user in the database (most apps will only have one user)
                fallback_user = session.query(User).first()
                
                if fallback_user:
                    logger.info(f"Using fallback user: {fallback_user.full_name} (ID: {fallback_user.id})")
                    
                    # Optional: Update the hardware ID to prevent future mismatches
                    if hardware_id and fallback_user.hardware_id != hardware_id:
                        logger.info(f"Updating user's hardware ID from {fallback_user.hardware_id} to {hardware_id}")
                        fallback_user.hardware_id = hardware_id
                    
                    # Create a simple dictionary with all the attributes we need
                    user_dict = {
                        'id': fallback_user.id,
                        'full_name': fallback_user.full_name,
                        'hardware_id': fallback_user.hardware_id,
                        'country': fallback_user.country,
                        'school_level': fallback_user.school_level,
                        'grade': fallback_user.grade
                    }
                    return user_dict
                
                logger.warning("No users found in database")
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving current user: {e}", exc_info=True)
            return None

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
        """Update the level selections for a user's subject"""
        print(f"\nUpdating subject levels:")
        print(f"User ID: {user_id}")
        print(f"Subject: {subject_name}")
        print(f"Levels to set: {levels}")
        
        with Session() as session:
            try:
                # Find the user-subject association
                user_subject = session.query(UserSubject)\
                    .join(Subject)\
                    .filter(
                        UserSubject.user_id == user_id,
                        Subject.name == subject_name
                    ).first()
                
                print(f"Found user_subject: {user_subject is not None}")
                
                if user_subject:
                    # Update only the provided levels
                    for level, value in levels.items():
                        if hasattr(user_subject, level):
                            print(f"Setting {level} to {value}")
                            setattr(user_subject, level, value)
                    
                    session.commit()
                    print("Changes committed successfully")
                    return True
                print("No user_subject found!")
                return False
            except Exception as e:
                print(f"Error updating subject levels: {e}")
                session.rollback()
                return False

    @staticmethod
    def get_user_subjects(user_id: int) -> List[Dict]:
        """
        Get a user's selected subjects with their levels
        
        Args:
            user_id: The user ID
            
        Returns:
            List of dictionaries with subject name and level selections
        """
        from src.utils.db import get_db_session
        from src.data.database.models import UserSubject, Subject
        
        try:
            with get_db_session() as session:
                # Query to join UserSubject with Subject to get names
                user_subjects = session.query(
                    UserSubject, Subject
                ).join(
                    Subject, UserSubject.subject_id == Subject.id
                ).filter(
                    UserSubject.user_id == user_id
                ).all()
                
                # No subjects found
                if not user_subjects:
                    logging.info(f"No subjects found for user {user_id}")
                    return []
                
                # Format results
                results = []
                for user_subject, subject in user_subjects:
                    # Create levels dictionary
                    levels = {
                        'grade_7': user_subject.grade_7,
                        'o_level': user_subject.o_level,
                        'a_level': user_subject.a_level
                    }
                    
                    # Add to results
                    results.append({
                        'id': user_subject.id,
                        'name': subject.name,
                        'levels': levels
                    })
                
                logging.info(f"Found {len(results)} subjects for user {user_id}")
                return results
                
        except Exception as e:
            logging.error(f"Error retrieving user subjects: {e}")
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
                    # Delete the user-subject association
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

    @staticmethod
    def get_subject_name(subject_id):
        """Get subject name by ID"""
        with Session() as session:
            subject = session.query(Subject).get(subject_id)
            return subject.name if subject else None

class PaperCacheOperations:
    @staticmethod
    def store_paper(user_subject_id: int, year: int, content: bytes) -> bool:
        """Store a new paper in the cache"""
        with get_db_session() as session:
            try:
                cache_entry = PaperCache(
                    user_subject_id=user_subject_id,
                    year=year,
                    paper_content=content,
                    last_accessed=datetime.now()
                )
                session.add(cache_entry)
                session.commit()
                return True
            except Exception as e:
                print(f"Error storing paper: {e}")
                session.rollback()
                return False

    @staticmethod
    def get_paper(user_subject_id: int, year: int) -> Optional[bytes]:
        """Retrieve a paper from cache"""
        with get_db_session() as session:
            try:
                cache_entry = session.query(PaperCache).filter_by(
                    user_subject_id=user_subject_id,
                    year=year
                ).first()
                
                if cache_entry:
                    # Update last accessed time
                    cache_entry.last_accessed = datetime.now()
                    session.commit()
                    return cache_entry.paper_content
                return None
            except Exception as e:
                print(f"Error retrieving paper: {e}")
                return None

    @staticmethod
    def mark_completed(user_subject_id: int, year: int) -> bool:
        """Mark a paper as completed"""
        with get_db_session() as session:
            try:
                cache_entry = session.query(PaperCache).filter_by(
                    user_subject_id=user_subject_id,
                    year=year
                ).first()
                
                if cache_entry:
                    cache_entry.is_completed = True
                    session.commit()
                    return True
                return False
            except Exception as e:
                print(f"Error marking paper as completed: {e}")
                return False

    @staticmethod
    def invalidate_completed_papers(user_id: int, max_papers_to_keep: int = 10) -> List[int]:
        """
        Invalidate (mark for removal) completed papers when needed
        
        Args:
            user_id: The user's ID
            max_papers_to_keep: Maximum number of papers to keep per subject/level
            
        Returns:
            List of invalidated paper IDs
        """
        invalidated_papers = []
        
        with get_db_session() as session:
            try:
                # Get all user subjects
                user_subjects = session.query(UserSubject).filter_by(user_id=user_id).all()
                
                for user_subject in user_subjects:
                    # For each subject, get all completed papers
                    completed_papers = session.query(PaperCache).filter_by(
                        user_subject_id=user_subject.id,
                        is_completed=True
                    ).order_by(PaperCache.last_accessed).all()
                    
                    # If we have more completed papers than our limit, remove the oldest accessed ones
                    if len(completed_papers) > max_papers_to_keep:
                        # Papers to remove (oldest accessed first)
                        papers_to_remove = completed_papers[:-max_papers_to_keep]
                        
                        for paper in papers_to_remove:
                            # Delete the paper content to free up space
                            paper.paper_content = None
                            invalidated_papers.append(paper.id)
                        
                        session.commit()
                
                return invalidated_papers
                
            except Exception as e:
                print(f"Error invalidating completed papers: {e}")
                session.rollback()
                return []

    @staticmethod
    def get_papers_to_download(user_id: int, papers_per_subject: int = 5) -> List[Dict]:
        """
        Determine which papers need to be downloaded based on completion status
        
        Args:
            user_id: The user's ID
            papers_per_subject: Target number of papers to maintain per subject/level
            
        Returns:
            List of dictionaries with subject_id, level, and year to download
        """
        papers_to_download = []
        
        with get_db_session() as session:
            try:
                # Get all user subjects
                user_subjects = session.query(UserSubject).filter_by(user_id=user_id).all()
                
                for user_subject in user_subjects:
                    # Check which levels are enabled
                    levels = []
                    if user_subject.grade_7:
                        levels.append('grade_7')
                    if user_subject.o_level:
                        levels.append('o_level')
                    if user_subject.a_level:
                        levels.append('a_level')
                    
                    for level in levels:
                        # Count active (non-completed) papers for this subject/level
                        active_papers = session.query(PaperCache).filter_by(
                            user_subject_id=user_subject.id,
                            is_completed=False
                        ).count()
                        
                        # If we have fewer active papers than our target, request more
                        papers_needed = max(0, papers_per_subject - active_papers)
                        
                        if papers_needed > 0:
                            # Get the most recent year we have
                            latest_paper = session.query(PaperCache).filter_by(
                                user_subject_id=user_subject.id
                            ).order_by(PaperCache.year.desc()).first()
                            
                            # Start from current year if no papers exist
                            start_year = datetime.now().year
                            if latest_paper:
                                # Start from the year after our most recent paper
                                start_year = latest_paper.year + 1
                            
                            # Add papers to download list
                            for i in range(papers_needed):
                                papers_to_download.append({
                                    'user_subject_id': user_subject.id,
                                    'level': level,
                                    'year': start_year - i,  # Get recent years first
                                    'subject_name': UserOperations.get_subject_name(user_subject.subject_id)
                                })
                
                return papers_to_download
                
            except Exception as e:
                print(f"Error determining papers to download: {e}")
                return []

    @staticmethod
    def cleanup_cache(threshold_mb: int = 100) -> bool:
        """
        Clean up cache when storage is running low
        
        Args:
            threshold_mb: Threshold in MB to trigger cleanup
            
        Returns:
            True if cleanup was performed, False otherwise
        """
        with get_db_session() as session:
            try:
                # Check available disk space
                stats = os.statvfs(tempfile.gettempdir())
                free_space_mb = (stats.f_bavail * stats.f_frsize) / (1024 * 1024)
                
                # If we're below threshold, clean up completed papers
                if free_space_mb < threshold_mb:
                    # Get all completed papers, ordered by last accessed (oldest first)
                    completed_papers = session.query(PaperCache).filter_by(
                        is_completed=True
                    ).order_by(PaperCache.last_accessed).limit(50).all()
                    
                    for paper in completed_papers:
                        # Remove paper content to free up space
                        paper.paper_content = None
                    
                    session.commit()
                    return True
                
                return False
                
            except Exception as e:
                print(f"Error cleaning up cache: {e}")
                session.rollback()
                return False
