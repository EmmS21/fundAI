import sys
import os
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
        
        logger.info("Entering application main loop...")
        return app.exec()

    except Exception as e:
        logger.critical(f"Unhandled exception: {str(e)}")
        logger.critical(f"Traceback: {traceback.format_exc()}")
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.critical(f"Fatal error: {str(e)}")
        logger.critical(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)
