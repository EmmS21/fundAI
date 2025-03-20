from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                              QPushButton, QLabel, QCheckBox, QFrame,
                              QMenu, QWidgetAction, QToolButton,
                              QSpacerItem, QSizePolicy, QProgressBar)
from PySide6.QtCore import Qt, Signal, QObject, QEvent, QTimer
from PySide6.QtGui import QCursor, QIcon, QColor, QAction
from src.data.database.operations import UserOperations
from src.utils.constants import PRIMARY_COLOR
from src.data.cache.cache_manager import CacheStatus, CacheProgressStatus, CacheManager
import logging

logger = logging.getLogger(__name__)

class SubjectCard(QWidget):
    deleted = Signal(str)
    levels_changed = Signal(str, dict)  # Emits subject name and level changes
    
    def __init__(self, subject_name, levels=None, parent=None):
        super().__init__(parent)
        self.subject_name = subject_name
        print(f"SubjectCard init - Subject: {subject_name}, Initial levels: {levels}")
        self.levels = levels or {'grade_7': False, 'o_level': False, 'a_level': False}
        self.cache_manager = CacheManager()
        self.level_cache_status = {}
        self.level_status_labels = {}
        self.level_progress_bars = {}
        
        # Timer for updating cache status
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self._update_cache_status)
        self.status_timer.start(10000)  # Update every 10 seconds
        
        self._setup_ui()
        self._update_cache_status()  # Initial update
    
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
        # Create popup menu
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: white;
                border: 1px solid #E5E7EB;
                border-radius: 8px;
                padding: 5px;
            }
        """)
        
        # Get available levels
        available_levels = [key for key, enabled in self.levels.items() if enabled]
        
        # Update cache status before showing menu
        self._update_cache_status()
        
        for level_key in available_levels:
            level_name = self._get_level_display_name(level_key)
            
            # Create level container widget
            level_item = QWidget()
            level_item.setObjectName(f"level_{level_key}")
            level_item.setFixedWidth(200)
            level_item.setStyleSheet("""
                QWidget {
                    background-color: transparent;
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
            
            # Cache status indicator
            status_label = QLabel()
            status_label.setFixedSize(16, 16)
            status_label.setStyleSheet("""
                QLabel {
                    border-radius: 8px;
                    background-color: #D1D5DB;  /* Default gray */
                }
            """)
            
            # Store reference to status label
            self.level_status_labels[level_key] = status_label
            
            # Progress bar for download/sync status - initially hidden
            progress_bar = QProgressBar()
            progress_bar.setRange(0, 100)
            progress_bar.setValue(0)
            progress_bar.setFixedHeight(6)
            progress_bar.setTextVisible(False)
            progress_bar.setStyleSheet("""
                QProgressBar {
                    background-color: #E5E7EB;
                    border-radius: 3px;
                    border: none;
                }
                QProgressBar::chunk {
                    background-color: #A855F7;
                    border-radius: 3px;
                }
            """)
            progress_bar.setVisible(False)
            
            # Store reference to progress bar
            self.level_progress_bars[level_key] = progress_bar
            
            # Add widgets to layout
            item_layout.addWidget(status_label)
            item_layout.addWidget(name_label)
            item_layout.addStretch()
            item_layout.addWidget(play_button)
            
            # Create vertical layout to add progress bar below
            v_layout = QVBoxLayout()
            v_layout.setContentsMargins(0, 0, 0, 0)
            v_layout.setSpacing(2)
            v_layout.addLayout(item_layout)
            v_layout.addWidget(progress_bar)
            
            level_item.setLayout(v_layout)
            
            # Create action and add widget
            action = QAction(self)
            menu.addAction(action)
            
            # Create hover event filter to show/hide play button
            hover_filter = HoverEventFilter(level_item, play_button)
            level_item.installEventFilter(hover_filter)
            
            # Connect play button to start test
            play_button.clicked.connect(lambda checked=False, lkey=level_key: self._start_test_for_level(lkey))
            
            # Set widget for action
            menu.setActionWidget(action, level_item)
            
        # Show menu
        menu.popup(QCursor.pos())
    
    def _start_test_for_level(self, level_key):
        """Start the test for the specified level"""
        print(f"Starting test for subject: {self.subject_name}, level: {level_key}")
        # Here you would implement the actual test starting logic
        # For now, we just print the selection

    # Add method to update cache status
    def _update_cache_status(self):
        """Update the cache status for each level"""
        try:
            for level_key, enabled in self.levels.items():
                if not enabled or level_key not in self.level_status_labels:
                    continue
                    
                # Get cache status from CacheManager
                cache_data = self.cache_manager.get_subject_cache_status(self.subject_name, level_key)
                status = cache_data.get('status', CacheStatus.INVALID)
                progress_status = cache_data.get('progress_status', CacheProgressStatus.IDLE)
                completion = cache_data.get('completion_percentage', 0)
                
                # Store status for later use
                self.level_cache_status[level_key] = cache_data
                
                # Update status indicator color
                status_label = self.level_status_labels[level_key]
                progress_bar = self.level_progress_bars[level_key]
                
                # Set color based on status
                if status == CacheStatus.FRESH:
                    status_label.setStyleSheet("QLabel { background-color: #10B981; border-radius: 8px; }")  # Green
                    status_label.setToolTip("Cache is fresh")
                elif status == CacheStatus.STALE:
                    status_label.setStyleSheet("QLabel { background-color: #F59E0B; border-radius: 8px; }")  # Yellow/amber
                    status_label.setToolTip("Cache is stale")
                elif status == CacheStatus.EXPIRED:
                    status_label.setStyleSheet("QLabel { background-color: #EF4444; border-radius: 8px; }")  # Red
                    status_label.setToolTip("Cache has expired")
                else:
                    status_label.setStyleSheet("QLabel { background-color: #D1D5DB; border-radius: 8px; }")  # Gray
                    status_label.setToolTip("No cached content")
                
                # Update progress bar if syncing or downloading
                if progress_status in [CacheProgressStatus.SYNCING, CacheProgressStatus.DOWNLOADING]:
                    progress_bar.setVisible(True)
                    progress_bar.setValue(int(completion))
                    
                    if progress_status == CacheProgressStatus.SYNCING:
                        progress_bar.setToolTip(f"Syncing: {completion:.1f}% complete")
                    else:
                        progress_bar.setToolTip(f"Downloading: {completion:.1f}% complete")
                else:
                    progress_bar.setVisible(False)
                    
        except Exception as e:
            logger.error(f"Error updating cache status: {e}")
