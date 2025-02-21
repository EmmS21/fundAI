from PySide6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, 
                              QHBoxLayout, QComboBox)
from PySide6.QtCore import Qt, Signal
from src.data.database.operations import UserOperations

class SubjectSelector(QWidget):
    subject_added = Signal(str)  
    subject_removed = Signal(str) 
    
    def __init__(self, user_data):
        super().__init__()
        self.user_data = user_data
        self.subjects = [
            "Accounting", "Biology", "Computer Science", 
            "Economics", "English Language", "English Literature",
            "Mathematics", "Physics", "History"
        ]
        self._setup_ui()
        
    def _setup_ui(self):
        print("Setting up SubjectSelector UI")  # Debug print
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(8)
        
        # Create the dropdown
        self.combo_box = QComboBox()
        self.combo_box.setFixedWidth(300)
        print(f"Available subjects: {self.subjects}")  # Debug print
        self.combo_box.setStyleSheet("""
            QComboBox {
                border: none;
                padding: 8px 16px;
                font-size: 14px;
                background-color: transparent;
            }
            QComboBox::drop-down {
                border: none;
                width: 0px;
            }
            QComboBox::down-arrow {
                image: none;
                border: none;
            }
            QComboBox QAbstractItemView {
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                selection-background-color: #7c3aed;
                selection-color: #4285f4;
                background-color: white;
                color: #374151;
                padding: 4px;
            }
            QComboBox QAbstractItemView::item {
                min-height: 24px;
            }
        """)
        
        # Add available subjects (excluding already selected ones)
        self._update_available_subjects()
        
        # Container for selected subjects
        self.selected_container = QWidget()
        selected_layout = QVBoxLayout(self.selected_container)
        selected_layout.setSpacing(8)
        selected_layout.setContentsMargins(0, 8, 0, 0)
        
        # Add existing selected subjects
        if hasattr(self.user_data, 'subjects'):
            for subject in self.user_data.subjects:
                self._add_subject_tag(subject)
        
        # Connect signals
        self.combo_box.activated.connect(self._on_subject_selected)
        
        layout.addWidget(self.combo_box)
        layout.addWidget(self.selected_container)
        
    def _update_available_subjects(self):
        """Update the combo box with available subjects"""
        print("Updating available subjects")  # Debug print
        self.combo_box.clear()
        self.combo_box.addItem("Select a subject...")
        
        selected_subjects = getattr(self.user_data, 'subjects', [])
        available_subjects = [s for s in self.subjects if s not in selected_subjects]
        print(f"Selected subjects: {selected_subjects}")  # Debug print
        print(f"Available subjects: {available_subjects}")  # Debug print
        self.combo_box.addItems(available_subjects)
    
    def _add_subject_tag(self, subject):
        """Create a tag for selected subject"""
        tag_container = QWidget()
        tag_layout = QHBoxLayout(tag_container)
        tag_layout.setContentsMargins(0, 0, 0, 0)
        tag_layout.setSpacing(8)
        
        # Create tag button
        tag = QPushButton(f"{subject}    ×")
        tag.setFixedHeight(36)
        tag.setStyleSheet("""
            QPushButton {
                background-color: #7c3aed;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 14px;
                text-align: left;
            }
            QPushButton:hover {
                background-color: #6d28d9;
            }
        """)
        
        tag.clicked.connect(lambda: self._remove_subject(subject, tag_container))
        tag_layout.addWidget(tag)
        tag_layout.addStretch()
        
        self.selected_container.layout().addWidget(tag_container)
    
    def _on_subject_selected(self, index):
        """Handle subject selection from dropdown"""
        if index == 0:  # Skip "Select a subject..." option
            return
            
        subject = self.combo_box.currentText()
        if not self._is_subject_selected(subject):
            # Add subject to database
            UserOperations.add_subject(self.user_data.id, subject)
            
            # Add subject tag
            self._add_subject_tag(subject)
            
            # Update available subjects
            self._update_available_subjects()
            
            self.subject_added.emit(subject)
    
    def _remove_subject(self, subject, tag_container):
        """Remove a subject"""
        # Remove from database
        UserOperations.remove_subject(self.user_data.id, subject)
        
        # Remove tag from UI
        tag_container.deleteLater()
        
        # Update available subjects
        self._update_available_subjects()
        
        self.subject_removed.emit(subject)
    
    def _is_subject_selected(self, subject):
        return hasattr(self.user_data, 'subjects') and subject in self.user_data.subjects
