import logging
import sqlite3
import json
import os
from datetime import datetime
from typing import Dict, Optional, Any, Tuple
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
        # TODO: Implement SQL UPDATE for cloud_sync_queued
        logger.info(f"Placeholder: Mark history entry {history_id} as queued for cloud.")
        return True # Placeholder

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


    def get_unsynced_history_ids(self, limit: int = 10) -> list[int]:
        """Gets IDs of history entries that haven't been successfully synced yet."""
        # (Implementation as previously proposed)
        conn = self._get_connection()
        if not conn: return []
        cursor = None
        ids = []
        try:
            cursor = conn.cursor()
            sql = """
                SELECT history_id FROM answer_history
                WHERE cloud_report_received = FALSE
                ORDER BY answer_timestamp ASC
                LIMIT ?
            """
            cursor.execute(sql, (limit,))
            results = cursor.fetchall()
            ids = [row[0] for row in results]
            logger.info(f"Found {len(ids)} unsynced history entries.")
        except sqlite3.Error as e:
            logger.error(f"DATABASE ERROR getting unsynced history IDs: {e}", exc_info=True)
        finally:
            if cursor: cursor.close()
        return ids

    def get_new_report_count(self) -> int:
        """Gets the count of received cloud reports."""
        # (Implementation as previously proposed)
        conn = self._get_connection()
        if not conn: return 0
        cursor = None
        count = 0
        try:
            cursor = conn.cursor()
            sql = "SELECT COUNT(*) FROM answer_history WHERE cloud_report_received = TRUE" # Add refinement later if needed (e.g., viewed flag)
            cursor.execute(sql)
            result = cursor.fetchone()
            count = result[0] if result else 0
            logger.debug(f"Found {count} new cloud reports.")
        except sqlite3.Error as e:
            logger.error(f"DATABASE ERROR getting new report count: {e}", exc_info=True)
        finally:
            if cursor: cursor.close()
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
