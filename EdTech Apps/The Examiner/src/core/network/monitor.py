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
import requests

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
    UNKNOWN = "unknown"      # Initial or undetermined quality

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
    _instance = None
    
    def __new__(cls):
        """Singleton pattern to ensure only one instance exists"""
        if cls._instance is None:
            cls._instance = super(NetworkMonitor, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize network monitor"""
        if self.initialized:
            return
            
        # Default to ONLINE status until we know otherwise
        self._status = NetworkStatus.ONLINE
        
        # Signal for notifying status changes
        self.status_changed = Signal()
        
        # Add a timer for regular status checks
        self.timer = None
        self.check_interval = 60  # seconds
        
        # Track "settling time" to prevent rapid status switching
        self.last_change_time = 0
        self.settling_time = 3.0  # seconds
        
        # Track connection quality
        self._quality = ConnectionQuality.UNKNOWN
        self._quality_history = []
        
        # Track external service connections
        self._last_mongodb_connection = 0  # timestamp of last successful MongoDB connection
        self._mongodb_connection_ttl = 300  # consider MongoDB connection valid for 5 minutes
        
        # Validation URLs for checking connectivity
        self._validation_urls = ["https://www.google.com", "https://www.cloudflare.com"]
        
        # Perform initial check immediately
        self._check_network_status()
        
        # Start regular checking
        self._start_timer()
        
        self.initialized = True
        logger.info(f"Network monitor initialized with status: {self._status}")
    
    def _start_timer(self):
        """Start the timer for regular network checks"""
        if self.timer is None:
            self.timer = threading.Timer(self.check_interval, self._timer_callback)
            self.timer.daemon = True
            self.timer.start()
    
    def _timer_callback(self):
        """Called when timer expires, check status and restart timer"""
        self._check_network_status()
        
        # Restart timer
        self.timer = None
        self._start_timer()
    
    def _check_network_status(self):
        """Check current network status"""
        try:
            # Check current connection
            is_connected, quality = self._validate_connection()
            current_time = time.time()
            
            # Check if MongoDB has a recent successful connection
            mongodb_connected = self._is_mongodb_recently_connected()
            
            if mongodb_connected and not is_connected:
                logger.info("Network appears offline, but MongoDB is connected. Considering network ONLINE.")
                is_connected = True
                quality = ConnectionQuality.GOOD
                
            # Determine new status
            new_status = NetworkStatus.ONLINE if is_connected else NetworkStatus.OFFLINE
            
            # Only update if status has changed and settling time has passed
            if new_status != self._status and (current_time - self.last_change_time) >= self.settling_time:
                old_status = self._status
                self._status = new_status
                self._quality = quality
                self.last_change_time = current_time
                
                logger.info(f"Network status changed: {old_status.value} -> {new_status.value}")
                
                # Notify connected callbacks
                self._notify_callbacks()
                
        except Exception as e:
            logger.error(f"Error checking network status: {e}")
    
    def _is_mongodb_recently_connected(self) -> bool:
        """Check if there was a recent successful MongoDB connection"""
        current_time = time.time()
        return (current_time - self._last_mongodb_connection) < self._mongodb_connection_ttl
    
    def get_status(self) -> NetworkStatus:
        """Get current network status"""
        # Perform a fresh check if it's been a while
        if time.time() - self.last_change_time > self.check_interval:
            self._check_network_status()
        return self._status
    
    def force_check(self) -> NetworkStatus:
        """Force an immediate status check and return result"""
        self._check_network_status()
        return self._status

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

    def get_connection_quality(self) -> ConnectionQuality:
        """Get assessed connection quality based on response times"""
        return self._quality
        
    def is_service_available(self) -> bool:
        """Check if the MongoDB service is available"""
        return self._status == NetworkStatus.ONLINE
    
    def get_recommended_batch_size(self, default_size: int = None) -> int:
        """
        Get recommended batch size for network operations based on current connection quality.
        
        Args:
            default_size: Default batch size (if not provided, uses internal default)
            
        Returns:
            Recommended batch size for current network conditions
        """
        if default_size is None:
            default_size = 20  # Default batch size
            
        if self._status != NetworkStatus.ONLINE:
            return 5  # Minimal batch size when offline
            
        # Scale batch size based on connection quality
        quality_factors = {
            ConnectionQuality.EXCELLENT: 1.5,  # 150% of default for excellent connections
            ConnectionQuality.GOOD: 1.0,      # 100% of default for good connections
            ConnectionQuality.POOR: 0.5,      # 50% of default for poor connections
            ConnectionQuality.NONE: 0.25      # 25% of default as fallback
        }
        
        factor = quality_factors.get(self._quality, 1.0)
        recommended_size = max(5, int(default_size * factor))
        
        logger.debug(f"Recommended batch size {recommended_size} for {self._quality.value} connection")
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
            base_delay = 5.0  # Default 5 second base delay
            
        if self._status != NetworkStatus.ONLINE:
            # When offline, use longer delays
            return min(300, base_delay * (2 ** (attempt - 1)))
            
        # Scale based on connection quality
        quality_factors = {
            ConnectionQuality.EXCELLENT: 0.5,  # 50% of base delay
            ConnectionQuality.GOOD: 1.0,      # 100% of base delay
            ConnectionQuality.POOR: 2.0,      # 200% of base delay
            ConnectionQuality.NONE: 4.0       # 400% of base delay
        }
        
        factor = quality_factors.get(self._quality, 1.0)
        
        # Apply exponential backoff with quality factor
        delay = base_delay * factor * (1.5 ** (attempt - 1))
        
        # Cap at reasonable values
        return min(300, max(1, delay))
    
    def _update_quality_history(self, quality: ConnectionQuality):
        """Track connection quality history to detect trends"""
        self._quality_history.append((time.time(), quality))
        
        # Trim history to recent entries (last hour)
        cutoff = time.time() - 3600
        self._quality_history = [q for q in self._quality_history if q[0] >= cutoff]

    def _check_connection(self) -> bool:
        """Check if we have internet connection"""
        # Try the lightweight validation first
        is_online, quality = self._validate_connection()
        
        # Update connection quality
        self._quality = quality
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
        self.settling_time = seconds
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

    def report_mongodb_connection(self) -> None:
        """
        Report a successful MongoDB connection.
        This method should be called whenever a successful MongoDB connection is established.
        """
        logger.info("Successful MongoDB connection reported to NetworkMonitor")
        self._last_mongodb_connection = time.time()
        
        # If we're currently offline, initiate a status check to potentially update to online
        if self._status != NetworkStatus.ONLINE:
            logger.info("Network status is currently OFFLINE but MongoDB is connected - rechecking status")
            self._check_network_status()

