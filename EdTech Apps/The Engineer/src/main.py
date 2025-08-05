#!/usr/bin/env python3
"""
The Engineer AI Tutor - Main Entry Point
Simple GUI application for 12-18 year olds learning software engineering concepts
"""

import sys
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("The Engineer")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 