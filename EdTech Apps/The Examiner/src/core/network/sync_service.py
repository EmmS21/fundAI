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
from src.core.events import EventSystem, EVENT_NEW_ACTIVITY_TO_SYNC, EVENT_NETWORK_CONNECTED, EVENT_NETWORK_DISCONNECTED

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
        self.firebase = FirebaseClient()  # Initialize Firebase client first
        
        # Register self in services registry
        services.sync_service = self
        
        # Thread control
        self._running = False
        self._sync_thread = None
        
        # Register for network status changes
        self._network_monitor.status_changed.connect(self._handle_network_change)
        
        # Subscribe to events
        self._event_system = EventSystem()
        self._event_system.subscribe(EVENT_NEW_ACTIVITY_TO_SYNC, self._handle_new_activity)
        
        # Activity sync timestamps
        self.last_student_activity_sync_time = 0
        self.student_activity_sync_interval = 900  # 15 minutes
        
        self.initialized = True
        logger.info("Sync Service initialized with Firebase client")

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
            
            # Emit network connected event
            self._event_system.publish(EVENT_NETWORK_CONNECTED)
            
            # Schedule activity sync
            self.last_student_activity_sync_time = time.time() - (self.student_activity_sync_interval - 60)
            
            # Ensure sync thread is running
            if not self._sync_thread or not self._sync_thread.is_alive():
                self._sync_thread = threading.Thread(target=self._sync_worker, daemon=True)
                self._sync_thread.start()
        else:
            logger.info("Network is offline, sync operations paused")
            # Emit network disconnected event
            self._event_system.publish(EVENT_NETWORK_DISCONNECTED)

    def _sync_worker(self):
        """Background thread to process sync queue."""
        while self._running:
            if self._network_monitor.get_status() != NetworkStatus.ONLINE:
                time.sleep(5)  # Wait for network
                continue
            
            # Only process queue items
            adaptive_batch_size = self._network_monitor.get_recommended_batch_size(self.BATCH_SIZE)
            
            batch_ids = self.get_pending_batch_ids()
            if batch_ids:
                for batch_id in batch_ids[:adaptive_batch_size]:
                    self._process_batch(batch_id)
                # If batches were processed, continue to prioritize batch processing
                time.sleep(0.1)  # Small delay to yield
                continue
            
            item = self._queue_manager.get_next_item()
            if item:
                self._process_item(item)
            else:
                # Check if it's time for periodic student activity sync
                current_time = time.time()
                if (current_time - self.last_student_activity_sync_time > self.student_activity_sync_interval):
                    logger.info("SyncService: Performing periodic student activity report sync.")
                    self.sync_student_activity_report()
                    self.last_student_activity_sync_time = current_time
                
                # No items in queue, sleep for a bit
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
        """Process a single queue item"""
        if item.type == "student_activity":
            success = self._sync_student_activity(item)
        elif item.type == 'user_data':
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
        DEPRECATED: This polling method is replaced by event-driven sync.
        
        Checks for preliminary reports in the database that haven't been queued
        for cloud analysis, reconstructs their prompts, and queues them.
        """
        # This method is no longer needed with event-driven architecture
        # Events from UserHistoryManager.add_history_entry will trigger syncs instead
        logger.info("SyncService: Polling for reports is disabled. Using event-driven architecture instead.")
        return

    def sync_student_activity_report(self):
        """Sync student activity report to Firebase"""
        logger.info("Starting student activity report sync...")
        
        try:
            hardware_id = HardwareIdentifier.get_hardware_id()
            all_activity = services.user_history_manager.get_all_student_activity_for_sync(user_id=1)
            
            if not all_activity:
                logger.info("No activity to sync")
                return
            
            # Format data properly for Firestore
            timestamp = datetime.now(timezone.utc).isoformat()
            formatted_updates = {
                "lastSyncTimestamp": {"timestampValue": timestamp}
            }
            
            # Format each activity for Firestore
            formatted_activities = []
            for activity in all_activity:
                formatted_activity = {
                    "mapValue": {
                        "fields": {
                            k: self.firebase._to_firestore_value(v)
                            for k, v in activity.items()
                        }
                    }
                }
                formatted_activities.append(formatted_activity)
            
            # Check if report exists
            existing_report = self.firebase.get_examiner_report(hardware_id)
            
            if existing_report:
                success = self.firebase.update_examiner_report(
                    hardware_id=hardware_id,
                    updates=formatted_updates,
                    new_answered_questions=formatted_activities
                )
            else:
                # For new reports, we need to format the entire document
                report_data = {
                    "lastSyncTimestamp": timestamp,
                    "answeredQuestions": all_activity
                }
                success = self.firebase.create_examiner_report(
                    hardware_id=hardware_id,
                    report_data=report_data
                )
            
            if success:
                logger.info(f"Successfully synced {len(all_activity)} activities to Firebase")
            else:
                logger.error("Failed to sync activities to Firebase")
            
        except Exception as e:
            logger.error(f"Error syncing student activity report: {e}", exc_info=True)

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

    def _handle_new_activity(self, user_id: int, history_id: int):
        """Handle new activity event by queueing it for sync"""
        logger.info(f"Queueing new activity for sync: user_id={user_id}, history_id={history_id}")
        
        # Get the activity details from UserHistoryManager
        activity_data = services.user_history_manager.get_history_details_for_sync(history_id)
        if not activity_data:
            logger.error(f"Could not get activity details for history_id {history_id}")
            return
        
        # Queue the activity for sync
        self._queue_manager.add_item(
            item_type="student_activity",
            data={
                "user_id": user_id,
                "history_id": history_id,
                "activity_data": activity_data
            },
            priority=QueuePriority.NORMAL
        )

    def _sync_student_activity(self, item: QueueItem) -> bool:
        """Sync a student activity item to Firestore"""
        try:
            user_id = item.data["user_id"]
            history_id = item.data["history_id"]
            activity_data = item.data["activity_data"]
            
            # Get hardware ID for the user
            hardware_id = HardwareIdentifier.get_hardware_id()
            
            # Check if report exists
            existing_report = self.firebase.get_examiner_report(hardware_id)
            
            if existing_report:
                # Update existing report
                success = self.firebase.update_examiner_report(
                    hardware_id=hardware_id,
                    updates={"lastSyncTimestamp": datetime.now(timezone.utc).isoformat()},
                    new_answered_questions=[activity_data]
                )
            else:
                # Create new report
                success = self.firebase.create_examiner_report(
                    hardware_id=hardware_id,
                    report_data={
                        "lastSyncTimestamp": datetime.now(timezone.utc).isoformat(),
                        "answeredQuestions": [activity_data]
                    }
                )
            
            if success:
                # Mark the history entry as synced
                services.user_history_manager.mark_as_sent_to_cloud(history_id)
            
            return success
        except Exception as e:
            logger.error(f"Error syncing student activity: {e}")
            return False
