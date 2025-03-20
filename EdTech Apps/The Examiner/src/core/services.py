"""
Central registry for application services.

This module serves as a central point for accessing application services,
helping to prevent circular imports between modules while maintaining
top-level imports.

During application initialization, these service variables will be set
to their respective singleton instances.
"""
import logging
import importlib
"""
Central registry for application services.

This module serves as a central point for accessing application services,
helping to prevent circular imports between modules while maintaining
top-level imports.

During application initialization, these service variables will be set
to their respective singleton instances.
"""
import logging
import importlib
from src.core.network.monitor import NetworkMonitor, NetworkStatus
from src.core.firebase.client import FirebaseClient
from src.core.mongodb.client import MongoDBClient
from src.core.network.sync_service import SyncService

# DON'T IMPORT THIS DIRECTLY - it creates a circular import
# from src.data.cache.cache_manager import CacheManager

logger = logging.getLogger(__name__)

# These will be set during application initialization
sync_service = None
cache_manager = None
network_monitor = None
mongodb_client = None
firebase_client = None

def initialize_services():
    """Initialize all application services in the correct order"""
    global network_monitor, firebase_client, mongodb_client, sync_service, cache_manager
    
    logger.info("Initializing application services...")
    
    # Initialize network monitor first
    network_monitor = NetworkMonitor()
    logger.info(f"Network monitor initialized with status: {network_monitor.get_status()}")
    
    # Force a network check to ensure accurate status
    status = network_monitor.force_check()
    logger.info(f"Network status after forced check: {status}")
    
    # Initialize Firebase client (needed for subscription verification)
    firebase_client = FirebaseClient()
    
    # Initialize MongoDB client
    mongodb_client = MongoDBClient()
    if status == NetworkStatus.ONLINE:
        if not mongodb_client.connected:
            connection_result = mongodb_client.connect()
            logger.info(f"MongoDB connection result: {connection_result}")
    
    # Initialize sync service
    sync_service = SyncService()
    sync_service.start()
    
    # Initialize cache manager last (depends on other services)
    # Use dynamic import to avoid circular import
    cache_module = importlib.import_module('src.data.cache.cache_manager')
    cache_manager = cache_module.CacheManager()
    cache_manager.start()
    
    logger.info("All services initialized successfully")

def shutdown_services():
    """Stop all services in the correct order"""
    global cache_manager, sync_service
    
    logger.info("Shutting down application services...")
    
    # Stop in reverse order of initialization
    if cache_manager:
        cache_manager.stop()
    
    if sync_service:
        sync_service.stop()
    
    logger.info("All services stopped successfully") 