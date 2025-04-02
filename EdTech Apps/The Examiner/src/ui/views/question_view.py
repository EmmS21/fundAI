import logging
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton, QTextEdit, QScrollArea)
from PySide6.QtCore import Qt, Signal
from src.data.cache.cache_manager import CacheManager

logger = logging.getLogger(__name__)

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

        self._setup_ui()
        self.load_random_question()

    def _setup_ui(self):
        """Set up the basic UI elements for the question view."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # --- Header ---
        header_layout = QHBoxLayout()
        self.title_label = QLabel(f"Question - {self.subject_name} ({self._get_level_display_name(self.level_key)})")
        self.title_label.setStyleSheet("font-size: 18px; font-weight: bold;")

        back_button = QPushButton("Back to Subjects")
        back_button.clicked.connect(self.back_requested.emit) # Emit signal on click

        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        header_layout.addWidget(back_button)
        layout.addLayout(header_layout)

        # --- Question Display Area (Scrollable) ---
        # Use QScrollArea for potentially long questions
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; background-color: #FFFFFF; }") # White background

        question_container = QWidget() # Widget inside scroll area
        question_layout = QVBoxLayout(question_container)

        self.question_text_label = QLabel("Loading question...")
        self.question_text_label.setWordWrap(True) # Allow text wrapping
        self.question_text_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.question_text_label.setStyleSheet("font-size: 16px; padding: 10px; background-color: white;")
        question_layout.addWidget(self.question_text_label)
        # TODO: Add widgets for images if needed later

        scroll_area.setWidget(question_container)
        layout.addWidget(scroll_area, 1) # Give scroll area stretchy space

        # --- Answer Input Area ---
        self.answer_input = QTextEdit()
        self.answer_input.setPlaceholderText("Enter your answer here...")
        self.answer_input.setFixedHeight(100) # Adjust height as needed
        self.answer_input.setStyleSheet("font-size: 14px; border: 1px solid #D1D5DB; border-radius: 6px; padding: 5px;")
        layout.addWidget(self.answer_input)

        # --- Action Buttons ---
        button_layout = QHBoxLayout()
        # TODO: Add "Previous" button if needed
        next_button = QPushButton("Next Question")
        next_button.setStyleSheet("...") # Add styling similar to other buttons
        next_button.clicked.connect(self.load_random_question) # Load another question

        submit_button = QPushButton("Submit Answer")
        submit_button.setStyleSheet("...") # Add styling
        # submit_button.clicked.connect(self._submit_answer) # TODO: Implement submit logic

        button_layout.addStretch()
        # button_layout.addWidget(previous_button)
        button_layout.addWidget(next_button)
        button_layout.addWidget(submit_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)


    def load_random_question(self):
        """Fetches and displays a random question from the cache."""
        logger.info(f"Loading random question for {self.subject_name} - {self.level_key}")
        try:
            # --- This method needs to be implemented in CacheManager ---
            question_data = self.cache_manager.get_random_question(self.subject_name, self.level_key)
            # ---

            if question_data:
                self.current_question_data = question_data
                # Assuming question_data is a dictionary with 'question_text', 'question_id', etc.
                question_text = question_data.get('question_text', 'Error: Question text not found.')
                self.question_text_label.setText(question_text)
                self.answer_input.clear() # Clear previous answer
                # TODO: Load images if present in question_data
                logger.debug(f"Loaded question ID: {question_data.get('question_id')}")
            else:
                self.question_text_label.setText(f"No cached questions found for {self.subject_name} - {self._get_level_display_name(self.level_key)}.")
                self.answer_input.setEnabled(False) # Disable input if no question
                logger.warning(f"Failed to load random question for {self.subject_name} - {self.level_key}")

        except Exception as e:
            logger.error(f"Error loading question: {e}", exc_info=True)
            self.question_text_label.setText("Error loading question. Please try again.")

    # Placeholder - adapt key->name mapping as needed
    def _get_level_display_name(self, level_key):
        """Convert level key to display name"""
        display_names = {
            'grade_7': 'Grade 7',
            'o_level': 'O Level',
            'a_level': 'A Level'
        }
        return display_names.get(level_key, level_key.replace('_', ' ').title())

    # --- Placeholder for future implementation ---
    # def _submit_answer(self):
    #     if self.current_question_data:
    #         user_answer = self.answer_input.toPlainText()
    #         question_id = self.current_question_data.get('question_id')
    #         logger.info(f"Submitting answer for question {question_id}: {user_answer[:50]}...")
    #         # TODO: Add logic to save the answer, maybe trigger local AI feedback, etc.
    #         # After submitting, might want to load the next question or show feedback
    #         self.load_random_question() # Example: load next question after submit
