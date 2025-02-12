from enum import Enum
from datetime import datetime, date
from typing import Dict, List, Any, Optional
import json
import os
import logging

logger = logging.getLogger(__name__)

class QueuePriority(Enum):
    HIGH = 3    
    MEDIUM = 2  
    LOW = 1    

class QueueStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    FAILED = "failed"
    COMPLETED = "completed"

class QueueItem:
    def __init__(self, data: Dict[str, Any], item_type: str, priority: QueuePriority):
        self.id = data.get('hardware_id')
        self.type = item_type
        self.data = data  # Store the complete data dictionary
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.status = QueueStatus.PENDING
        self.priority = priority
        self.attempts = 0
        self.retry_count = 0
        self.max_retries = 3
        self.last_attempt = None

class QueueManager:
    QUEUE_FILE = "sync_queue.json"
    
    def __init__(self):
        self.queue: List[QueueItem] = []
        self.max_retries = 3
        self.load_queue()

    def load_queue(self) -> None:
        """Load queue from file and convert to QueueItem objects"""
        try:
            if os.path.exists(self.QUEUE_FILE):
                with open(self.QUEUE_FILE, 'r') as f:
                    raw_queue = json.load(f)
                    # Convert raw dictionaries to QueueItem objects
                    self.queue = [
                        QueueItem(
                            data=item['data'],
                            item_type=item['type'],
                            priority=QueuePriority.HIGH  # Default to HIGH for existing items
                        ) for item in raw_queue
                    ]
            else:
                self.queue = []
        except Exception as e:
            logger.error(f"Error loading queue: {e}")
            self.queue = []

    def _serialize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Python objects to JSON-serializable format"""
        serialized = {}
        for key, value in data.items():
            if isinstance(value, (datetime, date)):
                serialized[key] = value.isoformat()
            elif isinstance(value, dict):
                serialized[key] = self._serialize_data(value)  # Recursively serialize nested dicts
            elif value is None:
                serialized[key] = None
            else:
                serialized[key] = value
        return serialized

    def save_queue(self) -> None:
        """Save queue to file with proper serialization"""
        try:
            serializable_queue = []
            for item in self.queue:
                if isinstance(item, QueueItem):
                    serialized_item = {
                        'type': item.type,
                        'data': self._serialize_data(item.data),
                        'created_at': item.created_at.isoformat(),
                        'attempts': item.attempts,
                        'priority': item.priority.value if item.priority else None
                    }
                    serializable_queue.append(serialized_item)

            with open(self.QUEUE_FILE, 'w') as f:
                json.dump(serializable_queue, f, indent=2)
                logger.debug(f"Queue saved successfully with {len(serializable_queue)} items")
        except Exception as e:
            logger.error(f"Error saving queue: {e}")

    def add_to_queue(self, data: Dict[str, Any], item_type: str, priority: QueuePriority) -> str:
        """Add item and trigger sync if needed"""
        hardware_id = data.get('hardware_id')
        
        # Check for existing item
        for existing_item in self.queue:
            if existing_item.id == hardware_id and existing_item.type == item_type:
                logger.info(f"Item with hardware_id {hardware_id} already exists in queue. Skipping.")
                return hardware_id
        
        # Create new QueueItem
        queue_item = QueueItem(data=data, item_type=item_type, priority=priority)
        self.queue.append(queue_item)
        self.save_queue()
        
        # Start sync service if this is the first item
        if len(self.queue) == 1:
            from src.core.network.sync_service import SyncService
            sync_service = SyncService()
            sync_service.start()
        
        return hardware_id

    def get_next_item(self) -> Optional[QueueItem]:
        """Get next item from queue"""
        if self.queue:
            item = self.queue[0]
            logger.debug(f"Retrieved queue item: {item}")
            return item
        logger.debug("Queue is empty")
        return None

    def remove_item(self, item: QueueItem) -> None:
        """Remove item from queue"""
        if item in self.queue:
            self.queue.remove(item)
            self.save_queue()

    def update_item(self, item: QueueItem) -> None:
        """Update item in queue"""
        if item in self.queue:
            index = self.queue.index(item)
            self.queue[index] = item
            self.save_queue()

    def mark_completed(self, hardware_id: str) -> None:
        """Mark item as completed and remove from queue"""
        for item in self.queue:
            if item.id == hardware_id:
                self.queue.remove(item)
                self.save_queue()
                logger.info(f"Marked item {hardware_id} as completed")
                break

    def mark_failed(self, hardware_id: str) -> None:
        """Mark item as failed, update attempts"""
        for item in self.queue:
            if isinstance(item, QueueItem) and item.id == hardware_id:
                item.attempts += 1
                if item.attempts >= self.max_retries:
                    self.queue.remove(item)
                    logger.warning(f"Item {hardware_id} exceeded max retries, removed from queue")
                else:
                    logger.warning(f"Item {hardware_id} failed, attempt {item.attempts}")
                self.save_queue()
                break

    def _get_item_by_id(self, item_id: str) -> QueueItem:
        return next((item for item in self.queue if item.id == item_id), None)

    def has_pending_items(self) -> bool:
        """Check if there are items needing sync"""
        return len(self.queue) > 0

