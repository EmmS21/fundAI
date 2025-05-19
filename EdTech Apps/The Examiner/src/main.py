import sys
import os
import ctypes
import builtins

# Store the original import
_original_import = builtins.__import__

def patch_llama_path():
    """Find and preload llama library before any imports of llama_cpp"""
    if not getattr(sys, 'frozen', False):
        return  # Only needed in PyInstaller bundle
        
    bundle_dir = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    print(f"Bundle directory: {bundle_dir}")
    
    # Find the llama library
    potential_paths = [
        os.path.join(bundle_dir, '_internal', 'llama_cpp_libs', 'libllama.so'),
    ]
    
    # Try to load any libraries we find
    loaded_lib = None
    lib_path = None
    
    for path in potential_paths:
        if os.path.exists(path):
            print(f"Found libllama.so at: {path}")
            try:
                loaded_lib = ctypes.CDLL(path)
                lib_path = path
                print(f"Successfully loaded libllama.so from: {path}")
                break
            except Exception as e:
                print(f"Failed to load from {path}: {e}")
    
    # If we couldn't find the library in expected locations, do a deeper search
    if loaded_lib is None:
        print("Searching for libllama.so in the entire bundle...")
        for root, _, files in os.walk(bundle_dir):
            for file in files:
                if file == 'libllama.so':
                    path = os.path.join(root, file)
                    try:
                        loaded_lib = ctypes.CDLL(path)
                        lib_path = path
                        print(f"Successfully loaded libllama.so from: {path}")
                        break
                    except Exception as e:
                        print(f"Failed to load from {path}: {e}")
            if loaded_lib:
                break
    
    if loaded_lib is None:
        print("ERROR: Could not find or load libllama.so")
        return
        
    # Set environment variables to help llama_cpp find the library
    lib_dir = os.path.dirname(lib_path)
    os.environ['LD_LIBRARY_PATH'] = f"{lib_dir}:{os.environ.get('LD_LIBRARY_PATH', '')}"
    os.environ['LLAMA_CPP_LIB'] = lib_path
    
    # Patch __import__ to intercept llama_cpp imports
    def patched_import(name, *args, **kwargs):
        module = _original_import(name, *args, **kwargs)
        
        # Check if this is the llama_cpp module we care about
        if name == 'llama_cpp' or name.startswith('llama_cpp.'):
            if hasattr(module, 'llama_cpp') and hasattr(module.llama_cpp, '_load_shared_library'):
                print("Intercepted llama_cpp import! Patching _load_shared_library...")
                
                # Replace the library loading function
                original_load = module.llama_cpp._load_shared_library
                def patched_load(*args, **kwargs):
                    print("Redirecting llama_cpp library loading to our preloaded library")
                    return loaded_lib
                    
                module.llama_cpp._load_shared_library = patched_load
                
                # Also ensure the _lib attribute is set if it exists
                if hasattr(module.llama_cpp, '_lib') and module.llama_cpp._lib is None:
                    print("Setting llama_cpp._lib directly")
                    module.llama_cpp._lib = loaded_lib
                
        return module
        
    # Replace the built-in __import__ function
    builtins.__import__ = patched_import
    
    print("llama_cpp import system patched")

# Call the function immediately
patch_llama_path()

import traceback
from datetime import datetime
import logging
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontDatabase, QIcon
from PySide6.QtCore import QCoreApplication
from src.app import initialize_app
from src.ui.components.onboarding.onboarding_window import OnboardingWindow
from src.ui.main_window import MainWindow
from src.data.database.models import Base
from src.utils.db import engine, Session
from src.data.database.models import User
from src.core import services
from logging.handlers import RotatingFileHandler
import platform
import uuid
import sentry_sdk

try:
    print("Python path:", sys.path)
    print("Current directory:", os.getcwd())
    
    # Try imports one by one
    print("Importing PySide6...")
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QFontDatabase, QIcon
    from PySide6.QtCore import QCoreApplication
    
    print("Importing app...")
    from src.app import initialize_app
    
    print("Importing UI components...")
    from src.ui.components.onboarding.onboarding_window import OnboardingWindow
    from src.ui.main_window import MainWindow
    
    print("Importing database modules...")
    from src.data.database.models import Base, User
    from src.utils.db import engine, Session
    
    print("Importing services...")
    from src.core import services
    
except Exception as e:
    print(f"Import error: {e}")
    print("Traceback:")
    traceback.print_exc()
    sys.exit(1)

LOG_DIR = Path.home() / '.examiner' / 'logs'
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / 'examiner_app.log'

log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log_handler = RotatingFileHandler(LOG_FILE, maxBytes=5*1024*1024, backupCount=3) 
log_handler.setFormatter(log_formatter)

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO) 
root_logger.addHandler(log_handler)

logger = logging.getLogger(__name__)
logger.info("Application starting...")

