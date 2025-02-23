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
        
        # Create subject list first
        self.subject_list = SubjectList()
        self.subject_list.subject_removed.connect(self._on_subject_removed)  # Connect the signal
        layout.addWidget(self.subject_list)
        
        # Create the popup after subject list
        self.subject_popup = SubjectPopup(self._get_available_subjects())
        self.subject_popup.subject_selected.connect(self._on_subject_selected)
        
        # Add already-selected subjects (if any)
        if hasattr(self.user_data, 'subjects') and self.user_data.subjects:
            for user_subject in self.user_data.subjects:
                if hasattr(user_subject, 'subject_id'):
                    subject_name = UserOperations.get_subject_name(user_subject.subject_id)
                    if subject_name:
                        # Get the saved levels for this subject
                        levels = {
                            'grade_7': user_subject.grade_7,
                            'o_level': user_subject.o_level,
                            'a_level': user_subject.a_level
                        }
                        self.subject_list.add_subject(subject_name, levels)
    
    def _get_available_subjects(self):
        """Get list of subjects that haven't been selected yet"""
        try:
            # If no subjects attribute or empty subjects, return all subjects
            if not hasattr(self.user_data, 'subjects') or not self.user_data.subjects:
                return self.subjects
            
            # Get currently selected subject names
            selected_subjects = set()
            for user_subject in self.user_data.subjects:
                if hasattr(user_subject, 'subject_id'):
                    subject_name = UserOperations.get_subject_name(user_subject.subject_id)
                    if subject_name:
                        selected_subjects.add(subject_name)
            
            # Return subjects that aren't already selected
            return [s for s in self.subjects if s not in selected_subjects]
        except Exception as e:
            print(f"Error getting available subjects: {e}")
            return self.subjects
    
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
            if UserOperations.add_subject(subject):  # No need to pass user_id
                # Get the saved levels for this subject
                levels = UserOperations.get_subject_levels(subject)  # No need to pass user_id
                # Add to UI with the correct levels
                self.subject_list.add_subject(subject, levels)
                self.subject_added.emit(subject)
                
                # Update available subjects
                available_subjects = self._get_available_subjects()
                self.subject_popup.update_subjects(available_subjects)
                self.subject_popup.hide()
    
    def _is_subject_selected(self, subject_name):
        """Checks if the subject is already selected"""
        if not hasattr(self.user_data, 'subjects'):
            return False
        
        # Get all subject names through the relationship
        selected_subjects = []
        for user_subject in self.user_data.subjects:
            if hasattr(user_subject, 'subject_id'):
                subject = UserOperations.get_subject_name(user_subject.subject_id)
                if subject:
                    selected_subjects.append(subject)
        
        return subject_name in selected_subjects
    
    def _on_subject_removed(self, subject_name):
        """Handle subject removal"""
        print(f"1. Subject removal triggered for: {subject_name}")
        print(f"2. Current user ID: {self.user_data.id}")
        
        # Remove from database
        removal_success = UserOperations.remove_subject(self.user_data.id, subject_name)
        print(f"3. Database removal success: {removal_success}")
        
        if removal_success:
            # Refresh user data
            self.user_data = UserOperations.get_current_user()
            print(f"4. User data refreshed. Current subjects: {[UserOperations.get_subject_name(us.subject_id) for us in self.user_data.subjects]}")
            
            # Get current selected subjects
            current_subjects = [UserOperations.get_subject_name(us.subject_id) for us in self.user_data.subjects]
            print(f"5. Current selected subjects: {current_subjects}")
            
            # Calculate available subjects
            available_subjects = [s for s in self.subjects if s not in current_subjects]
            print(f"6. Available subjects for dropdown: {available_subjects}")
            
            # Update popup
            self.subject_popup.update_subjects(available_subjects)
            print("7. Popup updated with available subjects")
            
            # Emit signal
            self.subject_removed.emit(subject_name)
            print("8. Subject removed signal emitted")
        else:
            print("3a. Failed to remove subject from database")

class SubjectPopup(QFrame):
    subject_selected = Signal(str)
    
    def __init__(self, subjects, parent=None):
        super().__init__(parent)
        self.subjects = subjects
        self._setup_ui()
        
    def _setup_ui(self):
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
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(2)
        self.layout.setContentsMargins(4, 4, 4, 4)
        
        # Create scroll area for subjects
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)
        
        # Container widget for subjects
        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setSpacing(2)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        
        # Add subject buttons
        for subject in self.subjects:
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
            self.container_layout.addWidget(btn)
        
        self.scroll.setWidget(self.container)
        self.layout.addWidget(self.scroll)
        
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
    
    def update_subjects(self, new_subjects):
        """Update the list of available subjects"""
        self.subjects = new_subjects
        
        # Clear existing buttons
        for i in reversed(range(self.container_layout.count())): 
            widget = self.container_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        
        # Add new subject buttons
        for subject in self.subjects:
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
            self.container_layout.addWidget(btn)
