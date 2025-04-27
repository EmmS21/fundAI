import logging
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, QScrollArea, QSizePolicy, QDialog, QFrame, QMessageBox, QGroupBox)
from PySide6.QtGui import QPixmap, QImage, QFont, QGuiApplication, QMovie
from PySide6.QtCore import Qt, Signal, QUrl, QThread, QStandardPaths
from src.data.cache.cache_manager import CacheManager
import os
import sys
import json
from src.core.ai.marker import run_ai_evaluation # Use the updated orchestrator name
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)

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

        # --- Optional Spinner GIF ---
        # self.spinner_label = QLabel()
        # self.movie = QMovie("path/to/your/spinner.gif") # Needs a GIF file
        # if self.movie.isValid():
        #     self.spinner_label.setMovie(self.movie)
        #     layout.addWidget(self.spinner_label, alignment=Qt.AlignCenter)
        #     self.movie.start()
        # else:
        #     logger.warning("Spinner GIF not found or invalid.")
        # ----------------------------

        self.setMinimumWidth(300)
        self.setLayout(layout)

# --- Worker Thread for AI Feedback ---
class AIFeedbackWorker(QThread):
    # Signal emits the results dictionary or potentially a more complex structure later
    feedback_ready = Signal(object)

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
        # --- NOTE: run_ai_evaluation needs to be updated to handle the user_answer dict ---
        # For now, it might fail or only process part of the answer depending on its implementation
        # We will update run_ai_evaluation and the backend API in the next step.
        evaluation_results = run_ai_evaluation(
            self.question_data,
            self.correct_answer_data,
            self.user_answer, # Pass the dictionary
            self.marks
        )
        self.feedback_ready.emit(evaluation_results)
        logger.info("AIFeedbackWorker finished.")

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
        self.waiting_dialog = None # Add instance variable for the dialog
        # --- ADDED: Dictionary to hold sub-question input fields ---
        self.sub_answer_fields: Dict[str, QTextEdit] = {}
        # ----------------------------------------------------------

        self._setup_ui()
        self.load_random_question()

    def _setup_ui(self):
        """Set up the basic UI elements for the question view."""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)
        self.setStyleSheet(PAPER_STYLE + MARKS_BUTTON_STYLE + SUB_QUESTION_STYLE) # Apply styles

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

        # --- ADDED: Feedback Display Area (Initially Hidden) ---
        self.feedback_groupbox = QGroupBox("AI Feedback")
        self.feedback_groupbox.setObjectName("FeedbackGroup")
        self.feedback_layout = QVBoxLayout(self.feedback_groupbox)
        self.feedback_layout.setSpacing(8)

        # --- FIX: Assign labels and textedit to self. ---
        self.mark_label = QLabel("Mark Awarded: N/A") # USE self.
        self.mark_label.setObjectName("FeedbackLabel")
        self.rating_label = QLabel("Understanding Rating: N/A") # USE self.
        self.rating_label.setObjectName("FeedbackLabel")

        mark_rating_layout = QHBoxLayout()
        mark_rating_layout.addWidget(self.mark_label) # Reference self.
        mark_rating_layout.addStretch()
        mark_rating_layout.addWidget(self.rating_label) # Reference self.
        self.feedback_layout.addLayout(mark_rating_layout)

        # Assign content label to self for consistency, though not strictly required by the error
        self.feedback_content_label = QLabel("Feedback Details:")
        self.feedback_content_label.setObjectName("FeedbackLabel")
        self.feedback_content_label.setStyleSheet("font-weight: bold;")
        self.feedback_layout.addWidget(self.feedback_content_label) # Reference self.

        # Assign QTextEdit to self
        self.feedback_text = QTextEdit() # USE self.
        self.feedback_text.setObjectName("FeedbackContent")
        self.feedback_text.setReadOnly(True)
        self.feedback_text.setFixedHeight(150)
        self.feedback_layout.addWidget(self.feedback_text) # Reference self.
        # --- END FIX ---

        self.feedback_groupbox.hide()
        self.main_layout.addWidget(self.feedback_groupbox)

        # --- Action Buttons ---
        self.button_layout = QHBoxLayout()
        self.next_button = QPushButton("Next Question")
        # ... styling ...
        self.next_button.clicked.connect(self.load_random_question)
        self.next_button.setEnabled(False)

        self.submit_button = QPushButton("Submit Answer")
        # ... styling ...
        self.submit_button.clicked.connect(self._trigger_ai_feedback)

        self.button_layout.addStretch()
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

        # --- Hide feedback from previous question ---
        self.feedback_groupbox.hide()
        self.submit_button.setEnabled(True) # Re-enable submit
        self.next_button.setEnabled(False) # Disable next until submitted

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
                             self.sub_elements_layout.addWidget(desc_label) # Add description to layout


                # --- Enable relevant controls ---
                self.submit_button.setEnabled(True)


                # --- Populate Image Links ---
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
        # ------------------------------------------

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
    # NOTE: This function now receives results potentially based on the dictionary input.
    # The structure of eval_results might need changes based on how run_ai_evaluation is updated.
    # For now, assume it returns a similar dictionary for overall feedback.
    def _handle_ai_feedback_result(self, eval_results: Optional[Dict[str, Optional[str]]]):
        """Receives the evaluation results dict (or None) from the worker thread."""
        # Close Dialog
        if self.waiting_dialog:
            self.waiting_dialog.accept()
            self.waiting_dialog = None
        self.submit_button.setText("Submit Answer") # Reset button text

        if eval_results and isinstance(eval_results, dict):
            self.logger.info("Received evaluation results from AI.")
            # Display overall feedback for now
            self._display_feedback(eval_results)
            self.next_button.setEnabled(True) # Enable next question
             # Keep answer fields read-only after successful submission/feedback
        else:
            error_message = "Failed to get evaluation from AI service."
            self.logger.error(error_message)
            QMessageBox.critical(self, "AI Evaluation Error", error_message)
            # Re-enable UI on critical failure
            self.submit_button.setEnabled(True)
            for text_edit in self.sub_answer_fields.values(): # Re-enable input fields
                text_edit.setReadOnly(False)
            self.next_button.setEnabled(True) # Allow moving on even if feedback failed


    # --- Updated _display_feedback ---
    def _display_feedback(self, data: Dict[str, Optional[str]]):
        """Populates the feedback UI elements with mark and justification."""
        logger.debug(f"Displaying evaluation data: {data}")

        mark_value = data.get('Mark Awarded', 'N/A')
        justification = data.get('Mark Justification') # Fetch the justification

        self.mark_label.setText(f"Mark Awarded: {mark_value}")

        # --- Display Justification (if available) ---
        display_text = ""
        if justification and not justification.startswith("N/A"):
            display_text = f"**Justification:**\n{justification}\n\n"
        elif mark_value and not mark_value.startswith("N/A"): # Mark found, but no justification
             display_text = "(AI did not provide a justification for this mark)\n\n"
        else: # Neither mark nor justification found
             display_text = "(AI evaluation failed to produce mark or justification)\n\n"

        # Add placeholder for other feedback types
        display_text += "(Other feedback sections currently disabled)"

        # Clear or hide other fields
        self.rating_label.setText("Understanding Rating: -")
        self.feedback_text.setText(display_text) # Use setText or setMarkdown
        # --- END DISPLAY Justification ---

        self.feedback_groupbox.setTitle("AI Evaluation")
        self.feedback_groupbox.show()

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
