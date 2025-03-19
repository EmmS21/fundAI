import sys
import os
from PySide6.QtWidgets import QApplication
from src.ui.components.onboarding.onboarding_window import OnboardingWindow
from src.ui.main_window import MainWindow
from src.core.network.sync_service import SyncService
from src.data.database.operations import UserOperations
from src.data.database.models import Base
from src.utils.db import engine, Session
from src.data.cache.cache_manager import CacheManager
from src.data.database.models import User


def main():
    app = QApplication(sys.argv)
    
    # Check if database exists and has a user
    db_exists = os.path.exists("student_profile.db")
    
    # Create/update tables
    Base.metadata.create_all(engine)
    
    # Start services
    sync_service = SyncService()
    sync_service.start()
    
    cache_manager = CacheManager()
    cache_manager.start()
    
    # Set up cleanup
    def cleanup():
        print("Performing application cleanup...")
        cache_manager.stop()
        sync_service.stop()
    
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
