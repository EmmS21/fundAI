import logging
import sys
import os
from datetime import datetime

# Core services
from src.core import services
from src.core.logging_config import configure_logging
from src.core.network.network_monitor import NetworkMonitor
from src.core.mongodb_client import MongoDBClient
from src.core.queue_manager import QueueManager
from src.core.network.sync_service import SyncService
from src.data.cache.cache_manager import CacheManager

# Set up logging
logger = logging.getLogger(__name__)

def initialize_app():
    """Initialize the application and its services"""
    # Configure logging first
    configure_logging()
    logger.info("Starting application initialization")
    
    # Initialize services in the correct order to avoid circular dependencies
    logger.info("Initializing core services...")
    
    # 1. First initialize the network monitor
    network_monitor = NetworkMonitor()
    services.network_monitor = network_monitor
    
    # 2. Initialize MongoDB client
    mongodb_client = MongoDBClient()
    services.mongodb_client = mongodb_client
    
    # 3. Initialize Queue Manager
    queue_manager = QueueManager()
    services.queue_manager = queue_manager
    
    # 4. Initialize Cache Manager
    cache_manager = CacheManager()
    services.cache_manager = cache_manager
    
    # 5. Initialize Sync Service (depends on network monitor, queue manager)
    sync_service = SyncService()
    services.sync_service = sync_service
    
    # Start services that need to be running continuously
    sync_service.start()
    
    logger.info("Application initialization complete")
    return True

def shutdown_app():
    """Gracefully shut down the application"""
    logger.info("Starting application shutdown")
    
    # Stop services in reverse order
    if services.sync_service:
        services.sync_service.stop()
    
    if services.cache_manager:
        services.cache_manager.close()
    
    if services.mongodb_client:
        services.mongodb_client.close()
    
    logger.info("Application shutdown complete")

if __name__ == "__main__":
    try:
        initialized = initialize_app()
        if initialized:
            # Main application loop would go here
            logger.info("Application started successfully")
        else:
            logger.error("Failed to initialize application")
            sys.exit(1)
    except Exception as e:
        logger.exception(f"Unhandled exception during startup: {e}")
        sys.exit(1)
    finally:
        # This will run when the application exits
        shutdown_app() 