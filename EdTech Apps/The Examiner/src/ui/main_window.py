import logging # Add logging import
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout,
                              QScrollArea, QStackedWidget) # Add QStackedWidget
from PySide6.QtCore import Slot # Add Slot
from src.data.database.operations import UserOperations
from .components.profile.profile_header import ProfileHeader
from .components.profile.achievements.achievement_widget import AchievementWidget
from .components.profile.profile_info_widget import ProfileInfoWidget
from .views.question_view import QuestionView # Import the QuestionView
from .views.report_view import ReportView # ADDED: Import ReportView
from src.core import services

logger = logging.getLogger(__name__) # Setup logger for this module


class MainWindow(QMainWindow):
    def __init__(self, user=None):
        super().__init__()
        self.setWindowTitle("The Examiner") # Changed title
        self.setFixedSize(1200, 800) # Kept fixed size for now

        # --- Use provided user or get current user ---
        # It's better to do this once, rather than potentially multiple times
        self.user = user or UserOperations.get_current_user()
        if not self.user:
             # Handle case where user is somehow still None (e.g., show error and exit)
             logger.error("MainWindow initialized without a valid user!")
             # You might want to close the window or show an error message here
             return # Avoid proceeding without a user

        # --- Setup Stacked Widget for Navigation ---
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget) # Set stack as the main widget

        # --- Create Profile Page (Page 0) ---
        # This combines the previous central widget's content
        self.profile_page_widget = QWidget() # Use a simple QWidget as the page container
        profile_page_layout = QVBoxLayout(self.profile_page_widget)
        profile_page_layout.setContentsMargins(0, 0, 0, 0) # No margins for the page itself
        profile_page_layout.setSpacing(0)

        # Create scroll area for the profile content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea { border: none; background-color: white; }
            QWidget { background-color: white; } /* Ensure contained widgets have white bg */
        """)

        # Create main container widget for content *inside* scroll area
        profile_content_container = QWidget()
        profile_content_layout = QVBoxLayout(profile_content_container)
        profile_content_layout.setContentsMargins(20, 20, 20, 20) # Original margins
        profile_content_layout.setSpacing(15) # Add some spacing

        # Add profile header
        profile_header = ProfileHeader(self.user)
        profile_content_layout.addWidget(profile_header)

        # Add achievement widget
        achievement_widget = AchievementWidget(self.user)
        profile_content_layout.addWidget(achievement_widget)

        # Add profile info widget (which contains SubjectSelector -> SubjectCards)
        # Store it as an attribute to access its signal
        self.profile_info_widget = ProfileInfoWidget(self.user)
        profile_content_layout.addWidget(self.profile_info_widget)
        self.profile_info_widget.test_requested.connect(self.show_question_view)
        self.profile_info_widget.report_view_requested.connect(self.show_report_view)

        # Add stretch to push everything to the top within the content container
        profile_content_layout.addStretch()

        # Set the container as the scroll area widget
        scroll_area.setWidget(profile_content_container)

        # Add the scroll area to the profile page layout
        profile_page_layout.addWidget(scroll_area)

        # Add the complete profile page to the stacked widget
        self.stacked_widget.addWidget(self.profile_page_widget) # Index 0

        # --- Store Question View instance ---
        self.question_view_instance = None # To keep track of the current question view

        # --- ADDED: Setup Report View ---
        self.report_view_instance = ReportView(self) # Create instance
        self.stacked_widget.addWidget(self.report_view_instance) # Add to stack
        self.report_view_instance.back_requested.connect(self.show_profile_view) # Connect back signal

        # --- Connect Signals ---
        # Connect the signal bubbled up from ProfileInfoWidget
        # self.profile_info_widget.test_requested.connect(self.show_question_view) # Moved up for clarity

    @Slot(str, str)
    def show_question_view(self, subject_name, level_key):
        """Creates/shows the question view for the selected subject/level."""
        logger.info(f"Switching to Question View for {subject_name}/{level_key}")

        # --- ADD LOGGING HERE ---
        try:
            logger.info("--- Checking services status before creating QuestionView in show_question_view ---")
            logger.info(f"ID of 'services' module in main_window.py: {id(services)}")
            logger.info(f"Value of services.user_history_manager in main_window.py: {getattr(services, 'user_history_manager', 'AttributeNotFound')}")
        except Exception as log_err:
             logger.error(f"Error logging services status in main_window.py: {log_err}")
        # ------------------------

        # Remove previous instance if it exists to avoid duplicates
        if self.question_view_instance:
             logger.debug("Removing previous QuestionView instance.")
             self.stacked_widget.removeWidget(self.question_view_instance)
             self.question_view_instance.deleteLater() # Ensure proper Qt cleanup

        # Create the new QuestionView
        logger.info("Creating new QuestionView instance...") # Add log
        self.question_view_instance = QuestionView(subject_name, level_key)
        # Connect its 'back' signal to our slot to switch back
        self.question_view_instance.back_requested.connect(self.show_profile_view)

        # Add the new view to the stack and make it visible
        self.stacked_widget.addWidget(self.question_view_instance)
        self.stacked_widget.setCurrentWidget(self.question_view_instance)

    @Slot()
    def show_profile_view(self):
        """Switches back to the profile view."""
        logger.info("Switching back to Profile View")
        # Set the current widget back to the main profile page
        self.stacked_widget.setCurrentWidget(self.profile_page_widget)

        # Optional: Clean up the question view instance after switching back
        if self.question_view_instance:
             logger.debug("Removing QuestionView instance after returning to profile.")
             self.stacked_widget.removeWidget(self.question_view_instance)
             self.question_view_instance.deleteLater()
             self.question_view_instance = None # Clear the reference
        

    @Slot(int)
    def show_report_view(self, history_id: int):
        """Switches to the ReportView and loads the specified report."""
        logger.info(f"Switching to Report View for history_id {history_id}")
        if self.report_view_instance:
            self.report_view_instance.load_report(history_id)
            self.stacked_widget.setCurrentWidget(self.report_view_instance)
        else:
            logger.error("ReportView instance not available.")
