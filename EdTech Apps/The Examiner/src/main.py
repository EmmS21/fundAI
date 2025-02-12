import sys
from PySide6.QtWidgets import QApplication
from src.ui.components.onboarding.onboarding_window import OnboardingWindow
from src.ui.main_window import MainWindow
from src.core.network.sync_service import SyncService
from src.data.database.operations import UserOperations

def main():
    app = QApplication(sys.argv)
    
    # Start sync service
    sync_service = SyncService()
    sync_service.start()
    
    # Check if user exists
    user = UserOperations.get_current_user()
    
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
