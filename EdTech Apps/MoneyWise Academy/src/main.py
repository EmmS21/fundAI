#!/usr/bin/env python3
"""
MoneyWise Academy - Main Entry Point
Financial literacy AI tutor for ages 12-18

Architecture: Offline-first with cloud sync
- Local SQLite database for user data
- Local LLM + Groq cloud fallback for AI tutoring
- MongoDB for cloud data persistence
- Firebase for authentication and real-time sync
"""

import sys
import logging
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from PySide6.QtCore import QCoreApplication

# Add project root to path for development
if __name__ == "__main__":
    project_root = Path(__file__).parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

# TODO: Import actual modules once implemented
# from src.ui.main_window import MainWindow
# from src.config.settings import Settings


def setup_logging():
    """Configure application logging"""
    log_dir = Path.home() / '.moneywise' / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / 'moneywise.log'
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)


def main():
    """Main application entry point"""
    logger = setup_logging()
    logger.info("Starting MoneyWise Academy...")
    
    try:
        # Create Qt application
        app = QApplication(sys.argv)
        app.setApplicationName("MoneyWise Academy")
        app.setOrganizationName("fundAI")
        app.setOrganizationDomain("fundai.co")
        
        # Set application icon (TODO: Add actual icon)
        icon_path = Path(__file__).parent.parent / "assets" / "icons" / "moneywise.png"
        if icon_path.exists():
            app.setWindowIcon(QIcon(str(icon_path)))
        
        # TODO: Initialize services
        # - Database
        # - Network monitor
        # - AI manager
        # - Sync service
        
        # TODO: Check for existing user
        # If no user: show onboarding
        # If user exists: show main window
        
        logger.info("Application initialized successfully")
        
        # TODO: Create and show main window
        # window = MainWindow()
        # window.show()
        
        # For now, just print a message
        print("MoneyWise Academy - Skeleton Setup Complete")
        print("See tasks.md for implementation roadmap")
        
        # TODO: Uncomment when UI is ready
        # return app.exec()
        
        return 0
        
    except Exception as e:
        logger.critical(f"Fatal error: {str(e)}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())

