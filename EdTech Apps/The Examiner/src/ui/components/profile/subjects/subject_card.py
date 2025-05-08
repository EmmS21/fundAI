from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                              QPushButton, QLabel, QCheckBox, QFrame,
                              QMenu, QWidgetAction, QToolButton,
                              QSpacerItem, QSizePolicy, QProgressBar,
                              QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView)
from PySide6.QtCore import Qt, Signal, QObject, QEvent, QTimer, Slot, QPoint
from PySide6.QtGui import QCursor, QIcon, QColor, QAction
from src.data.database.operations import UserOperations
from src.utils.constants import PRIMARY_COLOR
from src.data.cache.cache_manager import CacheStatus, CacheProgressStatus, CacheManager
import logging
import json
from datetime import datetime
from typing import List, Dict
from src.data.database.models import CachedQuestion

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

class PerformanceReportPopup(QWidget):
    report_selected = Signal(int) # Emits history_id when a report is selected

    def __init__(self, preliminary_reports, final_reports, parent=None):
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint) # Style as popup
        self.preliminary_reports = preliminary_reports
        self.final_reports = final_reports
        self.current_view = None # Track which view is active ('preliminary' or 'final')

        self._setup_ui()
        # Show preliminary reports by default if available, otherwise final
        if self.preliminary_reports:
             self._switch_view("preliminary")
        elif self.final_reports:
             self._switch_view("final")
        else:
             # Handle case with no reports (though the caller might prevent this)
             pass

        # Handle closing when clicking outside
        self.setFocusPolicy(Qt.StrongFocus)
        self.installEventFilter(self)
        self.setMinimumWidth(450) # Set a reasonable minimum width


    def eventFilter(self, source, event):
         if event.type() == QEvent.WindowDeactivate or \
           (event.type() == QEvent.MouseButtonPress and not self.rect().contains(event.pos())):
             self.close()
             return True
         return super().eventFilter(source, event)

    def _setup_ui(self):
        self.setStyleSheet("""
            QWidget#popupWidget { /* Name the main widget for specific styling */
                background-color: #FFFFFF;
                border: 1px solid #D1D5DB;
                border-radius: 8px;
            }
            QPushButton#toggleButton {
                font-size: 13px;
                font-weight: 500;
                color: #4B5563; /* Default text color */
                background-color: #F3F4F6; /* Default background */
                border: 1px solid #D1D5DB;
                padding: 6px 15px;
                border-radius: 6px;
                min-height: 28px;
            }
            QPushButton#toggleButton:checked {
                color: #FFFFFF; /* White text when checked */
                background-color: #A855F7; /* Purple background */
                border-color: #A855F7;
            }
            QPushButton#toggleButton:!checked:hover {
                 background-color: #E5E7EB; /* Light hover for non-checked */
                 border-color: #9CA3AF;
            }
            QTableWidget {
                border: none; /* Remove table border */
                border-top: 1px solid #E5E7EB; /* Separator line */
                gridline-color: #E5E7EB;
                font-size: 12px;
            }
            QHeaderView::section {
                background-color: #F9FAFB;
                padding: 5px;
                border: none;
                border-bottom: 1px solid #E5E7EB;
                font-weight: 500;
                color: #374151;
            }
            QTableWidget::item {
                padding: 6px 8px; /* Adjust padding */
                color: #374151;
            }
            QTableWidget::item:selected {
                background-color: #EDE9FE;
                color: #5B21B6;
            }
        """)
        self.setObjectName("popupWidget") # Set object name for stylesheet

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10) # Margins for the overall popup
        layout.setSpacing(8) # Spacing between elements

        # --- Toggle Buttons ---
        toggle_layout = QHBoxLayout()
        toggle_layout.setSpacing(5) # Spacing between buttons

        self.prelim_button = QPushButton("Preliminary")
        self.prelim_button.setObjectName("toggleButton")
        self.prelim_button.setCheckable(True)
        self.prelim_button.setEnabled(bool(self.preliminary_reports)) # Disable if no reports
        self.prelim_button.clicked.connect(lambda: self._switch_view("preliminary"))

        self.final_button = QPushButton("Full")
        self.final_button.setObjectName("toggleButton")
        self.final_button.setCheckable(True)
        self.final_button.setEnabled(bool(self.final_reports)) # Disable if no reports
        self.final_button.clicked.connect(lambda: self._switch_view("final"))

        toggle_layout.addWidget(self.prelim_button)
        toggle_layout.addWidget(self.final_button)
        toggle_layout.addStretch() # Push buttons left

        layout.addLayout(toggle_layout)

        # --- Single Table ---
        self.report_table = self._create_table()
        layout.addWidget(self.report_table)

    def _create_table(self) -> QTableWidget:
        table = QTableWidget()
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["Question #", "Date Answered", "Level"])
        table.verticalHeader().setVisible(False)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.setShowGrid(True) # Show grid lines for clarity
        table.setWordWrap(False) # Prevent word wrap initially
        # Enable horizontal scrollbar only when needed
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        header = table.horizontalHeader()
        # Resize Question# based on content, others fixed or stretch
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents) # Date usually fits
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch) # Level can stretch

        table.itemDoubleClicked.connect(self._on_item_selected)
        return table

    def _switch_view(self, view_type: str):
        """Clears and populates the table based on the selected view type."""
        if view_type == self.current_view: # Prevent reloading same view
            # Ensure the correct button is checked if clicked again somehow
            if view_type == "preliminary":
                self.prelim_button.setChecked(True)
            elif view_type == "final":
                self.final_button.setChecked(True)
            return

        self.current_view = view_type
        self.report_table.setRowCount(0) # Clear existing rows

        if view_type == "preliminary":
            self.final_button.setChecked(False) # Uncheck other button
            self.prelim_button.setChecked(True) # Check this button
            self._populate_specific_table(self.report_table, self.preliminary_reports)
        elif view_type == "final":
            self.prelim_button.setChecked(False) # Uncheck other button
            self.final_button.setChecked(True) # Check this button
            self._populate_specific_table(self.report_table, self.final_reports)

        # Adjust layout after populating
        self._adjust_popup_size()


    def _populate_specific_table(self, table: QTableWidget, reports: List[Dict]):
        table.setRowCount(len(reports))
        for row_idx, report_data in enumerate(reports):
            question_details = report_data.get("question", {})
            history_item = report_data.get("history", {})

            q_num = question_details.get('question_number_str', '?')
            q_level_key = question_details.get('level', '?')
            level_display = self._get_level_display_name(q_level_key)

            try:
                ts_str = history_item.get('timestamp')
                timestamp_dt = datetime.fromisoformat(ts_str) if ts_str else None
                formatted_date = timestamp_dt.strftime('%a/%d/%b/%Y %H:%M') if timestamp_dt else "No Date"
            except (ValueError, TypeError) as e:
                 logger.warning(f"Error formatting date in popup for history_id {history_item.get('history_id')}: {e}")
                 formatted_date = "Invalid Date"

            q_num_item = QTableWidgetItem(q_num)
            date_item = QTableWidgetItem(formatted_date)
            level_item = QTableWidgetItem(level_display)

            # Add full text as tooltip for Question # column
            q_num_item.setToolTip(q_num)

            history_id = history_item.get('history_id')
            if history_id is not None:
                q_num_item.setData(Qt.ItemDataRole.UserRole, history_id)

            table.setItem(row_idx, 0, q_num_item)
            table.setItem(row_idx, 1, date_item)
            table.setItem(row_idx, 2, level_item)

        # Optional: Resize rows after populating if desired, but might slow down for many items
        # table.resizeRowsToContents()
        table.resizeColumnsToContents() # Resize columns based on new content

    def _adjust_popup_size(self):
        """Adjust popup height based on table content."""
        # Simple height adjustment - might need fine-tuning
        header_height = self.report_table.horizontalHeader().height()
        rows_height = sum(self.report_table.rowHeight(i) for i in range(self.report_table.rowCount()))
        # Add some padding/margins
        target_table_height = header_height + rows_height + 10

        # Account for toggle button height and layout margins/spacing
        toggle_height = self.prelim_button.sizeHint().height()
        layout_margins = self.layout().contentsMargins()
        layout_spacing = self.layout().spacing()
        total_height = toggle_height + layout_spacing + target_table_height + layout_margins.top() + layout_margins.bottom()

        max_height = 500 # Set a maximum height
        self.setFixedHeight(min(total_height, max_height))
        # Width is handled by minimumWidth and ResizeToContents


    def _on_item_selected(self, item: QTableWidgetItem):
         # Get history_id stored in the first column item
         history_id_item = item.tableWidget().item(item.row(), 0)
         history_id = history_id_item.data(Qt.ItemDataRole.UserRole)
         if history_id is not None:
             logger.info(f"Report selected: history_id {history_id}")
             self.report_selected.emit(history_id)
             self.close()
         else:
              logger.warning("Could not retrieve history_id from selected table item.")

    def _get_level_display_name(self, level_key):
        """Convert level key to display name"""
        display_names = {
            'grade_7': 'Grade 7',
            'o_level': 'O Level',
            'a_level': 'A Level'
        }
        return display_names.get(level_key, str(level_key).replace('_', ' ').title())

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
        view_performance.setStyleSheet("border: none;")
        view_performance.clicked.connect(self._show_performance_dropdown)
        
        # Take Test Question button
        take_test_btn = QPushButton("Take Test Question")
        take_test_btn.setObjectName("takeTestButton")
        take_test_btn.setCursor(Qt.PointingHandCursor)
        take_test_btn.clicked.connect(self._show_test_level_dropdown)
        
        # Add buttons to bottom section
        bottom_section.addWidget(view_performance, alignment=Qt.AlignLeft)
        bottom_section.addStretch()
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

    def _show_performance_dropdown(self):
        """
        Fetches performance history and displays it in a custom popup table widget,
        with toggles for preliminary and final reports.
        """
        logger.debug(f"--- Showing performance popup for {self.subject_name} ---")

        button = self.findChild(QPushButton, "viewPerformance")
        if not button:
            logger.error("Could not find 'viewPerformance' button to show popup.")
            return

        # 1. Get User ID
        user = UserOperations.get_current_user()
        if not user:
            logger.error("Cannot fetch performance history: No current user found.")
            return
        user_id = user.get('id')
        if not user_id:
             logger.error("Could not determine user ID.")
             return
        logger.debug(f"User ID: {user_id}")

        # 2. Fetch Combined History + Basic Question Details
        # get_performance_history now returns dicts with necessary info from the join
        try:
            basic_history_list = UserOperations.get_performance_history(user_id)
            logger.info(f"Fetched {len(basic_history_list)} history entries for user {user_id}.")
        except Exception as e:
            logger.error(f"Error fetching performance history: {e}", exc_info=True)
            basic_history_list = []

        # 3. Filter and Process Data for Popup
        preliminary_reports_data = []
        final_reports_data = []
        enabled_level_keys = {key for key, enabled in self.levels.items() if enabled}
        logger.debug(f"Card Subject: '{self.subject_name}', Enabled Level Keys on card: {enabled_level_keys}")

        for history_item in basic_history_list:
            history_id = history_item.get('history_id', 'N/A')
            
            # Get subject and level directly from the history_item 
            # (fetched via the JOIN in get_performance_history)
            q_subject = history_item.get("subject") 
            q_level = history_item.get("level") # Key like 'o_level'

            if not q_subject or not q_level:
                 logger.warning(f"Skipping history_id {history_id} due to missing subject ('{q_subject}') or level ('{q_level}') from get_performance_history result.")
                 continue

            # Perform checks (Case-insensitive subject match, key-based level match)
            subject_match = (q_subject.strip().lower() == self.subject_name.strip().lower())
            level_match = (q_level in enabled_level_keys)
            
            logger.debug(f"Processing history_id: {history_id}, Subject='{q_subject}', Level='{q_level}' -> Subject Match: {subject_match}, Level Match: {level_match}")

            if not (subject_match and level_match):
                # logger.debug(f"  Skipping history_id {history_id} due to subject/level mismatch.") # Optional verbose log
                continue

            # Use is_final directly from history_item (derived from cloud_report_received)
            is_final = history_item.get('is_final', False) 
            
            # Create combined data for the popup using only history_item fields
            # The 'question' sub-dict now uses data already present in history_item
            combined_data = {
                "history": { # Keep history separate if PerformanceReportPopup expects it
                     "history_id": history_id,
                     "timestamp": history_item.get("timestamp"),
                     # Add other relevant history fields if needed by the popup
                },
                "question": { # Populate 'question' info from history_item
                    "unique_question_key": history_item.get("cached_question_id"),
                    "subject": q_subject,
                    "level": q_level,
                    "paper_year": history_item.get("paper_year"),
                    "question_number_str": history_item.get("paper_number"), # Using key from get_performance_history
                }
            }
            
            logger.debug(f"  history_id: {history_id}, is_final: {is_final}")

            if is_final:
                final_reports_data.append(combined_data)
                logger.debug(f"  Added history_id {history_id} to final_reports_data.")
            else:
                preliminary_reports_data.append(combined_data)
                logger.debug(f"  Added history_id {history_id} to preliminary_reports_data.")

        logger.debug(f"Total preliminary reports for popup: {len(preliminary_reports_data)}")
        logger.debug(f"Total final reports for popup: {len(final_reports_data)}")

        # 5. Create and Show Popup (No changes needed here)
        if not preliminary_reports_data and not final_reports_data:
            logger.info("No matching performance reports found for selected levels.")
            # You could show a brief message via QToolTip or QMessageBox here
            # Example: QtWidgets.QToolTip.showText(button.mapToGlobal(QtCore.QPoint(0, button.height())), "No reports found for selected levels.", button)
            return

        # Sort reports by date (newest first)
        def sort_key(report):
            ts_str = report.get("history", {}).get("timestamp")
            try:
                return datetime.fromisoformat(ts_str) if ts_str else datetime.min
            except ValueError:
                return datetime.min
        preliminary_reports_data.sort(key=sort_key, reverse=True)
        final_reports_data.sort(key=sort_key, reverse=True)

        # --- Instantiate the Popup ---
        # Store as instance variable to prevent garbage collection if needed
        self.performance_popup = PerformanceReportPopup(preliminary_reports_data, final_reports_data, self) # Pass self as parent

        # Connect signal (Example)
        # self.performance_popup.report_selected.connect(self.parent().parent().show_report_view) # Adjust signal connection target as needed

        # Position and show
        button_pos = button.mapToGlobal(QPoint(0, button.height())) # Use QPoint directly
        self.performance_popup.move(button_pos)
        self.performance_popup.show()
        self.performance_popup.setFocus()
