from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QProgressBar)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QIcon
from ..common.styled_widgets import StyledButton, StyledInput, AnimatedButton, DateInput, CountryInput, SchoolLevelInput
from datetime import datetime, date
import re

# Using QIcon theme icons that match our needs
STEP_ICONS = {
    "name": QIcon.fromTheme('help-about'),  # Person icon
    "birthday": QIcon.fromTheme('calendar'),  # Calendar icon
    "country": QIcon.fromTheme('applications-internet'),  # Globe/network icon
    "grade": QIcon.fromTheme('accessories-text-editor'),  # Education icon
}

# Fallback icons in case theme icons aren't available
FALLBACK_ICONS = {
    "name": QIcon.fromTheme('system-users'),
    "birthday": QIcon.fromTheme('x-office-calendar'),
    "country": QIcon.fromTheme('applications-internet'),
    "grade": QIcon.fromTheme('document-properties')
}

class StepWidget(QWidget):
    continue_clicked = Signal()
    back_clicked = Signal()
    
    def __init__(self, question, field_name, current_step, total_steps):
        super().__init__()
        self.field_name = field_name
        
        # Main layout
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        
        # Progress indicators
        progress_layout = QHBoxLayout()
        progress_layout.setSpacing(16)
        progress_layout.setContentsMargins(20, 10, 20, 10)
        
        # Create step indicators with icons
        for i, step_type in enumerate(["name", "birthday", "country", "grade"]):
            container = QWidget()
            container.setFixedSize(32, 32)
            
            # Get icon with fallback
            icon = STEP_ICONS.get(step_type, FALLBACK_ICONS.get(step_type))
            
            # Create icon label
            icon_label = QLabel()
            if icon and not icon.isNull():
                icon_label.setPixmap(icon.pixmap(20, 20))
            
            # Container layout
            container_layout = QVBoxLayout(container)
            container_layout.setContentsMargins(0, 0, 0, 0)
            container_layout.addWidget(icon_label, alignment=Qt.AlignCenter)
            
            # Style container
            container.setStyleSheet(f"""
                QWidget {{
                    background-color: {('#4285f4' if i == current_step else '#e0e0e0')};
                    border-radius: 16px;
                }}
            """)
            
            progress_layout.addWidget(container)
        
        # Steps remaining text
        steps_remaining = QLabel(f"{total_steps - current_step - 1} steps remaining")
        steps_remaining.setStyleSheet("""
            QLabel {
                color: #666666;
                font-size: 14px;
            }
        """)
        
        # Question label with centered text
        question_label = QLabel(question)
        question_label.setAlignment(Qt.AlignCenter)  # Center the question text
        question_label.setStyleSheet("""
            QLabel {
                font-size: 32px;
                color: #1a1a1a;
                font-weight: 500;
                margin: 24px 0;
            }
        """)
        
        # Input field with validation
        if field_name == "birthday":
            self.input = DateInput()
        elif field_name == "country":
            self.input = CountryInput()
        elif field_name == "school_level":
            self.input = SchoolLevelInput()
        else:
            self.input = StyledInput()
            self.input.setPlaceholderText(f"Enter your {field_name}")
        
        self.input.textChanged.connect(self.validate_input)
        
        # Buttons layout
        buttons_layout = QHBoxLayout()
        if current_step > 0:
            self.back_btn = AnimatedButton("Back", is_primary=False, direction="backward")
            self.back_btn.clicked.connect(self.back_clicked.emit)
            buttons_layout.addWidget(self.back_btn)
        
        buttons_layout.addStretch()
        self.continue_btn = AnimatedButton("Continue", direction="forward")
        self.continue_btn.clicked.connect(self.continue_clicked.emit)
        self.continue_btn.setEnabled(False)  # Disabled by default
        buttons_layout.addWidget(self.continue_btn)
        
        # Add all widgets to main layout
        main_layout.addLayout(progress_layout)
        main_layout.addWidget(steps_remaining, alignment=Qt.AlignRight)
        main_layout.addStretch()
        main_layout.addWidget(question_label)
        main_layout.addWidget(self.input)
        main_layout.addStretch()
        main_layout.addLayout(buttons_layout)
        
        # Initial validation
        self.validate_input()
    
    def validate_input(self):
        if self.field_name == "birthday":
            selected_date = self.input.get_date()
            if not selected_date:
                self.continue_btn.setEnabled(False)
                self.continue_btn.setErrorMessage("Please select your birthday")
                return
                
            # Check if date is not in the future
            if selected_date > date.today():
                self.continue_btn.setEnabled(False)
                self.continue_btn.setErrorMessage("Birthday cannot be in the future")
                return
                
            # Optional: Check for reasonable age range (e.g., 5-100 years)
            age = (date.today() - selected_date).days / 365
            if age < 5 or age > 100:
                self.continue_btn.setEnabled(False)
                self.continue_btn.setErrorMessage("Please enter a valid birth date")
                return
        
        elif self.field_name == "name":
            # Name validation: at least 2 words, letters only
            value = self.input.text().strip()
            if not re.match(r'^[A-Za-z]+\s+[A-Za-z]+', value):
                self.continue_btn.setEnabled(False)
                self.continue_btn.setErrorMessage("Please enter your full name")
                return
                
        elif self.field_name == "country":
            # Country validation: minimum length
            value = self.input.text().strip()
            if len(value) < 3:
                self.continue_btn.setEnabled(False)
                self.continue_btn.setErrorMessage("Please enter a valid country")
                return
                
        elif self.field_name == "grade":
            # Grade validation: numeric or valid grade format
            value = self.input.text().strip()
            if not re.match(r'^(1[0-2]|[1-9]|K)$', value):
                self.continue_btn.setEnabled(False)
                self.continue_btn.setErrorMessage("Enter grade (1-12 or K)")
                return
        
        # If we get here, input is valid
        self.continue_btn.setEnabled(True)
        self.continue_btn.setErrorMessage("")

    def get_value(self):
        if self.field_name == "birthday":
            return self.input.get_date()
        return self.input.text().strip()
