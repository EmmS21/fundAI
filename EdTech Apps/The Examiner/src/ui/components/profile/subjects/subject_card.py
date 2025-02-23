from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                              QPushButton, QLabel, QCheckBox, QFrame)
from PySide6.QtCore import Qt, Signal
from src.data.database.operations import UserOperations

class SubjectCard(QWidget):
    deleted = Signal(str)
    levels_changed = Signal(str, dict)  # Emits subject name and level changes
    
    def __init__(self, subject_name, levels=None, parent=None):
        super().__init__(parent)
        self.subject_name = subject_name
        print(f"SubjectCard init - Subject: {subject_name}, Initial levels: {levels}")
        self.levels = levels or {'grade_7': False, 'o_level': False, 'a_level': False}
        self._setup_ui()
    
    def _setup_ui(self):
        # Main card layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)  
        
        # Set fixed width for the card
        self.setFixedWidth(680)
        
        # Card container styling
        self.setStyleSheet("""
            SubjectCard {
                background-color: white;
                border: 1px solid #F3F4F6;
                border-radius: 12px;
            }
            QLabel#instructionLabel {
                color: #6B7280;
                font-size: 16px;
            }
            QLabel#subjectLabel {
                font-size: 20px;
                font-weight: bold;
                color: #1F2937;
            }
            QCheckBox {
                font-size: 14px;
                color: #374151;
                background-color: #F3F4F6;
                border-radius: 8px;
                padding: 12px 24px;
                spacing: 8px;
            }
            QCheckBox:hover {
                background-color: #E5E7EB;
            }
            QCheckBox:checked {
                background-color: #E5E7EB;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 2px solid #D1D5DB;
                border-radius: 4px;
                background-color: white;
            }
            QCheckBox::indicator:hover {
                border-color: #A855F7;
            }
            QCheckBox::indicator:checked {
                background-color: #A855F7;
                border-color: #A855F7;
            }
            QPushButton#deleteButton {
                background-color: transparent;
                color: #6B7280;
                border: none;
                font-size: 18px;
                font-weight: bold;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton#deleteButton:hover {
                background-color: #FEE2E2;
                color: #EF4444;
            }
            QPushButton#viewPerformance {
                color: #A855F7;
                border: none;
                font-size: 14px;
                text-align: left;
                padding: 0;
            }
        """)
        
        # Header with subject name and delete button
        header = QHBoxLayout()
        header.setSpacing(16)
        
        # Subject name
        name = QLabel(self.subject_name)
        name.setObjectName("subjectLabel")
        header.addWidget(name)
        
        # Delete button
        delete_btn = QPushButton("×")  
        delete_btn.setObjectName("deleteButton")
        delete_btn.setFixedSize(32, 32)
        delete_btn.setCursor(Qt.PointingHandCursor)
        delete_btn.clicked.connect(lambda: self.deleted.emit(self.subject_name))
        header.addWidget(delete_btn, alignment=Qt.AlignRight)
        
        layout.addLayout(header)
        
        # Instruction text
        instruction = QLabel("Select levels to access past papers:")
        instruction.setObjectName("instructionLabel")
        layout.addWidget(instruction)
        
        # Level selection container
        levels_container = QFrame()
        levels_container.setStyleSheet("""
            QFrame {
                background-color: #F9FAFB;
                border-radius: 8px;
                padding: 16px;
            }
        """)
        levels_layout = QHBoxLayout(levels_container)
        levels_layout.setSpacing(24)  
        
        # Create checkboxes for each level
        self.checkboxes = {}
        labels = {
            'grade_7': 'Grade 7',
            'o_level': 'O Level',
            'a_level': 'A Level'
        }
        
        for level, label in labels.items():
            checkbox = QCheckBox(label)
            checkbox.setChecked(self.levels.get(level, False))
            checkbox.stateChanged.connect(
                lambda state, l=level: self._on_level_changed(l, bool(state))
            )
            self.checkboxes[level] = checkbox
            levels_layout.addWidget(checkbox)
        
        levels_layout.addStretch()
        layout.addWidget(levels_container)
        
        # View performance button
        view_performance = QPushButton("View performance ▼")
        view_performance.setObjectName("viewPerformance")
        view_performance.setCursor(Qt.PointingHandCursor)
        layout.addWidget(view_performance, alignment=Qt.AlignLeft)
    
    def _on_level_changed(self, level: str, checked: bool):
        """Handle checkbox state changes"""
        print(f"1. Checkbox changed - Level: {level}, Checked: {checked}")
        self.levels[level] = checked
        print(f"2. Updated levels dict: {self.levels}")
        
        # Get current user
        user = UserOperations.get_current_user()
        if user:
            print(f"3. Current user ID: {user.id}")
            # Update database
            success = UserOperations.update_subject_levels(user.id, self.subject_name, self.levels)
            print(f"4. Database update success: {success}")
        else:
            print("3. No user found!")
        
        # Emit signal for UI updates
        self.levels_changed.emit(self.subject_name, self.levels)
        print("5. Level changed signal emitted")
