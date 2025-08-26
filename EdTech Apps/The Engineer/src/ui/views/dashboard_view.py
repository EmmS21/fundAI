"""
The Engineer AI Tutor - Dashboard View
Simple dashboard for young learners to continue their journey
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QGridLayout
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from ..utils import create_offline_warning_banner

class DashboardView(QWidget):
    """Main dashboard for learning activities"""
    
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setup_ui()
    

    
    def setup_ui(self):
        """Setup the dashboard UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # Check for offline warning
        create_offline_warning_banner(layout)
        
        # Welcome header
        self.create_welcome_header(layout)
        
        # User profile summary
        self.create_profile_summary(layout)
        
        # Learning activities
        self.create_learning_activities(layout)
        
        # Progress section
        self.create_progress_section(layout)
    
    def create_welcome_header(self, layout):
        """Create welcome header with user info"""
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background-color: #3498db;
                border-radius: 10px;
                padding: 20px;
            }
        """)
        
        header_layout = QHBoxLayout(header_frame)
        
        # Welcome message
        user = self.main_window.current_user
        welcome_text = f"Welcome back, {user.get('username', 'Engineer')}!"
        
        welcome_label = QLabel(welcome_text)
        welcome_label.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: white;
            }
        """)
        header_layout.addWidget(welcome_label)
        
        header_layout.addStretch()
        
        # Level indicator
        level = user.get('level', 'beginner').title()
        level_label = QLabel(f"Level: {level}")
        level_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                color: white;
                background-color: rgba(255, 255, 255, 0.2);
                border-radius: 5px;
                padding: 8px 15px;
            }
        """)
        header_layout.addWidget(level_label)
        
        layout.addWidget(header_frame)
    
    def create_profile_summary(self, layout):
        """Create profile summary section"""
        profile_frame = QFrame()
        profile_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border-radius: 8px;
                padding: 20px;
            }
        """)
        
        profile_layout = QVBoxLayout(profile_frame)
        
        # Title
        title = QLabel("Your Engineering Profile")
        title.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #2c3e50;
                margin-bottom: 15px;
            }
        """)
        profile_layout.addWidget(title)
        
        # Profile info grid
        info_layout = QGridLayout()
        
        user = self.main_window.current_user
        
        # Strengths
        strengths_label = QLabel("🌟 Strengths:")
        strengths_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        strengths_text = QLabel(user.get('strengths', 'Ready to learn!'))
        strengths_text.setWordWrap(True)
        strengths_text.setStyleSheet("color: #2c3e50;")
        
        info_layout.addWidget(strengths_label, 0, 0)
        info_layout.addWidget(strengths_text, 0, 1)
        
        # Areas to improve
        improve_label = QLabel("🎯 Focus Areas:")
        improve_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        improve_text = QLabel(user.get('areas_to_improve', 'Continue exploring!'))
        improve_text.setWordWrap(True)
        improve_text.setStyleSheet("color: #2c3e50;")
        
        info_layout.addWidget(improve_label, 1, 0)
        info_layout.addWidget(improve_text, 1, 1)
        
        # Next steps
        next_label = QLabel("🚀 Next Steps:")
        next_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        next_text = QLabel(user.get('next_steps', 'Start with basic concepts!'))
        next_text.setWordWrap(True)
        next_text.setStyleSheet("color: #2c3e50;")
        
        info_layout.addWidget(next_label, 2, 0)
        info_layout.addWidget(next_text, 2, 1)
        
        # Set column stretch
        info_layout.setColumnStretch(1, 1)
        
        profile_layout.addLayout(info_layout)
        layout.addWidget(profile_frame)
    
    def create_learning_activities(self, layout):
        """Create learning activities section"""
        activities_frame = QFrame()
        activities_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border-radius: 8px;
                padding: 20px;
            }
        """)
        
        activities_layout = QVBoxLayout(activities_frame)
        
        # Title
        title = QLabel("Learning Activities")
        title.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #2c3e50;
                margin-bottom: 15px;
            }
        """)
        activities_layout.addWidget(title)
        
        # Activities grid
        grid_layout = QGridLayout()
        
        # Activity cards
        activities = [
            {
                'title': 'Logic Puzzles',
                'description': 'Practice problem-solving with fun puzzles',
                'action': 'Start Puzzles'
            },
            {
                'title': 'Project Builder',
                'description': 'Build simple projects step by step',
                'action': 'Build Projects'
            },
            {
                'title': 'Code Playground',
                'description': 'Experiment with simple programming concepts',
                'action': 'Try Coding'
            },
            {
                'title': 'Concept Explorer',
                'description': 'Learn engineering concepts interactively',
                'action': 'Explore Concepts'
            }
        ]
        
        for i, activity in enumerate(activities):
            card = self.create_activity_card(activity)
            row = i // 2
            col = i % 2
            grid_layout.addWidget(card, row, col)
        
        activities_layout.addLayout(grid_layout)
        layout.addWidget(activities_frame)
    
    def create_activity_card(self, activity):
        """Create an activity card"""
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 2px solid #ecf0f1;
                border-radius: 8px;
                padding: 15px;
                margin: 5px;
            }
            QFrame:hover {
                border-color: #3498db;
            }
        """)
        
        card_layout = QVBoxLayout(card)
        
        # Title
        title = QLabel(activity['title'])
        title.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #2c3e50;
                margin-bottom: 8px;
            }
        """)
        card_layout.addWidget(title)
        
        # Description
        description = QLabel(activity['description'])
        description.setWordWrap(True)
        description.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: #7f8c8d;
                margin-bottom: 10px;
            }
        """)
        card_layout.addWidget(description)
        
        # Action button
        button = QPushButton(activity['action'])
        button.setStyleSheet("""
            QPushButton {
                font-size: 12px;
                color: #3498db;
                background-color: transparent;
                border: 1px solid #3498db;
                border-radius: 4px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #3498db;
                color: white;
            }
        """)
        button.clicked.connect(lambda: self.show_coming_soon(activity['title']))
        card_layout.addWidget(button)
        
        return card
    
    def create_progress_section(self, layout):
        """Create progress tracking section"""
        progress_frame = QFrame()
        progress_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border-radius: 8px;
                padding: 20px;
            }
        """)
        
        progress_layout = QVBoxLayout(progress_frame)
        
        # Title
        title = QLabel("Your Progress")
        title.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #2c3e50;
                margin-bottom: 15px;
            }
        """)
        progress_layout.addWidget(title)
        
        # Progress info
        progress_text = QLabel(
            "🎯 Assessment Completed\n"
            "📊 Engineering Level Identified\n"
            "🚀 Ready to Start Learning!"
        )
        progress_text.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #27ae60;
                line-height: 1.6;
            }
        """)
        progress_layout.addWidget(progress_text)
        
        # Settings button
        settings_button = QPushButton("⚙️ Settings")
        settings_button.setStyleSheet("""
            QPushButton {
                font-size: 14px;
                color: #7f8c8d;
                background-color: transparent;
                border: 1px solid #bdc3c7;
                border-radius: 5px;
                padding: 8px 15px;
                margin-top: 10px;
            }
            QPushButton:hover {
                background-color: #ecf0f1;
            }
        """)
        settings_button.clicked.connect(self.show_settings)
        progress_layout.addWidget(settings_button)
        
        layout.addWidget(progress_frame)
    
    def show_coming_soon(self, activity_name):
        """Show coming soon message"""
        # For now, just update status bar
        self.main_window.status_bar.showMessage(f"{activity_name} - Coming Soon!")
    
    def show_settings(self):
        """Show settings (placeholder)"""
        self.main_window.status_bar.showMessage("Settings - Coming Soon!") 