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
from typing import Optional
from .queue_manager import QueueManager

# DON'T IMPORT THIS DIRECTLY - it creates a circular import
# from src.data.cache.cache_manager import CacheManager

logger = logging.getLogger(__name__)

# These will be set during application initialization
sync_service = None
cache_manager = None
network_monitor: Optional[NetworkMonitor] = None
mongodb_client = None
firebase_client = None

def initialize_services():
    """Initialize all application services"""
    global cache_manager, network_monitor, sync_service, firebase_client, mongodb_client
    
    try:
        logger.info("Initializing application services...")
        
        # Initialize Firebase client (used by other services)
        firebase_client = FirebaseClient()
        logger.info("Firebase client initialized")
        
        # Initialize MongoDB client
        mongodb_client = MongoDBClient()
        logger.info("MongoDB client initialized")
        
        # Initialize network monitor
        network_monitor = NetworkMonitor()
        logger.info(f"Network monitor initialized with status: {network_monitor.get_status()}")
        
        # Initialize cache manager
        cache_manager = CacheManager()
        cache_manager.start()
        logger.info("Cache manager initialized and started")
        
        # Initialize sync service (depends on network monitor and cache manager)
        sync_service = SyncService()
        sync_service.initialize()
        logger.info("Sync service initialized")
        
        # Start Sync Service
        sync_service.start()
        
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
            
        if not cache_manager:
            cache_manager = CacheManager()
            cache_manager.start()
            
        if not sync_service:
            sync_service = SyncService()
            sync_service.initialize()
            
        logger.info("Services initialized with potential errors")
        
def shutdown_services():
    """Gracefully shut down application services."""
    logger.info("Shutting down application services...")
    try:
        # Stop services that have a stop method, in reverse order of start
        if sync_service:
            sync_service.stop()
            logger.info("Sync service stopped")
        if cache_manager:
            cache_manager.stop()
            logger.info("Cache manager stopped")

        if mongodb_client:
            mongodb_client.close()
            logger.info("MongoDB client connection closed")

        logger.info("Services shut down successfully")
    except Exception as e:
        logger.error(f"Error during service shutdown: {e}", exc_info=True)
        
        # Attempt to restart services if one fails
        if not sync_service:
            sync_service = SyncService()
            sync_service.initialize()
            
        if not cache_manager:
            cache_manager = CacheManager()
            cache_manager.start()
            
        if not mongodb_client:
            mongodb_client = MongoDBClient()
            
        logger.info("Services restarted with potential errors") 