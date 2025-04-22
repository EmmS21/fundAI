import logging
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, QScrollArea, QSizePolicy, QDialog, QFrame, QMessageBox, QGroupBox)
from PySide6.QtGui import QPixmap, QImage, QFont, QGuiApplication, QMovie
from PySide6.QtCore import Qt, Signal, QUrl, QThread
from src.data.cache.cache_manager import CacheManager
import os
import sys
import json
from src.core.ai.marker import run_ai_evaluation # Use the updated orchestrator name
from typing import Dict, Optional

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
    # Signal emits the results dictionary
    feedback_ready = Signal(object)

    def __init__(self, question_data, correct_answer_data, user_answer, marks):
        super().__init__()
        self.question_data = question_data
        self.correct_answer_data = correct_answer_data
        self.user_answer = user_answer
        self.marks = marks

    def run(self):
        """Runs the AI evaluation function in a separate thread."""
        logger.info("AIFeedbackWorker started (Mark + Justification).")
        # --- FIX: Call the updated function ---
        evaluation_results = run_ai_evaluation(
            self.question_data,
            self.correct_answer_data,
            self.user_answer,
            self.marks
        )
        self.feedback_ready.emit(evaluation_results)
        logger.info("AIFeedbackWorker finished (Mark + Justification).")

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

        self._setup_ui()
        self.load_random_question()

    def _setup_ui(self):
        """Set up the basic UI elements for the question view."""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)
        self.setStyleSheet(PAPER_STYLE + MARKS_BUTTON_STYLE) # Apply styles

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

        # --- Placeholder for dynamically added elements (like marks buttons) ---
        # This layout will hold sub-questions and their marks buttons
        self.sub_elements_layout = QVBoxLayout()
        self.sub_elements_layout.setSpacing(8)
        self.question_layout.addLayout(self.sub_elements_layout)


        self.question_layout.addStretch(1) # Push content to the top

        scroll_area.setWidget(self.question_content_widget) # Set the container as the scroll area's widget
        self.main_layout.addWidget(scroll_area, 1)

        # --- Answer Input Area ---
        self.answer_input = QTextEdit()
        self.answer_input.setPlaceholderText("Enter your answer here...")
        self.answer_input.setFixedHeight(100) # Adjust height as needed
        self.answer_input.setStyleSheet("font-size: 14px; border: 1px solid #D1D5DB; border-radius: 6px; padding: 5px;")
        self.main_layout.addWidget(self.answer_input)

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
        # Clear widgets from the sub-elements layout BEFORE loading new data
        while self.sub_elements_layout.count():
            item = self.sub_elements_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            else: # If it's a layout, clear it recursively (optional, depends on structure)
                 layout = item.layout()
                 if layout is not None:
                      # Basic recursive clear (can be enhanced)
                      while layout.count():
                           sub_item = layout.takeAt(0)
                           sub_widget = sub_item.widget()
                           if sub_widget: sub_widget.deleteLater()


        try:
            question_data = self.cache_manager.get_random_question(self.subject_name, self.level_key)
            self.logger.debug(f"Raw question data received: {question_data}")

            if question_data:
                self.current_question_data = question_data

                # --- Build and Display Question Content ---

                # 1. Display Main Question Text (if any)
                main_text = question_data.get('text') or question_data.get('question_text', '')
                self.question_text_label.setText(main_text.strip())
                self.question_text_label.setVisible(bool(main_text.strip())) # Show/hide if empty

                # 2. Process Sub-Questions (Create separate widgets)
                sub_questions = question_data.get('sub_questions', [])
                if sub_questions and isinstance(sub_questions, list):
                     # Optional: Add a label like "Sub Questions:"
                     # sub_q_header = QLabel("<b>Sub Questions:</b>")
                     # self.sub_elements_layout.addWidget(sub_q_header)

                     for sq_index, sq in enumerate(sub_questions):
                         if isinstance(sq, dict):
                             marks_val = sq.get('marks')
                             sub_num_str = sq.get('sub_number', f'({sq_index+1})') # Fallback numbering
                             sub_text_str = sq.get('text', '').strip()

                             # Layout for a single sub-question row (text + marks)
                             sub_q_row_layout = QHBoxLayout()
                             sub_q_row_layout.setSpacing(10)

                             # Sub-question Text Label
                             sub_q_text = f"<b>{sub_num_str}</b>) {sub_text_str}"
                             sub_q_label = QLabel(sub_q_text)
                             sub_q_label.setWordWrap(True)
                             sub_q_label.setStyleSheet("background-color: transparent;") # Ensure transparency
                             sub_q_row_layout.addWidget(sub_q_label, 1) # Give text stretchy space

                             # Marks Button (if marks exist)
                             if marks_val is not None:
                                 marks_button = QPushButton(f"{marks_val} marks")
                                 marks_button.setProperty("class", "MarksButton") # For QSS styling
                                 # marks_button.setToolTip("Click to highlight relevant section?") # Optional tooltip
                                 # Connect signal if needed: marks_button.clicked.connect(lambda m=marks_val: self._handle_marks_click(m))
                                 sub_q_row_layout.addWidget(marks_button) # Add button to row
                             else:
                                 sub_q_row_layout.addStretch(0) # Add stretch if no button to align items

                             # Add the row layout to the main sub-elements layout
                             self.sub_elements_layout.addLayout(sub_q_row_layout)

                         else:
                             self.logger.warning(f"Skipping invalid sub_question item (not a dict): {sq}")


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


                self.answer_input.clear()
                self.answer_input.setEnabled(True)


                # --- Populate Image Links --- (Keep existing logic)
                self._clear_image_links()
                images = question_data.get('images', []) # Get images again for links

                if images and isinstance(images, list):
                    valid_images_found = False
                    self.image_section_label.show()

                    self.logger.debug(f"Processing {len(images)} image entries for question.")
                    for i, img_data in enumerate(images):
                        if not isinstance(img_data, dict):
                            self.logger.warning(f"Skipping invalid image entry #{i} (not a dict): {img_data}")
                            continue

                        label = img_data.get('label')
                        local_path = img_data.get('local_path')
                        description = img_data.get('description', '')

                        # --- Add Detailed Logging Here ---
                        self.logger.debug(f"Image #{i}: Label='{label}', LocalPath='{local_path}', Type={type(local_path)}")
                        path_exists = False
                        abs_path = None # Initialize abs_path
                        if local_path and isinstance(local_path, str):
                            try:
                                 abs_path = os.path.abspath(local_path)
                                 path_exists = os.path.exists(abs_path)
                                 self.logger.debug(f"Image #{i}: Checking absolute path '{abs_path}' -> Exists: {path_exists}")
                            except Exception as e:
                                 self.logger.error(f"Image #{i}: Error checking path '{local_path}': {e}")
                        # --- End Detailed Logging ---

                        # Check conditions for creating the link
                        if label and local_path and isinstance(local_path, str) and path_exists:
                            self.logger.info(f"Image #{i}: Conditions met. Creating link for '{label}'.")

                            # --- ADD THIS LOG LINE ---
                            self.logger.info(f"Image #{i}: Using local_path '{local_path}' for link href and lambda.")
                            # --- END ADDED LOG LINE ---

                            # Create the clickable label
                            link_label = QLabel(f"<a href='{local_path}'>{label}</a>")
                            link_label.setToolTip(description or label)
                            link_label.linkActivated.connect(
                                lambda path=local_path, desc=description, lbl=label: self._show_image_popup(path, desc, lbl)
                            )
                            self.image_links_layout.addWidget(link_label)
                            valid_images_found = True
                        else:
                            # Log why the condition failed
                            self.logger.warning(f"Image #{i}: Skipping link creation for Label='{label}'. Reason: label={bool(label)}, local_path={bool(local_path)}, is_str={isinstance(local_path, str)}, path_exists={path_exists}.")
                            # Optionally add the greyed-out label even if skipped
                            if label:
                                 missing_label = QLabel(f"{label} (Image not available)")
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
                self.answer_input.setEnabled(False)
                self._clear_image_links() # Clear images if no question loaded

        except Exception as e:
            logger.error(f"Error loading question: {e}", exc_info=True)
            self.question_text_label.setText(f"Error loading question: {str(e)}")
            self.question_text_label.setVisible(True)
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
        """Starts the AI feedback process and shows the waiting dialog."""
        if self.feedback_worker and self.feedback_worker.isRunning():
            self.logger.warning("Feedback process already running.")
            return

        if self.current_question_data:
            # ... (Keep logic to get user_answer, validate, calculate marks, load correct_answer_data) ...
            user_answer = self.answer_input.toPlainText().strip()
            # ... validation checks ...
            marks = self.current_question_data.get('marks') # etc.
            # ... load correct_answer_data ...
            correct_answer_data = {} # Placeholder

            # --- Show Waiting Dialog & Disable UI ---
            self.submit_button.setEnabled(False)
            self.submit_button.setText("Processing...")
            self.answer_input.setReadOnly(True)
            self.next_button.setEnabled(False)

            # Create and show the dialog
            self.waiting_dialog = WaitingDialog(self)
            self.waiting_dialog.show()
            # --- End Show Waiting Dialog ---

            # --- Start Worker Thread ---
            self.feedback_worker = AIFeedbackWorker(
                self.current_question_data,
                correct_answer_data,
                user_answer,
                marks
            )
            self.feedback_worker.feedback_ready.connect(self._handle_ai_feedback_result)
            self.feedback_worker.start()

        else:
            # ... (Handle no current question data) ...
             pass

    # --- UPDATED _handle_ai_feedback_result ---
    def _handle_ai_feedback_result(self, eval_results: Optional[Dict[str, Optional[str]]]):
        """Receives the evaluation results dict (or None) from the worker thread."""
        # Close Dialog
        if self.waiting_dialog:
            self.waiting_dialog.accept()
            self.waiting_dialog = None
        self.submit_button.setText("Submit Answer") # Reset button

        # Process results
        if eval_results and isinstance(eval_results, dict):
            self.logger.info("Received evaluation results from AI.")
            # Check if mark parsing specifically failed
            mark_value = eval_results.get("Mark Awarded")
            if not mark_value or mark_value.startswith("N/A"):
                 QMessageBox.warning(self, "AI Evaluation Info", "AI could not determine a mark.")

            self._display_feedback(eval_results) # Display mark and justification
            self.next_button.setEnabled(True)
        else:
            # Handle critical errors (None return from run_ai_evaluation)
            error_message = "Failed to get evaluation from AI service (critical error)."
            self.logger.error(error_message)
            QMessageBox.critical(self, "AI Evaluation Error", error_message)
            # Re-enable UI on critical failure
            self.submit_button.setEnabled(True)
            self.answer_input.setReadOnly(False)
            self.next_button.setEnabled(True)


    # --- UPDATED _display_feedback ---
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
        self.logger.info(f"Popup triggered for '{label}'. Received image_path: '{image_path}' (Type: {type(image_path)})")

        if not image_path or not isinstance(image_path, str) or not os.path.exists(image_path):
            self.logger.error(f"Cannot show popup: Image path does not exist or is invalid: {image_path}")
            return 

        try:
            dialog = QDialog(self) 
            dialog.setWindowTitle(f"Image Viewer - {label}")
            dialog_layout = QVBoxLayout(dialog) # Set layout parent immediately

            img_label = QLabel()
            img_label.setAlignment(Qt.AlignCenter) # Center image/text in the label

            self.logger.debug(f"Loading QPixmap from: {image_path}")
            pixmap = QPixmap(image_path)
            
            if pixmap.isNull():
                 self.logger.error(f"QPixmap failed to load image from path: {image_path}")
                 error_text = f"Error: Could not load image '{label}'.\nFile might be missing, corrupted, or in an unsupported format."
                 img_label.setText(error_text)
                 img_label.setStyleSheet("color: red;") 
                 img_label.setWordWrap(True) # Ensure error text wraps
            else:
                 self.logger.debug(f"QPixmap loaded successfully. Original size: {pixmap.width()}x{pixmap.height()}")
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
