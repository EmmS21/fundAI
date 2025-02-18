from PySide6.QtWidgets import (QWidget, QGridLayout, QLabel, QVBoxLayout, 
                              QTabBar, QHBoxLayout, QPushButton, QLineEdit)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve

class ProfileInfoWidget(QWidget):
    def __init__(self, user_data):
        super().__init__()
        self.user_data = user_data
        self._setup_ui()
    
    def _setup_ui(self):
        # Main layout
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 60, 20, 20)
        self.setLayout(layout)
        
        # Create container for grid
        self.grid_widget = QWidget()
        grid_layout = QGridLayout(self.grid_widget)  # Set parent directly
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
                            tab_bar.setEnabled(True)  
                        
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
                            if not text: 
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
                        
                        field_layout.addWidget(error_label)  
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
                
            elif label_text == "Country":
                label = QLabel(label_text)
                label.setStyleSheet("""
                    QLabel {
                        color: #1a1a1a;
                        font-size: 16px;
                        font-weight: bold;
                    }
                """)
                
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
                
                if self.user_data.country:
                    # Create the country tag
                    tag = QPushButton(f"{self.user_data.country}    x")
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
                    
                    tag.clicked.connect(switch_to_edit)
                    
                    field_layout.addWidget(tag)
                    field_layout.addWidget(edit_field)
                    field_layout.addStretch()
                else:
                    value_label = QLabel("Not set")
                    value_label.setStyleSheet("""
                        QLabel {
                            font-size: 14px;
                            color: #374151;
                        }
                    """)
                    field_layout.addWidget(value_label)
                
                container_layout.addWidget(label, alignment=Qt.AlignCenter)
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

        print(f"Country value from database: {self.user_data}")        
        # Add fields to grid
        for i, (label, value) in enumerate(fields):
            row = i // 2
            col = i % 2
            grid_layout.addWidget(create_field(label, value), row, col)
        
        # Add buttons layout
        buttons_layout = QHBoxLayout()
        buttons_layout.setContentsMargins(0, 16, 0, 0)
        buttons_layout.setAlignment(Qt.AlignCenter)
        
        # Create Update button
        self.update_btn = QPushButton("Update")
        self.update_btn.setFixedSize(100, 36)
        self.update_btn.setStyleSheet("""
            QPushButton {
                background-color: #4285f4;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #357abd;
            }
        """)
        
        # Create Hide button
        self.hide_btn = QPushButton("Hide")
        self.hide_btn.setFixedSize(100, 36)
        self.hide_btn.setStyleSheet("""
            QPushButton {
                background-color: #f3f4f6;
                color: #374151;
                border: none;
                border-radius: 4px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #e5e7eb;
            }
        """)
        
        # Create toggle button with unicode arrow (hidden initially)
        self.toggle_icon = QPushButton("▼")
        self.toggle_icon.setFixedSize(32, 32)
        self.toggle_icon.setStyleSheet("""
            QPushButton {
                background-color: #f3f4f6;
                border-radius: 16px;
                padding: 8px;
                font-size: 16px;
                color: #374151;
            }
            QPushButton:hover {
                background-color: #e5e7eb;
            }
        """)
        self.toggle_icon.hide()
        
        # Add widgets to layouts
        buttons_layout.addWidget(self.update_btn)
        buttons_layout.addWidget(self.hide_btn)
        
        layout.addWidget(self.grid_widget)
        layout.addLayout(buttons_layout)
        layout.addWidget(self.toggle_icon, alignment=Qt.AlignCenter)
        
        # Connect buttons
        self.hide_btn.clicked.connect(self.animate_hide)
        self.toggle_icon.clicked.connect(self.animate_show)
        
    def animate_hide(self):
        """Animate hiding the fields"""
        self.animation = QPropertyAnimation(self.grid_widget, b"maximumHeight")
        self.animation.setDuration(300)
        self.animation.setStartValue(self.grid_widget.height())
        self.animation.setEndValue(0)
        self.animation.setEasingCurve(QEasingCurve.InOutQuad)
        
        def on_finish():
            self.grid_widget.hide()
            self.hide_btn.hide()
            self.update_btn.hide()
            self.toggle_icon.show()
        
        self.animation.finished.connect(on_finish)
        self.animation.start()
        
    def animate_show(self):
        """Animate showing the fields"""
        self.grid_widget.show()
        
        self.animation = QPropertyAnimation(self.grid_widget, b"maximumHeight")
        self.animation.setDuration(300)
        self.animation.setStartValue(0)
        self.animation.setEndValue(self.grid_widget.sizeHint().height())
        self.animation.setEasingCurve(QEasingCurve.InOutQuad)
        
        def on_finish():
            self.hide_btn.show()
            self.update_btn.show()
            self.toggle_icon.hide()
            self.grid_widget.setMaximumHeight(16777215)
        
        self.animation.finished.connect(on_finish)
        self.animation.start() 