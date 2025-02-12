from PySide6.QtWidgets import QMainWindow, QStackedWidget, QMessageBox, QWidget, QVBoxLayout
from PySide6.QtCore import Qt
from .step_widget import StepWidget
from src.data.database.operations import UserOperations
from src.utils.hardware_identifier import HardwareIdentifier
from src.ui.components.profile.profile_header import ProfileHeader

class OnboardingWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Student Profile Setup")
        self.setFixedSize(800, 600)
        
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
            
            # Save to database and queue for sync
            UserOperations.create_user(user_data)
            
            QMessageBox.information(
                self,
                "Success",
                "Your profile has been saved and will be synced when online."
            )
            
            # Get fresh user data
            fresh_user = UserOperations.get_current_user()
            
            # Clear existing widgets
            self.stacked_widget.setParent(None)
            
            # Create and set new central widget with profile content
            central_widget = QWidget()
            layout = QVBoxLayout(central_widget)
            layout.setContentsMargins(20, 20, 20, 20)
            
            # Add profile header
            profile_header = ProfileHeader(fresh_user)
            layout.addWidget(profile_header)
            layout.addStretch()
            
            # Set as central widget
            self.setCentralWidget(central_widget)
            self.setWindowTitle("Student Profile")  # Update window title
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to save user data: {str(e)}"
            )
