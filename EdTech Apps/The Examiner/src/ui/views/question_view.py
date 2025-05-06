import logging
logger = logging.getLogger(__name__)

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, QScrollArea, QSizePolicy, QDialog, QFrame, QMessageBox, QGroupBox)
from PySide6.QtGui import QPixmap, QImage, QFont, QGuiApplication
from PySide6.QtCore import Qt, Signal, QUrl, QThread, QStandardPaths, Slot
from src.data.cache.cache_manager import CacheManager
import os
import sys
import json
from src.core.ai.marker import run_ai_evaluation
from typing import Dict, Optional, Any
from src.core import services
from src.core.network.monitor import NetworkStatus
from src.core.ai.groq_client import GroqClient

# --- QSS Styles ---
# Define styles here for better organization
PAPER_STYLE = """
    QScrollArea#QuestionScrollArea {{
        border: 1px solid #E5E7EB; /* Subtle border like paper edge */
        background-color: #fdfaf2; /* Off-white paper color */
    }}
    QWidget#QuestionContainer {{
        background-color: #fdfaf2; /* Ensure container matches */
        padding: 15px; /* Add padding inside the paper */
    }}
    QLabel#QuestionTextLabel {{
        background-color: transparent; /* Make label background transparent */
        color: #111827; /* Darker text color */
        font-size: 15px; /* Adjust as needed */
        /* Removed padding here, handled by container */
    }}
"""

MARKS_BUTTON_STYLE = """
    QPushButton.MarksButton {{
        background-color: #DBEAFE; /* Light blue background */
        color: #1E40AF; /* Darker blue text */
        border: 1px solid #BFDBFE;
        border-radius: 12px; /* Rounded edges */
        padding: 3px 8px; /* Adjust padding */
        font-size: 11px; /* Smaller font for marks */
        font-weight: bold;
        min-width: 60px; /* Ensure minimum size */
        text-align: center;
    }}
    QPushButton.MarksButton:hover {{
        background-color: #93C5FD; /* Brighter blue on hover */
        border: 1px solid #60A5FA;
        /* Basic pulse effect idea (optional): slightly larger padding */
        /* padding: 4px 9px; */
    }}
"""

# --- Added: Style for Sub-Question GroupBox ---
SUB_QUESTION_STYLE = """
    QGroupBox.SubQuestionGroup {{
        border: 1px solid #D1D5DB; /* Light gray border */
        border-radius: 8px;
        margin-top: 10px; /* Space between sub-questions */
        padding-top: 15px; /* Space for the title */
        background-color: #F9FAFB; /* Very light gray background */
    }}
    QGroupBox.SubQuestionGroup::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 5px 0 5px;
        left: 10px; /* Position title from left edge */
        color: #374151; /* Darker gray title */
        font-weight: bold;
    }}
    /* Style for QTextEdit within the sub-question group */
    QGroupBox.SubQuestionGroup QTextEdit {{
        font-size: 14px;
        border: 1px solid #E5E7EB;
        border-radius: 4px;
        padding: 4px;
        background-color: white; /* White background for input */
        min-height: 60px; /* Minimum height */
    }}
"""

# --- ADDED/MODIFIED: Style for Feedback Area ---
FEEDBACK_STYLE = """
    QGroupBox#FeedbackGroup {{ /* Outer container */
        background-color: #374151; /* Darker gray background for the main AI Feedback area */
        border: 1px solid #4B5563;
        border-radius: 8px;
        margin-top: 15px; /* More space above */
        padding: 8px;
    }}
    QGroupBox#FeedbackGroup::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 5px 0 5px;
        margin-top: 5px;
        left: 10px;
        color: #F9FAFB; /* Light title on dark background */
        font-weight: bold;
    }}

    /* --- Styling for Preliminary Feedback Box --- */
    QGroupBox#PreliminaryFeedbackSubGroup {{
        background-color: #F3F4F6; /* Light Gray background */
        border: 1px solid #D1D5DB;
        border-radius: 6px;
        margin-top: 5px; /* Space below main title */
        padding-top: 5px; /* Reduced padding */
    }}
    QGroupBox#PreliminaryFeedbackSubGroup::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 5px 0 5px;
        left: 10px;
        color: #1F2937; /* Dark title on light background */
        font-weight: bold;
        /* font-size: 13px; Optional smaller title */
    }}
    QGroupBox#PreliminaryFeedbackSubGroup QPushButton {{ /* Style hide button inside */
        background-color: transparent; border: none; color: #9CA3AF; font-weight: bold; font-size: 14px; padding: 0px; margin: 0px; max-width: 20px; max-height: 20px;
    }}
     QGroupBox#PreliminaryFeedbackSubGroup QPushButton:hover {{ color: #374151; }}


    /* --- Styling for Finalized Report Box --- */
    QGroupBox#FinalizedReportSubGroup {{
        background-color: #ECFDF5; /* Very Light Green background */
        border: 1px solid #6EE7B7; /* Green border */
        border-radius: 6px;
        margin-top: 10px; /* Space between sections */
         padding-top: 5px; /* Reduced padding */
    }}
     QGroupBox#FinalizedReportSubGroup::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 5px 0 5px;
        left: 10px;
        color: #065F46; /* Dark Green title */
        font-weight: bold;
         /* font-size: 13px; */
    }}
     QGroupBox#FinalizedReportSubGroup QPushButton {{ /* Style hide button inside */
        background-color: transparent; border: none; color: #9CA3AF; font-weight: bold; font-size: 14px; padding: 0px; margin: 0px; max-width: 20px; max-height: 20px;
    }}
     QGroupBox#FinalizedReportSubGroup QPushButton:hover {{ color: #374151; }}

    /* Common styles for labels/text inside sub-groups */
    QGroupBox#PreliminaryFeedbackSubGroup QLabel, QGroupBox#FinalizedReportSubGroup QLabel {{
        background-color: transparent; /* Ensure labels inside have transparent background */
        color: #1F2937; 
    }}
     QGroupBox#PreliminaryFeedbackSubGroup QTextEdit, QGroupBox#FinalizedReportSubGroup QTextEdit {{
        font-size: 13px;
        border: 1px solid #D1D5DB; 
        border-radius: 4px;
        padding: 4px;
        background-color: white;
         margin-bottom: 5px;
    }}

    /* Style for the NEW "Show" buttons */
    QPushButton.ShowFeedbackButton {{
        font-size: 11px;
        padding: 3px 6px;
        color: #3B82F6; /* Blue text */
        background-color: transparent;
        border: 1px solid transparent; /* Optional: add border on hover */
        text-decoration: underline;
    }}
    QPushButton.ShowFeedbackButton:hover {{
        color: #1D4ED8; /* Darker blue */
        background-color: #EFF6FF; /* Very light blue background */
        border-color: #BFDBFE;
    }}

"""

# --- ADDED: Simple Waiting Dialog ---
class WaitingDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Processing")
        self.setModal(True) # Block interaction with parent window
        # Remove close button and help context button
        self.setWindowFlags(Qt.Dialog | Qt.CustomizeWindowHint | Qt.WindowTitleHint | Qt.WindowStaysOnTopHint)

        layout = QVBoxLayout(self)
        self.label = QLabel("Generating AI Feedback, please wait...")
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)
        self.setMinimumWidth(300)
        self.setLayout(layout)

