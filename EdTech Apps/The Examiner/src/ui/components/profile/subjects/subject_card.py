from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                              QPushButton, QLabel, QCheckBox)
from PySide6.QtCore import Qt, Signal

class SubjectCard(QWidget):
    deleted = Signal(str)
    levels_changed = Signal(str, dict)  # Emits subject name and level changes
    
    def __init__(self, subject_name, levels=None, parent=None):
        super().__init__(parent)
        self.subject_name = subject_name
        self.levels = levels or {'grade_7': False, 'o_level': False, 'a_level': False}
        self._setup_ui()
    
    def _setup_ui(self):
        # Main card layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)  # Space between header and checkboxes
        
        # Card container with border
        self.setStyleSheet("""
            SubjectCard {
                background-color: white;
                border: 1px solid #E5E7EB;
                border-radius: 8px;
            }
            QCheckBox {
                font-size: 14px;
                color: #374151;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 2px solid #D1D5DB;
                border-radius: 4px;
            }
            QCheckBox::indicator:checked {
                background-color: #A855F7;
                border-color: #A855F7;
                image: url(resources/icons/checkmark.svg);
            }
            QCheckBox::indicator:hover {
                border-color: #A855F7;
            }
        """)
        
        # Header with subject name and delete button
        header = QHBoxLayout()
        header.setSpacing(8)
        
        # Subject name
        name = QLabel(self.subject_name)
        name.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #1F2937;
            }
        """)
        header.addWidget(name)
        
        # Delete button
        delete_btn = QPushButton("×")
        delete_btn.setFixedSize(24, 24)
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #6B7280;
                border: none;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #EF4444;
            }
        """)
        delete_btn.clicked.connect(lambda: self.deleted.emit(self.subject_name))
        header.addWidget(delete_btn, alignment=Qt.AlignRight)
        
        layout.addLayout(header)
        
        # Level selection checkboxes
        checkbox_layout = QHBoxLayout()
        checkbox_layout.setSpacing(16)
        
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
            checkbox_layout.addWidget(checkbox)
        
        checkbox_layout.addStretch()  # Push checkboxes to the left
        layout.addLayout(checkbox_layout)
    
    def _on_level_changed(self, level: str, checked: bool):
        """Handle checkbox state changes"""
        self.levels[level] = checked
        self.levels_changed.emit(self.subject_name, self.levels)
