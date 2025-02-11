from typing import Callable, List
import urllib.request
import socket
import threading
import time
from enum import Enum
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NetworkStatus(Enum):
    ONLINE = "online"
    OFFLINE = "offline"

class NetworkMonitor:
    def __init__(self, check_interval: int = 300):  # 5 minutes default
        self._status = NetworkStatus.OFFLINE
        self._check_interval = check_interval
        self._callbacks: List[Callable[[NetworkStatus], None]] = []
        self._stop_flag = threading.Event()
        self._monitor_thread = None
        self._last_check = None
        
    def start(self):
        """Start network monitoring"""
        if self._monitor_thread is None:
            self._stop_flag.clear()
            self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self._monitor_thread.start()
            logger.info("Network monitoring started")

    def stop(self):
        """Stop network monitoring"""
        if self._monitor_thread is not None:
            self._stop_flag.set()
            self._monitor_thread.join()
            self._monitor_thread = None
            logger.info("Network monitoring stopped")

    def add_callback(self, callback: Callable[[NetworkStatus], None]):
        """Add callback for network status changes"""
        self._callbacks.append(callback)

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
        """Main monitoring loop"""
        while not self._stop_flag.is_set():
            current_status = NetworkStatus.ONLINE if self._check_connection() else NetworkStatus.OFFLINE
            
            # If status changed, notify callbacks
            if current_status != self._status:
                self._status = current_status
                self._last_check = datetime.now()
                logger.info(f"Network status changed to: {self._status.value}")
                
                # Notify all callbacks
                for callback in self._callbacks:
                    try:
                        callback(self._status)
                    except Exception as e:
                        logger.error(f"Error in network status callback: {e}")

            # Wait for next check
            self._stop_flag.wait(self._check_interval)