# --- Worker Thread for AI Feedback ---
class AIFeedbackWorker(QThread):
    # Signal emits: results dictionary (or None), prompt string (or None)
    feedback_ready = Signal(object, object) # Change signature to emit two objects

    # --- MODIFY: Accept dictionary for user_answer ---
    def __init__(self, question_data: Dict, correct_answer_data: Dict, user_answer: Dict[str, str], marks: Optional[int]):
        super().__init__()
        self.question_data = question_data
        self.correct_answer_data = correct_answer_data
        self.user_answer = user_answer # Now expects a dict
        self.marks = marks

    def run(self):
        """Runs the AI evaluation function in a separate thread."""
        logger.info("AIFeedbackWorker started.")
        # --- Get BOTH results and prompt ---
        evaluation_results, generated_prompt = run_ai_evaluation( # Capture both return values
            self.question_data,
            self.correct_answer_data,
            self.user_answer,
            self.marks
        )
        # --- Emit BOTH results and prompt ---
        self.feedback_ready.emit(evaluation_results, generated_prompt)
        logger.info("AIFeedbackWorker finished.")

# --- (GroqFeedbackWorker Class - Needs Modification) ---
class GroqFeedbackWorker(QThread):
    feedback_ready = Signal(int, object)
    feedback_error = Signal(int, str)

    # Modify __init__ to accept prompt string
    def __init__(self, history_id: int, local_prompt: str): # Simplified - only needs prompt now
        super().__init__()
        self.history_id = history_id
        self.local_prompt = local_prompt
        # Removed other data args (question_data, etc.) as GroqClient now only needs prompt
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def run(self):
        """Runs the Groq evaluation using the provided prompt."""
        self.logger.info(f"GroqFeedbackWorker started for history_id: {self.history_id}")
        if not self.local_prompt:
            self.logger.error(f"GroqFeedbackWorker cannot run for history_id {self.history_id}: Prompt is missing.")
            self.feedback_error.emit(self.history_id, "Worker started without prompt")
            return

        try:
            groq_client = GroqClient()
            # Call the method that accepts the prompt
            cloud_report = groq_client.generate_report_from_prompt(self.local_prompt)

            if cloud_report and not cloud_report.get("error"):
                self.logger.info(f"Groq report generated successfully for history_id: {self.history_id}")
                self.feedback_ready.emit(self.history_id, cloud_report)
            else:
                error_msg = cloud_report.get('error', 'Unknown error from GroqClient') if cloud_report else "GroqClient returned None"
                self.logger.error(f"Groq report generation failed for history_id {self.history_id}: {error_msg}")
                self.feedback_error.emit(self.history_id, error_msg)

        except ValueError as key_error:
             self.logger.error(f"Failed to initialize GroqClient in worker: {key_error}")
             self.feedback_error.emit(self.history_id, f"API Key Error: {key_error}")
        except Exception as e:
            self.logger.error(f"Exception in GroqFeedbackWorker for history_id {self.history_id}: {e}", exc_info=True)
            self.feedback_error.emit(self.history_id, f"Worker Exception: {e}")
        self.logger.info(f"GroqFeedbackWorker finished for history_id: {self.history_id}")

