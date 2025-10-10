#!/usr/bin/env python3
"""
The Engineer AI Tutor - Main Entry Point
Simple GUI application for 12-18 year olds learning software engineering concepts
"""

import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

# Add the project root to Python path for development
if __name__ == "__main__":
    project_root = Path(__file__).parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from src.ui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("The Engineer")
    
    icon_path = Path(__file__).parent.parent / "assets" / "icons" / "engineer.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 