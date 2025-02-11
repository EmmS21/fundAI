from PySide6.QtWidgets import QMainWindow, QStackedWidget
from PySide6.QtCore import Qt
from .step_widget import StepWidget
from src.data.database.operations import UserOperations

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
            StepWidget("What's your full name?", "name", 0, self.total_steps),
            StepWidget("When's your birthday?", "birthday", 1, self.total_steps),
            StepWidget("Which country are you from?", "country", 2, self.total_steps),
            StepWidget("What grade are you in?", "grade", 3, self.total_steps)
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
        user_data = {}
        for step in self.steps:
            user_data[step.field_name] = step.get_value()
        
        # Save to database
        UserOperations.create_user(user_data)
