from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                              QPushButton, QLabel, QCheckBox, QFrame,
                              QMenu, QWidgetAction, QToolButton,
                              QSpacerItem, QSizePolicy, QProgressBar)
from PySide6.QtCore import Qt, Signal, QObject, QEvent, QTimer, Slot
from PySide6.QtGui import QCursor, QIcon, QColor, QAction
from src.data.database.operations import UserOperations
from src.utils.constants import PRIMARY_COLOR
from src.data.cache.cache_manager import CacheStatus, CacheProgressStatus, CacheManager
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class SubjectStatusIndicator(QWidget):
    """Status indicator for subject's exam availability"""
    
    def __init__(self, subject, level):
        super().__init__()
        self.subject = subject
        self.level = level
        self._setup_ui()
        self.update_status()
    
    def _setup_ui(self):
        """Setup the UI components"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(4)
        
        # Status dot indicator
        self.status_dot = QLabel()
        self.status_dot.setFixedSize(8, 8)
        self.status_dot.setStyleSheet("""
            background-color: #D1D5DB;
            border-radius: 4px;
        """)
        
        # Status text
        self.status_label = QLabel("Checking...")
        self.status_label.setStyleSheet("""
            color: #4B5563;
            font-size: 12px;
        """)
        
        layout.addWidget(self.status_dot)
        layout.addWidget(self.status_label)
        layout.addStretch()
    
    def update_status(self):
        """Check and update the status of exam content for this subject"""
        try:
            # Create a background checker to avoid UI freezing
            class StatusChecker(QRunnable):
                def __init__(self, subject, level, status_update_callback):
                    super().__init__()
                    self.subject = subject
                    self.level = level
                    self.callback = status_update_callback
                
                def run(self):
                    """Check cache status for this subject in background thread"""
                    try:
                        # Get cache manager
                        cache_manager = CacheManager()
                        
                        # Get current progress status
                        progress_status = cache_manager._get_subject_progress_status(self.subject, self.level)
                        
                        # Set initial state based on progress
                        if progress_status == CacheProgressStatus.SYNCING or progress_status == CacheProgressStatus.DOWNLOADING:
                            self.callback("Loading", "#3B82F6")  # Blue for loading
                            return
                            
                        # Check if we have content
                        print(f"Checking subject: {self.subject}, level: {self.level}")
                        question_count = cache_manager._count_cached_questions(self.subject, self.level)
                        
                        if question_count > 0:
                            # We have content
                            self.callback("Ready", "#10B981")  # Green for ready
                        else:
                            # No content
                            self.callback("No Exams Available", "#6B7280")  # Gray for no content
                            
                    except Exception as e:
                        logger.error(f"Error checking subject status: {e}", exc_info=True)
                        self.callback("Error", "#EF4444")  # Red for error
            
            # Run the check in background
            try:
                if hasattr(services, 'threadpool') and services.threadpool is not None:
                    checker = StatusChecker(self.subject, self.level, self._update_ui)
                    services.threadpool.start(checker)
                else:
                    # Direct call if no threadpool
                    self._update_ui("Checking...", "#F59E0B")
                    
                    # Get cache manager
                    cache_manager = CacheManager()
                    question_count = cache_manager._count_cached_questions(self.subject, self.level)
                    
                    if question_count > 0:
                        self._update_ui("Ready", "#10B981")  # Green for ready
                    else:
                        self._update_ui("No Exams Available", "#6B7280")  # Gray for no content
            except Exception as e:
                logger.error(f"Error starting status checker: {e}", exc_info=True)
                self._update_ui("Error", "#EF4444")  # Red for error
                
        except Exception as e:
            logger.error(f"Error in update_status: {e}", exc_info=True)
    
    def _update_ui(self, text, color):
        """Update the UI with status information"""
        try:
            # Update status text
            self.status_label.setText(text)
            
            # Update status label style
            self.status_label.setStyleSheet(f"""
                color: {color};
                font-size: 12px;
                font-weight: bold;
            """)
            
            # Update status dot color
            self.status_dot.setStyleSheet(f"""
                background-color: {color};
                border-radius: 4px;
                min-width: 8px;
                max-width: 8px;
                min-height: 8px;
                max-height: 8px;
            """)
            
        except Exception as e:
            logger.error(f"Error updating status UI: {e}", exc_info=True)

class SubjectCard(QWidget):
    deleted = Signal(str)
    levels_changed = Signal(str, dict)  # Emits subject name and level changes
    start_test_requested = Signal(str, str)  # NEW SIGNAL: (subject_name, level_key)
    
    def __init__(self, subject_name, levels=None, parent=None):
        super().__init__(parent)
        self.subject_name = subject_name
        print(f"SubjectCard init - Subject: {subject_name}, Initial levels: {levels}")
        self.levels = levels or {'grade_7': False, 'o_level': False, 'a_level': False}
        self.cache_manager = CacheManager()
        self.level_cache_status = {}
        self.level_status_labels = {}
        self.level_progress_bars = {}
        
        # Initialize UI
        self._setup_ui()
        
        # Do a one-time check of cache status on initialization
        self._update_cache_status()
    
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
            
            QLabel#statusLabel {
                font-size: 12px;
                font-weight: 500;
                border-radius: 4px;
                padding: 2px 6px;
            }
            
            QLabel#readyStatus {
                background-color: #DCFCE7;
                color: #166534;
            }
            
            QLabel#loadingStatus {
                background-color: #DBEAFE;
                color: #1E40AF;
            }
            
            QLabel#noContentStatus {
                background-color: #F3F4F6;
                color: #6B7280;
            }
            
            QWidget#headerStatusWidget {
                background-color: transparent;
                border: none;
                margin-right: 10px;
            }
        """)
        
        # Header with subject name and status
        header = QHBoxLayout()
        header.setSpacing(16)
        
        # Subject name
        name = QLabel(self.subject_name)
        name.setObjectName("subjectLabel")
        name.setStyleSheet("border: none;")  # Explicitly set no border
        header.addWidget(name)
        
        # Add spacer to push status indicator and delete button to the right
        header.addStretch()
        
        # Create status indicator for the header
        self.header_status_widget = QWidget()
        self.header_status_widget.setObjectName("headerStatusWidget")
        self.header_status_widget.setFixedHeight(28)
        header_status_layout = QHBoxLayout(self.header_status_widget)
        header_status_layout.setContentsMargins(0, 0, 0, 0)
        header_status_layout.setSpacing(6)
        
        # Status dot
        self.header_status_dot = QLabel()
        self.header_status_dot.setFixedSize(10, 10)
        self.header_status_dot.setStyleSheet("""
            background-color: #D1D5DB;
            border-radius: 5px;
        """)
        
        # Status text
        self.header_status_text = QLabel("Checking...")
        self.header_status_text.setObjectName("statusLabel")
        self.header_status_text.setStyleSheet("""
            color: #6B7280;
            font-size: 13px;
            background-color: #F3F4F6;
            padding: 2px 8px;
            border-radius: 4px;
        """)
        
        # Add to layout
        header_status_layout.addWidget(self.header_status_dot, alignment=Qt.AlignLeft | Qt.AlignVCenter)
        header_status_layout.addWidget(self.header_status_text, alignment=Qt.AlignLeft | Qt.AlignVCenter)
        
        # Add status widget to header
        header.addWidget(self.header_status_widget, alignment=Qt.AlignRight | Qt.AlignVCenter)
        
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
        self.level_status_indicators = {}  # Store status indicators
        
        labels = {
            'grade_7': 'Grade 7',
            'o_level': 'O Level',
            'a_level': 'A Level'
        }
        
        for level, label in labels.items():
            # Create checkbox
            checkbox = QCheckBox(label)
            checkbox.setChecked(self.levels.get(level, False))
            checkbox.stateChanged.connect(
                lambda state, l=level: self._on_level_changed(l, bool(state))
            )
            checkbox.setStyleSheet("border: none;")  # Explicitly set no border
            self.checkboxes[level] = checkbox
            
            # Add checkbox to layout
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
        take_test_btn.clicked.connect(self._show_test_level_dropdown)
        
        # Add buttons to bottom section
        bottom_section.addWidget(view_performance, alignment=Qt.AlignLeft)
        bottom_section.addStretch()  # This pushes the Take Test button to the right
        bottom_section.addWidget(take_test_btn, alignment=Qt.AlignRight)
        
        # Add bottom section to content layout
        content_layout.addLayout(bottom_section)
        
        # Add content container to main layout
        layout.addWidget(content_container)
        
        # Update the header status after setup
        QTimer.singleShot(100, self._update_header_status)
    
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
        
        # Update header status
        self._update_header_status()
    
    def _update_header_status(self):
        """Update the header status indicator with the combined status of all enabled levels"""
        print(f"DEBUG: _update_header_status called for Subject: {self.subject_name}")
        try:
            has_loading = False
            has_ready = False
            has_content = False
            enabled_levels = 0
            question_count = 0
            
            # Check status for each enabled level
            for level_key, enabled in self.levels.items():
                if not enabled:
                    continue

                enabled_levels += 1
                print(f"DEBUG: Checking status for enabled level: {level_key}")

                # Get cache status from CacheManager
                cache_data = self.cache_manager.get_subject_cache_status(self.subject_name, level_key)
                print(f"DEBUG: Cache data received for {level_key}: {cache_data}")

                progress_status = cache_data.get('progress_status', CacheProgressStatus.IDLE)
                level_question_count = cache_data.get('question_count', 0)
                
                # Update counters
                question_count += level_question_count
                
                # Check status flags
                if progress_status in [CacheProgressStatus.SYNCING, CacheProgressStatus.DOWNLOADING]:
                    has_loading = True
                if level_question_count > 0:
                    has_ready = True
                    has_content = True
            
            # Update header status based on the combined state
            if has_loading:
                print("DEBUG: Setting header status to Loading")
                self.header_status_text.setText("Loading")
                self.header_status_text.setStyleSheet("""
                    background-color: #DBEAFE;
                    color: #1E40AF;
                    border-radius: 4px;
                    padding: 2px 8px;
                    font-size: 13px;
                    font-weight: 500;
                """)
                self.header_status_dot.setStyleSheet("""
                    background-color: #3B82F6;
                    border-radius: 5px;
                    min-width: 10px;
                    max-width: 10px;
                    min-height: 10px;
                    max-height: 10px;
                """)
            elif has_ready:
                print("DEBUG: Setting header status to Ready")
                self.header_status_text.setText("Ready")
                self.header_status_text.setStyleSheet("""
                    background-color: #DCFCE7;
                    color: #166534;
                    border-radius: 4px;
                    padding: 2px 8px;
                    font-size: 13px;
                    font-weight: 500;
                """)
                self.header_status_dot.setStyleSheet("""
                    background-color: #10B981;
                    border-radius: 5px;
                    min-width: 10px;
                    max-width: 10px;
                    min-height: 10px;
                    max-height: 10px;
                """)
            elif enabled_levels > 0:
                print("DEBUG: Setting header status to No Exams Available (has_loading=False, has_ready=False, enabled_levels > 0)")
                self.header_status_text.setText("No Exams Available")
                self.header_status_text.setStyleSheet("""
                    background-color: #F3F4F6;
                    color: #6B7280;
                    border-radius: 4px;
                    padding: 2px 8px;
                    font-size: 13px;
                    font-weight: 500;
                """)
                self.header_status_dot.setStyleSheet("""
                    background-color: #6B7280;
                    border-radius: 5px;
                    min-width: 10px;
                    max-width: 10px;
                    min-height: 10px;
                    max-height: 10px;
                """)
            else:
                print("DEBUG: Setting header status to No Levels Selected")
                self.header_status_text.setText("No Levels Selected")
                self.header_status_text.setStyleSheet("""
                    background-color: #F3F4F6;
                    color: #6B7280;
                    border-radius: 4px;
                    padding: 2px 8px;
                    font-size: 13px;
                    font-weight: 500;
                """)
                self.header_status_dot.setStyleSheet("""
                    background-color: #D1D5DB;
                    border-radius: 5px;
                    min-width: 10px;
                    max-width: 10px;
                    min-height: 10px;
                    max-height: 10px;
                """)
                
            self.header_status_widget.setVisible(enabled_levels > 0)
                
        except Exception as e:
            logger.error(f"Error updating header status for {self.subject_name}: {e}", exc_info=True)
            print(f"DEBUG: Error occurred in _update_header_status for {self.subject_name}, setting status to Error")
            self.header_status_text.setText("Error")
            self.header_status_text.setStyleSheet("color: red;") # Example error style
            
    def _show_test_level_dropdown(self):
        """Creates and shows a dropdown menu listing enabled levels with play icons."""
        # Find the button that triggered this
        button = self.findChild(QPushButton, "takeTestButton")
        if not button:
            logger.error("Could not find 'takeTestButton' to show dropdown.")
            return

        menu = QMenu(self)
        # Style the menu - using a light purple background and the button hover color for selection
        menu.setStyleSheet("""
            QMenu {
                background-color: #F5F3FF; /* Light purple background */
                border: 1px solid #E5E7EB; /* Soft border */
                border-radius: 6px;
                padding: 4px; /* Padding around items */
            }
            QMenu::item {
                padding: 8px 20px; /* Padding within each item */
                background-color: transparent;
                color: #1F2937; /* Dark text */
                border-radius: 4px; /* Slightly rounded corners for items */
                 margin: 2px; /* Add slight margin between items */
            }
            QMenu::item:selected { /* Hover/selected state */
                background-color: #D8B4FE; /* Button hover color */
                color: white; /* White text when selected */
            }
            QMenu::icon {
                 padding-left: 5px; /* Space for the icon */
            }
        """)

        # Get enabled levels
        enabled_levels = [key for key, enabled in self.levels.items() if enabled]

        if not enabled_levels:
            # Option 1: Show a disabled item
            no_levels_action = QAction("No levels selected", self)
            no_levels_action.setEnabled(False)
            menu.addAction(no_levels_action)
            # Option 2: Don't show the menu at all (uncomment below and comment above action)
            # logger.info("No levels selected, not showing dropdown.")
            # return
        else:
            # Get a standard "play" icon
            # Note: "media-playback-start" might depend on your desktop environment/theme.
            # Fallback to a unicode character if the theme icon isn't found.
            play_icon = QIcon.fromTheme("media-playback-start")
            if play_icon.isNull():
                 logger.warning("Standard 'media-playback-start' icon not found. Using fallback.")
                 # You might need to adjust the UI if using unicode directly
                 # play_icon = QIcon() # Or create an icon from a character/image path

            for level_key in enabled_levels:
                level_name = self._get_level_display_name(level_key)
                action = QAction(play_icon, level_name, self) # Add icon here
                # Connect to the new function, passing the level key
                action.triggered.connect(lambda checked=False, lk=level_key: self._start_test_for_level(lk))
                menu.addAction(action)

        # Calculate position below the button
        button_pos = button.mapToGlobal(button.rect().bottomLeft())
        menu.popup(button_pos)

    def _start_test_for_level(self, level_key):
        print(f"[DEBUG] Button clicked for {self.subject_name} - {level_key}")
        print(f"[DEBUG] Signal object: {self.start_test_requested}")
        print(f"[DEBUG] Parent widget: {self.parent()}")
        self.start_test_requested.emit(self.subject_name, level_key)

    def _update_cache_status(self):
        """Update the cache status for each level"""
        try:
            # Update header status first
            self._update_header_status()
            
            # Update dropdown menu status if it exists
            for level_key, enabled in self.levels.items():
                if not enabled:
                    continue
                
                # Skip if no status label exists in the dropdown
                if level_key not in self.level_status_labels:
                    continue
                    
                # Get cache status from CacheManager
                cache_data = self.cache_manager.get_subject_cache_status(self.subject_name, level_key)
                status = cache_data.get('status', CacheStatus.INVALID)
                progress_status = cache_data.get('progress_status', CacheProgressStatus.IDLE)
                completion = cache_data.get('completion_percentage', 0)
                question_count = cache_data.get('question_count', 0)
                
                # Store status for later use
                self.level_cache_status[level_key] = cache_data
                
                # Update status indicator color and text
                status_label = self.level_status_labels[level_key]
                progress_bar = self.level_progress_bars.get(level_key)
                
                # Use user-friendly labels based on status
                if progress_status in [CacheProgressStatus.SYNCING, CacheProgressStatus.DOWNLOADING]:
                    status_label.setStyleSheet("QLabel { background-color: #3B82F6; border-radius: 8px; }")  # Blue
                    status_label.setToolTip("Loading")
                elif question_count > 0:
                    status_label.setStyleSheet("QLabel { background-color: #10B981; border-radius: 8px; }")  # Green
                    status_label.setToolTip("Ready")
                else:
                    status_label.setStyleSheet("QLabel { background-color: #6B7280; border-radius: 8px; }")  # Gray
                    status_label.setToolTip("No Exams Available")
                
                # Update progress bar if syncing or downloading
                if progress_bar and progress_status in [CacheProgressStatus.SYNCING, CacheProgressStatus.DOWNLOADING]:
                    progress_bar.setVisible(True)
                    progress_bar.setValue(int(completion))
                    
                    if progress_status == CacheProgressStatus.SYNCING:
                        progress_bar.setToolTip(f"Loading: {completion:.1f}% complete")
                    else:
                        progress_bar.setToolTip(f"Loading: {completion:.1f}% complete")
                elif progress_bar:
                    progress_bar.setVisible(False)
                
        except Exception as e:
            logger.error(f"Error updating cache status: {e}")

    def update_content_status(self):
        """Update the status indicator for this subject"""
        # Update header status
        self._update_header_status()
    
    def on_sync_started(self):
        """Handle when sync process starts for this subject"""
        try:
            # Update header status to show loading
            self.header_status_text.setText("Loading")
            self.header_status_text.setStyleSheet("""
                background-color: #DBEAFE;
                color: #1E40AF;
                border-radius: 4px;
                padding: 2px 8px;
                font-size: 13px;
                font-weight: 500;
            """)
            self.header_status_dot.setStyleSheet("""
                background-color: #3B82F6;
                border-radius: 5px;
                min-width: 10px;
                max-width: 10px;
                min-height: 10px;
                max-height: 10px;
            """)
            
            # Make sure the status is visible
            self.header_status_widget.setVisible(True)
            
        except Exception as e:
            logger.error(f"Error in sync start handler: {e}", exc_info=True)
    
    def on_sync_completed(self, level_key=None):
        """Handle completion of sync for a level"""
        try:
            # Update header status
            self._update_header_status()
            
            # Update dropdown menu status
            self._update_cache_status()
        except Exception as e:
            logger.error(f"Error in sync completion handler: {e}", exc_info=True)

    def show_menu(self):
        """Show context menu for the subject card"""
        menu = QMenu(self)
        
        # Create menu actions
        sync_action = QAction("Sync Now", self)
        refresh_action = QAction("Refresh Status", self)
        details_action = QAction("Subject Details", self)
        
        # Connect actions
        sync_action.triggered.connect(self.sync_content)
        refresh_action.triggered.connect(self.update_content_status)
        details_action.triggered.connect(self.show_details)
        
        # Add actions to menu
        menu.addAction(sync_action)
        menu.addAction(refresh_action)
        menu.addSeparator()
        menu.addAction(details_action)
        
        # Show the menu at current cursor position
        menu.exec_(QCursor.pos())
    
    def sync_content(self):
        """Trigger content sync for this subject"""
        try:
            # Set status to loading
            self.update_status_indicator("Loading", "yellow")
            self.on_sync_started()
            
            # Queue the sync operation
            from src.data.database.operations import UserOperations
            
            # Get enabled levels
            enabled_levels = []
            if self.checkboxes['grade_7'].isChecked():
                enabled_levels.append("grade_7")
            if self.checkboxes['o_level'].isChecked():
                enabled_levels.append("o_level")
            if self.checkboxes['a_level'].isChecked():
                enabled_levels.append("a_level")
            
            # Save changes first - no need to pass user ID
            UserOperations.update_subject_for_user(
                self.subject_name,
                grade_7=self.checkboxes['grade_7'].isChecked(),
                o_level=self.checkboxes['o_level'].isChecked(),
                a_level=self.checkboxes['a_level'].isChecked()
            )
            
            # Trigger content sync for enabled levels
            from src.core import services
            for level in enabled_levels:
                # Convert level to MongoDB format
                mongo_level = self._convert_level_to_mongo_format(level)
                
                # Queue sync in the sync service
                services.sync_service.queue_content_sync(
                    self.subject_name,
                    mongo_level,
                    callback=self.on_sync_completed
                )
            
        except Exception as e:
            logger.error(f"Error syncing content: {e}")
            self.update_status_indicator("Error", "red")

    def show_details(self):
        """Show detailed information about this subject"""
        try:
            # This would show a dialog with more information
            # For now, just log that it was requested
            logger.info(f"Showing details for {self.subject_name}")
            
            # Get detailed cache stats for all enabled levels
            cache_manager = CacheManager()
            status_info = {}
            
            for level_key, enabled in self.levels.items():
                if not enabled:
                    continue
                    
                status = cache_manager.get_subject_cache_status(self.subject_name, level_key)
                status_info[level_key] = status
            
            # Convert to readable format
            status_json = json.dumps(status_info, indent=2)
            logger.info(f"Subject status: {status_json}")
            
            # In a real implementation, this would open a dialog showing the details
            # For example:
            # SubjectDetailsDialog(self.subject_name, status_info, self).exec_()
            
        except Exception as e:
            logger.error(f"Error showing details: {e}", exc_info=True)
    
    def _get_level_display_name(self, level_key):
        """Convert level key to display name"""
        display_names = {
            'grade_7': 'Grade 7',
            'o_level': 'O Level',
            'a_level': 'A Level'
        }
        return display_names.get(level_key, level_key.replace('_', ' ').title())

    def _on_checkbox_toggled(self):
        """Handle checkbox state changes and update database"""
        try:
            # Update database with new checkbox states
            from src.data.database.operations import UserOperations
            
            # No need to pass user ID parameter
            UserOperations.update_subject_for_user(
                self.subject_name,
                grade_7=self.checkboxes['grade_7'].isChecked(),
                o_level=self.checkboxes['o_level'].isChecked(),
                a_level=self.checkboxes['a_level'].isChecked()
            )
            
            # Update the status indicator based on the new states
            self._update_header_status()
            
        except Exception as e:
            logger.error(f"Error updating subject levels: {e}")
