from sqlalchemy.orm import Session, sessionmaker, joinedload
from sqlalchemy import create_engine, select
from .models import User, Subject, UserSubject, ExamResult, PaperCache, CachedQuestion
from src.utils.db import engine, Session, get_db_session
from src.utils.hardware_identifier import HardwareIdentifier
from src.core.queue_manager import QueueManager, QueuePriority
from src.core.history.user_history_manager import UserHistoryManager, DB_PATH as STUDENT_PROFILE_DB_PATH
from typing import Dict, List, Optional
from datetime import datetime
import os
import tempfile
import logging
import sqlite3

# Define logger at the module level (preferred)
logger = logging.getLogger(__name__)

class UserOperations:
    """Operations for user management"""
    
    @staticmethod
    def get_current_user():
        """Get the current (and only) user in the system"""
        try:
            with get_db_session() as session:
                user = session.query(User).first()
                
                # If user exists, return as dictionary for compatibility
                if user:
                    return {
                        'id': user.id,
                        'full_name': user.full_name,
                        'hardware_id': user.hardware_id,
                        'country': user.country,
                        'school_level': user.school_level,
                        'grade': user.grade
                    }
                return None
        except Exception as e:
            logger.error(f"Error getting current user: {e}")
            return None
    
    @staticmethod
    def get_user_subjects() -> List[Dict]:
        """
        Get the current user's selected subjects with their levels
        
        Returns:
            List of dictionaries with subject name and level selections
        """        
        logger = logging.getLogger(__name__)
        
        try:
            # Get the current (and only) user directly
            with get_db_session() as session:
                # Get the current user first
                user = session.query(User).first()
                
                if not user:
                    logger.warning("No user found in database")
                    return []
                
                # Query to join UserSubject with Subject to get names
                user_subjects = session.query(
                    UserSubject, Subject
                ).join(
                    Subject, UserSubject.subject_id == Subject.id
                ).filter(
                    UserSubject.user_id == user.id
                ).all()
                
                # No subjects found
                if not user_subjects:
                    logger.info(f"No subjects found for user {user.id}")
                    return []
                
                # Format results as dictionaries before returning
                results = []
                for user_subject, subject in user_subjects:
                    # Create levels dictionary
                    levels = {
                        'grade_7': user_subject.grade_7,
                        'o_level': user_subject.o_level,
                        'a_level': user_subject.a_level
                    }
                    
                    # Add to results - include both id and subject_id for compatibility
                    results.append({
                        'id': user_subject.id,
                        'subject_id': user_subject.subject_id,
                        'name': subject.name,
                        'levels': levels
                    })
                
                logger.info(f"Found {len(results)} subjects for user {user.id}")
                return results
                
        except Exception as e:
            logger.error(f"Error retrieving user subjects: {e}", exc_info=True)
            return []
    
    @staticmethod
    def get_user_subject(subject_id, user_id=None):
        """
        Get a specific subject for the user
        The user_id parameter is kept for backward compatibility but is no longer used.
        """
        try:
            with get_db_session() as session:
                # Get the current user
                user = session.query(User).first()
                
                if not user:
                    return None
                
                # Get the specific subject
                subject = session.query(UserSubject).filter_by(
                    user_id=user.id, 
                    id=subject_id
                ).first()
                
                return subject
        except Exception as e:
            logger.error(f"Error getting user subject: {e}")
            return None
    
    @staticmethod
    def add_subject_for_user(subject_name, grade_7=False, o_level=False, a_level=False, user_id=None):
        """
        Add a subject for the user. Creates the Subject entry if it doesn't exist.
        The user_id parameter is kept for backward compatibility but is no longer used.
        """
        try:
            with get_db_session() as session:
                user = session.query(User).first()
                if not user:
                    logger.warning("Cannot add subject: No user found.")
                    return None

                # 1. Find the Subject ID from the name, OR CREATE IT
                subject_entry = session.query(Subject).filter_by(name=subject_name).first()

                if not subject_entry:
                    # Subject not found, create it!
                    logger.info(f"Subject '{subject_name}' not found in Subject table. Creating it now.")
                    new_subject = Subject(name=subject_name)
                    session.add(new_subject)
                    # We need to flush to get the ID without fully committing yet
                    session.flush()
                    # Check if flush worked and we got an ID
                    if new_subject.id is None:
                         logger.error(f"Failed to get ID for newly created subject '{subject_name}'. Rolling back.")
                         session.rollback() # Explicit rollback here before raising/returning
                         return None
                    target_subject_id = new_subject.id
                    logger.info(f"Created new subject '{subject_name}' with ID: {target_subject_id}")
                else:
                    # Subject already exists
                    target_subject_id = subject_entry.id
                    logger.debug(f"Subject '{subject_name}' found with ID: {target_subject_id}")


                # 2. Check if the UserSubject link already exists using IDs
                existing = session.query(UserSubject).filter_by(
                    user_id=user.id,
                    subject_id=target_subject_id
                ).first()

                if existing:
                    # Update existing subject levels (optional, maybe just return existing?)
                    logger.info(f"UserSubject link already exists for user {user.id} and subject ID {target_subject_id}. Updating levels.")
                    existing.grade_7 = grade_7
                    existing.o_level = o_level
                    existing.a_level = a_level
                    # No need to commit here, context manager handles it if successful
                    return existing # Return the existing UserSubject object

                # 3. Create new UserSubject entry using subject_id
                logger.info(f"Creating new UserSubject link for user {user.id} and subject ID {target_subject_id}.")
                user_subject = UserSubject(
                    user_id=user.id,
                    subject_id=target_subject_id,
                    grade_7=grade_7,
                    o_level=o_level,
                    a_level=a_level
                )
                session.add(user_subject)
                # Flush again to potentially get the UserSubject ID if needed later
                session.flush()
                logger.info(f"Successfully staged add for UserSubject link (ID: {user_subject.id})")
                # Return the newly created UserSubject object
                return user_subject

        except Exception as e:
            logger.error(f"Error adding subject link for user: {e}", exc_info=True)
            # Rollback is handled by the context manager on exception
            return None
    
    @staticmethod
    def update_subject_for_user(subject_id, subject_name=None, grade_7=None, 
                               o_level=None, a_level=None, user_id=None):
        """
        Update a subject for the user
        The user_id parameter is kept for backward compatibility but is no longer used.
        """
        try:
            with get_db_session() as session:
                # Get the current user
                user = session.query(User).first()
                
                if not user:
                    return False
                
                # Get the subject
                subject = session.query(UserSubject).filter_by(
                    id=subject_id,
                    user_id=user.id
                ).first()
                
                if not subject:
                    return False
                
                # Update fields if provided
                if subject_name is not None:
                    subject.name = subject_name
                if grade_7 is not None:
                    subject.grade_7 = grade_7
                if o_level is not None:
                    subject.o_level = o_level
                if a_level is not None:
                    subject.a_level = a_level
                
                session.commit()
                return True
        except Exception as e:
            logger.error(f"Error updating subject for user: {e}")
            return False
    
    @staticmethod
    def delete_subject_for_user(subject_id, user_id=None):
        """
        Delete a subject for the user
        The user_id parameter is kept for backward compatibility but is no longer used.
        """
        try:
            with get_db_session() as session:
                # Get the current user
                user = session.query(User).first()
                
                if not user:
                    return False
                
                # Find and delete the subject
                subject = session.query(UserSubject).filter_by(
                    id=subject_id,
                    user_id=user.id
                ).first()
                
                if subject:
                    session.delete(subject)
                    session.commit()
                    return True
                return False
        except Exception as e:
            logger.error(f"Error deleting subject for user: {e}")
            return False

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

    @staticmethod
    def get_performance_history(user_id: int) -> List[Dict]:
        """
        Fetch performance history for a given user directly from answer_history.
        NOTE: This version cannot filter by subject/level and lacks detailed paper info
              due to missing data in cached_questions table.

        Args:
            user_id: The ID of the current user.

        Returns:
            A list of dictionaries, each representing a past answer attempt with
            timestamp and report status. Returns an empty list on error.
        """
        logger.debug(f"Fetching *basic* performance history for user {user_id}")
        history = []

        conn = None
        try:
            conn = sqlite3.connect(STUDENT_PROFILE_DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Simplified query - only select from answer_history
            sql = """
                SELECT
                    ah.history_id,
                    ah.answer_timestamp,
                    ah.cloud_report_received,
                    ah.cached_question_id, -- This is now unique_question_key
                    cq.paper_document_id, -- Keep paper_document_id if needed
                    cq.question_number_str,
                    cq.subject,
                    cq.level,
                    cq.paper_year,
                    cq.topic,            -- Added topic
                    cq.subtopic,         -- Added subtopic
                    cq.content AS question_content, -- Added question content
                    cq.marks AS question_marks,     -- Added question marks
                    ah.user_answer_json, -- Added user's answer
                    ah.local_ai_grade,   -- Added local AI grade
                    ah.local_ai_rationale -- Added local AI rationale
                FROM
                    answer_history ah
                JOIN
                    cached_questions cq ON ah.cached_question_id = cq.unique_question_key
                WHERE
                    ah.user_id = ?
                ORDER BY
                    ah.answer_timestamp DESC;
            """

            params = [user_id]
            logger.debug(f"Executing SQL: {sql} with params: {params}")
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            logger.info(f"Found {len(rows)} history records for user {user_id}.")

            for row in rows:
                history.append({
                    "history_id": row["history_id"],
                    "cached_question_id": row["cached_question_id"],
                    "timestamp": row["answer_timestamp"],
                    # Convert DB boolean (0/1) to Python bool
                    "is_final": bool(row["cloud_report_received"]),
                    # We cannot reliably get subject/level/paper info here
                    "subject": row["subject"],
                    "level": row["level"],
                    "paper_year": row["paper_year"],
                    "paper_number": row["question_number_str"],
                })

        except sqlite3.Error as e:
            logger.error(f"Database error fetching basic performance history: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Unexpected error fetching basic performance history: {e}", exc_info=True)
        finally:
            if conn:
                conn.close()

        return history

    @staticmethod
    def get_cached_question_details_bulk(unique_question_keys: List[str]) -> Dict[str, CachedQuestion]:
        """
        Fetches details for multiple cached questions from the main database
        using SQLAlchemy based on a list of unique_question_keys.
        Objects are expunged from the session to allow their use after session closure.
        """
        details_map: Dict[str, CachedQuestion] = {}
        if not unique_question_keys:
            logger.debug("No unique_question_keys provided to get_cached_question_details_bulk.")
            return details_map

        string_keys = [str(key) for key in unique_question_keys if key is not None]
        if not string_keys:
            logger.debug("All provided unique_question_keys were None.")
            return details_map

        logger.debug(f"Fetching cached question details for {len(string_keys)} unique keys.")

        try:
            with get_db_session() as session:
                results = session.query(CachedQuestion)\
                                 .filter(CachedQuestion.unique_question_key.in_(string_keys))\
                                 .all()
                
                temp_results = [] # Store results temporarily before expunging
                for question_obj in results:
                    temp_results.append(question_obj)
                    details_map[question_obj.unique_question_key] = question_obj
                
                # Expunge all fetched objects from the session *after* iterating
                # and populating the map, but before the session closes.
                # This ensures their data is loaded and they can be used detached.
                if temp_results:
                    session.expunge_all()
                
                found_ids = len(details_map)
                if found_ids < len(string_keys):
                    logger.warning(f"Found details for {found_ids}/{len(string_keys)} requested question keys. Missing keys might not be in DB or were None.")
                else:
                    logger.info(f"Successfully retrieved details for {found_ids} question keys.")

        except Exception as e:
            logger.error(f"Error fetching cached question details: {e}", exc_info=True)
            return {} # Return empty dict on error
        return details_map

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
