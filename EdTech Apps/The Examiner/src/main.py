import sys
import os
from PySide6.QtWidgets import QApplication
from src.ui.components.onboarding.onboarding_window import OnboardingWindow
from src.ui.main_window import MainWindow
from src.data.database.models import Base
from src.utils.db import engine, Session
from src.data.database.models import User
from src.core import services

def main():
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