class QuestionView(QWidget):
    """Widget to display a single question and handle user interaction."""

    # Signal to indicate user wants to go back to the profile/subject list
    back_requested = Signal()

    def __init__(self, subject_name: str, level_key: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.subject_name = subject_name
        self.level_key = level_key
        self.cache_manager = CacheManager()
        self.current_question_data = None # To store the loaded question details
        self.logger = logging.getLogger(__name__)
        self.feedback_worker = None
        self.waiting_dialog = None 
        self.sub_answer_fields: Dict[str, QTextEdit] = {}
        self.last_submitted_answers = None 
        self.last_used_prompt = None 
        self.groq_workers = {} 

        # --- ADDED: State flags for feedback generation ---
        self.preliminary_feedback_generated = False
        self.finalized_feedback_generated = False
        # --- END ADDED ---

        # ADD State flags - (These seem redundant now, consider removing if not used elsewhere)
        # self.preliminary_feedback_available = False
        # self.final_report_available = False

        self._setup_ui()
        self.load_random_question()

    def _setup_ui(self):
        """Set up the basic UI elements for the question view."""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)
        self.setStyleSheet(PAPER_STYLE + MARKS_BUTTON_STYLE + SUB_QUESTION_STYLE + FEEDBACK_STYLE) # Apply styles

        # --- Header ---
        header_layout = QHBoxLayout()
        self.title_label = QLabel(f"Question - {self.subject_name} ({self._get_level_display_name(self.level_key)})")
        self.title_label.setStyleSheet("font-size: 18px; font-weight: bold;")

        back_button = QPushButton("Back to Subjects")
        back_button.clicked.connect(self.back_requested.emit) # Emit signal on click

        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        header_layout.addWidget(back_button)
        self.main_layout.addLayout(header_layout)

        # --- Question Display Area (Scrollable) ---
        scroll_area = QScrollArea()
        scroll_area.setObjectName("QuestionScrollArea") # Set object name for styling
        scroll_area.setWidgetResizable(True)
        # scroll_area.setStyleSheet("QScrollArea { border: none; background-color: #FFFFFF; }") # Replaced by QSS

        # --- Container for all question content ---
        # Use a QFrame for better structure and potential borders/padding
        self.question_content_widget = QFrame()
        self.question_content_widget.setObjectName("QuestionContainer") # Set object name
        self.question_layout = QVBoxLayout(self.question_content_widget) # Layout *inside* the container
        self.question_layout.setContentsMargins(10, 10, 10, 10) # Padding within the container
        self.question_layout.setSpacing(10) # Spacing between question elements

        # --- Main Question Text Label ---
        self.question_text_label = QLabel("Loading question...")
        self.question_text_label.setObjectName("QuestionTextLabel") # Set object name
        self.question_text_label.setWordWrap(True)
        self.question_text_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        # self.question_text_label.setStyleSheet("font-size: 16px; padding: 10px; background-color: white; color: black;") # Replaced by QSS
        self.question_layout.addWidget(self.question_text_label)

        # --- Area for Sub-Questions (labels, inputs) and Diagrams ---
        self.sub_elements_layout = QVBoxLayout()
        self.sub_elements_layout.setSpacing(8)
        self.question_layout.addLayout(self.sub_elements_layout)


        self.question_layout.addStretch(1) # Push content to the top

        scroll_area.setWidget(self.question_content_widget) # Set the container as the scroll area's widget
        self.main_layout.addWidget(scroll_area, 1)

        # --- Main Feedback Container (Outer Shell) ---
        self.feedback_groupbox = QGroupBox("AI Feedback")
        self.feedback_groupbox.setObjectName("FeedbackGroup")
        self.feedback_groupbox.setAutoFillBackground(True) # Important for background color
        self.feedback_layout = QVBoxLayout(self.feedback_groupbox)
        self.feedback_layout.setSpacing(10)
        self.feedback_layout.setContentsMargins(10, 15, 10, 10) # L, T, R, B (Top adjusted for title)

        # --- Container 1: Preliminary Feedback ---
        self.preliminary_feedback_group = QGroupBox("Preliminary Feedback")
        self.preliminary_feedback_group.setObjectName("PreliminaryFeedbackSubGroup") # For styling
        prelim_layout = QVBoxLayout(self.preliminary_feedback_group)
        prelim_layout.setSpacing(5)
        prelim_layout.setContentsMargins(8, 25, 8, 8) # Adjusted Top margin for title/button

        prelim_hide_button = QPushButton("✕")
        prelim_hide_button.setFixedSize(18, 18)
        prelim_hide_button.setToolTip("Hide Preliminary Feedback")
        # Connect to NEW hide method
        prelim_hide_button.clicked.connect(self._hide_prelim_feedback) # MODIFIED
        prelim_hide_layout = QHBoxLayout()
        prelim_hide_layout.addStretch()
        prelim_hide_layout.addWidget(prelim_hide_button)
        # Add hide button layout *within* the prelim_layout
        prelim_layout.insertLayout(0, prelim_hide_layout) # Insert at top

        self.prelim_mark_label = QLabel("Mark Awarded: N/A")
        self.prelim_mark_label.setObjectName("FeedbackLabel")
        prelim_layout.addWidget(self.prelim_mark_label)

        self.prelim_details_label = QLabel("Feedback Details:")
        self.prelim_details_label.setObjectName("FeedbackLabel")
        self.prelim_details_label.setStyleSheet("font-weight: bold;")
        prelim_layout.addWidget(self.prelim_details_label)

        self.prelim_feedback_text = QTextEdit()
        self.prelim_feedback_text.setObjectName("FeedbackContent")
        self.prelim_feedback_text.setReadOnly(True)
        self.prelim_feedback_text.setMinimumHeight(100) # Example height
        prelim_layout.addWidget(self.prelim_feedback_text)

        self.feedback_layout.addWidget(self.preliminary_feedback_group)
        self.preliminary_feedback_group.hide() # Start hidden

        # --- Container 2: Finalized Report ---
        self.finalized_report_group = QGroupBox("Finalized Report")
        self.finalized_report_group.setObjectName("FinalizedReportSubGroup") # For styling
        self.finalized_report_group.setAutoFillBackground(True) # Important for background color
        final_layout = QVBoxLayout(self.finalized_report_group)
        final_layout.setSpacing(5)
        final_layout.setContentsMargins(8, 25, 8, 8) # Adjusted Top margin for title/button

        final_hide_button = QPushButton("✕")
        final_hide_button.setFixedSize(18, 18)
        final_hide_button.setToolTip("Hide Finalized Report")
        # Connect to NEW hide method
        final_hide_button.clicked.connect(self._hide_final_feedback) # MODIFIED
        final_hide_layout = QHBoxLayout()
        final_hide_layout.addStretch()
        final_hide_layout.addWidget(final_hide_button)
        # Add hide button layout *within* the final_layout
        final_layout.insertLayout(0, final_hide_layout) # Insert at top

        self.final_status_label = QLabel("Status: Pending Cloud Analysis...")
        self.final_status_label.setObjectName("FeedbackStatusLabel")
        self.final_status_label.setStyleSheet("font-style: italic; color: #555;")
        final_layout.addWidget(self.final_status_label)

        self.final_grade_label = QLabel("Grade: N/A")
        self.final_grade_label.setObjectName("FeedbackLabel")
        final_layout.addWidget(self.final_grade_label)

        self.final_feedback_text = QTextEdit()
        self.final_feedback_text.setObjectName("FeedbackContent") # Reuse style or make specific
        self.final_feedback_text.setReadOnly(True)
        self.final_feedback_text.setMinimumHeight(150) # Example height
        final_layout.addWidget(self.final_feedback_text)

        self.feedback_layout.addWidget(self.finalized_report_group)
        self.finalized_report_group.hide() # Start hidden

        # --- Add the main container to the main layout ---
        self.main_layout.addWidget(self.feedback_groupbox)
        self.feedback_groupbox.hide() # Start the whole area hidden

        # --- Action Buttons ---
        self.button_layout = QHBoxLayout()
        self.button_layout.setSpacing(10)

        # --- ADD "Show" Buttons ---
        self.show_prelim_button = QPushButton("Show Preliminary")
        self.show_prelim_button.setObjectName("ShowFeedbackButton") # For styling
        self.show_prelim_button.setProperty("class", "ShowFeedbackButton") # Apply class selector
        self.show_prelim_button.setToolTip("Show Preliminary Feedback")
        self.show_prelim_button.hide() # Start hidden
        self.show_prelim_button.clicked.connect(self._show_prelim_feedback) # Connect show action
        self.button_layout.addWidget(self.show_prelim_button) # Add to button row

        self.show_final_button = QPushButton("Show Finalized")
        self.show_final_button.setObjectName("ShowFeedbackButton") # For styling
        self.show_final_button.setProperty("class", "ShowFeedbackButton") # Apply class selector
        self.show_final_button.setToolTip("Show Finalized Report")
        self.show_final_button.hide() # Start hidden
        self.show_final_button.clicked.connect(self._show_final_feedback) # Connect show action
        self.button_layout.addWidget(self.show_final_button) # Add to button row
        # --- END ADD "Show" Buttons ---

        self.button_layout.addStretch() # Push Submit/Next to the right

        self.next_button = QPushButton("Next Question")
        # ... styling ...
        self.next_button.clicked.connect(self.load_random_question)
        self.next_button.setEnabled(False)

        self.submit_button = QPushButton("Submit Answer")
        # ... styling ...
        self.submit_button.clicked.connect(self._trigger_ai_feedback)

        self.button_layout.addWidget(self.submit_button)
        self.button_layout.addWidget(self.next_button)
        self.main_layout.addLayout(self.button_layout)

        self.setLayout(self.main_layout)

        # --- NEW: Area for Image Links ---
        # Use a QWidget as a container, allowing easy clearing
        self.image_links_container = QWidget() 
        self.image_links_layout = QVBoxLayout(self.image_links_container)
        self.image_links_layout.setContentsMargins(0, 5, 0, 5) # Add some spacing
        self.image_links_layout.setAlignment(Qt.AlignTop)
        # Optional: Add a label for this section
        self.image_section_label = QLabel("<b>Associated Figures:</b>") 
        self.image_section_label.hide() # Initially hidden

        self.main_layout.addWidget(self.image_section_label)
        self.main_layout.addWidget(self.image_links_container) 

    def load_random_question(self):
        """Fetches and displays a random question from the cache."""
        self.logger.info(f"Loading random question for {self.subject_name} - {self.level_key}")

        # --- Clear previous dynamic content ---
        # Clear previous answer fields dictionary
        self.sub_answer_fields.clear()

        # Clear widgets from the sub-elements layout
        while self.sub_elements_layout.count():
            item = self.sub_elements_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            else: # Clear layout items if necessary
                layout_item = item.layout()
                if layout_item is not None:
                    # Basic recursive clear (adapt if more complex layouts are nested)
                    while layout_item.count():
                        sub_item = layout_item.takeAt(0)
                        sub_widget = sub_item.widget()
                        if sub_widget: sub_widget.deleteLater()

        # --- Reset Feedback State ---
        self.preliminary_feedback_generated = False # Reset flag
        self.finalized_feedback_generated = False   # Reset flag

        self.preliminary_feedback_group.hide() # Hide section
        self.finalized_report_group.hide()   # Hide section
        self.feedback_groupbox.hide()        # Hide main container

        self.show_prelim_button.hide() # Explicitly hide button
        self.show_final_button.hide()  # Explicitly hide button
        # --- END Reset Feedback State ---

        self.submit_button.setEnabled(True)
        self.next_button.setEnabled(False)

        try:
            # CacheManager.get_random_question now includes 'correct_answer_data'
            question_data = self.cache_manager.get_random_question(self.subject_name, self.level_key)
            self.logger.debug(f"Raw question data received: {question_data}")

            if question_data:
                self.current_question_data = question_data

                # --- Build and Display Question Content ---

                # 1. Display Main Question Text (if any)
                main_text = question_data.get('text') or question_data.get('question_text', '')
                self.question_text_label.setText(main_text.strip())
                self.question_text_label.setVisible(bool(main_text.strip()))

                # 2. Process Sub-Questions (Create GroupBoxes with Inputs)
                sub_questions = question_data.get('sub_questions', [])
                has_sub_questions = bool(sub_questions and isinstance(sub_questions, list))

                if has_sub_questions:
                    for sq_index, sq in enumerate(sub_questions):
                        if isinstance(sq, dict):
                            marks_val = sq.get('marks')
                            # Ensure sub_number is a string and suitable as a dict key
                            sub_num_str = str(sq.get('sub_number', f'part_{sq_index+1}'))
                            sub_text_str = sq.get('text', '').strip()

                            # Create GroupBox for the sub-question
                            sub_q_group = QGroupBox()
                            sub_q_group.setProperty("class", "SubQuestionGroup") # For styling
                            # Use sub-question text and marks in the title
                            group_title = f"{sub_num_str}) {sub_text_str}"
                            if marks_val is not None:
                                group_title += f" [{marks_val} marks]"
                            sub_q_group.setTitle(group_title)

                            group_layout = QVBoxLayout(sub_q_group)
                            group_layout.setContentsMargins(10, 10, 10, 10) # Padding inside group
                            group_layout.setSpacing(5)

                            # Answer Input Field for this sub-question
                            sub_answer_input = QTextEdit()
                            sub_answer_input.setPlaceholderText(f"Enter answer for {sub_num_str}...")
                            # sub_answer_input.setFixedHeight(80) # Example fixed height
                            sub_answer_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding) # Allow vertical expansion

                            group_layout.addWidget(sub_answer_input) # Add input to group layout

                            # Store the input field, keyed by sub-question number
                            self.sub_answer_fields[sub_num_str] = sub_answer_input

                            # Add the group box to the main sub-elements layout
                            self.sub_elements_layout.addWidget(sub_q_group)

                        else:
                            self.logger.warning(f"Skipping invalid sub_question item (not a dict): {sq}")
                # --- If NO sub-questions, add a single input field ---
                else:
                    self.logger.info("No sub-questions found, adding a single main answer input.")
                    main_answer_input = QTextEdit()
                    main_answer_input.setPlaceholderText("Enter your answer here...")
                    main_answer_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding) # Allow vertical expansion
                    # Use a default key like "main" to store this field
                    self.sub_answer_fields["main"] = main_answer_input
                    self.sub_elements_layout.addWidget(main_answer_input)


                # 3. Add Diagram Descriptions (as simple labels for now)
                images = question_data.get('images', [])
                if images and any(img.get('description') for img in images if isinstance(img, dict)):
                     # Optional: Add a label like "Diagrams:"
                     # diag_header = QLabel("<b>Diagrams:</b>")
                     # self.sub_elements_layout.addWidget(diag_header) # Add to sub-elements layout

                     for img in images:
                         if isinstance(img, dict) and img.get('description'):
                             label_part = f"{img.get('label', '')}: " if img.get('label') else ""
                             desc_text = f"- {label_part}{img.get('description', '')}"
                             desc_label = QLabel(desc_text)
                             desc_label.setWordWrap(True)
                             desc_label.setStyleSheet("background-color: transparent;")
                             self.sub_elements_layout.addWidget(desc_label) 

                self.submit_button.setEnabled(True)
                self._clear_image_links()
                images = question_data.get('images', [])

                if images and isinstance(images, list):
                    valid_images_found = False
                    self.image_section_label.show()
                    self.logger.debug(f"Processing {len(images)} image entries for question.")

                    # --- Get Project Root (assuming 'src' is directly under it) ---
                    # This assumes the script is running from somewhere within the project structure
                    # A more robust method might be needed if deployment structure changes significantly
                    try:
                         # Go up from current file until 'src' is found, then one more level up
                         current_dir = os.path.dirname(os.path.abspath(__file__)) # /path/to/src/ui/views
                         src_dir = current_dir
                         while os.path.basename(src_dir) != 'src' and src_dir != os.path.dirname(src_dir):
                              src_dir = os.path.dirname(src_dir)
                         if os.path.basename(src_dir) == 'src':
                              project_root = os.path.dirname(src_dir)
                              self.logger.info(f"Determined project root: {project_root}")
                         else:
                              # Fallback: Use current working directory if src isn't found above
                              project_root = os.getcwd()
                              self.logger.warning(f"Could not reliably determine project root based on 'src' dir. Falling back to CWD: {project_root}")
                    except Exception as path_e:
                         project_root = os.getcwd()
                         self.logger.error(f"Error determining project root, falling back to CWD {project_root}: {path_e}")
                    # -----------------------------------------------------------------


                    for i, img_data in enumerate(images):
                        if not isinstance(img_data, dict):
                            self.logger.warning(f"Skipping invalid image entry #{i} (not a dict): {img_data}")
                            continue

                        label = img_data.get('label')
                        local_path = img_data.get('local_path') # Path like 'src/data/cache/assets/...'
                        description = img_data.get('description', '')

                        self.logger.debug(f"Image #{i}: Label='{label}', LocalPath='{local_path}', Type={type(local_path)}")

                        path_exists = False
                        abs_path = None
                        if local_path and isinstance(local_path, str):
                            try:
                                 # --- MODIFIED: Construct absolute path relative to determined project root ---
                                 abs_path = os.path.join(project_root, local_path)
                                 # Normalize the path (handles slashes, .., etc.)
                                 abs_path = os.path.normpath(abs_path)
                                 # -------------------------------------------------------------------------
                                 self.logger.debug(f"Image #{i}: Constructed absolute path: '{abs_path}'")
                                 path_exists = os.path.exists(abs_path)
                                 self.logger.debug(f"Image #{i}: Checking existence of constructed path -> Exists: {path_exists}")
                            except Exception as e:
                                 self.logger.error(f"Image #{i}: Error constructing/checking path from '{local_path}': {e}")
                        else:
                             self.logger.warning(f"Image #{i}: Invalid local_path provided: {local_path}")


                        # Check conditions for creating the link (using abs_path for the check)
                        if label and local_path and isinstance(local_path, str) and abs_path and path_exists: # Check abs_path exists
                            self.logger.info(f"Image #{i}: Conditions met. Creating link for '{label}'.")
                            # --- Use abs_path for the popup function ---
                            self.logger.info(f"Image #{i}: Using absolute path '{abs_path}' for link href and lambda.")

                            # Create the clickable label (href content doesn't really matter as we pass path to lambda)
                            link_label = QLabel(f"<a href='{abs_path}'>{label}</a>") # Use abs_path in href
                            link_label.setToolTip(description or label)
                            link_label.linkActivated.connect(
                                lambda path=abs_path, desc=description, lbl=label: self._show_image_popup(path, desc, lbl)
                            )
                            # -----------------------------------------
                            self.image_links_layout.addWidget(link_label)
                            valid_images_found = True
                        else:
                            # Log why the condition failed
                            self.logger.warning(f"Image #{i}: Skipping link creation for Label='{label}'. Reason: label={bool(label)}, local_path={bool(local_path)}, is_str={isinstance(local_path, str)}, abs_path_valid={bool(abs_path)}, path_exists={path_exists}.")
                            if label:
                                 missing_label = QLabel(f"{label} (Image not found)")
                                 missing_label.setStyleSheet("color: gray;")
                                 self.image_links_layout.addWidget(missing_label)

                    if not valid_images_found:
                         self.image_section_label.hide()
                else:
                    self.image_section_label.hide() 
                    # ... (optional logging if images is not None but not a list) ...

            else:
                error_msg = f"No cached questions found for {self.subject_name} - {self._get_level_display_name(self.level_key)}."
                logger.warning(error_msg)
                self.question_text_label.setText(error_msg)
                self.question_text_label.setVisible(True)
                self.submit_button.setEnabled(False)
                self._clear_image_links() # Clear images if no question loaded

        except Exception as e:
            logger.error(f"Error loading question: {e}", exc_info=True)
            self.question_text_label.setText(f"Error loading question: {str(e)}")
            self.question_text_label.setVisible(True)
            self.submit_button.setEnabled(False)
            self._clear_image_links()
            self._hide_prelim_feedback()
            self._hide_final_feedback()
            self.feedback_groupbox.hide()

    # Placeholder - adapt key->name mapping as needed
    def _get_level_display_name(self, level_key):
        """Convert level key to display name"""
        display_names = {
            'grade_7': 'Grade 7',
            'o_level': 'O Level',
            'a_level': 'A Level'
        }
        return display_names.get(level_key, level_key.replace('_', ' ').title())

    # --- Updated _trigger_ai_feedback ---
    def _trigger_ai_feedback(self):
        """Starts the AI feedback process, collecting answers from sub-question fields."""
        if self.feedback_worker and self.feedback_worker.isRunning():
            self.logger.warning("Feedback process already running.")
            return

        if not self.current_question_data:
            self.logger.error("Cannot trigger AI feedback: No current question data loaded.")
            QMessageBox.warning(self, "Error", "No question is currently loaded.")
            return

        # --- Get User Answers from Sub-Fields ---
        user_answers_dict: Dict[str, str] = {}
        missing_answers = []
        if not self.sub_answer_fields:
             self.logger.error("Cannot submit: No answer fields found!")
             QMessageBox.critical(self, "Internal Error", "Could not find answer input fields.")
             return

        for sub_num, text_edit in self.sub_answer_fields.items():
            answer_text = text_edit.toPlainText().strip()
            user_answers_dict[sub_num] = answer_text
            # Check if this field is empty
            if not answer_text: 
                # Try to get a more descriptive label if it's a sub-question group
                parent_group = text_edit.parentWidget()
                while parent_group and not isinstance(parent_group, QGroupBox):
                     parent_group = parent_group.parentWidget()
                
                display_num = sub_num # Default to the key
                if isinstance(parent_group, QGroupBox) and parent_group.property("class") == "SubQuestionGroup":
                     # Extract the number part from the title like "a) Text [marks]"
                     title = parent_group.title()
                     if title and ')' in title:
                          display_num = title.split(')', 1)[0].strip() 

                missing_answers.append(display_num) 

        if missing_answers:
            missing_str = ", ".join(sorted(missing_answers)) 
            QMessageBox.warning(self, 
                                "Input Needed", 
                                f"Please provide an answer for all parts before submitting.\n\nMissing answers for: {missing_str}")
            return

        self.last_submitted_answers = user_answers_dict

        # --- Get Question Data (unchanged) ---
        question_data_for_ai = self.current_question_data

        # --- Get Correct Answer Data (unchanged) ---
        correct_answer_data = self.current_question_data.get('correct_answer_data')
        if correct_answer_data is None:
            self.logger.error("Cannot trigger AI feedback: Correct answer data is missing from loaded question data.")
            # Decide how to handle this - show error? Proceed without answer?
            # For now, let's show an error and stop.
            QMessageBox.critical(self, "Internal Error", "Could not find the correct answer data for this question. Cannot proceed with evaluation.")
            return
        # Optionally log the structure if debugging
        # self.logger.debug(f"Correct answer data: {correct_answer_data}") # Optional Debug

        # --- Get Marks (unchanged) ---
        marks = self.current_question_data.get('marks')
        if marks is None:
            self.logger.warning("Total marks not found in question data. AI evaluation might be affected.")
            # Decide if marks are mandatory. Setting to 0 or None if missing?
            marks = 0 # Example: Default to 0 if missing

        # --- Show Waiting Dialog & Disable UI ---
        self.submit_button.setEnabled(False)
        self.submit_button.setText("Processing...")
        # Disable all sub-answer fields
        for text_edit in self.sub_answer_fields.values():
            text_edit.setReadOnly(True)
        self.next_button.setEnabled(False)

        # Create and show the dialog
        self.waiting_dialog = WaitingDialog(self)
        self.waiting_dialog.show()
        QGuiApplication.processEvents() # Ensure dialog displays immediately

        # --- Start Worker Thread (Pass the answers dict) ---
        self.logger.info("Starting AIFeedbackWorker thread with structured answers...")
        self.feedback_worker = AIFeedbackWorker(
            question_data_for_ai,
            correct_answer_data,
            user_answers_dict, # Pass the dictionary of answers
            marks
        )
        self.feedback_worker.feedback_ready.connect(self._handle_ai_feedback_result)
        # Connect error/finished signals if needed for better cleanup/state management
        # self.feedback_worker.finished.connect(self._on_worker_finished)
        self.feedback_worker.start()

    # --- Updated _handle_ai_feedback_result ---
    @Slot(object, object)
    def _handle_ai_feedback_result(self, eval_results: Optional[Dict[str, Optional[str]]], generated_prompt: Optional[str]):
        """Receives the LOCAL evaluation results AND the prompt used."""
        # Close Dialog
        if self.waiting_dialog:
            self.waiting_dialog.accept()
            self.waiting_dialog = None

        # Re-enable Submit button, change text back
        self.submit_button.setEnabled(True)
        self.submit_button.setText("Submit Answer")
        # Re-enable Next button
        self.next_button.setEnabled(True)
        # Re-enable answer fields (make them editable again)
        for text_edit in self.sub_answer_fields.values():
             text_edit.setReadOnly(False)

        # Store the prompt used for potential cloud sync
        self.last_used_prompt = generated_prompt
        history_id = None

        if eval_results:
            self.logger.info(f"Received local AI feedback: {eval_results}")
            # --- Set Preliminary Feedback Generated Flag ---
            self.preliminary_feedback_generated = True
            # ---

            # 1. Store Local results to history database
            try:
                history_manager = services.user_history_manager # Get the manager
                # --- Log prerequisite checks ---
                self.logger.debug(f"Attempting history storage. History Manager valid: {history_manager is not None}")
                self.logger.debug(f"Current Question Data valid: {self.current_question_data is not None}")
                self.logger.debug(f"Last Submitted Answers valid: {self.last_submitted_answers is not None}")
                # --- End Log ---

                if history_manager and self.current_question_data and self.last_submitted_answers:
                    # --- Use Default User ID for single-user app ---
                    current_user_id = 1 # Assuming user ID 1
                    # -----------------------------------------------

                    # --- Use the correct key 'id' from the loaded question data ---
                    cached_question_id = self.current_question_data.get('id')
                    # -------------------------------------------------------------
                    self.logger.debug(f"Extracted cached_question_id using key 'id': {cached_question_id}") # Updated log

                    if cached_question_id:
                         exam_id = self.current_question_data.get('exam_result_id', None)
                         feedback_dict = eval_results if isinstance(eval_results, dict) else {}

                         # --- Log before calling add_history_entry ---
                         self.logger.info("Calling add_history_entry with:")
                         self.logger.info(f"  user_id: {current_user_id}")
                         self.logger.info(f"  cached_question_id: {cached_question_id}")
                         self.logger.info(f"  user_answer_dict: {self.last_submitted_answers}")
                         self.logger.info(f"  local_ai_feedback_dict: {feedback_dict}")
                         self.logger.info(f"  exam_result_id: {exam_id}")
                         # --- End Log ---

                         history_id = history_manager.add_history_entry(
                             user_id=current_user_id,
                             cached_question_id=cached_question_id,
                             user_answer_dict=self.last_submitted_answers,
                             local_ai_feedback_dict=feedback_dict,
                             exam_result_id=exam_id
                         )
                         # Log result of the call
                         if history_id:
                              self.logger.info(f"add_history_entry call SUCCEEDED. Returned history_id: {history_id}")
                         else:
                              self.logger.error("add_history_entry call FAILED (returned None or 0).")
                    else:
                         # Log reason for not calling
                         self.logger.error("Skipping history storage: Could not extract 'question_id' from current_question_data.")
                else:
                     # Log which prerequisite failed
                    missing = []
                    if not history_manager: missing.append("History Manager")
                    if not self.current_question_data: missing.append("Current Question Data")
                    if not self.last_submitted_answers: missing.append("Last Submitted Answers")
                    self.logger.error(f"Skipping history storage: Prerequisites not met - Missing: {', '.join(missing)}")

            except Exception as e:
                self.logger.error(f"CRITICAL ERROR during history storage attempt: {e}", exc_info=True)
            # --- END: Store results ---

            # 2. Trigger Cloud Sync (if local save succeeded AND we have a prompt)
            if history_id and self.last_used_prompt:
                 self.trigger_cloud_sync(history_id, self.last_used_prompt) # Pass prompt
            elif not history_id:
                 self.logger.warning("Cannot trigger cloud sync because local history save failed.")
            elif not self.last_used_prompt:
                 self.logger.warning("Cannot trigger cloud sync because the local prompt was not available.")

            # 3. Display LOCAL feedback in UI (Preliminary Section)
            grade = eval_results.get('Grade', 'N/A')
            rationale = eval_results.get('Rationale', 'No details provided.')
            study_topics = eval_results.get('Study Topics', 'N/A')

            self.prelim_mark_label.setText(f"Mark Awarded: {grade}") # Update prelim label
            feedback_display_text = f"Rationale:\n{rationale}\n\nStudy Topics:\n{study_topics}"
            self.prelim_feedback_text.setText(feedback_display_text) # Update prelim text edit

            self.feedback_groupbox.show() # Show the main feedback area
            self._show_prelim_feedback() # Use method to show prelim & hide button
            self._hide_final_feedback() # Ensure finalized is hidden initially

            # --- Trigger Cloud Sync (if applicable) ---
            if history_id and self.last_used_prompt:
                 self.trigger_cloud_sync(history_id, self.last_used_prompt)
                 # Optionally update the status in the finalized report group here
                 self.final_status_label.setText("Status: Awaiting Cloud Analysis...")
                 self._show_final_feedback() # Show the finalized box (with pending status)
                 self._hide_prelim_feedback() # Optionally hide prelim once finalized starts
            elif not history_id:
                 self.logger.warning("Cannot trigger cloud sync because local history save failed.")
                 self.final_status_label.setText("Status: Cloud Sync Failed (History Error)")
                 self._show_final_feedback() # Show the finalized box (with error status)
                 self._hide_prelim_feedback() # Optionally hide prelim once finalized starts
            elif not self.last_used_prompt:
                 self.logger.warning("Cannot trigger cloud sync because the local prompt was not available.")
                 self.final_status_label.setText("Status: Cloud Sync Failed (Prompt Error)")
                 self._show_final_feedback() # Show the finalized box (with error status)
                 self._hide_prelim_feedback() # Optionally hide prelim once finalized starts

        else:
            self.logger.error("AI feedback process returned None.")
            QMessageBox.critical(self, "Error", "Failed to get feedback from the AI.")
            # Hide all feedback sections on error
            self._hide_prelim_feedback()
            self._hide_final_feedback()
            self.feedback_groupbox.hide()
            self.last_submitted_answers = None

        # Reset temp prompt after handling
        # self.last_used_prompt = None # Keep prompt until cloud sync attempted
        self.last_submitted_answers = None

    def _clear_image_links(self):
        """Removes all widgets from the image links layout."""
        # Check if the layout exists (good practice)
        if not hasattr(self, 'image_links_layout'):
             print("Warning: image_links_layout not found in QuestionView.") # Or use logger
             return
             
        # Iterate backwards while removing items from the layout
        # This is safer than iterating forwards when modifying the layout's contents
        while self.image_links_layout.count():
            # takeAt(0) removes the item at index 0 and returns it
            item = self.image_links_layout.takeAt(0) 
            if item:
                # Get the widget associated with the layout item
                widget = item.widget()
                if widget is not None:
                    # Schedule the widget for deletion. 
                    # This is important to free memory and avoid issues,
                    # especially as Qt/PySide manages object lifetimes.
                    widget.deleteLater() 

    # --- NEW METHOD: Show Image Pop-up ---
    def _show_image_popup(self, image_path, description, label):
        """Creates and shows a pop-up dialog for the selected image."""
        # Now receives absolute path
        self.logger.info(f"Popup triggered for '{label}'. Received absolute image_path: '{image_path}'")

        # Check if path is valid before proceeding
        if not image_path or not isinstance(image_path, str) or not os.path.exists(image_path):
            # This check might be redundant if called only when path_exists is true, but safe to keep
            self.logger.error(f"Cannot show popup: Image path does not exist or is invalid: {image_path}")
            QMessageBox.warning(self, "Image Error", f"Could not find the image file for '{label}' at the expected location:\n{image_path}")
            return

        try:
            dialog = QDialog(self)
            dialog.setWindowTitle(f"Image Viewer - {label}")
            dialog_layout = QVBoxLayout(dialog)

            img_label = QLabel()
            img_label.setAlignment(Qt.AlignCenter)

            self.logger.debug(f"Loading QPixmap from absolute path: {image_path}")
            pixmap = QPixmap(image_path)

            if pixmap.isNull():
                 # --- ADDED: More detailed error logging ---
                 img = QImage(image_path) # Try loading as QImage to get error string
                 error_string = img.text("load_error") if not img.isNull() else "QPixmap returned null, QImage also failed or wasn't attempted."
                 self.logger.error(f"QPixmap failed to load image from path: {image_path}. Error hint: {error_string}")
                 error_text = f"Error: Could not load image '{label}'.\nFile might be missing, corrupted, or in an unsupported format.\nPath: {image_path}\nDetails: {error_string}"
                 # --- END ADDED ---
                 img_label.setText(error_text)
                 img_label.setStyleSheet("color: red;")
                 img_label.setWordWrap(True)
            else:
                 # Scale pixmap to fit screen reasonably
                 screen = QGuiApplication.primaryScreen()
                 if screen: 
                      screen_geometry = screen.availableGeometry() 
                      max_width = screen_geometry.width() * 0.8 
                      max_height = screen_geometry.height() * 0.8
                      self.logger.debug(f"Screen available geometry: {screen_geometry.width()}x{screen_geometry.height()}. Max popup size: {max_width}x{max_height}")
                 else:
                      self.logger.warning("Could not get primary screen geometry, using fallback max size.")
                      max_width = 1000 
                      max_height = 800
                 scaled_pixmap = pixmap.scaled(int(max_width), int(max_height), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                 img_label.setPixmap(scaled_pixmap)
                 # Ensure the label requests enough space (might help layout calculation)
                 img_label.setMinimumSize(scaled_pixmap.width(), scaled_pixmap.height()) 

            # Description Label
            desc_label = QLabel(description or "No description available.")
            desc_label.setWordWrap(True)
            desc_label.setAlignment(Qt.AlignCenter)

            # Close Button
            close_button = QPushButton("Close")
            close_button.clicked.connect(dialog.accept)

            # Add widgets to dialog layout
            dialog_layout.addWidget(img_label)
            dialog_layout.addWidget(desc_label)
            dialog_layout.addWidget(close_button)

            # --- FIX: Ensure Dialog Resizes to Contents ---
            # Option 1 (Preferred): Let the layout manager calculate the best size
            dialog.adjustSize() 
            
            # Option 2 (Alternative): Explicitly set size based on scaled image + padding
            # H = img_label.minimumHeight() + desc_label.sizeHint().height() + close_button.sizeHint().height() + dialog_layout.spacing() * 3 
            # W = max(img_label.minimumWidth(), desc_label.sizeHint().width(), close_button.sizeHint().width()) + dialog_layout.contentsMargins().left() * 2
            # dialog.resize(W, H) 
            # --- End FIX ---

            dialog.exec_() 

        except Exception as e:
            self.logger.error(f"Unexpected error creating image popup for {image_path}: {e}", exc_info=True)
            QMessageBox.critical(self, "Popup Error", f"An unexpected error occurred while trying to display the image:\n{e}")

    def trigger_cloud_sync(self, history_id: int, local_prompt: str):
        """Checks network and either triggers immediate Groq call or queues."""
        self.logger.info(f"Triggering cloud sync process for history_id: {history_id}")
        if not local_prompt:
             self.logger.error(f"Cannot trigger cloud sync for {history_id}: Local prompt is missing.")
             return

        network_monitor = services.network_monitor
        sync_service = services.sync_service
        history_manager = services.user_history_manager

        if not history_manager:
             self.logger.error("UserHistoryManager not available. Cannot mark status or process fully.")
             # Decide if we should still attempt queueing/worker start without DB updates
             # For now, let's proceed but log the limitation

        # Check Online Status
        if network_monitor and network_monitor.get_status() == NetworkStatus.ONLINE:
            self.logger.info("Network ONLINE. Attempting immediate Groq analysis.")

            # --- Ensure Worker Management is Correct ---
            # Check if a worker for this ID is already running (safety)
            if history_id in self.groq_workers and self.groq_workers[history_id].isRunning():
                 self.logger.warning(f"Groq worker for history_id {history_id} is already running. Skipping.")
                 return

            # Create the worker
            worker = GroqFeedbackWorker(
                history_id=history_id,
                local_prompt=local_prompt
            )
            # Connect signals BEFORE adding to dict or starting
            worker.feedback_ready.connect(self._handle_groq_feedback_result)
            worker.feedback_error.connect(self._handle_groq_feedback_error)
            # Connect finished signal to remove worker from the tracking dict
            # Using a direct lambda is standard and should work fine here.
            worker.finished.connect(lambda hid=history_id: self._on_groq_worker_finished(hid))

            # Add worker to dictionary BEFORE starting the thread
            self.groq_workers[history_id] = worker
            self.logger.debug(f"Added Groq worker for {history_id} to tracking dictionary.")

            # Start the thread
            worker.start()
            self.logger.debug(f"Groq worker for {history_id} started.")
            # --- End Worker Management Verification ---

        elif sync_service:
            self.logger.info("Network OFFLINE or status unknown. Queueing request via SyncService.")
            # Pass prompt to queueing method
            queued = sync_service.queue_cloud_analysis(history_id, local_prompt)
            if not queued:
                 self.logger.error(f"Failed to queue cloud analysis request for history_id: {history_id}")
        else:
            self.logger.error("Cannot queue offline request: SyncService unavailable.")

    @Slot(int, object)
    def _handle_groq_feedback_result(self, history_id: int, cloud_report: Dict):
        """Receives the cloud report from the GroqFeedbackWorker."""
        self.logger.info(f"Received successful Groq feedback for history_id: {history_id}")
        history_manager = services.user_history_manager

        if history_manager:
            success = history_manager.update_with_cloud_report(history_id, cloud_report)

            if success:
                 self.logger.info(f"Successfully updated answer_history for {history_id} with cloud report via direct call.")

                 # --- Set Flag indicating generation SUCCESS ---
                 # Set this regardless of whether the user is still viewing the question,
                 # as the data *was* generated successfully.
                 self.finalized_feedback_generated = True
                 self.logger.info(f"Flag finalized_feedback_generated set to True for history_id {history_id} based on successful DB update.")
                 # ---

                 # --- Update UI only if still relevant ---
                 self.logger.info(f"Checking if UI should be updated for finalized report (history_id: {history_id})")
                 try:
                      current_qid = self.current_question_data.get('id') if self.current_question_data else None
                      history_qid = history_manager.get_question_id_for_history(history_id) # Needs implementation in UHM
                      self.logger.debug(f"Check: current_qid={current_qid}, history_qid={history_qid}")

                      if history_qid and current_qid == history_qid:
                            self.logger.info(f"Cloud report matches current question {current_qid}. Updating Finalized UI section.")

                            # Set Title for the finalized group
                            # self.finalized_report_group.setTitle("Finalized Report (Cloud AI)") # Already set potentially

                            cloud_grade = cloud_report.get('grade', 'N/A (Cloud)')
                            cloud_rationale = cloud_report.get('rationale', 'N/A (Cloud)')
                            cloud_study_topics_obj = cloud_report.get('study_topics', {})

                            # Update status label
                            self.final_status_label.setText("Status: Analysis Complete")
                            self.final_status_label.setStyleSheet("font-style: normal; color: #166534; font-weight: bold;")

                            # Update grade and feedback text in the FINALIZED section
                            self.final_grade_label.setText(f"Grade: {cloud_grade}")

                            study_topics_display = "Study Topics:\n"
                            if isinstance(cloud_study_topics_obj, dict):
                                if 'raw' in cloud_study_topics_obj: study_topics_display += cloud_study_topics_obj['raw']
                                elif 'lines' in cloud_study_topics_obj: study_topics_display += "\n".join(f"- {line}" for line in cloud_study_topics_obj['lines'])
                                else: study_topics_display += json.dumps(cloud_study_topics_obj, indent=2)
                            else:
                                study_topics_display += str(cloud_study_topics_obj)

                            full_feedback = f"Rationale:\n{cloud_rationale}\n\n{study_topics_display}"
                            self.final_feedback_text.setText(full_feedback)

                            # Ensure the finalized section is visible using the method
                            self._show_final_feedback() # Shows box, hides show button

                            self.logger.info(f"Finalized UI section updated successfully for {history_id}.")
                            # Optional: Automatically hide preliminary once finalized is ready
                            # self._hide_prelim_feedback()
                      else:
                           self.logger.info(f"Cloud report received for history_id {history_id}, but user has navigated away or IDs don't match (Current: {current_qid}, History: {history_qid}). UI not updated, but flag was set.")
                           # Since UI isn't updated, ensure the "Show" button isn't wrongly displayed
                           # if the section was previously hidden.
                           # If the finalized group is hidden, the corresponding show button might
                           # need to be explicitly hidden here if the flag was just set.
                           if self.finalized_report_group.isHidden():
                               self.show_final_button.hide()


                 except Exception as ui_update_err:
                      self.logger.error(f"Error updating UI with cloud report for {history_id}: {ui_update_err}", exc_info=True)
                 # --- END UI UPDATE ---

                 self.update_new_report_indicator() # Update badge count
            else:
                 self.logger.error(f"Failed to update answer_history for {history_id} with cloud report data.")
                 # Failed DB update, so don't set the flag
                 self.finalized_feedback_generated = False
        else:
            self.logger.error("UserHistoryManager service not available when Groq result received. Cannot save cloud report to DB.")
            # Cannot confirm generation, don't set the flag
            self.finalized_feedback_generated = False

    @Slot(int, str)
    def _handle_groq_feedback_error(self, history_id: int, error_message: str):
        """Handles errors reported by the GroqFeedbackWorker."""
        self.logger.error(f"GroqFeedbackWorker reported error for history_id {history_id}: {error_message}")
        # Optional: Add logic here, like marking DB entry as failed direct sync

    def update_new_report_indicator(self):
        """Placeholder: Signal or call method to update the UI badge."""
        self.logger.info("Placeholder: Update UI indicator for new reports.")
        # Find the profile widget and call its update method
        # This might involve traversing parent widgets or using signals/slots
        # Example (highly dependent on your exact UI structure):
        main_window = self.window() # Get the top-level window
        if hasattr(main_window, 'profile_info_widget') and hasattr(main_window.profile_info_widget, 'update_new_report_indicator'):
             self.logger.debug("Calling update_new_report_indicator on main window's profile widget.")
             main_window.profile_info_widget.update_new_report_indicator()
        else:
             self.logger.warning("Could not find profile_info_widget or its update method to update badge.")

    # --- ADDED: Dedicated slot for worker finished ---
    @Slot(int)
    def _on_groq_worker_finished(self, history_id: int):
        """Cleans up the worker reference when the thread finishes."""
        self.logger.debug(f"Groq worker thread finished for history_id: {history_id}. Removing from tracking dictionary.")
        # Remove the worker reference from the dictionary
        removed_worker = self.groq_workers.pop(history_id, None)
        if removed_worker:
             # Optional: Explicitly schedule the worker object for deletion
             # This can sometimes help Python's GC timing issues with Qt objects
             removed_worker.deleteLater()
             self.logger.debug(f"Scheduled worker object for deletion for history_id: {history_id}.")
        else:
             self.logger.warning(f"Attempted to remove finished worker for history_id {history_id}, but it was not found in the dictionary.")
    # --- END ADDED SLOT ---

    # --- ADDED: Methods to handle individual feedback visibility ---
    def _hide_prelim_feedback(self):
        """Hides the preliminary feedback box and shows the 'Show Preliminary' button *if generated*."""
        self.preliminary_feedback_group.hide()
        # --- MODIFIED: Only show button if feedback was generated ---
        if self.preliminary_feedback_generated:
            self.show_prelim_button.show()
        # ---
        self.logger.debug("Preliminary Feedback hidden.")
        # If both sections are hidden, hide the main container
        if self.finalized_report_group.isHidden():
             self.feedback_groupbox.hide()

    def _show_prelim_feedback(self):
        """Shows the preliminary feedback box and hides the 'Show Preliminary' button."""
        self.feedback_groupbox.show() # Ensure main container is visible
        self.preliminary_feedback_group.show()
        self.show_prelim_button.hide()
        self.logger.debug("Preliminary Feedback shown.")

    def _hide_final_feedback(self):
        """Hides the finalized report box and shows the 'Show Finalized' button *if generated*."""
        self.finalized_report_group.hide()
        # --- MODIFIED: Only show button if feedback was generated ---
        if self.finalized_feedback_generated:
            self.show_final_button.show()
        # ---
        self.logger.debug("Finalized Report hidden.")
        # If both sections are hidden, hide the main container
        if self.preliminary_feedback_group.isHidden():
             self.feedback_groupbox.hide()

    def _show_final_feedback(self):
        """Shows the finalized report box and hides the 'Show Finalized' button."""
        self.feedback_groupbox.show() # Ensure main container is visible
        self.finalized_report_group.show()
        self.show_final_button.hide()
        self.logger.debug("Finalized Report shown.")
    # --- END ADDED METHODS ---

# Example Usage (if run standalone)
if __name__ == '__main__':
    from PySide6.QtWidgets import QApplication
    import sys

    # --- Basic Logging Setup ---
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    app = QApplication(sys.argv)
    # You need to initialize CacheManager and potentially other services if running standalone
    # cache_mgr = CacheManager()
    # cache_mgr.start() # Ensure it's initialized and potentially running

    # Example: Assuming 'Biology' and 'o_level' exist in cache
    # You might need to ensure data is cached first if running standalone
    view = QuestionView('Biology', 'o_level')
    view.show()
    sys.exit(app.exec())
