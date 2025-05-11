from typing import Optional, Dict, Any, List, Callable
from datetime import datetime, date, timezone
import logging
from ..queue_manager import QueueManager, QueuePriority, QueueStatus, QueueItem
from .monitor import NetworkMonitor, NetworkStatus
from ..firebase.client import FirebaseClient
from ...utils.hardware_identifier import HardwareIdentifier
import time
import threading
from src.data.cache.cache_manager import CacheManager
from src.core import services
from enum import Enum
import json
from src.core.ai.groq_client import GroqClient
from src.core.ai.marker import run_ai_evaluation
import pprint
import sqlite3
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SyncError(Exception):
    """Custom exception for sync errors"""
    pass

class ConflictError(SyncError):
    """Error raised when there's a conflict during sync"""
    pass

class SyncService:
    _instance = None
    MAX_RETRIES = 3
    RETRY_DELAY = 5  # seconds between retries
    BATCH_SIZE = 10  # maximum items to process in a batch
    # Define poll intervals
    INITIAL_SYNC_ACTIVE_POLL_INTERVAL = 0.5 # seconds, when actively processing initial online reports
    REGULAR_IDLE_POLL_INTERVAL = 3        # seconds, when idle after initial sync or if queue is empty
    POST_ITEM_PROCESS_DELAY = 0.2         # seconds, short delay after processing any item
    DB_SCAN_ERROR_RETRY_DELAY = 10    # seconds, if DB scan for pending items fails

    def __new__(cls):
        """Singleton pattern to ensure only one instance exists"""
        if cls._instance is None:
            cls._instance = super(SyncService, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the sync service"""
        if hasattr(self, 'initialized') and self.initialized:
            return
            
        # Initialize components
        self._queue_manager = services.queue_manager
        self._network_monitor = NetworkMonitor()
        
        # Register self in services registry
        services.sync_service = self
        
        # Thread control
        self._running = False
        self._sync_thread = None
        
        # Flag for initial online DB scan for cloud analysis reports in the current session
        self._initial_db_scan_for_cloud_reports_done_this_session = False
        
        # Register for network status changes
        self._network_monitor.status_changed.connect(self._handle_network_change)
        
        self.initialized = True
        logger.info("Sync Service initialized")

    def initialize(self):
        """Legacy initialization method for backward compatibility"""
        pass

    def start(self):
        """Start the sync service"""
        if self._running:
            logger.info("Sync service already running")
            return
            
        self._running = True
        
        # Start sync thread if we're online
        if self._network_monitor.get_status() == NetworkStatus.ONLINE:
            self._sync_thread = threading.Thread(target=self._sync_worker, daemon=True)
            self._sync_thread.start()
            logger.info("Sync service started")
        else:
            logger.info("Sync service started (waiting for network)")

    def stop(self):
        """Stop the sync service"""
        self._running = False
        if self._sync_thread:
            self._sync_thread.join(timeout=1.0)
        logger.info("Sync service stopped")

    def _handle_network_change(self, status: NetworkStatus):
        """Handle network status changes"""
        if status == NetworkStatus.ONLINE:
            logger.info("Network is online, sync operations can resume/start.")
            # Reset the flag to ensure initial DB scan runs if network (re)connects
            self._initial_db_scan_for_cloud_reports_done_this_session = False 
            
            if self._running: # Only start/ensure worker is running if service is active
                if not self._sync_thread or not self._sync_thread.is_alive():
                    self._sync_thread = threading.Thread(target=self._sync_worker, daemon=True)
                    self._sync_thread.start()
                    logger.info("Sync worker thread started/restarted due to network online.")
            else:
                logger.info("Sync service is not marked as running, worker thread not started despite network online.")
        else:
            logger.info("Network is offline, sync operations paused")
            # When offline, the initial scan state is reset for the next online session.
            self._initial_db_scan_for_cloud_reports_done_this_session = False

    def _sync_worker(self):
        """Background thread to process sync queue and manage cloud analysis report generation."""
        logger.info("SyncService: Sync worker started.")
        
        while self._running:
            if self._network_monitor.get_status() != NetworkStatus.ONLINE:
                logger.debug("SyncService: Network offline, worker pausing.")
                self._initial_db_scan_for_cloud_reports_done_this_session = False # Reset for next online session
                time.sleep(self.REGULAR_IDLE_POLL_INTERVAL)
                continue

            # --- Initial Online Database Scan for Cloud Analysis Reports (once per online session) ---
            if not self._initial_db_scan_for_cloud_reports_done_this_session:
                logger.info("SyncService: Performing initial DB scan for pending cloud analysis reports.")
                try:
                    self._perform_initial_db_scan_and_queue_cloud_reports()
                    self._initial_db_scan_for_cloud_reports_done_this_session = True
                    logger.info("SyncService: Initial DB scan for cloud reports completed for this session.")
                except Exception as e: # Catch broad exceptions to prevent worker crash from this scan
                    logger.error(f"SyncService: Error during initial DB scan for cloud reports: {e}", exc_info=True)
                    # Don't set the flag to true, so it retries on the next suitable worker iteration
                    # Or, could implement a specific retry counter for the scan itself if needed.
                    time.sleep(self.DB_SCAN_ERROR_RETRY_DELAY) # Wait a bit before retrying the scan
                    continue # Skip to next iteration to re-evaluate
            
            # --- Regular Queue Processing (all item types) ---
            processed_something_this_cycle = False

            # 1. Process Batches (if any)
            adaptive_batch_size = self._network_monitor.get_recommended_batch_size(self.BATCH_SIZE)
            batch_ids = self.get_pending_batch_ids()
            if batch_ids:
                logger.debug(f"SyncService: Found {len(batch_ids)} pending batches. Processing up to {adaptive_batch_size}.")
                for batch_id in batch_ids[:adaptive_batch_size]:
                    if not (self._running and self._network_monitor.get_status() == NetworkStatus.ONLINE): break
                    self._process_batch(batch_id)
                    processed_something_this_cycle = True
                if processed_something_this_cycle:
                    time.sleep(self.POST_ITEM_PROCESS_DELAY) 
                    continue # Re-evaluate queue state immediately after batch processing

            # 2. Process Individual Items
            item = self._queue_manager.get_next_item() # Gets any type of item based on QueueManager's priority
            if item:
                logger.debug(f"SyncService: Processing individual item {item.id} (type: {item.type}).")
                self._process_item(item)
                processed_something_this_cycle = True
            
            # Sleep logic
            if processed_something_this_cycle:
                time.sleep(self.POST_ITEM_PROCESS_DELAY) # Short delay if work was done
            else:
                # Queue is empty or no suitable items were processed
                logger.debug(f"SyncService: Queue empty or no items processed. Sleeping for {self.REGULAR_IDLE_POLL_INTERVAL}s.")
                time.sleep(self.REGULAR_IDLE_POLL_INTERVAL)
        
        logger.info("SyncService: Sync worker stopped.")

    def _process_batch(self, batch_id: str):
        """
        Process a batch of sync items
        
        Args:
            batch_id: The batch ID to process
        """
        # Get all items in this batch
        items = self._queue_manager.get_batch_items(batch_id)
        
        if not items:
            logger.warning(f"No items found for batch {batch_id}")
            return
            
        # Group items by type
        items_by_type = {}
        for item in items:
            item_type = item.type
            if item_type not in items_by_type:
                items_by_type[item_type] = []
            items_by_type[item_type].append(item)
            
        # Process each type of item
        success = True
        for item_type, type_items in items_by_type.items():
            try:
                if item_type == 'exam_result':
                    self._sync_batch_exam_results(type_items)
                elif item_type == 'question_response':
                    self._sync_batch_question_responses(type_items)
                elif item_type == 'question':
                    self._sync_batch_questions(type_items)
                elif item_type == 'user':
                    # Process user items individually
                    for item in type_items:
                        self._process_item(item)
                elif item_type == 'cloud_analysis_request':
                    for item in type_items:
                        self._process_item(item)
                else:
                    logger.warning(f"Unknown batch item type: {item_type}")
                    success = False
            except Exception as e:
                logger.error(f"Error processing batch {batch_id} items of type {item_type}: {e}")
                success = False
                        
        # Mark batch as completed if successful
        if success:
            self._queue_manager.mark_batch_completed(batch_id)
            logger.info(f"Successfully processed batch {batch_id}")
        else:
            logger.warning(f"Batch {batch_id} processing had errors")

    def _process_item(self, item: QueueItem):
        """
        Process a single sync item
        
        Args:
            item: The queue item to process
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if item.type == 'user_data':
                self._sync_with_retry(self._sync_user_data, item)
            elif item.type == 'exam_result':
                self._sync_with_retry(self._sync_exam_result, item)
            elif item.type == 'question_response':
                self._sync_with_retry(self._sync_question_response, item)
            elif item.type == 'question':
                self._sync_with_retry(self._sync_question, item)
            elif item.type == 'system_metrics':
                self._sync_with_retry(self._sync_system_metrics, item)
            elif item.type == 'cloud_analysis_request':
                self._sync_with_retry(self._sync_cloud_analysis_request, item)
            else:
                logger.warning(f"Unknown item type: {item.type}")
                self._queue_manager.mark_failed(item.id)
                return False
            return True
        except Exception as e:
            logger.error(f"Error processing item {item.id}: {e}")
            self._queue_manager.mark_failed(item.id)
            return False

    def _sync_with_retry(self, sync_func: Callable, item: QueueItem) -> bool:
        """
        Attempt to sync with retry logic
        
        Args:
            sync_func: The function to call for syncing
            item: The queue item to sync
            
        Returns:
            True if eventually successful, False if all retries failed
        """
        max_retries = self.MAX_RETRIES
        
        for attempt in range(1, max_retries + 1):
            try:
                if sync_func(item):
                    self._queue_manager.mark_completed(item.id)
                    return True
            except Exception as e:
                logger.error(f"Error syncing item {item.id} (attempt {attempt}/{max_retries}): {e}")
            
            # Update retry count
            self._queue_manager.update_item(item.increment_attempts())
            
            # Don't sleep on the last attempt
            if attempt < max_retries:
                # Use adaptive retry delay based on connection quality and attempt number
                retry_delay = self._network_monitor.get_retry_delay(attempt, self.RETRY_DELAY)
                logger.info(f"Retrying in {retry_delay:.1f} seconds (attempt {attempt}/{max_retries})")
                time.sleep(retry_delay)
                
        # All retries failed
        self._queue_manager.mark_failed(item.id)
        return False

    def _serialize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Serialize data for sync operations, converting dates/times to strings
        
        Args:
            data: The data to serialize
            
        Returns:
            Serialized data
        """
        result = {}
        for key, value in data.items():
            if isinstance(value, datetime):
                result[key] = value.isoformat()
            elif isinstance(value, date):
                result[key] = value.isoformat()
            elif isinstance(value, Enum):
                result[key] = value.value
            elif isinstance(value, dict):
                result[key] = self._serialize_data(value)
            elif isinstance(value, list):
                result[key] = [
                    self._serialize_data(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                result[key] = value
        return result

    def _sync_user_data(self, item: QueueItem):
        """Sync user data using Firebase REST API"""
        try:
            user_data = {
                'name': item.data['name'],
                'email': item.data['email'],
                'school': item.data['school'],
                'grade': item.data['grade'],
                'hardware_id': self.hardware_id,
                'updated_at': datetime.now()
            }
            
            # Serialize the data before sending to Firebase
            serialized_data = self._serialize_data(user_data)
            
            path = f"users/{self.hardware_id}"
            self.firebase.update_data(path, serialized_data)
            logger.info(f"Successfully synced user data")
            
        except Exception as e:
            logger.error(f"Failed to sync user data: {e}")
            raise

    def _sync_exam_result(self, item: QueueItem):
        """Sync exam result using Firebase REST API"""
        try:
            exam_data = {
                'exam_date': item.data['exam_date'],
                'exam_id': item.data['exam_id'],
                'subject': item.data['subject'],
                'grade': item.data['grade'],
                'total_possible': item.data['total_possible'],
                'level': item.data['level'],
                'topics': item.data['topics'],
                'report_version': item.data['report_version'],
                'hardware_id': self.hardware_id,
                'updated_at': datetime.now()
            }
            
            # Serialize the data before sending to Firebase
            serialized_data = self._serialize_data(exam_data)
            
            path = f"exam_results/{self.hardware_id}/{item.data['exam_id']}"
            self.firebase.update_data(path, serialized_data)
            logger.info(f"Successfully synced exam result {item.data['exam_id']}")
            
        except Exception as e:
            logger.error(f"Failed to sync exam result: {e}")
            raise

    def _sync_question_response(self, item: QueueItem):
        """Sync question response using Firebase REST API"""
        try:
            response_data = {
                'question_id': item.data['question_id'],
                'exam_id': item.data['exam_id'],
                'student_answer': item.data['student_answer'],
                'is_correct': item.data['is_correct'],
                'score': item.data['score'],
                'feedback': item.data['feedback'],
                'is_preliminary': item.data['is_preliminary'],
                'hardware_id': self.hardware_id,
                'updated_at': datetime.now()
            }
            
            # Serialize the data before sending to Firebase
            serialized_data = self._serialize_data(response_data)
            
            path = f"question_responses/{self.hardware_id}/{item.data['exam_id']}/{item.data['question_id']}"
            self.firebase.update_data(path, serialized_data)
            logger.info(f"Successfully synced question response {item.data['question_id']}")
            
        except Exception as e:
            logger.error(f"Failed to sync question response: {e}")
            raise

    def _sync_question(self, item: QueueItem):
        """Sync a question to the local cache"""
        try:
            # Check subscription status before syncing
            if not self._verify_subscription():
                logger.warning(f"Skipping question sync - subscription not active")
                return False
                
            # Extract data from queue item
            question_data = item.data
            subject = question_data.get('subject')
            level = question_data.get('level')
            
            if not subject or not level:
                logger.error(f"Missing required fields in question data")
                return False
                
            # Get CacheManager instance
            cache_manager = services.cache_manager
            
            # Save question to file-based cache
            result = cache_manager.save_question_from_mongodb(question_data, subject, level)
            
            if result:
                logger.info(f"Successfully synced question for {subject} at {level} level")
                return True
            else:
                logger.error(f"Failed to save question to cache")
                return False
                
        except Exception as e:
            logger.error(f"Error syncing question: {e}")
            return False
            
    def _sync_system_metrics(self, item: QueueItem):
        """Sync system metrics using Firebase REST API"""
        try:
            metrics_data = {
                'cache_hit_ratio': item.data.get('cache_hit_ratio'),
                'offline_success_rate': item.data.get('offline_success_rate'),
                'model_performance': item.data.get('model_performance'),
                'hardware_id': self.hardware_id,
                'timestamp': datetime.now()
            }
            
            # Serialize the data before sending to Firebase
            serialized_data = self._serialize_data(metrics_data)
            
            path = f"system_metrics/{self.hardware_id}/{int(time.time())}"
            self.firebase.update_data(path, serialized_data)
            logger.info(f"Successfully synced system metrics")
            
        except Exception as e:
            logger.error(f"Failed to sync system metrics: {e}")
            raise

    def _sync_batch_exam_results(self, items: List[QueueItem]):
        """Sync multiple exam results in a single batch"""
        try:
            batch_data = {}
            
            for item in items:
                exam_id = item.data['exam_id']
                exam_data = {
                    'exam_date': item.data['exam_date'],
                    'exam_id': exam_id,
                    'subject': item.data['subject'],
                    'grade': item.data['grade'],
                    'total_possible': item.data['total_possible'],
                    'level': item.data['level'],
                    'topics': item.data['topics'],
                    'report_version': item.data['report_version'],
                    'hardware_id': self.hardware_id,
                    'updated_at': datetime.now()
                }
                
                # Serialize the data
                serialized_data = self._serialize_data(exam_data)
                batch_data[f"exam_results/{self.hardware_id}/{exam_id}"] = serialized_data
            
            # Send batch update to Firebase
            self.firebase.batch_update(batch_data)
            logger.info(f"Successfully synced {len(items)} exam results in batch")
            
        except Exception as e:
            logger.error(f"Failed to sync batch exam results: {e}")
            raise

    def _sync_batch_question_responses(self, items: List[QueueItem]):
        """Sync multiple question responses in a single batch"""
        try:
            batch_data = {}
            
            for item in items:
                question_id = item.data['question_id']
                exam_id = item.data['exam_id']
                
                response_data = {
                    'question_id': question_id,
                    'exam_id': exam_id,
                    'student_answer': item.data['student_answer'],
                    'is_correct': item.data['is_correct'],
                    'score': item.data['score'],
                    'feedback': item.data['feedback'],
                    'is_preliminary': item.data['is_preliminary'],
                    'hardware_id': self.hardware_id,
                    'updated_at': datetime.now()
                }
                
                # Serialize the data
                serialized_data = self._serialize_data(response_data)
                path = f"question_responses/{self.hardware_id}/{exam_id}/{question_id}"
                batch_data[path] = serialized_data
            
            # Send batch update to Firebase
            self.firebase.batch_update(batch_data)
            logger.info(f"Successfully synced {len(items)} question responses in batch")
            
        except Exception as e:
            logger.error(f"Failed to sync batch question responses: {e}")
            raise

    def _sync_batch_questions(self, items: List[QueueItem]):
        """Sync multiple questions in a batch"""
        try:
            # Check subscription status before syncing
            if not self._verify_subscription():
                logger.warning(f"Skipping batch question sync - subscription not active")
                return False
                
            success_count = 0
            
            # Get CacheManager instance
            cache_manager = services.cache_manager
            
            for item in items:
                try:
                    # Extract data from queue item
                    question_data = item.data
                    subject = question_data.get('subject')
                    level = question_data.get('level')
                    
                    if not subject or not level:
                        logger.error(f"Missing required fields in question data")
                        continue
                        
                    # Save question to file-based cache
                    result = cache_manager.save_question_from_mongodb(question_data, subject, level)
                    
                    if result:
                        success_count += 1
                        self._queue_manager.mark_completed(item.id)
                    else:
                        logger.error(f"Failed to save question to cache")
                        self._queue_manager.mark_failed(item.id)
                        
                except Exception as e:
                    logger.error(f"Error processing question in batch: {e}")
                    self._queue_manager.mark_failed(item.id)
            
            logger.info(f"Batch question sync completed: {success_count}/{len(items)} successful")
            return success_count > 0
                
        except Exception as e:
            logger.error(f"Error in batch question sync: {e}")
            return False
            
    def _verify_subscription(self) -> bool:
        """
        Verify if user has active subscription for syncing
        
        Returns:
            bool: True if subscription is active, False otherwise
        """
        try:
            # Get Firebase client
            firebase = FirebaseClient()
            
            # Get user document with subscription info
            user_doc = firebase._get_user_document()
            
            # If no user document, no subscription
            if not user_doc:
                return False
                
            # Extract subscription fields
            subscribed = user_doc.get('subscribed', {}).get('stringValue')
            sub_end_str = user_doc.get('sub_end', {}).get('stringValue')
            
            # If subscription fields don't exist, no subscription
            if not subscribed or not sub_end_str:
                return False
                
            # Check if subscription is inactive
            if subscribed == "inactive":
                return False
                
            # Check if subscription has expired
            try:
                from datetime import datetime
                sub_end = datetime.fromisoformat(sub_end_str)
                if datetime.now() > sub_end:
                    return False
            except (ValueError, TypeError):
                # If date parsing fails, assume expired
                return False
                
            # If we've passed all checks, subscription is active
            return True
            
        except Exception as e:
            logger.error(f"Error verifying subscription for sync: {e}")
            # For exceptions, deny sync to be safe
            return False
            
    def queue_user_data(self, user_data: Dict[str, Any]) -> str:
        """Queue user data for sync"""
        return self._queue_manager.add_to_queue(
            data=user_data,
            item_type='user',
            priority=QueuePriority.LOW  # T4: User profile changes
        )

    def queue_exam_result(self, exam_data: Dict[str, Any]) -> str:
        """Queue exam result for sync"""
        return self._queue_manager.add_to_queue(
            data=exam_data,
            item_type='exam_result',
            priority=QueuePriority.CRITICAL  # T1: Final reports/scores
        )

    def queue_question_responses(self, responses: List[Dict[str, Any]]) -> str:
        """Queue multiple question responses as a batch"""
        return self._queue_manager.add_batch_to_queue(
            items=responses,
            item_type='question_response',
            priority=QueuePriority.CRITICAL  # T1: Final reports/scores
        )

    def queue_question(self, question_data: Dict[str, Any]) -> str:
        """Queue question for sync"""
        return self._queue_manager.add_to_queue(
            data=question_data,
            item_type='question',
            priority=QueuePriority.HIGH  # T2: Question cache updates
        )
        
    def queue_questions(self, questions: List[Dict[str, Any]]) -> str:
        """
        Queue multiple questions for syncing
        
        Args:
            questions: List of question data objects
            
        Returns:
            str: Batch ID
        """
        # Check subscription before queuing
        if not self._verify_subscription():
            logger.warning("Not queuing questions - subscription not active")
            return ""
            
        # Add to queue with medium priority
        return self._queue_manager.add_batch_to_queue(
            questions, 
            item_type="question", 
            priority=QueuePriority.MEDIUM
        )

    def queue_system_metrics(self, metrics_data: Dict[str, Any]) -> str:
        """Queue system metrics for sync"""
        return self._queue_manager.add_to_queue(
            data=metrics_data,
            item_type='system_metrics',
            priority=QueuePriority.MEDIUM  # T3: System metrics
        )

    def get_pending_batch_ids(self) -> List[str]:
        """
        Get a list of all unique batch IDs for pending items in the queue.
        
        Returns:
            List of batch IDs
        """
        batch_ids = set()
        for item in self._queue_manager.queue:
            if item.batch_id and item.status == QueueStatus.PENDING:
                batch_ids.add(item.batch_id)
        return list(batch_ids)

    def _sync_cloud_analysis_request(self, item: QueueItem) -> bool:
        """Handles syncing a request for cloud AI analysis using a pre-gen prompt."""
        logger.info(f"Starting cloud analysis sync for history_id: {item.data.get('history_id')}, item_id: {item.id}")

        history_id = item.data.get('history_id')
        local_prompt = item.data.get('local_prompt') # Get the prompt from queue data

        if not history_id:
            logger.error(f"Missing 'history_id' in queue item data for item ID {item.id}. Cannot process.")
            return False # Non-retryable
        if not local_prompt:
            logger.error(f"Missing 'local_prompt' in queue item data for history_id {history_id}. Cannot process.")
            return False # Non-retryable

        # Mark as sent before making API call (optimistic)
        history_manager = services.user_history_manager
        if history_manager:
             history_manager.mark_as_sent_to_cloud(history_id)
        else:
             logger.error("UserHistoryManager service not available in SyncService. Cannot mark as sent.")
             # Proceed with API call anyway, but log this issue.

        # Call Groq Client with the prompt
        try:
             groq_client = GroqClient()
             logger.info(f"Calling GroqClient.generate_report_from_prompt for history_id {history_id}")
             cloud_report = groq_client.generate_report_from_prompt(local_prompt)
        except ValueError as key_error:
             logger.error(f"Failed to initialize GroqClient: {key_error}. Cannot process item {history_id}.")
             return False # Don't retry if key is missing
        except Exception as client_err:
             logger.error(f"Unexpected error creating GroqClient or calling generate_report: {client_err}", exc_info=True)
             return False # Allow retry

        if cloud_report and not cloud_report.get("error"):
            logger.info(f"Successfully received cloud report for history_id {history_id}.")
            # TODO: Send report to actual cloud DB if needed
            logger.info("Placeholder: Sending report to cloud DB...")
            cloud_db_success = True 

            if cloud_db_success:
                 if history_manager:
                      update_success = history_manager.update_with_cloud_report(history_id, cloud_report)
                      if update_success:
                           logger.info(f"Successfully updated local answer_history for {history_id} with cloud report.")
                           return True 
                      else:
                           logger.error(f"Failed to update local answer_history for {history_id} after receiving cloud report.")
                           return False 
                 else:
                      logger.error("UserHistoryManager service not available to update local DB after successful Groq call.")
                      return False 
            else:
                 logger.error(f"Failed to store cloud report in cloud database for history_id {history_id}.")
                 return False 
        else:
            error_detail = cloud_report.get('error', 'Unknown Groq error') if cloud_report else 'Groq call returned None'
            logger.error(f"Failed to generate cloud report via Groq for history_id {history_id}. Error: {error_detail}")
            return False 

    def queue_cloud_analysis(self, history_id: int, local_prompt: str) -> bool: 
        """Queues an item for cloud analysis."""
        if not local_prompt:
            logger.error(f"Cannot queue cloud analysis for history_id {history_id}: Local prompt is missing.")
            return False

        logger.info(f"Queueing cloud analysis request for history_id: {history_id}")
        item_data = {
            "history_id": history_id,
            "local_prompt": local_prompt 
        }
        item_type = 'cloud_analysis_request'
        priority = QueuePriority.HIGH 

        try:
            # Ensure queue_manager is accessed via services like other parts of the code
            queue_manager = services.queue_manager
            history_manager = services.user_history_manager
            if queue_manager:
                queue_manager.add_to_queue(item_data, item_type, priority)
                if history_manager:
                     history_manager.mark_as_queued_for_cloud(history_id)
                else:
                     logger.warning(f"Could not mark history {history_id} as queued: UserHistoryManager not found.")
                return True
            else:
                logger.error("QueueManager service is not available. Cannot queue cloud analysis.")
                return False
        except Exception as e:
            logger.error(f"Failed to add cloud analysis request to queue for history_id {history_id}: {e}", exc_info=True)
            return False

    def _perform_initial_db_scan_and_queue_cloud_reports(self):
        """
        Scans the database for all preliminary reports that need cloud analysis,
        reconstructs their prompts, checks for duplicates in the QueueManager, 
        and queues new ones. This is run once per online session.
        """
        logger.info("SyncService: Performing one-time DB scan to queue all pending cloud analysis reports.")
        if not services.user_history_manager or not services.cache_manager or not services.queue_manager:
            logger.error("SyncService: UserHistoryManager, CacheManager, or QueueManager not available. Cannot perform initial DB scan.")
            return

        total_newly_queued = 0
        fetch_limit = 50  # Process in batches from DB
        processed_db_history_ids_this_scan = set() # To avoid re-processing a DB item if get_pending_cloud_analysis_items is not perfectly stateful across calls

        while self._running and self._network_monitor.get_status() == NetworkStatus.ONLINE:
            try:
                # Fetch items not yet marked as 'queued_for_cloud' or 'sent_to_cloud' or 'cloud_sync_failed'
                # The get_pending_cloud_analysis_items should ideally handle this filtering.
                pending_db_items = services.user_history_manager.get_pending_cloud_analysis_items(limit=fetch_limit)

                if not pending_db_items:
                    logger.info("SyncService: No more pending reports found in DB for initial scan pass.")
                    break

                logger.debug(f"SyncService: Fetched {len(pending_db_items)} items from DB for initial cloud analysis queuing.")
                batch_newly_queued = 0

                for history_id, cached_question_key in pending_db_items:
                    if not (self._running and self._network_monitor.get_status() == NetworkStatus.ONLINE):
                        logger.info("SyncService: Aborting initial DB scan due to service stop or network offline.")
                        return
                    
                    if history_id in processed_db_history_ids_this_scan:
                        continue # Already processed this history_id in the current scan execution
                    processed_db_history_ids_this_scan.add(history_id)

                    # Check if this history_id (for cloud analysis) is already in the QueueManager's queue
                    is_already_queued = False
                    for q_item in services.queue_manager.queue: # Iterate over a copy or ensure thread safety if queue can change
                        if q_item.type == 'cloud_analysis_request' and q_item.data.get('history_id') == history_id:
                            is_already_queued = True
                            break
                    
                    if is_already_queued:
                        logger.debug(f"SyncService: history_id {history_id} is already in QueueManager. Skipping duplicate queueing.")
                        # Ensure its DB status reflects it's queued if not already
                        services.user_history_manager.ensure_marked_as_queued_for_cloud(history_id) # Conceptual, UserHistoryManager might need this
                        continue

                    logger.debug(f"SyncService: Reconstructing prompt for history_id: {history_id}, question_key: {cached_question_key}")
                    question_data_dict = services.cache_manager.get_question_details_by_key(cached_question_key)
                    student_answer_json = services.user_history_manager.get_user_answer_json(history_id)
                    correct_answer_dict = services.cache_manager.get_correct_answer_details(cached_question_key)

                    if not student_answer_json:
                        logger.warning(f"SyncService: Missing student_answer_json for history_id {history_id} from DB scan. Cannot reconstruct prompt.")
                        services.user_history_manager.mark_cloud_sync_failed(history_id, reason="DBScan: Missing student answer")
                        continue
                    try:
                        student_answer_dict = json.loads(student_answer_json)
                    except json.JSONDecodeError as jde:
                        logger.error(f"SyncService: Failed to decode student_answer_json for history_id {history_id} (initial scan): {jde}")
                        services.user_history_manager.mark_cloud_sync_failed(history_id, reason="Invalid student answer JSON (initial scan)")
                        continue

                    if question_data_dict and student_answer_dict and correct_answer_dict:
                        prelim_report_text, prompt_for_groq = run_ai_evaluation(
                            question_data=question_data_dict,
                            correct_answer_data=correct_answer_dict,
                            user_answer=student_answer_dict,
                            marks=question_data_dict.get('marks')
                        )
                        if prompt_for_groq:
                            if prelim_report_text and isinstance(prelim_report_text, str):
                                services.user_history_manager.update_preliminary_report_text(history_id, prelim_report_text)
                            
                            if self.queue_cloud_analysis(history_id, prompt_for_groq): # This method calls mark_as_queued_for_cloud
                                batch_newly_queued += 1
                            else:
                                logger.error(f"SyncService: Failed to queue cloud analysis for history_id {history_id} during initial scan.")
                        else:
                            logger.warning(f"SyncService: Prompt reconstruction failed for history_id {history_id} (initial scan).")
                            services.user_history_manager.mark_cloud_sync_failed(history_id, reason="Prompt reconstruction failed (initial scan)")
                    else:
                        missing = [p for p,d in [("Q",question_data_dict),("SA",student_answer_dict),("CA",correct_answer_dict)] if not d]
                        logger.warning(f"SyncService: Missing data for prompt reconstruction (history_id {history_id}, initial scan): {missing}")
                        services.user_history_manager.mark_cloud_sync_failed(history_id, reason=f"Missing data for prompt (initial scan): {missing}")
                
                total_newly_queued += batch_newly_queued
                if batch_newly_queued > 0:
                     logger.info(f"SyncService: Queued {batch_newly_queued} new reports in this DB batch for cloud analysis.")
                
                if len(pending_db_items) < fetch_limit: # Fetched less than limit, so assume DB is exhausted for now
                    break
            
            except sqlite3.Error as db_err:
                logger.error(f"SyncService: Database error during initial scan: {db_err}", exc_info=True)
                # Potentially break or sleep and retry the whole scan later if critical
                break 
            except Exception as e:
                logger.error(f"SyncService: Unexpected error during initial DB scan loop: {e}", exc_info=True)
                break # Break on other unexpected errors to prevent hammering

        if total_newly_queued > 0:
            logger.info(f"SyncService: Initial DB scan finished. Total {total_newly_queued} new reports were queued for cloud analysis.")
        else:
            logger.info("SyncService: Initial DB scan finished. No new reports from DB were added to the queue in this pass.")

    def sync_student_activity_report(self):
        """
        Syncs the student's entire activity report (answered questions, reports, grades)
        to the 'examiner-reports' collection in Firestore.
        """
        if not self._network_monitor or self._network_monitor.get_status() != NetworkStatus.ONLINE:
            logger.info("SyncService: Network offline or monitor unavailable, skipping student activity report sync.")
            return

        if not self.firebase:
            logger.error("SyncService: Firebase client not available for student activity sync.")
            return
        
        if not services.user_history_manager:
            logger.error("SyncService: UserHistoryManager not available for student activity sync.")
            return

        logger.info("SyncService: Attempting to sync student activity report.")
        current_user_data = services.user_history_manager.get_current_user()
        if not current_user_data:
            logger.error("SyncService: Could not get current user from local DB for activity sync.")
            return
        
        local_user_id = current_user_data.get('id')
        # Use hardware_id from UserHistoryManager if available, otherwise from HardwareIdentifier
        hardware_id = current_user_data.get('hardware_id') or HardwareIdentifier.get_hardware_id()
        username = current_user_data.get('full_name', 'Unknown User')

        if not local_user_id or not hardware_id:
            logger.error(f"SyncService: Missing local_user_id ('{local_user_id}') or hardware_id ('{hardware_id}') for activity sync.")
            return

        all_answered_questions_py = services.user_history_manager.get_all_student_activity_for_sync(local_user_id)
        logger.info(f"SyncService: Found {len(all_answered_questions_py)} answered questions for user {local_user_id} (HWID: {hardware_id}) to sync.")
        current_sync_utc_dt = datetime.now(timezone.utc)
        existing_report_py = self.firebase.get_examiner_report(hardware_id)

        if existing_report_py is not None: 
            logger.info(f"SyncService: Existing examiner-report found for {hardware_id}. Updating.")
            
            updates_for_firebase = {
                "lastSyncTimestamp": current_sync_utc_dt,
                "username": username 
            }            
            success = self.firebase.update_examiner_report(
                hardware_id=hardware_id,
                updates_py=updates_for_firebase,
                new_answered_questions_py=all_answered_questions_py 
            )
            if success:
                logger.info(f"SyncService: Successfully updated examiner-report for {hardware_id}.")
            else:
                logger.error(f"SyncService: Failed to update examiner-report for {hardware_id}.")
        else:
            logger.info(f"SyncService: No examiner-report found for {hardware_id}. Creating new one.")
            
            new_report_data_py = {
                "hardwareID": hardware_id, 
                "username": username,
                "lastSyncTimestamp": current_sync_utc_dt,
                "answeredQuestions": all_answered_questions_py if all_answered_questions_py else []
            }
            
            success = self.firebase.create_examiner_report(
                hardware_id=hardware_id, 
                report_data_py=new_report_data_py
            )
            if success:
                logger.info(f"SyncService: Successfully created examiner-report for {hardware_id}.")
            else:
                logger.error(f"SyncService: Failed to create examiner-report for {hardware_id}.")
        
        if success:
            self.last_student_activity_sync_time = time.time()

    def _process_queue(self):
        """Handles processing items from the queue manager."""
        if self._queue_manager:
            item = self._queue_manager.get_item()
            if item:
                logger.info(f"SyncService: Processing item type {item.type.value} from queue.")
                # ... (your existing item processing logic for other types) ...
                # Example:
                # if item.type == QueueItemType.EXAM_RESULT:
                #    self._sync_exam_result(item)
                # elif item.type == QueueItemType.QUESTION_RESPONSE:
                #    self._sync_question_response(item)
                
                # Mark item as processed or handle error
                # self._queue_manager.mark_processed(item.id) or self._queue_manager.mark_failed(item.id)
                return True # Item was processed
        return False # No item processed

    def run(self):
        logger.info("SyncService: Starting main sync loop.")
        if not hasattr(self, '_stop_event'): self._stop_event = threading.Event() 
        if not hasattr(self, 'sync_interval'): self.sync_interval = 5 
        if not hasattr(self, 'initial_online_sync_done'): self.initial_online_sync_done = False
        if not hasattr(self, 'last_student_activity_sync_time'): self.last_student_activity_sync_time = 0
        if not hasattr(self, 'student_activity_sync_interval'): self.student_activity_sync_interval = 900

        while not self._stop_event.is_set():
            try:
                is_online = self._network_monitor and self._network_monitor.get_status() == NetworkStatus.ONLINE
                
                if is_online:
                    if not self.initial_online_sync_done:
                        logger.info("SyncService: Network online, performing initial sync tasks.")
                        self.sync_student_activity_report() 
                        self.initial_online_sync_done = True
                    queue_had_items = self._process_queue()                    
                    current_time = time.time()
                    if (not queue_had_items and 
                        current_time - self.last_student_activity_sync_time > self.student_activity_sync_interval):
                        logger.info("SyncService: Performing periodic student activity report sync.")
                        self.sync_student_activity_report()
                
                else: 
                    if self.initial_online_sync_done: 
                        logger.info("SyncService: Network offline. Pausing proactive sync tasks.")
                    self.initial_online_sync_done = False 

                time.sleep(self.sync_interval)
            except Exception as e:
                logger.error(f"SyncService: Unhandled error in main sync loop: {e}", exc_info=True)
                time.sleep(self.sync_interval * 5)
        logger.info("SyncService: Exiting main sync loop.")
