from typing import Callable, List, Tuple
import urllib.request
import socket
import threading
import time
from enum import Enum
from datetime import datetime
import logging
from threading import Thread, Event
import http.client
import ssl
import random  # For jitter in retry calculations

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NetworkStatus(Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    UNKNOWN = "unknown"

# Expanded to include service-specific status
class ConnectionQuality(Enum):
    EXCELLENT = "excellent"  # Fast, reliable connection
    GOOD = "good"            # Normal connection
    POOR = "poor"            # Slow or intermittent connection
    NONE = "none"            # No connection

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
        
        # Validation parameters
        self._connection_quality = ConnectionQuality.NONE
        self._validation_urls = [
            "https://www.google.com",  # Popular service
            "https://www.cloudflare.com",  # Alternative CDN
            "https://www.example.com"   # Lightweight option
        ]
        self._last_response_time = 0
        self._mongodb_service_available = False
        
        # Network adaptation parameters
        self._default_batch_size = 10
        self._default_retry_delay = 5  # seconds
        self._max_retry_delay = 300    # 5 minutes max
        
        # Quality trend tracking
        self._quality_history = []     # Store recent quality measurements 
        self._quality_history_limit = 5  # Number of measurements to keep

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
        
    def get_connection_quality(self) -> ConnectionQuality:
        """Get assessed connection quality based on response times"""
        return self._connection_quality
        
    def is_service_available(self) -> bool:
        """Check if the MongoDB service is available"""
        return self._mongodb_service_available
    
    def get_recommended_batch_size(self, default_size: int = None) -> int:
        """
        Get recommended batch size for network operations based on current connection quality.
        
        Args:
            default_size: Default batch size (if not provided, uses internal default)
            
        Returns:
            Recommended batch size for current network conditions
        """
        if default_size is None:
            default_size = self._default_batch_size
            
        # If offline, recommend very small batch to minimize wasted attempts
        if self._status != NetworkStatus.ONLINE:
            return 1
            
        # Scale batch size based on connection quality
        quality_factors = {
            ConnectionQuality.EXCELLENT: 1.5,  # 150% of default for excellent connections
            ConnectionQuality.GOOD: 1.0,      # 100% of default for good connections
            ConnectionQuality.POOR: 0.3,      # 30% of default for poor connections
            ConnectionQuality.NONE: 0.1       # 10% of default as fallback
        }
        
        factor = quality_factors.get(self._connection_quality, 0.5)
        recommended_size = max(1, int(default_size * factor))
        
        logger.debug(f"Recommended batch size {recommended_size} for {self._connection_quality.value} connection")
        return recommended_size
    
    def get_retry_delay(self, attempt: int = 1, base_delay: float = None) -> float:
        """
        Get recommended retry delay with exponential backoff based on connection quality and attempt number.
        
        Args:
            attempt: Current attempt number (1-based)
            base_delay: Base delay in seconds (if not provided, uses internal default)
            
        Returns:
            Recommended delay in seconds before retry
        """
        if base_delay is None:
            base_delay = self._default_retry_delay
            
        # Quality-based factors
        quality_factors = {
            ConnectionQuality.EXCELLENT: 0.7,  # Shorter delays for excellent connections
            ConnectionQuality.GOOD: 1.0,      # Standard delay for good connections
            ConnectionQuality.POOR: 1.5,      # Longer delays for poor connections
            ConnectionQuality.NONE: 2.0       # Much longer delays when connection appears down
        }
        
        # Calculate exponential backoff with quality factor
        factor = quality_factors.get(self._connection_quality, 1.0)
        delay = min(
            self._max_retry_delay,  # Cap at max delay
            base_delay * (2 ** (attempt - 1)) * factor  # Exponential backoff with quality factor
        )
        
        # Add jitter (±15%) to prevent thundering herd
        jitter = random.uniform(0.85, 1.15)
        delay = delay * jitter
        
        logger.debug(f"Recommended retry delay {delay:.1f}s for attempt {attempt} on {self._connection_quality.value} connection")
        return delay
    
    def _update_quality_history(self, quality: ConnectionQuality):
        """Track connection quality history to detect trends"""
        self._quality_history.append((time.time(), quality))
        
        # Keep history within limit
        if len(self._quality_history) > self._quality_history_limit:
            self._quality_history = self._quality_history[1:]

    def _check_connection(self) -> bool:
        """Check if we have internet connection"""
        # Try the lightweight validation first
        is_online, quality = self._validate_connection()
        
        # Update connection quality
        self._connection_quality = quality
        self._update_quality_history(quality)
        
        if is_online:
            return True
            
        # Fall back to original methods if validation fails
        try:
            # Try to connect to a reliable host
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            
            # Connection succeeded but validation failed - might be a captive portal
            # We'll consider this offline since our services won't work
            logger.debug("Socket connection successful but validation failed - possible captive portal")
            return False
        except OSError:
            return False

    def _validate_connection(self) -> Tuple[bool, ConnectionQuality]:
        """
        Validate internet connectivity using lightweight requests.
        
        Returns:
            Tuple of (is_connected, connection_quality)
        """
        start_time = time.time()
        
        # Try each validation URL
        for url in self._validation_urls:
            try:
                # Parse the URL to get hostname
                if url.startswith("https://"):
                    hostname = url[8:].split("/")[0]
                    port = 443
                    use_ssl = True
                else:
                    hostname = url[7:].split("/")[0]
                    port = 80
                    use_ssl = False
                
                # Create appropriate connection
                if use_ssl:
                    conn = http.client.HTTPSConnection(hostname, port=port, timeout=3,
                                               context=ssl.create_default_context())
                else:
                    conn = http.client.HTTPConnection(hostname, port=port, timeout=3)
                
                # Make a HEAD request (much lighter than GET)
                conn.request("HEAD", "/")
                response = conn.getresponse()
                
                # Check response status
                if 200 <= response.status < 400:
                    # Calculate response time
                    self._last_response_time = time.time() - start_time
                    
                    # Determine connection quality based on response time
                    if self._last_response_time < 0.5:
                        quality = ConnectionQuality.EXCELLENT
                    elif self._last_response_time < 1.5:
                        quality = ConnectionQuality.GOOD
                    else:
                        quality = ConnectionQuality.POOR
                        
                    # Check MongoDB availability if connected
                    try:
                        from src.core import services
                        if services.mongodb_client:
                            # We won't actually ping here to avoid imports
                            # In a real implementation, we'd check if a lightweight MongoDB
                            # operation succeeds
                            self._mongodb_service_available = True
                    except Exception as e:
                        logger.debug(f"MongoDB service check failed: {e}")
                        self._mongodb_service_available = False
                        
                    logger.debug(f"Connectivity validated via {hostname} in {self._last_response_time:.2f}s")
                    conn.close()
                    return True, quality
                
                conn.close()
            except Exception as e:
                logger.debug(f"Validation for {url} failed: {e}")
        
        # All validation attempts failed
        return False, ConnectionQuality.NONE

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
        
    def set_validation_urls(self, urls: List[str]):
        """
        Set custom validation URLs.
        
        Args:
            urls: List of URLs to use for validation
        """
        if not urls:
            raise ValueError("At least one validation URL must be provided")
        self._validation_urls = urls
        logger.info(f"Network monitor validation URLs updated: {', '.join(urls)}")

