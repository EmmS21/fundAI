from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout
from src.data.database.operations import UserOperations
from .components.profile.profile_header import ProfileHeader
from .components.profile.achievements.achievement_widget import AchievementWidget

class MainWindow(QMainWindow):
    def __init__(self, user=None):
        super().__init__()
        self.setWindowTitle("Student Profile")
        self.setFixedSize(800, 600)
        
        # Set window background to white
        self.setStyleSheet("""
            QMainWindow {
                background-color: white;
            }
        """)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Use provided user or get current user
        self.user = user or UserOperations.get_current_user()
        
        # Add profile header
        profile_header = ProfileHeader(self.user)
        layout.addWidget(profile_header)
        
        # Add achievement widget
        achievement_widget = AchievementWidget(self.user)
        layout.addWidget(achievement_widget)
        
        # Add stretch to push everything to the top
        layout.addStretch()
        
        # TODO: Add profile components here
        # This is where we'll add the profile header, achievements, and subjects
