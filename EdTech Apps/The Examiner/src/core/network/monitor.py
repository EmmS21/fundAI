from typing import Callable, List
import urllib.request
import socket
import threading
import time
from enum import Enum
from datetime import datetime
import logging
from threading import Thread, Event

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NetworkStatus(Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    UNKNOWN = "unknown"

class Signal:
    """Simple signal class to support the connect/disconnect pattern"""
    def __init__(self):
        self._callbacks = []
        
    def connect(self, callback):
        """Connect a callback to this signal"""
        if callback not in self._callbacks:
            self._callbacks.append(callback)
            return True
        return False
        
    def disconnect(self, callback):
        """Disconnect a callback from this signal"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
            return True
        return False
        
    def emit(self, *args, **kwargs):
        """Emit the signal, calling all connected callbacks"""
        for callback in self._callbacks:
            try:
                callback(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in signal callback {callback}: {e}")

class NetworkMonitor:
    def __init__(self):
        self._callbacks = []
        self._status = NetworkStatus.UNKNOWN
        self._stop_flag = Event()
        self._monitor_thread = None
        self.CHECK_INTERVAL = 300  # 5 minutes default
        
        # Add the status_changed signal
        self.status_changed = Signal()
        
        # Settling time parameters
        self.SETTLING_TIME = 5  # Seconds to wait before confirming a status change
        self._potential_status = None
        self._status_change_time = None

    def start(self):
        """Start monitoring only when needed"""
        if not self._stop_flag.is_set():
            self._stop_flag.clear()
            self._monitor_thread = Thread(target=self._monitor_loop)
            self._monitor_thread.daemon = True
            self._monitor_thread.start()
            logger.info("Network monitoring started")

    def stop(self):
        """Stop monitoring gracefully"""
        self._stop_flag.set()
        if self._monitor_thread and self._monitor_thread.is_alive():
            try:
                self._monitor_thread.join(timeout=1.0)  # Wait up to 1 second
            except RuntimeError:
                # Handle case where thread is current thread
                pass
        logger.info("Network monitoring stopped")

    def register_callback(self, callback):
        """Register a callback to be called on network status change"""
        if callback not in self._callbacks:
            self._callbacks.append(callback)
            logger.debug(f"Registered callback: {callback}")
            
        # Also register with the signal for compatibility
        self.status_changed.connect(callback)

    def unregister_callback(self, callback):
        """Remove a callback"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
            logger.debug(f"Unregistered callback: {callback}")
            
        # Also unregister from the signal
        self.status_changed.disconnect(callback)

    def get_status(self) -> NetworkStatus:
        """Get current network status"""
        return self._status

    def _check_connection(self) -> bool:
        """Check if we have internet connection"""
        try:
            # Try to connect to a reliable host
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            return True
        except OSError:
            try:
                # Fallback to HTTP request
                urllib.request.urlopen("http://www.google.com", timeout=3)
                return True
            except:
                return False

    def _monitor_loop(self):
        """Monitor network and stop when no longer needed"""
        while not self._stop_flag.is_set():
            current_status = NetworkStatus.ONLINE if self._check_connection() else NetworkStatus.OFFLINE
            
            # Different handling based on whether we're in a settling period
            if self._potential_status is None:
                # Not in a settling period - check if status has changed
                if current_status != self._status:
                    # Start settling period
                    self._potential_status = current_status
                    self._status_change_time = time.time()
                    logger.debug(f"Potential network status change detected: {self._status} -> {current_status}")
            else:
                # In settling period - check if status is consistent
                if current_status == self._potential_status:
                    # Check if settling time has elapsed
                    elapsed = time.time() - self._status_change_time
                    if elapsed >= self.SETTLING_TIME:
                        # Settling time has elapsed, confirm the status change
                        logger.info(f"Network status changed from {self._status} to {self._potential_status} after {elapsed:.1f}s settling time")
                        self._status = self._potential_status
                        self._potential_status = None
                        self._status_change_time = None
                        self._notify_callbacks()
                else:
                    # Status changed during settling period, reset settling period
                    if current_status != self._status:
                        # Start a new settling period
                        logger.debug(f"Network status fluctuated during settling period, resetting ({self._potential_status} -> {current_status})")
                        self._potential_status = current_status
                        self._status_change_time = time.time()
                    else:
                        # Status reverted to original, cancel settling period
                        logger.debug(f"Network status reverted during settling period, canceling change")
                        self._potential_status = None
                        self._status_change_time = None
            
            # Shorter sleep interval during settling period
            if self._potential_status is not None:
                time.sleep(min(1.0, self.SETTLING_TIME / 5))  # Check more frequently during settling
            else:
                time.sleep(self.CHECK_INTERVAL)

    def _notify_callbacks(self):
        """Notify all registered callbacks of current status"""
        for callback in self._callbacks:
            try:
                callback(self._status)
            except Exception as e:
                logger.error(f"Error in callback {callback}: {e}")
                
        # Also emit the signal
        self.status_changed.emit(self._status)
        
    def set_settling_time(self, seconds: float):
        """
        Set the settling time in seconds.
        
        Args:
            seconds: Time in seconds to wait before confirming a status change
        """
        if seconds < 0:
            raise ValueError("Settling time cannot be negative")
        self.SETTLING_TIME = seconds
        logger.info(f"Network monitor settling time set to {seconds} seconds")

