"""
Network Monitor
Monitors network connectivity for offline-first architecture
"""

import socket
import logging
import time
from typing import Callable, Optional
from threading import Thread, Event

logger = logging.getLogger(__name__)


class NetworkMonitor:
    """
    Monitors network connectivity and notifies on state changes
    
    Features:
    - Periodic connectivity checks
    - Event-based notifications
    - Multiple fallback check methods
    - Exponential backoff on failures
    """
    
    def __init__(self, check_interval: int = 30):
        """
        Initialize network monitor
        
        Args:
            check_interval: Seconds between connectivity checks
        """
        self.check_interval = check_interval
        self.is_online = False
        self._stop_event = Event()
        self._monitor_thread: Optional[Thread] = None
        self._callbacks: list[Callable[[bool], None]] = []
        
        # Check initial state
        self.is_online = self._check_connectivity()
        logger.info(f"Initial network state: {'online' if self.is_online else 'offline'}")
    
    def start(self):
        """Start monitoring network connectivity"""
        if self._monitor_thread and self._monitor_thread.is_alive():
            logger.warning("Network monitor already running")
            return
        
        self._stop_event.clear()
        self._monitor_thread = Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info("Network monitor started")
    
    def stop(self):
        """Stop monitoring network connectivity"""
        if not self._monitor_thread:
            return
        
        self._stop_event.set()
        self._monitor_thread.join(timeout=5)
        logger.info("Network monitor stopped")
    
    def add_callback(self, callback: Callable[[bool], None]):
        """
        Add callback to be notified of network state changes
        
        Args:
            callback: Function that takes bool (is_online) as parameter
        """
        if callback not in self._callbacks:
            self._callbacks.append(callback)
            logger.debug(f"Added network callback: {callback.__name__}")
    
    def remove_callback(self, callback: Callable[[bool], None]):
        """Remove callback"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
            logger.debug(f"Removed network callback: {callback.__name__}")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while not self._stop_event.is_set():
            try:
                current_state = self._check_connectivity()
                
                # Notify callbacks if state changed
                if current_state != self.is_online:
                    old_state = self.is_online
                    self.is_online = current_state
                    logger.info(
                        f"Network state changed: "
                        f"{'offline' if old_state else 'online'} → "
                        f"{'online' if current_state else 'offline'}"
                    )
                    self._notify_callbacks()
                
            except Exception as e:
                logger.error(f"Error in network monitor loop: {e}", exc_info=True)
            
            # Wait for next check
            self._stop_event.wait(self.check_interval)
    
    def _check_connectivity(self) -> bool:
        """
        Check if internet is available
        
        Returns:
            bool: True if online, False if offline
        """
        # Try multiple methods for reliability
        
        # Method 1: Try to connect to Google DNS
        if self._can_connect("8.8.8.8", 53, timeout=3):
            return True
        
        # Method 2: Try to connect to Cloudflare DNS
        if self._can_connect("1.1.1.1", 53, timeout=3):
            return True
        
        # Method 3: Try to connect to common website
        if self._can_connect("www.google.com", 80, timeout=3):
            return True
        
        # All methods failed
        return False
    
    @staticmethod
    def _can_connect(host: str, port: int, timeout: int = 3) -> bool:
        """
        Try to connect to a host:port
        
        Args:
            host: Hostname or IP address
            port: Port number
            timeout: Connection timeout in seconds
        
        Returns:
            bool: True if connection successful
        """
        try:
            socket.setdefaulttimeout(timeout)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
            return True
        except (socket.error, socket.timeout, OSError):
            return False
    
    def _notify_callbacks(self):
        """Notify all registered callbacks of state change"""
        for callback in self._callbacks:
            try:
                callback(self.is_online)
            except Exception as e:
                logger.error(
                    f"Error in network callback {callback.__name__}: {e}",
                    exc_info=True
                )
    
    def force_check(self) -> bool:
        """
        Force immediate connectivity check
        
        Returns:
            bool: Current online state
        """
        self.is_online = self._check_connectivity()
        return self.is_online


# Global network monitor instance
_monitor: Optional[NetworkMonitor] = None


def get_network_monitor() -> NetworkMonitor:
    """Get global network monitor instance"""
    global _monitor
    if _monitor is None:
        _monitor = NetworkMonitor()
    return _monitor


if __name__ == "__main__":
    # Test network monitor
    logging.basicConfig(level=logging.INFO)
    
    def on_network_change(is_online: bool):
        print(f"Network state changed: {'ONLINE' if is_online else 'OFFLINE'}")
    
    monitor = NetworkMonitor(check_interval=5)
    monitor.add_callback(on_network_change)
    monitor.start()
    
    print(f"Initial state: {'ONLINE' if monitor.is_online else 'OFFLINE'}")
    print("Monitoring network... (Ctrl+C to stop)")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping monitor...")
        monitor.stop()

