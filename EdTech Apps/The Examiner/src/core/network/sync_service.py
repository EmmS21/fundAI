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
                
            # Process batches first
            batch_ids = self.get_pending_batch_ids()
            if batch_ids:
                for batch_id in batch_ids[:self.BATCH_SIZE]:
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
        """Process all items in a batch together"""
        batch_items = self._queue_manager.get_batch_items(batch_id)
        if not batch_items:
            logger.warning(f"No items found for batch {batch_id}")
            return
            
        logger.info(f"Processing batch {batch_id} with {len(batch_items)} items")
        
        # Group items by type for efficient processing
        items_by_type = {}
        for item in batch_items:
            if item.type not in items_by_type:
                items_by_type[item.type] = []
            items_by_type[item.type].append(item)
        
        # Process each type of item
        success = True
        for item_type, items in items_by_type.items():
            try:
                if item_type == 'exam_result':
                    self._sync_batch_exam_results(items)
                elif item_type == 'question_response':
                    self._sync_batch_question_responses(items)
                elif item_type == 'question':
                    self._sync_batch_questions(items)
                elif item_type == 'user':
                    # Process user items individually
                    for item in items:
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
        else:
            # Mark individual items as failed
            for item in batch_items:
                self._queue_manager.mark_failed(item.id)

    def _process_item(self, item: QueueItem):
        """Process a single queue item"""
        try:
            if item.type == 'user':
                self._sync_with_retry(self._sync_user_data, item)
            elif item.type == 'exam_result':
                self._sync_with_retry(self._sync_exam_result, item)
            elif item.type == 'question_response':
                self._sync_with_retry(self._sync_question_response, item)
            elif item.type == 'question':
                self._sync_with_retry(self._sync_question, item)
            elif item.type == 'system_metrics':
                self._sync_with_retry(self._sync_system_metrics, item)
            else:
                logger.warning(f"Unknown item type: {item.type}")
                self._queue_manager.mark_failed(item.id)
                return
            
            self._queue_manager.mark_completed(item.id)
        except Exception as e:
            logger.error(f"Failed to process item {item.id}: {e}")
            self._queue_manager.mark_failed(item.id)

    def _sync_with_retry(self, sync_func: Callable, item: QueueItem) -> bool:
        """Retry sync operations with backoff"""
        retries = 0
        while retries < self.MAX_RETRIES:
            try:
                sync_func(item)
                return True
            except Exception as e:
                retries += 1
                logger.error(f"Sync attempt {retries} failed: {e}")
                if retries < self.MAX_RETRIES:
                    time.sleep(self.RETRY_DELAY)
        return False

    def _serialize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Python objects to JSON-serializable format"""
        serialized = {}
        for key, value in data.items():
            if isinstance(value, (datetime, date)):
                serialized[key] = value.isoformat()
            elif value is None:
                serialized[key] = None
            elif isinstance(value, dict):
                serialized[key] = self._serialize_data(value)
            elif isinstance(value, list):
                serialized[key] = [
                    self._serialize_data(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                serialized[key] = value
        return serialized

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
        """Sync a question from the server to local cache"""
        try:
            question_id = item.data['question_id']
            
            # Fetch question data from server
            path = f"questions/{question_id}"
            question_data = self.firebase.get_data(path)
            
            if not question_data:
                logger.warning(f"Question {question_id} not found on server")
                raise SyncError(f"Question {question_id} not found")
                
            # Fetch assets for this question
            assets_path = f"question_assets/{question_id}"
            assets_data = self.firebase.get_data(assets_path) or {}
            
            # Convert assets to list format
            assets = []
            for asset_id, asset_data in assets_data.items():
                assets.append({
                    'asset_id': asset_id,
                    'question_id': question_id,
                    'asset_type': asset_data['asset_type'],
                    'content': asset_data['content']
                })
                
            # Save to local cache
            success = self._cache_manager.save_question(question_data, assets)
            
            if not success:
                raise SyncError(f"Failed to save question {question_id} to cache")
                
            logger.info(f"Successfully synced question {question_id}")
            
        except Exception as e:
            logger.error(f"Failed to sync question: {e}")
            raise

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
        """Sync multiple questions"""
        # Questions need to be processed individually due to their assets
        for item in items:
            try:
                self._sync_question(item)
            except Exception as e:
                logger.error(f"Failed to sync question item {item.id}: {e}")
                self._queue_manager.mark_failed(item.id)

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
        """Queue multiple questions as a batch"""
        return self._queue_manager.add_batch_to_queue(
            items=questions,
            item_type='question',
            priority=QueuePriority.HIGH  # T2: Question cache updates
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
