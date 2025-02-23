from PySide6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, 
                              QHBoxLayout, QFrame, QScrollArea)
from PySide6.QtCore import Qt, Signal, QPoint
from src.data.database.operations import UserOperations
from .subject_list import SubjectList

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
        print("Setting up SubjectSelector UI")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 8, 20, 0)
        
        # Create the popup (but don't show it yet)
        self.subject_popup = SubjectPopup(self._get_available_subjects())
        self.subject_popup.subject_selected.connect(self._on_subject_selected)
        
        # Create subject list
        self.subject_list = SubjectList()
        layout.addWidget(self.subject_list)
        
        # Add already-selected subjects (if any)
        if hasattr(self.user_data, 'subjects') and self.user_data.subjects:
            for subject in self.user_data.subjects:
                self.subject_list.add_subject(subject.name)  # Assuming subject has a name attribute
    
    def _get_available_subjects(self):
        """Get list of subjects that haven't been selected yet"""
        # Access subjects directly from the User object
        selected_subjects = [subject.name for subject in getattr(self.user_data, 'subjects', [])]
        return [s for s in self.subjects if s not in selected_subjects]
    
    def _show_subject_popup(self, button):
        """Show the subject popup under the specified button"""
        # Update available subjects
        self.subject_popup = SubjectPopup(self._get_available_subjects())
        self.subject_popup.subject_selected.connect(self._on_subject_selected)
        self.subject_popup.show_under_widget(button)
    
    def _on_subject_selected(self, subject):
        """Handle a subject selection from the popup"""
        if not self._is_subject_selected(subject):
            # Add to database first
            if UserOperations.add_subject(self.user_data['id'], subject):
                # Add to UI
                self.subject_list.add_subject(subject)
                
                # Update user data dictionary
                if 'subjects' not in self.user_data:
                    self.user_data['subjects'] = []
                if subject not in self.user_data['subjects']:
                    self.user_data['subjects'].append(subject)
                
                # Emit signal and close popup
                self.subject_added.emit(subject)
                self.subject_popup.hide()
    
    def _is_subject_selected(self, subject):
        """Checks if the subject is already selected"""
        # Access subjects directly from the User object
        selected_subjects = [subject.name for subject in getattr(self.user_data, 'subjects', [])]
        return subject in selected_subjects

class SubjectPopup(QFrame):
    subject_selected = Signal(str)
    
    def __init__(self, subjects, parent=None):
        super().__init__(parent)
        self.subjects = subjects
        
        # Set up popup styling and behavior
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #E5E7EB;
                border-radius: 8px;
            }
        """)
        
        # Create layout
        layout = QVBoxLayout(self)
        layout.setSpacing(2)
        layout.setContentsMargins(4, 4, 4, 4)
        
        # Create scroll area for subjects
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)
        
        # Container widget for subjects
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setSpacing(2)
        container_layout.setContentsMargins(0, 0, 0, 0)
        
        # Add subject buttons
        for subject in subjects:
            btn = QPushButton(subject)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: white;
                    color: #374151;
                    border: none;
                    border-radius: 4px;
                    padding: 8px 12px;
                    font-size: 14px;
                    text-align: left;
                }
                QPushButton:hover {
                    background-color: #F3F8FF;
                    color: #A855F7;
                }
            """)
            btn.clicked.connect(lambda checked, s=subject: self._on_subject_clicked(s))
            container_layout.addWidget(btn)
        
        scroll.setWidget(container)
        layout.addWidget(scroll)
        
        # Set fixed width and maximum height
        self.setFixedWidth(200)
        self.setMaximumHeight(300)
    
    def _on_subject_clicked(self, subject):
        self.subject_selected.emit(subject)
        self.hide()
    
    def show_under_widget(self, widget):
        """Position the popup under the specified widget and show it"""
        pos = widget.mapToGlobal(QPoint(0, widget.height()))
        self.move(pos)
        self.show()
