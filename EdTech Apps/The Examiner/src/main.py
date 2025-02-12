import sys
from PySide6.QtWidgets import QApplication
from src.ui.components.onboarding.onboarding_window import OnboardingWindow
from src.core.network.sync_service import SyncService

def main():
    app = QApplication(sys.argv)
    
    # Start sync service
    sync_service = SyncService()
    sync_service.start()
    
    window = OnboardingWindow()
    window.show()
    
    # Run application and only stop service on explicit app close
    try:
        exit_code = app.exec()
        if exit_code == 0:  # Normal exit/close
            sync_service.stop()
        sys.exit(exit_code)
    except SystemExit:
        sync_service.stop()
        raise

if __name__ == "__main__":
    main()
