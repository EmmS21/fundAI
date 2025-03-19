from enum import Enum
from datetime import datetime, date
from typing import Dict, List, Any, Optional
import json
import os
import logging
import uuid

logger = logging.getLogger(__name__)

class QueuePriority(Enum):
    """Priority levels for sync queue items, from highest to lowest"""
    CRITICAL = 1  # Final reports/scores (T1)
    HIGH = 2      # Question cache updates (T2)
    MEDIUM = 3    # System metrics (T3)
    LOW = 4       # User profile changes (T4)

class QueueStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    FAILED = "failed"
    COMPLETED = "completed"

class QueueItem:
    """Represents an item in the sync queue"""
    
    def __init__(self, data: Dict[str, Any], item_type: str, priority: QueuePriority = QueuePriority.MEDIUM):
        self.id = data.get('hardware_id', str(uuid.uuid4()))
        self.type = item_type
        self.data = data
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.status = QueueStatus.PENDING
        self.priority = priority
        self.attempts = 0
        self.retry_count = 0
        self.max_retries = 3
        self.last_attempt = None
        self.batch_id = data.get('batch_id', None) 

    def increment_attempts(self):
        """Increment the number of sync attempts"""
        self.attempts += 1

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
                    self.queue = []
                    for item in raw_queue:
                        priority = QueuePriority.MEDIUM  # Default
                        if item.get('priority'):
                            try:
                                priority = QueuePriority(item['priority'])
                            except ValueError:
                                pass
                        
                        queue_item = QueueItem(
                            data=item['data'],
                            item_type=item['type'],
                            priority=priority
                        )
                        queue_item.created_at = datetime.fromisoformat(item['created_at'])
                        queue_item.attempts = item['attempts']
                        if 'batch_id' in item:
                            queue_item.batch_id = item['batch_id']
                        self.queue.append(queue_item)
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
                serialized[key] = self._serialize_data(value)  
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
                        'priority': item.priority.value if item.priority else None,
                        'batch_id': item.batch_id
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
    
    def add_batch_to_queue(self, items: List[Dict[str, Any]], item_type: str, priority: QueuePriority) -> str:
        """Add multiple related items as a batch"""
        if not items:
            return None
            
        # Generate a batch ID
        batch_id = str(uuid.uuid4())
        
        # Add batch ID to each item
        for item in items:
            item['batch_id'] = batch_id
            self.add_to_queue(item, item_type, priority)
            
        return batch_id
    
    def get_next_item(self) -> Optional[QueueItem]:
        """Get the next item to process based on priority"""
        if not self.queue:
            return None
            
        # Sort by priority (lowest value = highest priority) then by creation time
        self.queue.sort(key=lambda x: (x.priority.value, x.created_at))
        
        # Return the highest priority item
        return self.queue[0] if self.queue else None
    
    def get_batch_items(self, batch_id: str) -> List[QueueItem]:
        """Get all items belonging to a specific batch"""
        return [item for item in self.queue if item.batch_id == batch_id]
    
    def mark_completed(self, item_id: str) -> None:
        """Mark an item as successfully synced"""
        self.queue = [item for item in self.queue if item.id != item_id]
        self.save_queue()
    
    def mark_batch_completed(self, batch_id: str) -> None:
        """Mark all items in a batch as completed"""
        self.queue = [item for item in self.queue if item.batch_id != batch_id]
        self.save_queue()
    
    def mark_failed(self, item_id: str) -> None:
        """Mark an item as failed after max retries"""
        for item in self.queue:
            if item.id == item_id:
                item.increment_attempts()
                if item.attempts >= self.max_retries:
                    logger.warning(f"Item {item_id} failed after {self.max_retries} attempts. Removing from queue.")
                    self.queue = [i for i in self.queue if i.id != item_id]
                self.save_queue()
                break

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

    def _get_item_by_id(self, item_id: str) -> QueueItem:
        return next((item for item in self.queue if item.id == item_id), None)

    def has_pending_items(self) -> bool:
        """Check if there are items needing sync"""
        return len(self.queue) > 0

