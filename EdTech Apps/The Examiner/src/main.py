import sys
from PySide6.QtWidgets import QApplication
from src.ui.components.onboarding.onboarding_window import OnboardingWindow

def main():
    app = QApplication(sys.argv)
    window = OnboardingWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
