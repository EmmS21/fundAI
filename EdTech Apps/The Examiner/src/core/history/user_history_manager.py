import logging
import sqlite3
import json
import os
from datetime import datetime, timezone
from typing import Dict, Optional, Any, Tuple, List
import threading
import sys 
import re

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
DB_FILE = 'student_profile.db' 
DB_PATH = os.path.join(PROJECT_ROOT, DB_FILE)

logger = logging.getLogger(__name__)

class UserHistoryManager:
    _instance = None
    _lock = threading.RLock() 

    def __new__(cls, *args, **kwargs):
        print(">>> DEBUG: UserHistoryManager __new__() called.", file=sys.stderr)
        if cls._instance is None:
            print(">>> DEBUG: UserHistoryManager creating new instance.", file=sys.stderr)
            cls._instance = super(UserHistoryManager, cls).__new__(cls)
            cls._instance.initialized = False
        else:
            print(">>> DEBUG: UserHistoryManager returning existing instance.", file=sys.stderr)
        return cls._instance

    def __init__(self):
        print(">>> DEBUG: UserHistoryManager __init__() started.", file=sys.stderr)
        # Check if already initialized by singleton
        if hasattr(self, 'initialized') and self.initialized:
            print(">>> DEBUG: UserHistoryManager already initialized (skipping __init__ body).", file=sys.stderr)
            return

        self.db_path = DB_PATH
        self.conn = None
        print(f">>> DEBUG: UserHistoryManager attempting DB connection to: {self.db_path}", file=sys.stderr)
        try:
            self._connect_db()
            # Check connection status IMMEDIATELY after trying to connect
            if self.conn:
                 print(">>> DEBUG: UserHistoryManager DB connection SUCCESS in __init__.", file=sys.stderr)
            else:
                 # This is the critical failure point if DB connect fails
                 print(">>> DEBUG: *** UserHistoryManager DB connection FAILED in __init__ (self.conn is None). ***", file=sys.stderr)
        except Exception as e:
             print(f">>> DEBUG: *** UserHistoryManager EXCEPTION during _connect_db() call in __init__: {e} ***", file=sys.stderr)


        self.initialized = True
        print(">>> DEBUG: UserHistoryManager __init__() finished.", file=sys.stderr)
        # logger.info(f"UserHistoryManager initialized.") # Avoid logger here until stable

    def _connect_db(self):
        """Establish database connection."""
        print(">>> DEBUG: UserHistoryManager _connect_db() entered.", file=sys.stderr)
        try:
            # Ensure the directory exists before checking the file (optional but safer)
            db_dir = os.path.dirname(self.db_path)
            if not os.path.isdir(db_dir):
                 print(f">>> DEBUG: *** Database directory NOT FOUND at {db_dir} ***", file=sys.stderr)
                 self.conn = None
                 return

            if not os.path.exists(self.db_path):
                 print(f">>> DEBUG: *** Database file NOT FOUND at {self.db_path} ***", file=sys.stderr)
                 self.conn = None
                 return

            print(f">>> DEBUG: Attempting sqlite3.connect for {self.db_path}", file=sys.stderr)
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.execute("PRAGMA foreign_keys = ON;")
            print(f">>> DEBUG: sqlite3.connect successful for {self.db_path}", file=sys.stderr)
        except sqlite3.Error as e:
            print(f">>> DEBUG: *** UserHistoryManager sqlite3.Error connecting to DB {self.db_path}: {e} ***", file=sys.stderr)
            self.conn = None
        except Exception as e: # Catch other potential errors
             print(f">>> DEBUG: *** UserHistoryManager UNEXPECTED ERROR during DB connect: {e} ***", file=sys.stderr)
             self.conn = None
        print(">>> DEBUG: UserHistoryManager _connect_db() exiting.", file=sys.stderr)

    def _get_connection(self) -> Optional[sqlite3.Connection]:
        """Gets the current DB connection, attempting to reconnect if necessary."""
        # Add print here too, to see if it's called later
        print(">>> DEBUG: UserHistoryManager _get_connection() called.", file=sys.stderr)
        if self.conn is None:
            print(">>> DEBUG: UserHistoryManager _get_connection(): self.conn is None, attempting reconnect.", file=sys.stderr)
            self._connect_db()
        # Maybe add a check here too
        # print(f">>> DEBUG: UserHistoryManager _get_connection() returning connection. Is None: {self.conn is None}", file=sys.stderr)
        return self.conn

    def close_connection(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
            logger.info("Database connection closed.")

    # --- Core Method ---
    def add_history_entry(
        self,
        user_id: int,
        cached_question_id: str,
        user_answer_dict: Dict[str, str],
        local_ai_feedback_dict: Dict[str, Optional[str]],
        exam_result_id: Optional[int] = None
    ) -> Optional[int]:
        """
        Adds a new entry to the answer_history table.

        Args:
            user_id: The ID of the user.
            cached_question_id: The unique ID of the question from cached_questions.
            user_answer_dict: Dictionary containing the user's answer(s).
            local_ai_feedback_dict: Dictionary containing feedback from local AI.
            exam_result_id: Optional ID of the exam session.

        Returns:
            The history_id of the newly inserted row, or None if insertion fails.
        """
        conn = self._get_connection()
        if not conn:
            logger.error("Cannot add history entry: No database connection.")
            return None

        sql = """
            INSERT INTO answer_history (
                user_id, cached_question_id, exam_result_id, answer_timestamp,
                user_answer_json, local_ai_grade, local_ai_rationale,
                local_ai_study_topics_json, cloud_sync_queued, cloud_report_received
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        now = datetime.now()
        user_answer_json = json.dumps(user_answer_dict)

        grade = local_ai_feedback_dict.get('Grade')
        rationale = local_ai_feedback_dict.get('Rationale')
        study_topics = local_ai_feedback_dict.get('Study Topics') 
        study_topics_json = None
        if study_topics:
            topics_data = {}
            try:
                topics_match = re.search(r"Specific Topics:(.*?)(Guiding Questions:|Google Search Terms:|$)", study_topics, re.DOTALL | re.IGNORECASE)
                questions_match = re.search(r"Guiding Questions:(.*?)(Specific Topics:|Google Search Terms:|$)", study_topics, re.DOTALL | re.IGNORECASE)
                search_match = re.search(r"Google Search Terms:(.*?)(Specific Topics:|Guiding Questions:|$)", study_topics, re.DOTALL | re.IGNORECASE)

                if topics_match: topics_data['specific_topics'] = [t.strip() for t in topics_match.group(1).strip().split('\n') if t.strip()]
                if questions_match: topics_data['guiding_questions'] = [q.strip() for q in questions_match.group(1).strip().split('\n') if q.strip()]
                if search_match: topics_data['search_terms'] = [s.strip() for s in search_match.group(1).strip().split('\n') if s.strip()]

                # If any data was parsed, store as JSON
                if topics_data:
                    study_topics_json = json.dumps(topics_data)
                else: # Store the raw string if parsing fails or yields nothing
                     study_topics_json = json.dumps({"raw": study_topics})
            except Exception as parse_err:
                 logger.warning(f"Could not parse study topics into JSON, storing raw: {parse_err}")
                 study_topics_json = json.dumps({"raw": study_topics})
        else:
            study_topics_json = json.dumps(None) # Store null if no study topics

        params = (
            user_id,
            cached_question_id,
            exam_result_id,
            now,
            user_answer_json,
            grade,
            rationale,
            study_topics_json,
            False, # cloud_sync_queued
            False  # cloud_report_received
        )

        history_id = None
        with self._lock: # Ensure thread safety for the transaction
            try:
                cursor = conn.cursor()
                cursor.execute(sql, params)
                conn.commit()
                history_id = cursor.lastrowid
                logger.info(f"Successfully added answer history entry with ID: {history_id} for user {user_id}, question {cached_question_id}")
            except sqlite3.Error as e:
                logger.error(f"Failed to insert into answer_history for user {user_id}, question {cached_question_id}: {e}", exc_info=True)
                conn.rollback() # Rollback on error
            finally:
                 if cursor: cursor.close() # Ensure cursor is closed even on error


        return history_id

    # --- Placeholder methods for future cloud sync features ---
    def mark_as_queued_for_cloud(self, history_id: int) -> bool:
        """Marks a history entry as having been queued for cloud sync by setting cloud_sync_queued to TRUE."""
        conn = self._get_connection()
        if not conn:
            logger.error(f"Cannot mark history_id {history_id} as queued: No database connection.")
            return False

        # We are NOT setting a cloud_sync_queue_timestamp as per your decision.
        sql = """
            UPDATE answer_history
            SET cloud_sync_queued = TRUE
            WHERE history_id = ?;
        """
        params = (history_id,) # SQLite expects a tuple for parameters
        
        return self._execute_update(sql, params)

    def mark_as_sent_to_cloud(self, history_id: int) -> bool:
        # TODO: Implement SQL UPDATE for cloud_sync_sent_timestamp
        logger.info(f"Placeholder: Mark history entry {history_id} as sent to cloud.")
        return True # Placeholder

    def update_with_cloud_report(self, history_id: int, cloud_report_dict: Dict[str, Any]) -> bool:
        """
        Updates an existing answer_history entry with data from a received cloud report.

        Args:
            history_id: The ID of the history entry to update.
            cloud_report_dict: A dictionary containing the parsed cloud report data
                               (e.g., {'grade': ..., 'rationale': ..., 'study_topics': ...}).

        Returns:
            True if the update was successful, False otherwise.
        """
        conn = self._get_connection()
        if not conn:
            logger.error(f"Cannot update history {history_id} with cloud report: No database connection.")
            return False

        # Prepare data from the cloud report dictionary
        now_timestamp = datetime.now()
        cloud_grade = cloud_report_dict.get('grade')
        cloud_rationale = cloud_report_dict.get('rationale')
        cloud_study_topics = cloud_report_dict.get('study_topics')
        # Serialize study topics to JSON, handle None or various structures
        cloud_study_topics_json = None
        try:
            if cloud_study_topics is not None:
                cloud_study_topics_json = json.dumps(cloud_study_topics)
            else:
                cloud_study_topics_json = json.dumps(None) # Explicitly store JSON null
        except TypeError as json_err:
             logger.error(f"Could not serialize cloud study topics for history_id {history_id}: {json_err}. Storing null.")
             cloud_study_topics_json = json.dumps(None)


        sql = """
            UPDATE answer_history
            SET
                cloud_report_received = ?,
                cloud_report_received_timestamp = ?,
                cloud_ai_grade = ?,
                cloud_ai_rationale = ?,
                cloud_ai_study_topics_json = ?
            WHERE
                history_id = ?;
        """
        params = (
            True,                   
            now_timestamp,          
            cloud_grade,            
            cloud_rationale,        
            cloud_study_topics_json,
            history_id              
        )

        success = False
        with self._lock: 
            cursor = None
            try:
                cursor = conn.cursor()
                cursor.execute(sql, params)
                # Check if any row was actually updated
                if cursor.rowcount > 0:
                    conn.commit()
                    logger.info(f"Successfully updated answer_history entry {history_id} with cloud report data.")
                    success = True
                else:
                    logger.warning(f"Attempted to update history_id {history_id} with cloud report, but no matching row was found.")
                    success = False # Indicate failure if no row matched

            except sqlite3.Error as e:
                logger.error(f"Failed to UPDATE answer_history for {history_id} with cloud report: {e}", exc_info=True)
                conn.rollback() # Rollback on error
                success = False
            finally:
                 if cursor: cursor.close()

        return success

    def mark_report_as_viewed(self, history_id: int) -> bool:
        """
        Marks a specific cloud report as viewed by setting the viewed timestamp.

        Args:
            history_id: The ID of the history entry to mark as viewed.

        Returns:
            True if the update was successful and a row was affected, False otherwise.
        """
        conn = self._get_connection()
        if not conn:
            logger.error(f"Cannot mark report as viewed for history_id {history_id}: No database connection.")
            return False

        now_timestamp = datetime.now()
        sql = """
            UPDATE answer_history
            SET
                cloud_report_viewed_timestamp = ?
            WHERE
                history_id = ?;
        """
        params = (
            now_timestamp,
            history_id
        )

        success = False
        with self._lock:
            cursor = None
            try:
                cursor = conn.cursor()
                cursor.execute(sql, params)
                if cursor.rowcount > 0:
                    conn.commit()
                    logger.info(f"Successfully marked report as viewed for history_id {history_id}.")
                    success = True
                else:
                    logger.warning(f"Attempted to mark report as viewed for history_id {history_id}, but no matching row was found (it might have already been marked or history_id is invalid).")
                    # No commit needed if no rows affected, and no rollback needed as it's not an error state for the DB.
                    success = False 
            except sqlite3.Error as e:
                logger.error(f"Database error while marking report as viewed for history_id {history_id}: {e}", exc_info=True)
                if conn: # Check if conn is still valid before rollback
                    conn.rollback()
                success = False
            finally:
                if cursor:
                    cursor.close()
        return success

    def get_history_for_user(self, user_id: int) -> list:
        # TODO: Implement SQL SELECT query
        logger.info(f"Placeholder: Get history for user {user_id}.")
        return [] # Placeholder

    def _execute_update(self, sql: str, params: tuple) -> bool:
        """Helper function to execute UPDATE statements."""
        conn = self._get_connection()
        if not conn:
            logger.error("_execute_update: Cannot proceed, no database connection.")
            return False
        success = False
        cursor = None
        with self._lock:
            try:
                cursor = conn.cursor()
                logger.debug(f"Executing SQL: {sql}")
                logger.debug(f"With Params: {params}")
                cursor.execute(sql, params)
                conn.commit()
                success = True
                logger.debug(f"Update successful for history_id: {params[-1]}") # Assumes ID is last param
            except sqlite3.Error as e:
                logger.error(f"DATABASE ERROR during update: {e}", exc_info=True)
                if conn: conn.rollback()
            except Exception as e_generic:
                 logger.error(f"UNEXPECTED ERROR during database update: {e_generic}", exc_info=True)
                 if conn: conn.rollback()
            finally:
                if cursor: cursor.close()
        return success

    def get_history_details_for_sync(self, history_id: int) -> Optional[Tuple[str, str]]:
        """Retrieves cached_question_id, user_answer_json for syncing."""
        # (Implementation as previously proposed)
        conn = self._get_connection()
        if not conn: return None
        cursor = None
        try:
            cursor = conn.cursor()
            sql = "SELECT cached_question_id, user_answer_json FROM answer_history WHERE history_id = ?"
            cursor.execute(sql, (history_id,))
            result = cursor.fetchone()
            if result:
                logger.debug(f"Retrieved details for sync for history_id {history_id}")
                return result # Returns (cached_question_id, user_answer_json)
            else:
                logger.warning(f"No history entry found for history_id {history_id}")
                return None
        except sqlite3.Error as e:
            logger.error(f"DATABASE ERROR getting history details for sync (id={history_id}): {e}", exc_info=True)
            return None
        finally:
            if cursor: cursor.close()


    def get_pending_cloud_analysis_items(self, limit: int = 10) -> List[Tuple[int, str]]:
        """
        Gets history_id and cached_question_id for entries that need cloud report generation.
        Filters out items already marked as cloud_sync_queued or already processed (cloud_report_received = TRUE).
        """
        conn = self._get_connection()
        if not conn:
            logger.error("Cannot get pending cloud analysis items: No database connection.")
            return []
        
        items: List[Tuple[int, str]] = [] # Ensure type hint for clarity
        cursor = None
        try:
            cursor = conn.cursor()
            # Select history_id and cached_question_id for items not yet processed 
            # AND not yet marked as queued by the SyncService's proactive check.
            sql = """
                SELECT history_id, cached_question_id 
                FROM answer_history
                WHERE cloud_report_received = FALSE 
                  AND (cloud_sync_queued = FALSE OR cloud_sync_queued IS NULL)
                ORDER BY answer_timestamp ASC
                LIMIT ?;
            """
            cursor.execute(sql, (limit,))
            results = cursor.fetchall() # This will be a list of tuples
            if results:
                items = results
            logger.info(f"Found {len(items)} pending items for cloud analysis (history_id, cached_question_id).")
        except sqlite3.Error as e:
            logger.error(f"DATABASE ERROR getting pending cloud analysis items: {e}", exc_info=True)
            items = [] # Ensure empty list on error
        finally:
            if cursor:
                cursor.close()
        return items

    def get_user_answer_json(self, history_id: int) -> Optional[str]:
        """Retrieves the user_answer_json for a given history_id."""
        conn = self._get_connection()
        if not conn:
            logger.error(f"Cannot get user answer for history_id {history_id}: No database connection.")
            return None
        
        cursor = None
        user_answer_json: Optional[str] = None
        try:
            cursor = conn.cursor()
            sql = "SELECT user_answer_json FROM answer_history WHERE history_id = ?;"
            cursor.execute(sql, (history_id,))
            result = cursor.fetchone()
            if result:
                user_answer_json = result[0]
                logger.debug(f"Retrieved user_answer_json for history_id {history_id}.")
            else:
                logger.warning(f"No history entry found for history_id {history_id} when fetching user_answer_json.")
        except sqlite3.Error as e:
            logger.error(f"DATABASE ERROR getting user_answer_json for history_id {history_id}: {e}", exc_info=True)
            user_answer_json = None # Ensure None on error
        finally:
            if cursor:
                cursor.close()
        return user_answer_json

    def get_new_report_count(self, subject_name: Optional[str] = None, level_key: Optional[str] = None) -> int:
        """
        Gets the count of received cloud reports that have not yet been viewed.
        Can be filtered by subject and/or level.
        If subject_name is None, counts all unviewed reports (maintaining previous general functionality if needed).
        If subject_name is provided, level_key can also be provided for more specific filtering.
        """
        conn = self._get_connection()
        if not conn:
            logger.error("Cannot get new report count: No database connection.")
            return 0
        
        cursor = None
        count = 0
        try:
            cursor = conn.cursor()
            
            # NEW SQL CONSTRUCTION FOR TASK 4.A:
            base_sql = """
                SELECT COUNT(DISTINCT ah.history_id) 
                FROM answer_history ah
            """
            join_sql = ""  # Will be populated if filtering by subject/level
            where_clauses = [
                "ah.cloud_report_received = TRUE",
                "ah.cloud_report_viewed_timestamp IS NULL"
            ]
            params = [] # To hold values for parameterized query

            if subject_name:
                # Add JOIN with cached_questions if subject_name is provided
                join_sql = " JOIN cached_questions cq ON ah.cached_question_id = cq.unique_question_key "
                
                where_clauses.append("cq.subject = ?")
                params.append(subject_name)
                
                if level_key: # Add level filter only if subject is also specified
                    where_clauses.append("cq.level = ?")
                    params.append(level_key)
            
            # Combine the SQL parts
            sql = base_sql + join_sql + " WHERE " + " AND ".join(where_clauses) + ";"
            
            logger.debug(f"Executing SQL for new report count: {sql} with params: {params}")
            cursor.execute(sql, tuple(params)) # Use parameterized query
            result = cursor.fetchone()
            count = result[0] if result else 0
            
            # MODIFIED: More detailed logging
            log_message = f"Found {count} new, unviewed cloud reports"
            if subject_name:
                log_message += f" for subject '{subject_name}'"
                if level_key:
                    log_message += f", level '{level_key}'"
            logger.debug(log_message + ".")
            
        except sqlite3.Error as e:
            logger.error(f"DATABASE ERROR getting new report count: {e}", exc_info=True)
            count = 0
        finally:
            if cursor:
                cursor.close()
        return count

    def get_question_id_for_history(self, history_id: int) -> Optional[str]:
        """Retrieves the cached_question_id for a given history_id."""
        conn = self._get_connection()
        if not conn: return None
        cursor = None
        try:
            cursor = conn.cursor()
            sql = "SELECT cached_question_id FROM answer_history WHERE history_id = ?"
            cursor.execute(sql, (history_id,))
            result = cursor.fetchone()
            return result[0] if result else None
        except sqlite3.Error as e:
            logger.error(f"DATABASE ERROR getting question ID for history_id {history_id}: {e}", exc_info=True)
            return None
        finally:
            if cursor: cursor.close()

    def get_all_history_details(self, user_id: int) -> list[Dict[str, Any]]:
        """
        Fetches all history entries for a user, joined with question details.

        Args:
            user_id: The ID of the user.

        Returns:
            A list of dictionaries, each containing details for one history entry.
            Returns an empty list on error or if no history exists.
        """
        conn = self._get_connection()
        if not conn:
            logger.error("Cannot get history details: No database connection.")
            return []

        results = []
        cursor = None
        sql = """
            SELECT
                ah.history_id,
                ah.answer_timestamp,
                ah.cloud_report_received,
                cq.question_id,
                cq.subject,
                cq.level,
                cq.paper_number,
                cq.paper_year
            FROM
                answer_history ah
            JOIN
                cached_questions cq ON ah.cached_question_id = cq.question_id
            WHERE
                ah.user_id = ?
            ORDER BY
                ah.answer_timestamp DESC;
            """
        try:
            cursor = conn.cursor()
            # Set row factory to easily convert rows to dictionary-like objects
            conn.row_factory = sqlite3.Row 
            cursor = conn.cursor() # Re-create cursor after setting row_factory
            
            logger.debug(f"Executing SQL to get all history details for user {user_id}")
            cursor.execute(sql, (user_id,))
            rows = cursor.fetchall()
            
            # Convert Row objects to dictionaries
            results = [dict(row) for row in rows] 
            logger.info(f"Retrieved {len(results)} history entries for user {user_id}")

        except sqlite3.Error as e:
            logger.error(f"DATABASE ERROR getting all history details for user {user_id}: {e}", exc_info=True)
            return [] # Return empty list on error
        finally:
            # Reset row_factory to default if necessary, or handle appropriately elsewhere
            conn.row_factory = None 
            if cursor: cursor.close()

        return results

    def is_cloud_report_received(self, history_id: int) -> bool: # Ensure this method from Task 5 is present
        """Checks if the cloud report for a given history_id has been received."""
        conn = self._get_connection()
        if not conn:
            logger.error(f"Cannot check if cloud report received for history_id {history_id}: No database connection.")
            return False 

        cursor = None
        is_received = False
        try:
            cursor = conn.cursor()
            sql = "SELECT cloud_report_received FROM answer_history WHERE history_id = ?;"
            cursor.execute(sql, (history_id,))
            result = cursor.fetchone()
            if result:
                is_received = bool(result[0]) 
            else:
                logger.warning(f"No history entry found for history_id {history_id} when checking if cloud report received.")
        except sqlite3.Error as e:
            logger.error(f"DATABASE ERROR checking if cloud report received for history_id {history_id}: {e}", exc_info=True)
        finally:
            if cursor:
                cursor.close()
        
        logger.debug(f"Cloud report received status for history_id {history_id}: {is_received}")
        return is_received

    def get_all_student_activity_for_sync(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Fetches all student activity (questions, answers, reports, grades)
        for a given user, formatted for Firebase sync.

        Args:
            user_id: The ID of the user.

        Returns:
            A list of dictionaries, where each dictionary represents an answered question
            with its associated data. Returns an empty list on error or if no history.
        """
        conn = self._get_connection()
        if not conn:
            logger.error(f"Cannot get student activity for sync (user {user_id}): No database connection.")
            return []

        sql = """
            SELECT
                history_id, 
                cached_question_id,
                answer_timestamp,
                user_answer_json,
                local_ai_grade,
                local_ai_rationale,
                local_ai_study_topics_json,
                cloud_report_received,
                cloud_ai_grade,
                cloud_ai_rationale,
                cloud_ai_study_topics_json
            FROM
                answer_history
            WHERE
                user_id = ?
            ORDER BY
                answer_timestamp ASC; 
        """

        activities = []
        cursor = None
        try:
            original_row_factory = conn.row_factory
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            logger.debug(f"Executing SQL to get all student activity for sync for user {user_id}")
            cursor.execute(sql, (user_id,))
            rows = cursor.fetchall()

            for row in rows:
                try:
                    user_answer = None
                    if row["user_answer_json"]:
                        try:
                            user_answer = json.loads(row["user_answer_json"])
                        except json.JSONDecodeError:
                            logger.warning(f"Could not parse user_answer_json for history_id {row['history_id']}: {row['user_answer_json']}")
                            user_answer = row["user_answer_json"] 

                    preliminary_report = {}
                    if row["local_ai_grade"] or row["local_ai_rationale"] or row["local_ai_study_topics_json"]:
                        preliminary_report["grade"] = row["local_ai_grade"]
                        preliminary_report["rationale"] = row["local_ai_rationale"]
                        study_topics_prelim = None
                        if row["local_ai_study_topics_json"]:
                            try:
                                study_topics_prelim = json.loads(row["local_ai_study_topics_json"])
                            except json.JSONDecodeError:
                                logger.warning(f"Could not parse local_ai_study_topics_json for history_id {row['history_id']}")
                                study_topics_prelim = {"raw": row["local_ai_study_topics_json"]}
                        preliminary_report["study_topics"] = study_topics_prelim

                    full_report = None
                    if row["cloud_report_received"]:
                        full_report = {}
                        full_report["grade"] = row["cloud_ai_grade"]
                        full_report["rationale"] = row["cloud_ai_rationale"]
                        study_topics_full = None
                        if row["cloud_ai_study_topics_json"]:
                            try:
                                study_topics_full = json.loads(row["cloud_ai_study_topics_json"])
                            except json.JSONDecodeError:
                                logger.warning(f"Could not parse cloud_ai_study_topics_json for history_id {row['history_id']}")
                                study_topics_full = {"raw": row["cloud_ai_study_topics_json"]}
                        full_report["study_topics"] = study_topics_full
                    
                    grade = row["cloud_ai_grade"] if row["cloud_report_received"] and row["cloud_ai_grade"] is not None else row["local_ai_grade"]
                    submission_timestamp_str = row["answer_timestamp"]
                    submission_timestamp_dt = None
                    if isinstance(submission_timestamp_str, str):
                        try:
                            submission_timestamp_dt = datetime.fromisoformat(submission_timestamp_str)
                        except ValueError:
                            try: 
                                submission_timestamp_dt = datetime.strptime(submission_timestamp_str, '%Y-%m-%d %H:%M:%S.%f')
                            except ValueError:
                                logger.error(f"Could not parse answer_timestamp for history_id {row['history_id']}: {submission_timestamp_str}")
                                submission_timestamp_dt = datetime.now() 
                    elif isinstance(submission_timestamp_str, datetime):
                        submission_timestamp_dt = submission_timestamp_str
                    else: 
                         submission_timestamp_dt = datetime.now()


                    activity_entry = {
                        "questionID": row["cached_question_id"],
                        "userAnswer": user_answer, 
                        "preliminaryReport": preliminary_report if preliminary_report else None,
                        "fullReport": full_report, 
                        "grade": grade,
                        "submissionTimestamp": submission_timestamp_dt 
                    }
                    activities.append(activity_entry)

                except Exception as e:
                    logger.error(f"Error processing history row (history_id {row['history_id'] if row else 'Unknown'}) for sync: {e}", exc_info=True)

            logger.info(f"Retrieved and processed {len(activities)} student activities for sync for user {user_id}")

        except sqlite3.Error as e:
            logger.error(f"DATABASE ERROR getting student activities for sync (user {user_id}): {e}", exc_info=True)
            return [] 
        finally:
            if conn:
                conn.row_factory = original_row_factory
            if cursor:
                cursor.close()

        return activities
