from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                              QPushButton, QLabel, QCheckBox, QFrame,
                              QMenu, QWidgetAction)
from PySide6.QtCore import Qt, Signal, QObject, QEvent
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
        # Main card layout with grey background
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)  # Reduced margins to show grey background
        layout.setSpacing(0)  
        
        # Set fixed width for the card and grey background
        self.setFixedWidth(680)
        
        # Content container with border - this is the only border we want
        content_container = QFrame()
        content_container.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #D1D5DB;  /* Faint black border */
                border-radius: 12px;
            }
        """)
        
        # Content layout
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(24, 24, 24, 24)
        content_layout.setSpacing(20)
        
        # Global stylesheet for the widget - explicitly remove ALL borders except the content container
        self.setStyleSheet("""
            /* Main widget background */
            SubjectCard {
                background-color: #F3F4F6;  /* Light grey background */
                border: none;
            }
            
            /* Remove borders from ALL elements */
            QLabel, QPushButton, QCheckBox, QFrame {
                border: none;
            }
            
            /* Specific styling for elements */
            QLabel#instructionLabel {
                color: #6B7280;
                font-size: 16px;
                border: none;
            }
            
            QLabel#subjectLabel {
                font-size: 20px;
                font-weight: bold;
                color: #1F2937;
                border: none;
            }
            
            QCheckBox {
                font-size: 14px;
                color: #374151;
                background-color: #F3F4F6;
                border-radius: 8px;
                padding: 12px 24px;
                spacing: 8px;
                border: none;
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
            
            QPushButton#takeTestButton {
                background-color: #A855F7; 
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: 500;
            }
            
            QPushButton#takeTestButton:hover {
                background-color: #D8B4FE;  
            }
        """)
        
        # Header with subject name and delete button
        header = QHBoxLayout()
        header.setSpacing(16)
        
        # Subject name
        name = QLabel(self.subject_name)
        name.setObjectName("subjectLabel")
        name.setStyleSheet("border: none;")  # Explicitly set no border
        header.addWidget(name)
        
        # Delete button
        delete_btn = QPushButton("×")  
        delete_btn.setObjectName("deleteButton")
        delete_btn.setFixedSize(32, 32)
        delete_btn.setCursor(Qt.PointingHandCursor)
        delete_btn.clicked.connect(lambda: self.deleted.emit(self.subject_name))
        header.addWidget(delete_btn, alignment=Qt.AlignRight)
        
        content_layout.addLayout(header)
        
        # Instruction text
        instruction = QLabel("Select levels to access past papers:")
        instruction.setObjectName("instructionLabel")
        instruction.setStyleSheet("border: none;")  # Explicitly set no border
        content_layout.addWidget(instruction)
        
        # Level selection container - removing border
        levels_container = QFrame()
        levels_container.setStyleSheet("""
            QFrame {
                background-color: #F9FAFB;
                border-radius: 8px;
                padding: 16px;
                border: none;
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
            checkbox.setStyleSheet("border: none;")  # Explicitly set no border
            self.checkboxes[level] = checkbox
            levels_layout.addWidget(checkbox)
        
        levels_layout.addStretch()
        content_layout.addWidget(levels_container)
        
        # Bottom section with buttons
        bottom_section = QHBoxLayout()
        
        # View performance button
        view_performance = QPushButton("View performance ▼")
        view_performance.setObjectName("viewPerformance")
        view_performance.setCursor(Qt.PointingHandCursor)
        view_performance.setStyleSheet("border: none;")  # Explicitly set no border
        
        # Take Test Question button
        take_test_btn = QPushButton("Take Test Question")
        take_test_btn.setObjectName("takeTestButton")
        take_test_btn.setCursor(Qt.PointingHandCursor)
        take_test_btn.setStyleSheet("border: none;")  # Explicitly set no border
        take_test_btn.clicked.connect(self._show_test_level_dropdown)
        
        # Add buttons to bottom section
        bottom_section.addWidget(view_performance, alignment=Qt.AlignLeft)
        bottom_section.addStretch()  # This pushes the Take Test button to the right
        bottom_section.addWidget(take_test_btn, alignment=Qt.AlignRight)
        
        # Add bottom section to content layout
        content_layout.addLayout(bottom_section)
        
        # Add content container to main layout
        layout.addWidget(content_container)
    
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

    def _show_test_level_dropdown(self):
        """Show dropdown with selected levels and start button"""
        # Create dropdown menu
        dropdown = QMenu(self)
        dropdown.setStyleSheet("""
            QMenu {
                background-color: white;
                border: 1px solid #D1D5DB;
                border-radius: 8px;
                padding: 8px;
                min-width: 200px;
            }
            QMenu::item {
                padding: 8px 16px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #F3F4F6;
            }
        """)
        
        # Add header
        header_label = QLabel("Select the test level:")
        header_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #1F2937;
                padding: 8px 16px;
            }
        """)
        header_action = QWidgetAction(dropdown)
        header_action.setDefaultWidget(header_label)
        dropdown.addAction(header_action)
        
        # Add selected levels
        selected_levels = []
        level_labels = {
            'grade_7': 'Grade 7',
            'o_level': 'O Level',
            'a_level': 'A Level'
        }
        
        # Check which levels are selected
        for level_key, checkbox in self.checkboxes.items():
            if checkbox.isChecked():
                selected_levels.append((level_key, level_labels[level_key]))
        
        # If no levels selected, show message
        if not selected_levels:
            no_levels_label = QLabel("No levels selected. Please select at least one level.")
            no_levels_label.setStyleSheet("""
                QLabel {
                    font-size: 14px;
                    color: #EF4444;
                    padding: 8px 16px;
                }
            """)
            no_levels_action = QWidgetAction(dropdown)
            no_levels_action.setDefaultWidget(no_levels_label)
            dropdown.addAction(no_levels_action)
        else:
            # Create a container for the level list
            levels_container = QWidget()
            levels_layout = QVBoxLayout(levels_container)
            levels_layout.setContentsMargins(8, 4, 8, 4)
            levels_layout.setSpacing(4)
            
            # Add each level as a button with play icon
            for level_key, level_name in selected_levels:
                # Create a container for each level item
                level_item = QWidget()
                level_item.setObjectName(f"levelItem_{level_key}")
                level_item.setCursor(Qt.PointingHandCursor)
                
                # Set hover effect with light purple background
                level_item.setStyleSheet("""
                    QWidget {
                        border-radius: 6px;
                        padding: 8px;
                    }
                    QWidget:hover {
                        background-color: #F5F3FF;
                    }
                """)
                
                # Create horizontal layout for level name and play button
                item_layout = QHBoxLayout(level_item)
                item_layout.setContentsMargins(8, 4, 8, 4)
                
                # Level name
                name_label = QLabel(level_name)
                name_label.setStyleSheet("""
                    QLabel {
                        font-size: 14px;
                        color: #4B5563;
                    }
                """)
                
                # Play button - initially hidden
                play_button = QPushButton("▶")
                play_button.setObjectName("playButton")
                play_button.setCursor(Qt.PointingHandCursor)
                play_button.setFixedSize(28, 28)
                play_button.setStyleSheet("""
                    QPushButton {
                        background-color: #A855F7;
                        color: white;
                        border: none;
                        border-radius: 14px;
                        font-size: 12px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: #D8B4FE;
                    }
                """)
                play_button.setVisible(False)  # Initially hidden
                
                # Connect the play button to start the test
                play_button.clicked.connect(lambda _, lk=level_key: self._start_test_for_level(lk))
                
                # Add widgets to layout
                item_layout.addWidget(name_label)
                item_layout.addStretch()
                item_layout.addWidget(play_button)
                
                # Create event filters for hover effects
                class HoverEventFilter(QObject):
                    def __init__(self, parent, play_button):
                        super().__init__(parent)
                        self.play_button = play_button
                        
                    def eventFilter(self, obj, event):
                        if event.type() == QEvent.Enter:
                            self.play_button.setVisible(True)
                            return True
                        elif event.type() == QEvent.Leave:
                            self.play_button.setVisible(False)
                            return True
                        return False
                
                # Install event filter to show/hide play button on hover
                hover_filter = HoverEventFilter(level_item, play_button)
                level_item.installEventFilter(hover_filter)
                
                # Make the entire item clickable
                level_item.mousePressEvent = lambda event, lk=level_key: self._start_test_for_level(lk)
                
                # Add to levels layout
                levels_layout.addWidget(level_item)
            
            # Add a widget action for the levels container
            levels_action = QWidgetAction(dropdown)
            levels_action.setDefaultWidget(levels_container)
            dropdown.addAction(levels_action)
        
        # Show dropdown below the button
        button = self.sender()
        dropdown.exec_(button.mapToGlobal(button.rect().bottomLeft()))
    
    def _start_test_for_level(self, level_key):
        """Start the test for the specified level"""
        print(f"Starting test for subject: {self.subject_name}, level: {level_key}")
        # Here you would implement the actual test starting logic
        # For now, we just print the selection
