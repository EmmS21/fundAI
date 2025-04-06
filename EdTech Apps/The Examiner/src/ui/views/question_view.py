import logging
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, QScrollArea)
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
        self.question_text_label.setStyleSheet("font-size: 16px; padding: 10px; background-color: white; color: black;")
        question_layout.addWidget(self.question_text_label)
        question_layout.addStretch(1)
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
            question_data = self.cache_manager.get_random_question(self.subject_name, self.level_key)
            logger.debug(f"Raw question data received: {question_data}")

            if question_data:
                self.current_question_data = question_data
                
                # Build formatted question text
                formatted_text = []
                
                # Main question text
                main_text = question_data.get('text', '')
                formatted_text.append(main_text)
                
                # Get original question data which contains sub-questions
                original = question_data.get('original_question', {})
                
                # Add sub-questions with marks
                sub_questions = original.get('sub_questions', [])
                if sub_questions:
                    formatted_text.append("\nSub Questions:")
                    for sq in sub_questions:
                        sub_text = f"\n{sq['sub_number']}. {sq['text']} [{sq['marks']} marks]"
                        formatted_text.append(sub_text)
                
                # Add image descriptions if any
                images = original.get('images', [])
                if images:
                    formatted_text.append("\nDiagrams:")
                    for img in images:
                        formatted_text.append(f"- {img.get('description', '')}")
                
                # Join all parts and set the text
                final_text = "\n".join(formatted_text)
                logger.debug(f"Formatted question text: {final_text}")  # Debug log to verify formatting
                self.question_text_label.setText(final_text)
                self.answer_input.clear()

                # --- Add UI update debugging ---
                # Attempt to force layout recalculation and repaint
                self.question_text_label.adjustSize() 
                container_widget = self.question_text_label.parentWidget()
                if container_widget:
                     container_widget.adjustSize()
                     container_widget.update()
                self.question_text_label.update()
                
                # Log sizes and visibility after setting text
                label_size = self.question_text_label.size()
                container_size = container_widget.size() if container_widget else "N/A"
                # Find the QScrollArea parent more reliably
                scroll_area = self.findChild(QScrollArea) 
                scroll_area_size = scroll_area.size() if scroll_area else "N/A"
                scroll_area_widget_size = scroll_area.widget().size() if scroll_area and scroll_area.widget() else "N/A"

                logger.debug(f"--- UI State After setText ---")
                logger.debug(f"QLabel size: {label_size}")
                logger.debug(f"Container QWidget size: {container_size}")
                logger.debug(f"ScrollArea size: {scroll_area_size}")
                logger.debug(f"ScrollArea's Widget (question_container) size: {scroll_area_widget_size}")
                logger.debug(f"QLabel visible: {self.question_text_label.isVisible()}")
                logger.debug(f"Container visible: {container_widget.isVisible() if container_widget else 'N/A'}")
                logger.debug(f"ScrollArea visible: {scroll_area.isVisible() if scroll_area else 'N/A'}")
                logger.debug(f"--- End UI State ---")
                # --- End UI update debugging ---
                
            else:
                error_msg = f"No cached questions found for {self.subject_name} - {self._get_level_display_name(self.level_key)}."
                logger.warning(error_msg)
                self.question_text_label.setText(error_msg)
                self.answer_input.setEnabled(False)

        except Exception as e:
            logger.error(f"Error loading question: {e}", exc_info=True)
            self.question_text_label.setText(f"Error loading question: {str(e)}")

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
