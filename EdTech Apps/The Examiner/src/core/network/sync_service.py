from typing import Optional, Dict, Any
from datetime import datetime, date
import logging
from ..queue_manager import QueueManager, QueueStatus, QueueItem
from .monitor import NetworkMonitor, NetworkStatus
from ..firebase.client import FirebaseClient
from ...utils.hardware_identifier import HardwareIdentifier
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SyncError(Exception):
    """Custom exception for sync errors"""
    pass

class ConflictError(SyncError):
    """Raised when there's a conflict during sync"""
    pass

class SyncService:
    _instance = None
    MAX_RETRIES = 3
    RETRY_DELAY = 5  # seconds between retries

    def __init__(self):
        self._initialized = False
        self._network_monitor = None
        self._queue_manager = None
        self._monitor_thread = None
        self.firebase = None
        self.hardware_id = None

    def initialize(self):
        """Initialize only when needed"""
        if not self._initialized:
            self._queue_manager = QueueManager()
            self._network_monitor = NetworkMonitor()
            self.firebase = FirebaseClient()
            _, _, self.hardware_id = HardwareIdentifier.get_hardware_id()
            self._initialized = True

    def start(self):
        """Start the sync service"""
        if not self._initialized:
            self.initialize()
        
        self._network_monitor.register_callback(self._handle_network_change)
        self._network_monitor.start()
        logger.info("Sync service started")

    def stop(self):
        """Clean up resources properly"""
        if self._network_monitor:
            self._network_monitor.stop()
            # Give the thread time to clean up
            time.sleep(0.1)
        self._initialized = False
        logger.info("Sync service stopped")

    def _handle_network_change(self, status: NetworkStatus) -> None:
        """Handle network status change"""
        if status == NetworkStatus.ONLINE:
            try:
                self._process_queue()
            except Exception as e:
                logger.error(f"Error processing queue: {e}")

    def _process_queue(self):
        """Process pending items in queue"""
        while True:
            item = self._queue_manager.get_next_item()
            if not item:
                continue 

            try:
                if item.type == 'user':
                    self._sync_with_retry(self._sync_user_data, item)
                elif item.type == 'exam_result':
                    self._sync_with_retry(self._sync_exam_result, item)
                
                self._queue_manager.mark_completed(item.id)
            except Exception as e:
                logger.error(f"Failed to sync item {item.id}: {e}")
                self._queue_manager.mark_failed(item.id)

    def _sync_with_retry(self, sync_func, item):
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
            else:
                serialized[key] = value
        return serialized

    def _sync_user_data(self, item: QueueItem):
        """Sync user data to Firebase"""
        try:
            user_data = item.data.get('user_data')
            
            if not user_data:
                raise SyncError(f"No user data found in queue item: {item.data}")
            
            # Just use the collection name, the data already contains hardware_id
            path = "examiner-users"
            self.firebase.update_data(path, user_data)
            logger.info(f"Successfully synced user data")
            
        except Exception as e:
            logger.error(f"Failed to sync user data: {e}")
            raise

    def _sync_exam_result(self, item: Dict[str, Any]):
        """Sync exam result using Firebase REST API"""
        try:
            exam_data = {
                'exam_date': item.data['exam_date'],
                'exam_id': item.data['exam_id'],
                'grade': item.data['grade'],
                'hardware_id': self.hardware_id,
                'level': item.data['level'],
                'subject': item.data['subject'],
                'topics': item.data['topics'],
                'total_possible': item.data['total_possible'],
                'updated_at': datetime.now()
            }
            
            # Serialize the data before sending to Firebase
            serialized_data = self._serialize_data(exam_data)
            
            path = f"examiner-exam_results/{item.data['exam_id']}"
            self.firebase.update_data(path, serialized_data)
            logger.info(f"Successfully synced exam result: {item.data['exam_id']}")
            
        except Exception as e:
            logger.error(f"Failed to sync exam result: {e}")
            raise

    def sync_all(self):
        """Sync all pending items"""
        try:
            while True:
                item = self._queue_manager.get_next_item()
                logger.debug(f"Got next item from queue: {item}")
                if not item:
                    continue

                try:
                    if item['type'] == 'user':
                        logger.debug(f"Processing user sync item: {item}")
                        self._sync_with_retry(self._sync_user_data, item)
                    elif item['type'] == 'exam_result':
                        logger.debug(f"Processing exam result sync item: {item}")
                        self._sync_with_retry(self._sync_exam_result, item)
                    
                    logger.debug(f"Marking item as completed with hardware_id: {item['data']['hardware_id']}")
                    self._queue_manager.mark_completed(item['data']['hardware_id'])
                    
                except (SyncError, ConflictError) as e:
                    logger.error(f"Failed to sync item with hardware_id {item['data']['hardware_id']}: {e}")
                    self._queue_manager.mark_failed(item['data']['hardware_id'])
                except Exception as e:
                    logger.error(f"Unexpected error processing item: {item}. Error: {e}")
                    raise

        except Exception as e:
            logger.error(f"Error during sync_all: {e}")
            raise
