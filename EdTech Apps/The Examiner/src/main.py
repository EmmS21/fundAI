import sys
import os
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
import logging

logger = logging.getLogger(__name__)

def main():
    # Initialize core application services first
    if not initialize_app():
        print("Failed to initialize application services. Exiting.", file=sys.stderr)
        if logger: logger.critical("Failed to initialize application services. Exiting.")
        sys.exit(1)

    try:
        logger.info("--- Checking services status immediately after initialize_app() in main.py ---")
        logger.info(f"ID of 'services' module in main.py: {id(services)}")
        logger.info(f"Value of services.user_history_manager in main.py: {getattr(services, 'user_history_manager', 'AttributeNotFound')}")
    except Exception as log_err:
        print(f"Error logging services status in main.py: {log_err}", file=sys.stderr)

    app = QApplication(sys.argv)
    
    # Check if database exists and has a user
    db_exists = os.path.exists("student_profile.db")
    
    # Create/update tables
    Base.metadata.create_all(engine)
    
    # Initialize all services
    services.initialize_services()
    
    # Set up cleanup
    def cleanup():
        print("Performing application cleanup...")
        services.shutdown_services()
    
    app.aboutToQuit.connect(cleanup)
    
    # Simply check if we have any user in the database
    if db_exists:
        with Session() as session:
            user = session.query(User).first()  # Get any user, no hardware ID filter
            if user:
                print("Found existing user, showing MainWindow")
                window = MainWindow(user)
            else:
                print("No user found in database, showing OnboardingWindow")
                window = OnboardingWindow()
    else:
        print("No database found, showing OnboardingWindow")
        window = OnboardingWindow()
    
    window.show()
    return app.exec()

if __name__ == "__main__":
    main()
