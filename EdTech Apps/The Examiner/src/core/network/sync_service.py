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
        """Background thread to process sync queue"""
        while self._running:
            if self._network_monitor.get_status() != NetworkStatus.ONLINE:
                # Sleep and check again if network is offline
                time.sleep(5)
                continue
                
            # Get adaptive batch size based on connection quality
            adaptive_batch_size = self._network_monitor.get_recommended_batch_size(self.BATCH_SIZE)
                
            # Process batches first
            batch_ids = self.get_pending_batch_ids()
            if batch_ids:
                # Only process up to adaptive_batch_size batches at a time
                for batch_id in batch_ids[:adaptive_batch_size]:
                    self._process_batch(batch_id)
                continue
                
            # Then process individual items
            item = self._queue_manager.get_next_item()
            if item:
                self._process_item(item)
            else:
                # No items in queue, sleep and check again
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
