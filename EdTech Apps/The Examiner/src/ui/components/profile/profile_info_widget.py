from PySide6.QtWidgets import (QWidget, QGridLayout, QLabel, QVBoxLayout, 
                              QTabBar, QHBoxLayout, QPushButton, QLineEdit, QMessageBox)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer, Signal, Slot
from src.data.database.operations import UserOperations
from .achievements.medal_widget import MedalWidget
from .subjects.subject_selector import SubjectSelector
import logging

logger = logging.getLogger(__name__)

class ProfileInfoWidget(QWidget):
    test_requested = Signal(str, str)
    report_view_requested = Signal(int)

    def __init__(self, user_data):
        super().__init__()
        self.user_data = user_data
        self._setup_ui()
        self._setup_subjects_section()
    
    def create_field(self, label_text, value):
        """Create a field widget with label and value. Moved from _setup_ui to be accessible by all methods."""
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
            
            # Create tag-like element for "Not set"
            tag = QPushButton(f"{value}    x")
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
            
            container_layout.addWidget(label, alignment=Qt.AlignCenter)
            container_layout.addWidget(field_container)
                    
        return container

    def _setup_ui(self):
        # Main layout
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 60, 20, 20)
        self.setLayout(layout)
        
        # Create container for grid
        self.grid_widget = QWidget()
        grid_layout = QGridLayout(self.grid_widget)
        grid_layout.setSpacing(16)
        
        # Create fields
        fields = [
            ("School", self.user_data.school or "Not set"),
            ("Grade/Form", self.user_data.school_level.capitalize() if self.user_data.school_level else "Not set"),
            ("City", self.user_data.city or "Not set"),
            ("Country", self.user_data.country or "Not set")
        ]

        # Add fields to grid
        for i, (label, value) in enumerate(fields):
            row = i // 2
            col = i % 2
            self.grid_widget.layout().addWidget(self.create_field(label, value), row, col)
        
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
        self.update_btn.clicked.connect(self.update_fields)  
        
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
        self.toggle_icon = QPushButton("👤 Edit ▼")
        self.toggle_icon.setFixedSize(128, 32)
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
        
        # Add subjects toggle button
        self.subjects_toggle = QPushButton("📚 Subjects ▼")
        self.subjects_toggle.setFixedSize(128, 32)
        self.subjects_toggle.setStyleSheet("""
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
        self.subjects_toggle.clicked.connect(self.animate_show_subjects)
        layout.addWidget(self.subjects_toggle, alignment=Qt.AlignCenter)
        
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

    def update_fields(self):
        """Update edited fields in database and refresh display"""
        try:
            updates = {}
            
            # Iterate through all fields in the grid
            for i in range(self.grid_widget.layout().count()):
                field_container = self.grid_widget.layout().itemAt(i).widget()
                if field_container:
                    # Get the field layout
                    field_layout = field_container.layout()
                    if field_layout:
                        # Get the label and the container widget
                        label = None
                        for j in range(field_layout.count()):
                            widget = field_layout.itemAt(j).widget()
                            if isinstance(widget, QLabel):
                                label = widget
                            # Look inside the container widget for QLineEdit
                            elif isinstance(widget, QWidget):
                                container_layout = widget.layout()
                                if container_layout:
                                    for k in range(container_layout.count()):
                                        inner_widget = container_layout.itemAt(k).widget()
                                        if isinstance(inner_widget, QLineEdit) and inner_widget.isVisible():
                                            field_name = label.text().lower()
                                            if field_name == "grade/form":
                                                field_name = "school_level"
                                            elif field_name == "school":
                                                field_name = "school"
                                            value = inner_widget.text()
                                            updates[field_name] = value

            # Update database if we have changes
            if updates:
                for field, value in updates.items():
                    UserOperations.update_field(self.user_data.id, field, value)
                
                fresh_user = UserOperations.get_current_user()
                self.user_data = fresh_user
                self._refresh_fields()

                # Find and update the City field specifically
                for i in range(self.grid_widget.layout().count()):
                    container = self.grid_widget.layout().itemAt(i).widget()
                    if container and container.layout():
                        for j in range(container.layout().count()):
                            widget = container.layout().itemAt(j).widget()
                            if isinstance(widget, QLabel) and widget.text() == "City":
                                # Found the City field container
                                input_container = container.layout().itemAt(1).widget()
                                if input_container and input_container.layout():
                                    line_edit = None
                                    for k in range(input_container.layout().count()):
                                        if isinstance(input_container.layout().itemAt(k).widget(), QLineEdit):
                                            line_edit = input_container.layout().itemAt(k).widget()
                                            break
                                    if line_edit:
                                        line_edit.setText(self.user_data.city or "Not set")
                                        line_edit.setVisible(False)
                                        # Show the edit button again
                                        for k in range(input_container.layout().count()):
                                            if isinstance(input_container.layout().itemAt(k).widget(), QPushButton):
                                                input_container.layout().itemAt(k).widget().setVisible(True)
                                                break
                
                QMessageBox.information(
                    self,
                    "Success",
                    "Profile updated successfully!"
                )
            else:
                print("No updates found to apply")

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to update profile: {str(e)}"
            )

    def _refresh_fields(self):
        """Refresh all fields with current database values"""        
        # Store the current layout state before clearing
        visible_edits = {}
        layout = self.grid_widget.layout()
        
        # Capture which fields are in edit mode before refresh
        for i in range(layout.count()):
            container = layout.itemAt(i).widget()
            if container and container.layout():
                for j in range(container.layout().count()):
                    widget = container.layout().itemAt(j).widget()
                    if isinstance(widget, QLabel):
                        field_name = widget.text()
                    elif isinstance(widget, QWidget) and widget.layout():
                        for k in range(widget.layout().count()):
                            inner = widget.layout().itemAt(k).widget()
                            if isinstance(inner, QLineEdit) and inner.isVisible():
                                visible_edits[field_name] = inner.text()
        
        # Clear and recreate widgets
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Use the fresh user data for field values
        fields = [
            ("School", self.user_data.school or "Not set"),
            ("Grade/Form", self.user_data.school_level.capitalize() if self.user_data.school_level else "Not set"),
            ("City", self.user_data.city or "Not set"),
            ("Country", self.user_data.country or "Not set")
        ]        
        # Recreate and restore edit states
        for i, (label, value) in enumerate(fields):
            row, col = i // 2, i % 2
            new_widget = self.create_field(label, value)
            layout.addWidget(new_widget, row, col)
            
            # If this field was being edited, restore that state
            if label in visible_edits:
                for child in new_widget.findChildren(QPushButton):
                    if isinstance(child, QPushButton):
                        child.click()  # Simulate click to show edit field
                        break
        
        # Update layout
        layout.activate()
        self.grid_widget.updateGeometry()

    def _setup_subjects_section(self):
        print("Setting up subjects section")
        self.subjects_container = QWidget()
        subjects_layout = QVBoxLayout(self.subjects_container)
        subjects_layout.setContentsMargins(20, 20, 20, 20)
        subjects_layout.setAlignment(Qt.AlignLeft)
        
        # Header with title and hide button
        header_layout = QHBoxLayout()
        header_layout.setAlignment(Qt.AlignLeft)
        
        title = QLabel("My Subjects")
        title.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #1a1a1a;
            }
        """)
        header_layout.addWidget(title)
        
        self.subjects_hide_btn = QPushButton("▲ Hide")
        self.subjects_hide_btn.setFixedSize(80, 32)
        self.subjects_hide_btn.setStyleSheet("""
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
        self.subjects_hide_btn.clicked.connect(self.animate_hide_subjects)
        header_layout.addWidget(self.subjects_hide_btn)
        
        subjects_layout.addLayout(header_layout)
        
        # Add subject button
        add_subject_btn = QPushButton("+ Add Subject")
        add_subject_btn.setFixedSize(180, 48)
        add_subject_btn.setStyleSheet("""
            QPushButton {
                background-color: #A855F7;
                color: white;
                border: none;
                border-radius: 24px;
                font-size: 16px;
                font-weight: 500;
                padding: 12px 16px;
            }
            QPushButton:hover {
                background-color: #9333EA;
            }
        """)
        subjects_layout.addWidget(add_subject_btn, alignment=Qt.AlignCenter)
        
        # Create subject selector
        self.subject_selector = SubjectSelector(self.user_data)
        subjects_layout.addWidget(self.subject_selector, alignment=Qt.AlignCenter)
        
        # Simplified button click handler - just show the popup
        add_subject_btn.clicked.connect(
            lambda: self.subject_selector._show_subject_popup(add_subject_btn)
        )
        
        # Connect subject signals
        self.subject_selector.subject_added.connect(self._on_subject_added)
        self.subject_selector.subject_removed.connect(self._on_subject_removed)
        self.subject_selector.test_requested.connect(self.test_requested.emit)
        self.subject_selector.report_view_requested.connect(self.report_view_requested.emit)
        
        # Add to main layout
        self.layout().addWidget(self.subjects_container)
        self.subjects_container.hide()
        self.subjects_hide_btn.hide()

    def animate_hide_subjects(self):
        """Animate hiding subjects section"""
        self.animation = QPropertyAnimation(self.subjects_container, b"maximumHeight")
        self.animation.setDuration(300)
        self.animation.setStartValue(self.subjects_container.height())
        self.animation.setEndValue(0)
        self.animation.setEasingCurve(QEasingCurve.InOutQuad)
        
        def on_finish():
            self.subjects_container.hide()
            self.subjects_hide_btn.hide()
            self.subjects_toggle.show()
        
        self.animation.finished.connect(on_finish)
        self.animation.start()

    def animate_show_subjects(self):
        """Animate showing subjects section"""
        self.subjects_container.show()
        self.subjects_hide_btn.show()
        self.subjects_toggle.hide()

        self.animation = QPropertyAnimation(self.subjects_container, b"maximumHeight")
        self.animation.setDuration(300)
        self.animation.setStartValue(0)
        self.animation.setEndValue(self.subjects_container.sizeHint().height())
        self.animation.setEasingCurve(QEasingCurve.InOutQuad)
        self.animation.start()

    def _on_subject_added(self, subject):
        """Handle when a subject is added"""
        # You can add any additional UI updates here
        pass

    def _on_subject_removed(self, subject):
        """Handle when a subject is removed"""
        # You can add any additional UI updates here
        pass

    @Slot(str, str)
    def on_selector_test_requested(self, subject_name, level_key):
        """Relays the signal from SubjectSelector upwards."""
        logger.debug(f"ProfileInfoWidget received test request for {subject_name}/{level_key}, emitting signal.")
        self.test_requested.emit(subject_name, level_key)

    def _load_user_data(self):
        """Load user data from the database"""
        try:
            # Get current user data
            user_data = UserOperations.get_current_user()
            
            if not user_data:
                logger.warning("No user data found")
                return
            
            # Set user info
            self.user_id = user_data['id']
            self.user_name = user_data['full_name']
            self.user_country = user_data['country']
            self.user_school_level = user_data['school_level']
            
            # Update UI elements
            self.name_label.setText(self.user_name)
            
            # Set country flag if available
            if self.user_country:
                self._set_country_flag(self.user_country)
            
            # Set school level
            if self.user_school_level:
                self.school_level_label.setText(self.user_school_level)
            
            # Load user subjects
            self._load_subjects()
            
        except Exception as e:
            logger.error(f"Error loading user data: {e}")
    
    def _load_subjects(self):
        """Load user subjects from the database"""
        try:
            # Get user subjects - no need to pass user ID
            subjects = UserOperations.get_user_subjects()
            
            # Clear current subjects
            self._clear_subjects()
            
            # Add each subject to the UI
            for subject in subjects:
                self._add_subject_card(subject)
            
        except Exception as e:
            logger.error(f"Error loading subjects: {e}")
