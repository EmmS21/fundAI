from PySide6.QtWidgets import QWidget, QGridLayout, QLabel, QVBoxLayout, QTabBar, QHBoxLayout, QPushButton, QLineEdit
from PySide6.QtCore import Qt

class ProfileInfoWidget(QWidget):
    def __init__(self, user_data):
        super().__init__()
        self.user_data = user_data
        self._setup_ui()
    
    def _setup_ui(self):
        # Main layout
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 60, 20, 20)  # Top margin to account for profile picture overflow
        self.setLayout(layout)
        
        # Grid for info fields
        grid_layout = QGridLayout()
        grid_layout.setSpacing(16)
        
        def create_field(label_text, value):
            container = QWidget()
            container_layout = QVBoxLayout(container)
            container_layout.setSpacing(8)
            
            if label_text == "Grade/Form":
                # Create tab bar
                tab_bar = QTabBar()
                tab_bar.addTab("Grade")
                tab_bar.addTab("Form")
                tab_bar.setStyleSheet("""
                    QTabBar::tab {
                        padding: 8px 16px;
                        margin-right: 4px;
                        border: none;
                        color: #6b7280;
                    }
                    QTabBar::tab:selected {
                        color: #4285f4;
                        font-weight: bold;
                    }
                    QTabBar::tab:disabled {
                        color: #d1d5db;
                    }
                """)
                
                # Disable tab bar initially when there's a selected value
                tab_bar.setEnabled(False)
                
                if self.user_data.school_level:
                    import re
                    match = re.match(r"(Primary|High School): (?:Grade |Form )?(\d+)", self.user_data.school_level)
                    if match:
                        level_type, number = match.groups()
                        # Set correct tab
                        is_primary = level_type == "Primary"
                        tab_bar.setCurrentIndex(0 if is_primary else 1)
                        
                        # Create the field container
                        field_container = QWidget()
                        field_container.setStyleSheet("""
                            QWidget {
                                border: 1px solid #e5e7eb;
                                border-radius: 8px;
                                min-width: 200px;
                            }
                        """)
                        field_layout = QHBoxLayout(field_container)
                        field_layout.setContentsMargins(12, 12, 12, 12)
                        
                        # Create the number tag
                        tag = QPushButton(f"{number}    x")
                        tag.setFixedHeight(28)
                        tag.setStyleSheet("""
                            QPushButton {
                                background-color: #4285f4;
                                color: white;
                                border: none;
                                border-radius: 2px;
                                padding: 4px 4px;
                                font-size: 14px;
                                text-align: left;
                            }
                            QPushButton:hover {
                                background-color: #357abd;
                            }
                        """)
                        
                        # Create editable field (hidden initially)
                        edit_field = QLineEdit()
                        edit_field.setStyleSheet("""
                            QLineEdit {
                                border: none;
                                font-size: 14px;
                                color: #374151;
                                background: transparent;
                            }
                        """)
                        edit_field.hide()
                        
                        def switch_to_edit():
                            tag.hide()
                            edit_field.show()
                            edit_field.setFocus()
                            tab_bar.setEnabled(True)  # Enable tab bar when tag is removed
                        
                        tag.clicked.connect(switch_to_edit)
                        
                        # Add widgets directly to field_layout
                        field_layout.addWidget(tag)
                        field_layout.addWidget(edit_field)
                        field_layout.addStretch()
                        
                        # Create error label (hidden initially)
                        error_label = QLabel()
                        error_label.setStyleSheet("""
                            QLabel {
                                color: #dc2626;
                                font-size: 12px;
                                margin-top: 4px;
                            }
                        """)
                        error_label.hide()
                        
                        def validate_input():
                            text = edit_field.text()
                            if not text:  # Allow empty field
                                error_label.hide()
                                return True
                            
                            is_grade = tab_bar.currentIndex() == 0
                            max_value = 7 if is_grade else 6
                            
                            try:
                                num = int(text)
                                if 1 <= num <= max_value:
                                    error_label.hide()
                                    return True
                                else:
                                    error_label.setText(f"Please enter a number between 1 and {max_value}")
                                    error_label.show()
                                    # Revert to last valid value
                                    edit_field.setText(text[:-1])
                                    return False
                            except ValueError:
                                if text and not text[-1].isdigit():
                                    # Remove non-digit character
                                    edit_field.setText(text[:-1])
                                return False
                        
                        def update_placeholder():
                            is_grade = tab_bar.currentIndex() == 0
                            edit_field.setPlaceholderText(f"Enter {'grade (1-7)' if is_grade else 'form (1-6)'}")
                            if edit_field.isVisible():
                                validate_input()
                        
                        # Connect validation to text changes
                        edit_field.textChanged.connect(validate_input)
                        
                        # Set initial placeholder and connect tab changes
                        update_placeholder()
                        tab_bar.currentChanged.connect(update_placeholder)
                        
                        field_layout.addWidget(error_label)  # Add error label to layout
                else:
                    field_container = QLabel("Not set")
                    field_container.setStyleSheet("""
                        QLabel {
                            background-color: white;
                            border: 1px solid #e5e7eb;
                            border-radius: 8px;
                            padding: 12px;
                            font-size: 14px;
                            color: #374151;
                            min-width: 200px;
                        }
                    """)
                
                container_layout.addWidget(tab_bar, alignment=Qt.AlignCenter)
                container_layout.addWidget(field_container)
                
            else:
                label = QLabel(label_text)
                label.setStyleSheet("""
                    QLabel {
                        color: #1a1a1a;
                        font-size: 16px;
                        font-weight: bold;
                    }
                """)
                
                value_label = QLabel(value)
                value_label.setStyleSheet("""
                    QLabel {
                        background-color: white;
                        border: 1px solid #e5e7eb;
                        border-radius: 8px;
                        padding: 12px;
                        font-size: 14px;
                        color: #374151;
                        min-width: 200px;
                    }
                """)
                
                container_layout.addWidget(label, alignment=Qt.AlignCenter)
                container_layout.addWidget(value_label)
            
            return container
        
        # Create fields
        fields = [
            ("School", "Not set"),
            ("Grade/Form", self.user_data.school_level.capitalize() if self.user_data.school_level else "Not set"),
            ("City", self.user_data.city or "Not set"),
            ("Country", self.user_data.country or "Not set")
        ]
        
        # Add fields to grid
        for i, (label, value) in enumerate(fields):
            row = i // 2
            col = i % 2
            grid_layout.addWidget(create_field(label, value), row, col)
        
        layout.addLayout(grid_layout) 