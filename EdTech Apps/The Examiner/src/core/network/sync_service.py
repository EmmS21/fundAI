from typing import Optional, Dict, Any, List, Callable
from datetime import datetime, date
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

    def __new__(cls):
        """Singleton pattern to ensure only one instance exists"""
        if cls._instance is None:
            cls._instance = super(SyncService, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the sync service"""
        if self.initialized:
            return
            
        # Initialize components
        self._queue_manager = QueueManager()
        self._network_monitor = NetworkMonitor()
        
        # Register self in services registry
        services.sync_service = self
        
        # Thread control
        self._running = False
        self._sync_thread = None
        
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
            logger.info("Network is online, processing sync queue")
            # Ensure sync thread is running
            if not self._sync_thread or not self._sync_thread.is_alive():
                self._sync_thread = threading.Thread(target=self._sync_worker, daemon=True)
                self._sync_thread.start()
        else:
            logger.info("Network is offline, sync operations paused")

    def _sync_worker(self):
        """Background thread to process sync queue and proactively queue pending reports."""
        while self._running:
            if self._network_monitor.get_status() != NetworkStatus.ONLINE:
                time.sleep(5) # Wait for network
                continue
            
            # --- ADDED: Proactive check for pending reports ---
            # This should ideally run when the queue is empty or at intervals,
            # to avoid constant DB polling if the queue is busy.
            # For simplicity, let's try to run it if the queue is empty.
            if not self._queue_manager.has_pending_items(): # Check if queue is empty
                logger.info("SyncService: Queue is empty, checking for pending reports in DB to queue.")
                self._check_and_queue_pending_reports()
            # --- END ADDED ---
                
            adaptive_batch_size = self._network_monitor.get_recommended_batch_size(self.BATCH_SIZE)
            
            batch_ids = self.get_pending_batch_ids() # This should ideally be self._queue_manager.get_pending_batch_ids()
            if batch_ids:
                for batch_id in batch_ids[:adaptive_batch_size]:
                    self._process_batch(batch_id)
                # If batches were processed, continue to prioritize batch processing in the next iteration
                time.sleep(0.1) # Small delay to yield
                continue 
                
            item = self._queue_manager.get_next_item()
            if item:
                self._process_item(item)
            else:
                # No items in queue, and no pending items found by _check_and_queue_pending_reports
                # Or, _check_and_queue_pending_reports itself is now adding to the queue,
                # so get_next_item() might pick them up in subsequent iterations.
                time.sleep(1) 

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
            item_type = item.item_type
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
            if item.item_type == 'user_data':
                self._sync_with_retry(self._sync_user_data, item)
            elif item.item_type == 'exam_result':
                self._sync_with_retry(self._sync_exam_result, item)
            elif item.item_type == 'question_response':
                self._sync_with_retry(self._sync_question_response, item)
            elif item.item_type == 'question':
                self._sync_with_retry(self._sync_question, item)
            elif item.item_type == 'system_metrics':
                self._sync_with_retry(self._sync_system_metrics, item)
            elif item.item_type == 'cloud_analysis_request':
                self._sync_with_retry(self._sync_cloud_analysis_request, item)
            else:
                logger.warning(f"Unknown item type: {item.item_type}")
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
        logger.info(f"Starting cloud analysis sync for history_id: {item.data.get('history_id')}")

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

    def _check_and_queue_pending_reports(self, limit: int = 5):
        """
        Checks for preliminary reports in the database that haven't been queued
        for cloud analysis, reconstructs their prompts, and queues them.
        """
        logger.info("SyncService: Checking for pending reports to queue for cloud analysis...")
        if not services.user_history_manager or not services.cache_manager:
            logger.error("SyncService: UserHistoryManager or CacheManager not available. Cannot check for pending reports.")
            return

        try:
            pending_items = services.user_history_manager.get_pending_cloud_analysis_items(limit=limit)
            if not pending_items:
                logger.info("SyncService: No pending reports found in DB to queue.")
                return

            logger.info(f"SyncService: Found {len(pending_items)} pending reports to process for queueing.")
            queued_count = 0

            for history_id, cached_question_key in pending_items:
                logger.debug(f"SyncService: Processing pending history_id: {history_id}, cached_question_key: {cached_question_key}")

                question_data_dict = services.cache_manager.get_question_details_by_key(cached_question_key)
                student_answer_json = services.user_history_manager.get_user_answer_json(history_id)
                correct_answer_dict = services.cache_manager.get_correct_answer_details(cached_question_key)

                if not student_answer_json:
                    logger.warning(f"SyncService: Missing student_answer_json for history_id {history_id}. Skipping.")
                    continue
                
                student_answer_dict = json.loads(student_answer_json)

                if question_data_dict and student_answer_dict and correct_answer_dict:
                    # We need to pass data to run_ai_evaluation in the format it expects.
                    # It typically takes the main question text, details about sub-questions (if any),
                    # the student's answers (structured), and correct answer data.
                    # The `question_data_dict` from CacheManager should already be structured
                    # similarly to how it's loaded in QuestionView.
                    # `correct_answer_dict` is also the direct content.
                    
                    # Assuming run_ai_evaluation expects the main question data, 
                    # correct answer, student's answer dict, and marks.
                    # The `question_data_dict` should have 'content' and 'marks'.
                    # The `correct_answer_dict` is from `get_correct_answer_details`
                    # The `student_answer_dict` is from `get_user_answer_json`
                    
                    # This call is ONLY to get the `generated_prompt`. The `evaluation_results` are ignored here.
                    # If `run_ai_evaluation` has side effects or is too heavy,
                    # consider extracting its prompt-building logic into a separate utility.
                    logger.debug(f"SyncService: Reconstructing prompt for history_id {history_id} using question_key {cached_question_key}")

                    _ , prompt_for_groq = run_ai_evaluation(
                        question_data=question_data_dict, # This is the dict from CachedQuestion
                        correct_answer_data=correct_answer_dict, # This is the dict from CachedAnswer
                        user_answer=student_answer_dict, # Dict of user's answers
                        marks=question_data_dict.get('marks') # Marks from the question
                    )

                    if prompt_for_groq:
                        logger.info(f"SyncService: Successfully reconstructed prompt for history_id {history_id}.")
                        if self.queue_cloud_analysis(history_id, prompt_for_groq):
                            queued_count += 1
                            # Mark as queued in DB to prevent re-fetching by this method
                            # before QueueManager processes it.
                            services.user_history_manager.mark_as_queued_for_cloud(history_id)
                        else:
                            logger.error(f"SyncService: Failed to queue cloud analysis for history_id {history_id} after reconstructing prompt.")
                    else:
                        logger.warning(f"SyncService: Failed to reconstruct prompt for history_id {history_id}. Necessary data might be missing or run_ai_evaluation failed.")
                else:
                    logger.warning(f"SyncService: Missing some data components for history_id {history_id}. "
                                   f"QuestionData: {bool(question_data_dict)}, "
                                   f"StudentAnswer: {bool(student_answer_dict)}, "
                                   f"CorrectAnswer: {bool(correct_answer_dict)}. Skipping.")
            
            if queued_count > 0:
                logger.info(f"SyncService: Queued {queued_count} pending reports for cloud analysis.")

        except Exception as e:
            logger.error(f"SyncService: Error in _check_and_queue_pending_reports: {e}", exc_info=True)
