import logging
import sys
import os
from datetime import datetime
import threading

# Core services
from src.core import services
from src.core.logging_config import configure_logging
from src.core.network.monitor import NetworkMonitor
from src.core.mongodb.client import MongoDBClient
from src.core.queue_manager import QueueManager
from src.core.network.sync_service import SyncService
from src.data.cache.cache_manager import CacheManager
from src.core.history.user_history_manager import UserHistoryManager
from src.core.firebase.client import FirebaseClient

# Set up logging
configure_logging()
logger = logging.getLogger(__name__)

def initialize_app():
    """Initialize the application and its services"""
    print(">>> DEBUG: Entered initialize_app()", file=sys.stderr)

    # Configure logging first
    print(">>> DEBUG: Attempting to call configure_logging()...", file=sys.stderr)
    try:
        configure_logging()
    except Exception as e:
        print(f">>> DEBUG: *** ERROR IN configure_logging() CALL ***: {e}", file=sys.stderr)

    # Now get the logger AFTER attempting configuration
    logger = logging.getLogger(__name__)
    logger.info("Log attempt after basic config.") # Test if logger works at all

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
    
    # 5. Initialize User History Manager
    uhm_instance = None # Define outside try
    print(">>> DEBUG: == Attempting UserHistoryManager Initialization ==", file=sys.stderr)
    try:
        # Add a print RIGHT BEFORE instantiation
        print(">>> DEBUG: Instantiating UserHistoryManager()...", file=sys.stderr)
        uhm_instance = UserHistoryManager()
        # Add print RIGHT AFTER instantiation attempt
        print(f">>> DEBUG: UserHistoryManager() instantiation finished. Instance: {uhm_instance}", file=sys.stderr)

        services.user_history_manager = uhm_instance
        print(f">>> DEBUG: Assigned UserHistoryManager to services. Service is None: {services.user_history_manager is None}", file=sys.stderr)
        logger.info("User History Manager initialization step completed in app.py.")

    except Exception as e:
        print(f">>> DEBUG: *** ERROR DURING UserHistoryManager INITIALIZATION OR ASSIGNMENT ***: {e}", file=sys.stderr)
        logger.error(f"CRITICAL: Failed UserHistoryManager init/assignment: {e}", exc_info=True)
    
    # 6. Initialize Firebase client
    firebase_client = FirebaseClient()
    services.firebase_client = firebase_client
    logger.info("Firebase client initialized")

    # 7. Initialize Sync Service (depends on network monitor, queue manager)
    sync_service = SyncService()
    services.sync_service = sync_service
    
    # Start services that need to be running continuously
    sync_service.start()
    
    # Maybe start network monitor here if it has a start method
    if hasattr(network_monitor, 'start'):
        network_monitor.start()
    
    # Start background sync of question cache to DB
    logger.info("Starting background sync of question cache to DB...")
    sync_thread = threading.Thread(target=cache_manager.sync_question_cache_to_db, daemon=True)
    sync_thread.start()
    logger.info("Cache-to-DB sync started in background thread.")

    logger.info(f"--- Initializing services. ID of 'services' module: {id(services)} ---")
    logger.info("Application initialization complete")
    print(">>> DEBUG: Exiting initialize_app()", file=sys.stderr)
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