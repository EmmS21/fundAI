import logging
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, QScrollArea, QSizePolicy, QDialog)
from PySide6.QtGui import QPixmap, QImage, QFont, QGuiApplication
from PySide6.QtCore import Qt, Signal, QUrl
from src.data.cache.cache_manager import CacheManager
import os
import sys

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
        self.logger = logging.getLogger(__name__)

        self._setup_ui()
        self.load_random_question()

    def _setup_ui(self):
        """Set up the basic UI elements for the question view."""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)

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
        self.main_layout.addWidget(scroll_area, 1) # Give scroll area stretchy space

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
        # submit_button.clicked.connect(self._submit_answer) # TODO: Implement submit logic

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
        try:
            question_data = self.cache_manager.get_random_question(self.subject_name, self.level_key)
            self.logger.debug(f"Raw question data received: {question_data}")

            if question_data:
                self.current_question_data = question_data

                # --- Build formatted question text ---
                formatted_text = []

                # Get main text from top level (corrected)
                main_text = question_data.get('text')
                if not main_text:
                    main_text = question_data.get('question_text', '')
                if main_text:
                     formatted_text.append(main_text.strip())

                # Get sub-questions from top level (corrected)
                sub_questions = question_data.get('sub_questions', [])
                if sub_questions and isinstance(sub_questions, list):
                    if main_text: formatted_text.append("")
                    formatted_text.append("<b>Sub Questions:</b>")
                    for sq in sub_questions:
                         if isinstance(sq, dict):
                              marks_val = sq.get('marks')
                              marks_text = f" [{marks_val} marks]" if marks_val is not None else ""
                              sub_num_str = sq.get('sub_number', '?')
                              sub_text_str = sq.get('text', '')
                              sub_text = f"<b>{sub_num_str}</b>) {sub_text_str}{marks_text}"
                              formatted_text.append(sub_text)
                         else:
                              self.logger.warning(f"Skipping invalid sub_question item (not a dict): {sq}")

                # Add image descriptions from the TOP-LEVEL images list
                images = question_data.get('images', [])
                if images and any(img.get('description') for img in images if isinstance(img, dict)):
                    if main_text or sub_questions: formatted_text.append("")
                    formatted_text.append("<b>Diagrams:</b>")
                    for img in images:
                        if isinstance(img, dict) and img.get('description'):
                             label_part = f"{img.get('label', '')}: " if img.get('label') else ""
                             formatted_text.append(f"- {label_part}{img.get('description', '')}")

                # --- Set the text ---
                final_text_html = "<br>".join(formatted_text).strip()
                self.logger.debug(f"Formatted question text (length {len(final_text_html)}): {final_text_html[:300]}...")

                self.question_text_label.setTextFormat(Qt.RichText)
                self.question_text_label.setText(final_text_html)
                self.answer_input.clear()

                # --- RESTORED: UI update debugging logs ---
                self.logger.debug("Attempting to force UI updates and log state...")
                try: # Wrap debug code in try/except to prevent it crashing main logic
                    self.question_text_label.adjustSize()
                    container_widget = self.question_text_label.parentWidget()
                    if container_widget:
                         container_widget.adjustSize()
                         container_widget.update()
                    self.question_text_label.update()

                    label_size = self.question_text_label.size()
                    container_size = container_widget.size() if container_widget else "N/A"
                    # Find the QScrollArea parent more reliably
                    scroll_area = self.findChild(QScrollArea) # Check if findChild works as expected
                    if not scroll_area: # Fallback if findChild fails
                        scroll_area = self.question_text_label.parentWidget().parentWidget().parentWidget() # Example of traversing parents, adjust based on actual hierarchy
                        if not isinstance(scroll_area, QScrollArea):
                             scroll_area = None

                    scroll_area_size = scroll_area.size() if scroll_area else "N/A"
                    scroll_area_widget_size = scroll_area.widget().size() if scroll_area and scroll_area.widget() else "N/A"

                    self.logger.debug(f"--- UI State After setText ---")
                    self.logger.debug(f"QLabel size: {label_size}")
                    self.logger.debug(f"Container QWidget size: {container_size}")
                    self.logger.debug(f"ScrollArea size: {scroll_area_size}")
                    self.logger.debug(f"ScrollArea's Widget (question_container) size: {scroll_area_widget_size}")
                    self.logger.debug(f"QLabel visible: {self.question_text_label.isVisible()}")
                    self.logger.debug(f"Container visible: {container_widget.isVisible() if container_widget else 'N/A'}")
                    self.logger.debug(f"ScrollArea visible: {scroll_area.isVisible() if scroll_area else 'N/A'}")
                    self.logger.debug(f"--- End UI State ---")
                except Exception as debug_e:
                    self.logger.warning(f"Error during UI debug update/log: {debug_e}")
                # --- END RESTORED DEBUG BLOCK ---

                # --- Populate Image Links (Uses top-level images) ---
                self._clear_image_links()
                images = question_data.get('images', [])

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
