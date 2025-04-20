import logging
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, QScrollArea, QSizePolicy, QDialog, QFrame)
from PySide6.QtGui import QPixmap, QImage, QFont, QGuiApplication
from PySide6.QtCore import Qt, Signal, QUrl
from src.data.cache.cache_manager import CacheManager
import os
import sys
import json
from src.core.ai.marker import get_ai_feedback # <-- Import the AI feedback function

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

        # --- Action Buttons ---
        button_layout = QHBoxLayout()
        # TODO: Add "Previous" button if needed
        next_button = QPushButton("Next Question")
        next_button.setStyleSheet("""
            QPushButton {
                background-color: #F3F4F6;
                color: #374151;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #E5E7EB;
            }
        """)
        next_button.clicked.connect(self.load_random_question) # Load another question

        submit_button = QPushButton("Submit Answer")
        submit_button.setStyleSheet("""
            QPushButton {
                background-color: #A855F7;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #9333EA;
            }
        """)
        submit_button.clicked.connect(self._submit_answer)

        button_layout.addStretch()
        # button_layout.addWidget(previous_button)
        button_layout.addWidget(next_button)
        button_layout.addWidget(submit_button)
        self.main_layout.addLayout(button_layout)

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

    def _submit_answer(self):
        if self.current_question_data:
            user_answer = self.answer_input.toPlainText().strip()
            
            # --- Extract necessary info from current question data ---\
            question_id = self.current_question_data.get('id')
            subject = self.current_question_data.get('subject')
            level = self.current_question_data.get('level')
            year = self.current_question_data.get('year')
            answer_ref = self.current_question_data.get('answer_ref') # e.g., "1a.json"
            
            # Basic validation
            if not all([question_id, subject, level, year, answer_ref]):
                self.logger.error("Could not submit answer: Missing critical data in current_question_data (id, subject, level, year, or answer_ref)")
                # TODO: Show error message to user
                return
            
            if not user_answer:
                self.logger.warning("User tried to submit an empty answer.")
                # TODO: Show message to user to enter an answer
                return

            # --- Calculate Marks (Keep existing logic) ---\
            marks = self.current_question_data.get('marks')
            if marks is None and 'sub_questions' in self.current_question_data:
                try:
                    marks = sum(sq.get('marks', 0) or 0 for sq in self.current_question_data['sub_questions'] if isinstance(sq, dict))
                except TypeError:
                    marks = None 
                    self.logger.warning(f"Could not sum marks from sub-questions for question {question_id}")
            
            # --- Construct path to the correct answer file ---\
            # Use CacheManager's base paths if available, otherwise construct relatively
            base_answer_dir = getattr(self.cache_manager, 'ANSWERS_DIR', os.path.join("src", "data", "cache", "answers"))
            safe_subject = getattr(self.cache_manager, '_safe_filename', lambda s: s)(subject) # Use safe filename func if possible
            answer_file_path = os.path.join(base_answer_dir, safe_subject, level, str(year), answer_ref)
            
            self.logger.debug(f"Attempting to load correct answer from: {answer_file_path}")
            
            correct_answer_data = None
            try:
                with open(answer_file_path, 'r', encoding='utf-8') as f:
                    correct_answer_data = json.load(f)
                self.logger.info(f"Successfully loaded correct answer for question {question_id}")
            except FileNotFoundError:
                self.logger.error(f"Correct answer file not found at: {answer_file_path}")
                # TODO: Show error to user - "Could not retrieve marking information"
                return
            except json.JSONDecodeError:
                self.logger.error(f"Error decoding JSON from answer file: {answer_file_path}")
                # TODO: Show error to user
                return
            except Exception as e:
                self.logger.error(f"Unexpected error loading answer file {answer_file_path}: {e}", exc_info=True)
                # TODO: Show error to user
                return
            
            # --- Now we have: ---\
            # self.current_question_data (dict)
            # correct_answer_data (dict)
            # user_answer (str)
            # marks (int or None)

            self.logger.info(f"Ready for AI Marking - QID: {question_id}, Marks: {marks}")
            self.logger.debug(f"User Answer: {user_answer}")
            # self.logger.debug(f"Correct Answer Data: {correct_answer_data}") # Potentially large, log carefully

            # TODO:
            # 1. Create src/core/ai/marker.py with get_ai_feedback(question, correct_answer, user_answer, marks)
            # 2. Import and call get_ai_feedback here
            # --- Call the AI marker service ---
            self.logger.info("Calling AI feedback service...")
            parsed_response = get_ai_feedback(
                question_data=self.current_question_data,
                correct_answer_data=correct_answer_data,
                user_answer=user_answer,
                marks=marks
            )

            # Check if the response is valid
            if parsed_response and "Error" not in parsed_response:
                self.logger.info("Received and parsed AI feedback/suggestions.")
                # TODO: Display feedback and suggestions in the UI using parsed_response dict
                print("--- AI FEEDBACK ---") # Temporary console output
                for heading, content in parsed_response.items():
                    print(f"## {heading}:\n{content}\n")
                # print(f"Feedback: {parsed_response.get('Feedback', 'N/A')}")
                # print(f"Mark Awarded: {parsed_response.get('Mark Awarded', 'N/A')}")
                # ... access other sections as needed ...
                print("-------------------\n")
                # Maybe disable input/submit here and show feedback, 
                # then provide a button to go to the next question.
            else:
                # Handle cases where model wasn't found, server failed, request failed, or parsing failed
                error_message = "Failed to get valid feedback from AI service."
                if isinstance(parsed_response, dict) and "Error" in parsed_response:
                    error_message = f"AI Service Error: {parsed_response['Error']}"
                self.logger.error(error_message)
                # TODO: Show specific error message to user ("Could not get AI feedback: [Reason]")

            # 3. Process the response (feedback, suggestions) and display it
            # 4. Update UI state (e.g., disable submit, show feedback area)

            # Placeholder action: Clear input and load next question
            # We might want to change this behavior now - e.g., wait for user to acknowledge feedback
            self.answer_input.clear()
            self.load_random_question()
        else:
            self.logger.warning("Submit button clicked, but no current question data loaded.")

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
