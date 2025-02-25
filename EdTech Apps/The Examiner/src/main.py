import sys
from PySide6.QtWidgets import QApplication
from src.ui.components.onboarding.onboarding_window import OnboardingWindow
from src.ui.main_window import MainWindow
from src.core.network.sync_service import SyncService
from src.data.database.operations import UserOperations
from src.data.database.models import Base
from src.utils.db import engine
from src.data.cache.cache_manager import CacheManager


def main():
    # Create any missing tables
    Base.metadata.create_all(engine)
    
    app = QApplication(sys.argv)
    
    # Start sync service
    sync_service = SyncService()
    sync_service.start()
    
    # Check if user exists
    user = UserOperations.get_current_user()
    
    # Initialize cache manager
    cache_manager = CacheManager()
    cache_manager.start()
    
    # Set up cleanup for application exit
    def cleanup():
        print("Performing application cleanup...")
        cache_manager.stop()
        sync_service.stop()
    
    # Connect cleanup to application aboutToQuit signal
    app.aboutToQuit.connect(cleanup)
    
    # Show appropriate window
    if user:
        window = MainWindow()
    else:
        window = OnboardingWindow()
    
    window.show()
    
    # Keep application running
    return app.exec()

if __name__ == "__main__":
    main()
