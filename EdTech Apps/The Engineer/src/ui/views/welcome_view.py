"""
The Engineer AI Tutor - Welcome View
Simple welcome screen for young learners
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QLineEdit, QSpinBox, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

class WelcomeView(QWidget):
    """Welcome screen for new users"""
    
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the welcome UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(30)
        layout.setContentsMargins(50, 50, 50, 50)
        
        # Add some stretch at the top
        layout.addStretch(1)
        
        # Welcome title
        title = QLabel("Welcome to The Engineer!")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            QLabel {
                font-size: 32px;
                font-weight: bold;
                color: #2c3e50;
                margin-bottom: 20px;
            }
        """)
        layout.addWidget(title)
        
        # Subtitle
        subtitle = QLabel("Learn to think like a software engineer")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("""
            QLabel {
                font-size: 16px;
                color: #7f8c8d;
                margin-bottom: 30px;
            }
        """)
        layout.addWidget(subtitle)
        
        # Create user form
        form_frame = QFrame()
        form_frame.setMaximumWidth(400)
        form_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border-radius: 10px;
                padding: 20px;
            }
        """)
        
        form_layout = QVBoxLayout(form_frame)
        
        # Username input
        username_label = QLabel("What should we call you?")
        username_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #2c3e50;")
        form_layout.addWidget(username_label)
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter your name...")
        self.username_input.setStyleSheet("""
            QLineEdit {
                font-size: 14px;
                padding: 10px;
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                margin-bottom: 15px;
            }
            QLineEdit:focus {
                border-color: #3498db;
            }
        """)
        form_layout.addWidget(self.username_input)
        
        # Age input
        age_label = QLabel("How old are you?")
        age_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #2c3e50;")
        form_layout.addWidget(age_label)
        
        self.age_input = QSpinBox()
        self.age_input.setRange(12, 18)
        self.age_input.setValue(15)
        self.age_input.setStyleSheet("""
            QSpinBox {
                font-size: 14px;
                padding: 10px;
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                margin-bottom: 20px;
            }
            QSpinBox:focus {
                border-color: #3498db;
            }
        """)
        form_layout.addWidget(self.age_input)
        
        # Start button
        self.start_button = QPushButton("Start My Engineering Journey!")
        self.start_button.setStyleSheet("""
            QPushButton {
                font-size: 16px;
                font-weight: bold;
                color: white;
                background-color: #3498db;
                border: none;
                border-radius: 8px;
                padding: 15px 30px;
                margin-top: 10px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
        """)
        self.start_button.clicked.connect(self.start_journey)
        form_layout.addWidget(self.start_button)
        
        # Center the form
        form_container = QHBoxLayout()
        form_container.addStretch()
        form_container.addWidget(form_frame)
        form_container.addStretch()
        layout.addLayout(form_container)
        
        # Info text
        info_text = QLabel(
            "We'll start with a fun assessment to see how you think about problems!\n"
            "Don't worry - there are no wrong answers. We just want to understand\n"
            "how your mind works so we can help you learn better."
        )
        info_text.setAlignment(Qt.AlignCenter)
        info_text.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: #7f8c8d;
                line-height: 1.4;
                margin-top: 20px;
            }
        """)
        layout.addWidget(info_text)
        
        # Add stretch at the bottom
        layout.addStretch(1)
    
    def start_journey(self):
        """Start the onboarding process"""
        username = self.username_input.text().strip()
        age = self.age_input.value()
        
        if not username:
            # Simple validation - could add more user-friendly error display
            self.username_input.setPlaceholderText("Please enter your name!")
            self.username_input.setStyleSheet("""
                QLineEdit {
                    font-size: 14px;
                    padding: 10px;
                    border: 2px solid #e74c3c;
                    border-radius: 5px;
                    margin-bottom: 15px;
                }
            """)
            return
        
        # Create user in database
        user_id = self.main_window.db_manager.create_user(username, age)
        
        if user_id:
            # Store current user info
            self.main_window.current_user = {
                'id': user_id,
                'username': username,
                'age': age
            }
            
            # Move to onboarding
            self.main_window.show_onboarding()
        else:
            # Username exists - simple handling
            self.username_input.clear()
            self.username_input.setPlaceholderText("That name is taken, try another!")
            self.username_input.setStyleSheet("""
                QLineEdit {
                    font-size: 14px;
                    padding: 10px;
                    border: 2px solid #f39c12;
                    border-radius: 5px;
                    margin-bottom: 15px;
                }
            """) 