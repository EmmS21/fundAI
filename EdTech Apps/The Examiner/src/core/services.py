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
from src.data.cache.cache_manager import CacheManager
from PySide6.QtCore import QThreadPool

# DON'T IMPORT THIS DIRECTLY - it creates a circular import
# from src.data.cache.cache_manager import CacheManager

logger = logging.getLogger(__name__)

# These will be set during application initialization
sync_service = None
cache_manager = None
network_monitor = None
mongodb_client = None
firebase_client = None
threadpool = None  # Thread pool for background tasks

def initialize_services():
    """Initialize all application services"""
    global cache_manager, network_monitor, sync_service, firebase_client, mongodb_client, threadpool
    
    try:
        logger.info("Initializing application services...")
        
        # Initialize thread pool
        threadpool = QThreadPool.globalInstance()
        # Configure max thread count - adjust based on system capabilities
        threadpool.setMaxThreadCount(4)  # Reasonable default for most systems
        logger.info(f"Thread pool initialized with max thread count: {threadpool.maxThreadCount()}")
        
        # Initialize Firebase client (used by other services)
        firebase_client = FirebaseClient()
        logger.info("Firebase client initialized")
        
        # Initialize MongoDB client
        mongodb_client = MongoDBClient()
        logger.info("MongoDB client initialized")
        
        # Initialize network monitor
        network_monitor = NetworkMonitor()
        network_monitor.start()
        logger.info("Network monitor initialized and started")
        
        # Initialize cache manager
        cache_manager = CacheManager()
        cache_manager.start()
        logger.info("Cache manager initialized and started")
        
        # Initialize sync service (depends on network monitor and cache manager)
        sync_service = SyncService()
        sync_service.initialize()
        logger.info("Sync service initialized")
        
        logger.info("All application services initialized successfully")
        
    except Exception as e:
        logger.error(f"Error initializing services: {e}", exc_info=True)
        
        # Attempt to initialize remaining services if one fails
        if not firebase_client:
            firebase_client = FirebaseClient()
            
        if not mongodb_client:
            mongodb_client = MongoDBClient()
            
        if not network_monitor:
            network_monitor = NetworkMonitor()
            network_monitor.start()
            
        if not cache_manager:
            cache_manager = CacheManager()
            cache_manager.start()
            
        if not sync_service:
            sync_service = SyncService()
            sync_service.initialize()
            
        if not threadpool:
            threadpool = QThreadPool.globalInstance()
            
        logger.info("Services initialized with potential errors")
        
def shutdown_services():
    """Shutdown all services in the appropriate order"""
    global cache_manager, network_monitor, sync_service
    
    logger.info("Shutting down application services...")
    
    # Stop sync service first
    if sync_service:
        try:
            sync_service.stop()
            logger.info("Sync service stopped")
        except Exception as e:
            logger.error(f"Error stopping sync service: {e}")
    
    # Then stop cache manager
    if cache_manager:
        try:
            cache_manager.stop()
            logger.info("Cache manager stopped")
        except Exception as e:
            logger.error(f"Error stopping cache manager: {e}")
    
    # Finally stop network monitor
    if network_monitor:
        try:
            network_monitor.stop()
            logger.info("Network monitor stopped")
        except Exception as e:
            logger.error(f"Error stopping network monitor: {e}")
            
    logger.info("All services shutdown complete") 