from PySide6.QtWidgets import QMainWindow, QStackedWidget, QMessageBox, QWidget, QVBoxLayout, QScrollArea
from PySide6.QtCore import Qt
from .step_widget import StepWidget
from src.data.database.operations import UserOperations
from src.utils.hardware_identifier import HardwareIdentifier
from ..profile.profile_header import ProfileHeader
from ..profile.achievements.achievement_widget import AchievementWidget
from ..profile.profile_info_widget import ProfileInfoWidget

class OnboardingWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Student Profile Setup")
        self.setFixedSize(1200, 800)
        
        # Set window background to white
        self.setStyleSheet("""
            QMainWindow {
                background-color: white;
            }
        """)
        
        # Create stacked widget to handle multiple steps
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)
        
        # Define steps
        self.total_steps = 4
        self.steps = [
            StepWidget("What's your full name?", "full_name", 0, self.total_steps),
            StepWidget("When's your birthday?", "birthday", 1, self.total_steps),
            StepWidget("Which country are you from?", "country", 2, self.total_steps),
            StepWidget("Are you in high school or primary school?", "school_level", 3, self.total_steps)
        ]
        
        # Add steps to stacked widget and connect signals
        for step in self.steps:
            self.stacked_widget.addWidget(step)
            step.continue_clicked.connect(self.next_step)
            step.back_clicked.connect(self.previous_step)
            
        self.current_step = 0
        
    def next_step(self):
        if self.current_step < len(self.steps) - 1:
            self.current_step += 1
            self.stacked_widget.setCurrentIndex(self.current_step)
        else:
            self.save_user_data()
            
    def previous_step(self):
        if self.current_step > 0:
            self.current_step -= 1
            self.stacked_widget.setCurrentIndex(self.current_step)
        
    def save_user_data(self):
        try:
            user_data = {}
            for step in self.steps:
                user_data[step.field_name] = step.get_value()
            
            print("Collected user data:", user_data)  # Debug log 1
            
            # Save to database and queue for sync
            created_user = UserOperations.create_user(user_data)
            print("Created user result:", created_user)  # Debug log 2
            
            # Get fresh user data
            fresh_user = UserOperations.get_current_user()
            print("Fresh user data:", fresh_user)  # Debug log 3
            
            if fresh_user is None:
                print("Warning: get_current_user returned None")  # Debug log 4
            
            QMessageBox.information(
                self,
                "Success",
                "Your profile has been saved and will be synced when online."
            )
            
            # Create scroll area for better content management
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            scroll_area.setStyleSheet("""
                QScrollArea {
                    border: none;
                    background-color: white;
                }
            """)
            
            # Create container widget
            container = QWidget()
            container.setStyleSheet("""
                QWidget {
                    background-color: white;
                }
            """)
            layout = QVBoxLayout(container)
            layout.setContentsMargins(20, 20, 20, 20)
            
            # Add profile header
            profile_header = ProfileHeader(fresh_user)
            layout.addWidget(profile_header)
            
            # Add achievement widget
            achievement_widget = AchievementWidget(fresh_user)
            layout.addWidget(achievement_widget)
            
            # Add profile info widget
            profile_info = ProfileInfoWidget(fresh_user)
            layout.addWidget(profile_info)
            
            # Add stretch to push everything to the top
            layout.addStretch()
            
            # Set the container as the scroll area widget
            scroll_area.setWidget(container)
            
            # Set as central widget
            self.setCentralWidget(scroll_area)
            self.setWindowTitle("Student Profile")
            
            # Set window and all widgets background to white
            self.setStyleSheet("""
                QMainWindow, QScrollArea, QWidget {
                    background-color: white;
                }
                QScrollArea {
                    border: none;
                }
            """)
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to save user data: {str(e)}"
            )
