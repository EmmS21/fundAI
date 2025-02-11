from enum import Enum
from datetime import datetime
from typing import Dict, List, Any
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
        self.id = f"{item_type}_{datetime.now().timestamp()}"
        self.data = data
        self.type = item_type
        self.priority = priority
        self.status = QueueStatus.PENDING
        self.retry_count = 0
        self.max_retries = 3
        self.created_at = datetime.now()
        self.last_attempt = None

class QueueManager:
    QUEUE_FILE = "sync_queue.json"
    
    def __init__(self):
        self.queue: List[Dict[str, Any]] = []
        self.load_queue()

    def load_queue(self) -> None:
        """Load queue from file, creating if doesn't exist"""
        try:
            if os.path.exists(self.QUEUE_FILE):
                with open(self.QUEUE_FILE, 'r') as f:
                    self.queue = json.load(f)
            else:
                # Initialize empty queue file
                self.save_queue()
                logger.info("Created new queue file")
        except json.JSONDecodeError:
            logger.warning("Queue file corrupted, creating new one")
            self.queue = []
            self.save_queue()
        except Exception as e:
            logger.error(f"Error loading queue: {e}")
            self.queue = []

    def save_queue(self) -> None:
        """Save queue to file"""
        try:
            with open(self.QUEUE_FILE, 'w') as f:
                json.dump(self.queue, f, default=str)
        except Exception as e:
            logger.error(f"Error saving queue: {e}")

    def add_item(self, item_type: str, data: Dict[str, Any]) -> None:
        """Add item to queue"""
        queue_item = {
            'type': item_type,
            'data': data,
            'created_at': datetime.now().isoformat(),
            'attempts': 0
        }
        self.queue.append(queue_item)
        self.save_queue()

    def get_next_item(self) -> Dict[str, Any]:
        """Get next item from queue"""
        if self.queue:
            return self.queue[0]
        return None

    def remove_item(self, item: Dict[str, Any]) -> None:
        """Remove item from queue"""
        if item in self.queue:
            self.queue.remove(item)
            self.save_queue()

    def update_item(self, item: Dict[str, Any]) -> None:
        """Update item in queue"""
        if item in self.queue:
            index = self.queue.index(item)
            self.queue[index] = item
            self.save_queue()

    def add_to_queue(self, data: Dict[str, Any], item_type: str, priority: QueuePriority) -> str:
        item = QueueItem(data, item_type, priority)
        self.queue.append(item)
        self.save_queue()
        return item.id

    def mark_failed(self, item_id: str):
        item = self._get_item_by_id(item_id)
        if item:
            item.retry_count += 1
            item.last_attempt = datetime.now()
            if item.retry_count >= item.max_retries:
                item.status = QueueStatus.FAILED
            self.save_queue()

    def mark_completed(self, item_id: str):
        item = self._get_item_by_id(item_id)
        if item:
            item.status = QueueStatus.COMPLETED
            self.save_queue()

    def _get_item_by_id(self, item_id: str) -> QueueItem:
        return next((item for item in self.queue if item['id'] == item_id), None)