def get_machine_id():
    """Generates a persistent machine ID based on the network MAC address."""
    node_id = uuid.getnode()
    is_local_mac = (node_id >> 40) % 2
    if is_local_mac:
        logger.warning("Using potentially locally administered MAC address for machine ID.")
    return str(uuid.UUID(int=node_id))

SENTRY_DSN = "https://43f3b6b362eccf4641a30d1fb7652046@o4509312109051904.ingest.us.sentry.io/4509312198705152" # <-- Your DSN

try:
    APP_VERSION = "1.0.0" 

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        debug=True,
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
        integrations=[
            sentry_sdk.integrations.logging.LoggingIntegration(
                level=logging.INFO,        
                event_level=logging.ERROR 
            ),
        ],
        send_default_pii=True, 
        release=f"examiner@{APP_VERSION}" 
    )

    sentry_sdk.set_user({"id": get_machine_id()})
    sentry_sdk.set_context("app", {"app_name": "The Examiner", "version": APP_VERSION})
    sentry_sdk.set_context("os", {
        "name": platform.system(),
        "version": platform.release(),
        "machine": platform.machine()
    })
    sentry_sdk.set_tag("platform", platform.system()) 

    logger.info(f"Sentry SDK initialized for release {APP_VERSION}.")

except Exception as e:
    logger.error(f"Failed to initialize Sentry SDK: {e}", exc_info=True)

def setup_logging():
    """Set up logging configuration for debugging"""
    # Create logs directory in user's home
    log_dir = Path.home() / '.examiner' / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Create log file with timestamp
    log_file = log_dir / f'examiner_debug_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
    
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

def main():
    logger = setup_logging()
    logger.info("Application starting...")
    
    try:
        logger.debug("Importing required modules...")
        from PySide6.QtWidgets import QApplication
        from PySide6.QtGui import QFontDatabase, QIcon
        from PySide6.QtCore import QCoreApplication
        
        logger.debug("Importing local modules...")
        from src.app import initialize_app
        from src.ui.components.onboarding.onboarding_window import OnboardingWindow
        from src.ui.main_window import MainWindow
        from src.data.database.models import Base, User
        from src.utils.db import engine, Session
        from src.core import services

        logger.info("Creating QApplication instance...")
        app = QApplication(sys.argv)
        
        logger.info("Initializing application services...")
        if not initialize_app():
            logger.critical("Failed to initialize application services")
            return 1

        logger.debug("Checking database existence...")
        db_path = os.path.expanduser('~/.examiner/data/student_profile.db')
        db_exists = os.path.exists(db_path)
        logger.info(f"Database exists: {db_exists}")
        
        logger.debug("Creating database tables...")
        Base.metadata.create_all(engine)
        
        logger.info("Initializing services...")
        services.initialize_services()
        
        def cleanup():
            logger.info("Performing application cleanup...")
            services.shutdown_services()
        
        app.aboutToQuit.connect(cleanup)
        
        logger.debug("Checking for existing user...")
        with Session() as session:
            user = session.query(User).first()
            if user:
                logger.info("Existing user found, launching MainWindow")
                window = MainWindow(user)
            else:
                logger.info("No user found, launching OnboardingWindow")
                window = OnboardingWindow()
        
        logger.debug("Showing window...")
        window.show()
        
        # --- Sentry Test Error ---
        try:
            logger.info("Triggering intentional error for Sentry test...")
            division_by_zero = 1 / 0 # <-- This will raise a ZeroDivisionError
            logger.info("This line should not be reached.") # Proof it crashed
        except ZeroDivisionError as e:
            # While Sentry's auto-integration would catch this if unhandled,
            # explicitly capturing it here demonstrates manual capture too.
            logger.error("Caught expected ZeroDivisionError for Sentry test.", exc_info=True)
            sentry_sdk.capture_exception(e)
            logger.info("Manually captured exception sent to Sentry.")
            # Decide if you want the app to continue or exit after this test error
            # For now, let's let it continue to the event loop if possible,
            # but normally an error like this might halt execution.
            pass # Continue to app.exec()
        # --- End Sentry Test Error ---

        logger.info("Starting application event loop...")
        exit_code = app.exec()
        logger.info(f"Application event loop finished with exit code: {exit_code}")
        sys.exit(exit_code)

    except Exception as e:
        logger.critical(f"Unhandled exception: {str(e)}")
        logger.critical(f"Traceback: {traceback.format_exc()}")
        sentry_sdk.capture_exception(e)
        sentry_sdk.flush(timeout=5)
        return 1

if __name__ == "__main__":
    logger.info("Starting The Examiner application...")
    try:
        main()
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.critical(f"Fatal error: {str(e)}")
        logger.critical(f"Traceback: {traceback.format_exc()}")
        sentry_sdk.capture_exception(e)
        sentry_sdk.flush(timeout=5)
        sys.exit(1)
    finally:
        # Ensure Sentry events are sent before the application closes
        logger.info("Flushing Sentry events before shutdown...")
        sentry_sdk.flush(timeout=5)
        logger.info("Application shutdown complete.")
