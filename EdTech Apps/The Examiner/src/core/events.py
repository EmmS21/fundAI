import logging
from typing import Callable, Dict, List, Any

logger = logging.getLogger(__name__)

class EventSystem:
    """Simple event system to allow components to communicate without direct dependencies"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EventSystem, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance
    
    def __init__(self):
        if self.initialized:
            return
            
        self._subscribers = {}
        self.initialized = True
        logger.info("EventSystem initialized")
    
    def subscribe(self, event_name: str, callback: Callable):
        """Subscribe to an event"""
        if event_name not in self._subscribers:
            self._subscribers[event_name] = []
        
        if callback not in self._subscribers[event_name]:
            self._subscribers[event_name].append(callback)
            logger.debug(f"Subscribed to event '{event_name}'")
            return True
        return False
    
    def unsubscribe(self, event_name: str, callback: Callable):
        """Unsubscribe from an event"""
        if event_name in self._subscribers and callback in self._subscribers[event_name]:
            self._subscribers[event_name].remove(callback)
            logger.debug(f"Unsubscribed from event '{event_name}'")
            return True
        return False
    
    def publish(self, event_name: str, **kwargs):
        """Publish an event to all subscribers"""
        if event_name not in self._subscribers or not self._subscribers[event_name]:
            logger.debug(f"No subscribers for event '{event_name}'")
            return
        
        for callback in self._subscribers[event_name]:
            try:
                callback(**kwargs)
            except Exception as e:
                logger.error(f"Error in event callback for '{event_name}': {e}")

# Common event names
EVENT_NEW_ACTIVITY_TO_SYNC = "new_activity_to_sync"
EVENT_NETWORK_CONNECTED = "network_connected"
EVENT_NETWORK_DISCONNECTED = "network_disconnected"
EVENT_USER_PROFILE_UPDATED = "user_profile_updated"
