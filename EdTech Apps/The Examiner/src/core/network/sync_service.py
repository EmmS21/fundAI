from typing import Optional, Dict, Any
from datetime import datetime, timedelta, date
import logging
from ..queue_manager import QueueManager, QueueStatus
from .monitor import NetworkMonitor, NetworkStatus
import firebase
from ..firebase.client import FirebaseClient
from ...utils.hardware_identifier import HardwareIdentifier
import backoff 
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
    _instance: Optional['SyncService'] = None
    MAX_RETRIES = 3
    RETRY_DELAY = 5  # seconds
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self._queue_manager = QueueManager()
        self._network_monitor = NetworkMonitor()
        self._network_monitor.add_callback(self._handle_network_change)
        self.firebase = FirebaseClient()
        _, _, self.hardware_id = HardwareIdentifier.get_hardware_id()
        
    def start(self):
        """Start the sync service"""
        self._network_monitor.start()
        logger.info("Sync service started")

    def stop(self):
        """Stop the sync service"""
        self._network_monitor.stop()
        logger.info("Sync service stopped")

    def _handle_network_change(self, status: NetworkStatus):
        """Handle network status changes"""
        if status == NetworkStatus.ONLINE:
            self._process_queue()

    def _process_queue(self):
        """Process pending items in the queue"""
        while True:
            item = self._queue_manager.get_next_item()
            if not item:
                break

            try:
                # TODO: Implement actual sync logic here
                if item.type == 'user':
                    self._sync_with_retry(self._sync_user_data, item)
                elif item.type == 'exam_result':
                    self._sync_with_retry(self._sync_exam_result, item)
                
                self._queue_manager.mark_completed(item.id)
                logger.info(f"Successfully synced item: {item.id}")
                
            except Exception as e:
                logger.error(f"Failed to sync item {item.id}: {e}")
                self._queue_manager.mark_failed(item.id)

    def _sync_with_retry(self, operation_func, *args):
        """Generic retry mechanism for sync operations"""
        attempts = 0
        last_error = None

        while attempts < self.MAX_RETRIES:
            try:
                return operation_func(*args)
            except Exception as e:
                attempts += 1
                last_error = e
                logger.warning(f"Sync attempt {attempts} failed: {e}")
                if attempts < self.MAX_RETRIES:
                    time.sleep(self.RETRY_DELAY)
                
        logger.error(f"All sync attempts failed: {last_error}")
        raise SyncError(f"Sync failed after {self.MAX_RETRIES} attempts")

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

    def _sync_user_data(self, item: Dict[str, Any]):
        """Sync user data using Firebase REST API"""
        try:
            user_data = {
                'full_name': item.data['full_name'],
                'birthday': item.data['birthday'],
                'country': item.data['country'],
                'school_level': item.data['school_level'],
                'grade': item.data['grade'],
                'hardware_id': self.hardware_id,
                'updated_at': datetime.now()
            }
            
            # Serialize the data before sending to Firebase
            serialized_data = self._serialize_data(user_data)
            
            path = f"examiner-users/{self.hardware_id}"
            self.firebase.update_data(path, serialized_data)
            logger.info(f"Successfully synced user data for hardware_id: {self.hardware_id}")
            
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
                if not item:
                    break

                try:
                    if item.type == 'user':
                        self._sync_with_retry(self._sync_user_data, item)
                    elif item.type == 'exam_result':
                        self._sync_with_retry(self._sync_exam_result, item)
                    
                    self._queue_manager.mark_completed(item.id)
                    
                except (SyncError, ConflictError) as e:
                    logger.error(f"Failed to sync item {item.id}: {e}")
                    self._queue_manager.mark_failed(item.id)

        except Exception as e:
            logger.error(f"Error during sync_all: {e}")
            raise
