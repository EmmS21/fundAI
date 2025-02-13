from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, 
                              QScrollArea)
from src.data.database.operations import UserOperations
from .components.profile.profile_header import ProfileHeader
from .components.profile.achievements.achievement_widget import AchievementWidget
from .components.profile.profile_info_widget import ProfileInfoWidget

class MainWindow(QMainWindow):
    def __init__(self, user=None):
        super().__init__()
        self.setWindowTitle("Student Profile")
        self.setFixedSize(800, 600)
        
        # Set window background to white
        self.setStyleSheet("""
            QMainWindow, QScrollArea, QWidget {
                background-color: white;
            }
            QScrollArea {
                border: none;
            }
        """)
        
        # Create scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        self.setCentralWidget(scroll_area)
        
        # Create main container widget
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Use provided user or get current user
        self.user = user or UserOperations.get_current_user()
        
        # Add profile header
        profile_header = ProfileHeader(self.user)
        layout.addWidget(profile_header)
        
        # Add achievement widget
        achievement_widget = AchievementWidget(self.user)
        layout.addWidget(achievement_widget)
        
        # Add profile info widget
        profile_info = ProfileInfoWidget(self.user)
        layout.addWidget(profile_info)
        
        # Add stretch to push everything to the top
        layout.addStretch()
        
        # Set the container as the scroll area widget
        scroll_area.setWidget(container)
        
        # TODO: Add profile components here
        # This is where we'll add the profile header, achievements, and subjects
