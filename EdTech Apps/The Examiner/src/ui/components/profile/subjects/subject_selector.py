from PySide6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, 
                              QHBoxLayout, QFrame, QScrollArea)
from PySide6.QtCore import Qt, Signal, QPoint, Slot, QObject
from src.data.database.operations import UserOperations
from .subject_list import SubjectList
from .subject_card import SubjectCard
import logging

logger = logging.getLogger(__name__)

class SubjectSelector(QWidget):
    subject_added = Signal(str)  
    subject_removed = Signal(str)
    test_requested = Signal(str, str)
    
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
            # Add subject to the database using add_subject_for_user
            # Default all levels to False initially - they can be toggled later
            result = UserOperations.add_subject_for_user(
                subject_name=subject,
                grade_7=False,
                o_level=False,
                a_level=False
            )
            
            if result:
                # Get the levels for this subject (should all be False initially)
                levels = {
                    'grade_7': False,
                    'o_level': False,
                    'a_level': False
                }
                
                # Add to UI with the correct levels
                self.subject_list.add_subject(subject, levels)
                self.subject_added.emit(subject)
                
                # Update available subjects
                available_subjects = self._get_available_subjects()
                self.subject_popup.update_subjects(available_subjects)
                self.subject_popup.hide()
            else:
                print(f"Failed to add subject: {subject}")
    
    def _is_subject_selected(self, subject_name):
        """Checks if the subject is already selected"""
        # Get all user subjects using the modified UserOperations method
        subjects = UserOperations.get_user_subjects()
        
        # Check if the subject name is in the list
        for subject in subjects:
            if subject.name == subject_name:
                return True
                
        return False
    
    def _on_subject_removed(self, subject_name):
        """Handle subject removal"""
        print(f"1. Subject removal triggered for: {subject_name}")
        
        # Get all subjects
        subjects = UserOperations.get_user_subjects()
        
        # Find the subject ID for the given name
        subject_id = None
        for subject in subjects:
            if subject.name == subject_name:
                subject_id = subject.id
                break
                
        if subject_id is None:
            print(f"Cannot find subject ID for name: {subject_name}")
            return
            
        # Remove from database using delete_subject_for_user
        removal_success = UserOperations.delete_subject_for_user(subject_id)
        print(f"3. Database removal success: {removal_success}")
        
        if removal_success:
            # Get current selected subjects
            updated_subjects = UserOperations.get_user_subjects()
            current_subject_names = [s.name for s in updated_subjects]
            print(f"5. Current selected subjects: {current_subject_names}")
            
            # Calculate available subjects
            available_subjects = [s for s in self.subjects if s not in current_subject_names]
            print(f"6. Available subjects for dropdown: {available_subjects}")
            
            # Update popup
            self.subject_popup.update_subjects(available_subjects)
            print("7. Popup updated with available subjects")
            
            # Emit signal
            self.subject_removed.emit(subject_name)
            print("8. Subject removed signal emitted")
        else:
            print("3a. Failed to remove subject from database")

    def _add_subject_card(self, subject_name, levels):
        """Adds a subject card to the layout and connects its signals."""
        card = SubjectCard(subject_name, levels)
        self.subject_cards[subject_name] = card

        # Connect delete signal
        card.deleted.connect(lambda name=subject_name: self._remove_subject(name))
        # Connect level changes signal
        card.levels_changed.connect(self._on_levels_changed)

        # --- Detailed Debugging for Signal Connection ---
        try:
            logger.info(f"Attempting to connect start_test_requested for {subject_name}...")
            # Check types before connecting
            signal_instance = card.start_test_requested
            slot_instance = self.on_card_test_requested
            logger.info(f"  - Signal type: {type(signal_instance)}")
            logger.info(f"  - Slot type: {type(slot_instance)}")

            # Make the connection
            connection_successful = signal_instance.connect(slot_instance)

            # Check the return value of connect (though it's often True even if the slot doesn't run later)
            logger.info(f"  - Connection result for {subject_name}: {connection_successful}")

            # Verify connection exists using receivers() - More reliable check
            # Note: This might show the number of connections, not just True/False
            receiver_count = card.receivers(card.start_test_requested)
            logger.info(f"  - Receivers count for {subject_name}'s start_test_requested: {receiver_count}")
            if receiver_count == 0:
                 logger.error(f"  - *** FAILED TO CONNECT start_test_requested for {subject_name} ***")

        except Exception as e:
            logger.error(f"  - *** EXCEPTION during connect for {subject_name}: {e} ***", exc_info=True)
        # --- End Detailed Debugging ---

        # Insert card into layout
        insert_index = self.subjects_layout.count()
        if insert_index > 0:
             insert_index -= 1
        self.subjects_layout.insertWidget(insert_index, card)
        logger.info(f"Added SubjectCard for {subject_name} to layout")

    @Slot(str, str)
    def on_card_test_requested(self, subject_name, level_key):
        """Relays the signal from SubjectCard upwards."""
        # Keep the INFO log here for when it *does* work
        logger.info(f"SubjectSelector received test request for {subject_name}/{level_key}, emitting signal.")
        self.test_requested.emit(subject_name, level_key)

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
