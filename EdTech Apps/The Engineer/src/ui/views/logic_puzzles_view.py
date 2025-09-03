"""
Logic Puzzles View for The Engineer
Handles Python MCQ question sessions with progressive clues
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QProgressBar, QTextEdit, QButtonGroup, QRadioButton,
    QScrollArea, QGroupBox, QGridLayout, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QTimer, QThread
from PySide6.QtGui import QFont, QPixmap, QPainter, QPainterPath
import json
import time
import logging
from datetime import datetime
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from core.ai.logic_puzzles_prompts import create_question_generation_prompt, validate_generated_questions
from core.ai.groq_client import GroqProgrammingClient
from utils.hardware_identifier import HardwareIdentifier

logger = logging.getLogger(__name__)

class QuestionGenerationWorker(QThread):
    """Background worker for generating questions with AI"""
    
    questions_generated = Signal(list) 
    generation_failed = Signal(str)     
    
    def __init__(self, category_info, existing_questions, batch_size=10):
        super().__init__()
        self.category_info = category_info
        self.existing_questions = existing_questions
        self.batch_size = batch_size
        
    def run(self):
        """Generate questions in background thread"""
        try:
            # Create the prompt
            prompt = create_question_generation_prompt(
                category_name=self.category_info['name'],
                category_description=self.category_info['display_name'],
                difficulty_level=1,  # Start with beginner level
                batch_size=self.batch_size
            )
            
            # Add context about existing questions to avoid duplicates
            if self.existing_questions:
                existing_context = "\n\nEXISTING QUESTIONS TO AVOID DUPLICATING:\n"
                for i, q in enumerate(self.existing_questions[-5:]):  # Show last 5 questions
                    existing_context += f"{i+1}. {q.get('question_text', '')[:100]}...\n"
                prompt += existing_context
                prompt += "\nEnsure your new questions are completely different from the existing ones above."
            
            # Debug: Log the prompt being sent
            print(f"[DEBUG] Prompt length: {len(prompt)}")
            print(f"[DEBUG] Prompt preview: {prompt[:300]}...")
            
            groq_client = GroqProgrammingClient()
            response = groq_client.generate_response(prompt)
            
            # Debug: Log the full raw response
            print(f"[DEBUG] AI Response length: {len(response) if response else 0}")
            print(f"[DEBUG] Full AI Response:")
            print("=" * 80)
            print(response if response else 'EMPTY RESPONSE')
            print("=" * 80)
            
            if not response:
                self.generation_failed.emit("Failed to get response from AI")
                return
                
            if not response.strip():
                self.generation_failed.emit("AI returned empty response")
                return
            
            # Clean the response - remove thinking tags and extract JSON
            cleaned_response = self.extract_json_from_response(response)
            print(f"[DEBUG] Cleaned response length: {len(cleaned_response)}")
            print(f"[DEBUG] Full Cleaned Response:")
            print("-" * 80)
            print(cleaned_response)
            print("-" * 80)
                
            is_valid, questions, errors = validate_generated_questions(cleaned_response)            
            if not is_valid:
                print(f"[DEBUG] Validation failed!")
                print(f"[DEBUG] Validation errors: {errors}")
                error_msg = "AI response validation failed: " + "; ".join(errors)
                self.generation_failed.emit(error_msg)
                return
                
            if not questions:
                print(f"[DEBUG] No questions in validated response!")
                self.generation_failed.emit("No valid questions generated")
                return
            
            print(f"[DEBUG] Successfully generated {len(questions)} questions!")
            for i, q in enumerate(questions):
                print(f"[DEBUG] Question {i+1}: {q.get('question_text', 'NO TEXT')[:100]}...")
            
            self.questions_generated.emit(questions)
            
        except Exception as e:
            logger.error(f"Question generation failed: {e}")
            self.generation_failed.emit(f"Error generating questions: {str(e)}")
    
    def extract_json_from_response(self, response: str) -> str:
        """Extract JSON from AI response that may contain thinking tags or extra text"""
        import re
        
        # Remove thinking tags if present
        if '<think>' in response:
            # Extract everything after </think>
            think_end = response.find('</think>')
            if think_end != -1:
                response = response[think_end + 8:].strip()
        
        # Look for JSON array pattern
        json_match = re.search(r'\[.*\]', response, re.DOTALL)
        if json_match:
            return json_match.group(0)
        
        # Look for JSON between code blocks
        code_block_match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', response, re.DOTALL)
        if code_block_match:
            return code_block_match.group(1)
        
        # If no clear JSON found, return the original response
        return response

class QuestionWidget(QWidget):
    """Widget for displaying a single MCQ question with clues"""
    
    answer_submitted = Signal(str, int, list) 
    
    def __init__(self, question_data, question_number, total_questions):
        super().__init__()
        self.question_data = question_data
        self.question_number = question_number
        self.total_questions = total_questions
        self.start_time = time.time()
        self.clues_revealed = []
        
        # Debug: Log the question data being rendered
        print(f"[DEBUG] Rendering Question {question_number}:")
        print(f"[DEBUG] Question text: {question_data.get('question_text', 'MISSING')}")
        print(f"[DEBUG] Options: A={question_data.get('option_a', 'MISSING')}")
        print(f"[DEBUG] Code snippet: {question_data.get('code_snippet', 'MISSING')}")
        
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        progress_layout = QHBoxLayout()
        progress_label = QLabel(f"Question {self.question_number} of {self.total_questions}")
        progress_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: rgba(255, 255, 255, 0.7);
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }
        """)
        progress_layout.addWidget(progress_label)
        progress_layout.addStretch()
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(self.total_questions)
        self.progress_bar.setValue(self.question_number)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid rgba(255, 255, 255, 0.2);
                border-radius: 5px;
                background-color: rgba(255, 255, 255, 0.1);
                height: 8px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: rgba(100, 210, 255, 0.8);
                border-radius: 3px;
            }
        """)
        progress_layout.addWidget(self.progress_bar)
        layout.addLayout(progress_layout)
        question_container = QFrame()
        question_container.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
                padding: 20px;
            }
        """)
        question_layout = QVBoxLayout(question_container)
        
        # Question text
        question_text = QLabel(self.question_data['question_text'])
        question_text.setWordWrap(True)
        question_text.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: 600;
                color: rgba(255, 255, 255, 0.95);
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                margin-bottom: 15px;
                line-height: 1.4;
            }
        """)
        question_layout.addWidget(question_text)
        
        # Code snippet if present
        code_snippet = self.question_data.get('code_snippet', '')
        if code_snippet and code_snippet.lower() != 'none' and code_snippet.strip():
            code_container = QFrame()
            code_container.setStyleSheet("""
                QFrame {
                    background: rgba(0, 0, 0, 0.3);
                    border: 1px solid rgba(255, 255, 255, 0.2);
                    border-radius: 8px;
                    padding: 15px;
                    margin: 10px 0px;
                }
            """)
            code_layout = QVBoxLayout(code_container)
            
            code_label = QLabel("Code:")
            code_label.setStyleSheet("""
                QLabel {
                    font-size: 12px;
                    color: rgba(255, 255, 255, 0.6);
                    font-weight: 500;
                    margin-bottom: 5px;
                }
            """)
            code_layout.addWidget(code_label)
            
            code_text = QLabel(self.question_data['code_snippet'])
            code_text.setStyleSheet("""
                QLabel {
                    font-family: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, 'Courier New', monospace;
                    font-size: 14px;
                    color: rgba(255, 255, 255, 0.9);
                    background: transparent;
                    padding: 5px;
                    line-height: 1.5;
                }
            """)
            code_text.setWordWrap(True)
            code_layout.addWidget(code_text)
            question_layout.addWidget(code_container)
        
        layout.addWidget(question_container)
        
        # Answer options
        options_container = QFrame()
        options_container.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 10px;
                padding: 15px;
            }
        """)
        options_layout = QVBoxLayout(options_container)
        
        # Button group for radio buttons
        self.answer_group = QButtonGroup()
        
        # Create radio buttons for each option
        options = ['A', 'B', 'C', 'D']
        for option in options:
            option_text = self.question_data[f'option_{option.lower()}']
            
            radio_button = QRadioButton(f"{option}. {option_text}")
            radio_button.setWordWrap(True)
            radio_button.setStyleSheet("""
                QRadioButton {
                    font-size: 14px;
                    color: rgba(255, 255, 255, 0.9);
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    padding: 8px;
                    spacing: 10px;
                    min-height: 40px;
                }
                QRadioButton::indicator {
                    width: 18px;
                    height: 18px;
                    border-radius: 9px;
                    border: 2px solid rgba(255, 255, 255, 0.4);
                    background-color: transparent;
                }
                QRadioButton::indicator:checked {
                    background-color: rgba(100, 210, 255, 0.8);
                    border-color: rgba(100, 210, 255, 1.0);
                }
                QRadioButton::indicator:hover {
                    border-color: rgba(255, 255, 255, 0.6);
                }
            """)
            self.answer_group.addButton(radio_button, ord(option) - ord('A'))
            options_layout.addWidget(radio_button)
        
        layout.addWidget(options_container)
        
        # Clues section
        self.clues_container = QFrame()
        self.clues_container.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 10px;
                padding: 15px;
            }
        """)
        self.clues_layout = QVBoxLayout(self.clues_container)
        
        clues_title = QLabel("Need a hint?")
        clues_title.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: 600;
                color: rgba(255, 255, 255, 0.8);
                margin-bottom: 10px;
            }
        """)
        self.clues_layout.addWidget(clues_title)
        
        # Clue buttons
        self.clue_buttons = []
        for i in range(3):
            clue_button = QPushButton(f"Clue {i+1}")
            clue_button.setStyleSheet("""
                QPushButton {
                    font-size: 13px;
                    padding: 8px 15px;
                    border: 1px solid rgba(255, 255, 255, 0.3);
                    border-radius: 5px;
                    background-color: rgba(255, 255, 255, 0.1);
                    color: rgba(255, 255, 255, 0.8);
                    margin: 2px;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 0.2);
                    border-color: rgba(255, 255, 255, 0.5);
                }
                QPushButton:disabled {
                    background-color: rgba(255, 255, 255, 0.05);
                    border-color: rgba(255, 255, 255, 0.1);
                    color: rgba(255, 255, 255, 0.3);
                }
            """)
            clue_button.clicked.connect(lambda checked, idx=i: self.reveal_clue(idx))
            self.clue_buttons.append(clue_button)
            self.clues_layout.addWidget(clue_button)
        
        layout.addWidget(self.clues_container)
        
        # Submit button
        self.submit_button = QPushButton("Submit Answer")
        self.submit_button.setStyleSheet("""
            QPushButton {
                font-size: 16px;
                font-weight: 600;
                padding: 12px 30px;
                border: none;
                border-radius: 8px;
                background-color: rgba(100, 210, 255, 0.8);
                color: white;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }
            QPushButton:hover {
                background-color: rgba(100, 210, 255, 1.0);
            }
            QPushButton:disabled {
                background-color: rgba(255, 255, 255, 0.2);
                color: rgba(255, 255, 255, 0.5);
            }
        """)
        self.submit_button.clicked.connect(self.submit_answer)
        self.submit_button.setEnabled(False)  # Enable when answer is selected
        
        # Enable submit button when answer is selected
        self.answer_group.buttonClicked.connect(lambda: self.submit_button.setEnabled(True))
        
        layout.addWidget(self.submit_button)
        
    def reveal_clue(self, clue_index):
        """Reveal a clue and disable the button"""
        clue_key = f'clue_{clue_index + 1}'
        clue_text = self.question_data.get(clue_key, '')
        
        if clue_text and clue_index not in self.clues_revealed:
            self.clues_revealed.append(clue_index)
            
            # Add clue text
            clue_label = QLabel(f"💡 Clue {clue_index + 1}: {clue_text}")
            clue_label.setWordWrap(True)
            clue_label.setStyleSheet("""
                QLabel {
                    font-size: 13px;
                    color: rgba(255, 255, 255, 0.85);
                    background: rgba(100, 210, 255, 0.1);
                    border: 1px solid rgba(100, 210, 255, 0.3);
                    border-radius: 5px;
                    padding: 8px;
                    margin: 5px 0px;
                }
            """)
            self.clues_layout.addWidget(clue_label)
            
            # Disable the button
            self.clue_buttons[clue_index].setEnabled(False)
            self.clue_buttons[clue_index].setText(f"Clue {clue_index + 1} ✓")
    
    def submit_answer(self):
        """Submit the selected answer"""
        checked_button = self.answer_group.checkedButton()
        if not checked_button:
            return
            
        # Get selected answer
        button_id = self.answer_group.id(checked_button)
        selected_answer = chr(ord('A') + button_id)
        
        # Calculate time taken
        time_taken = int(time.time() - self.start_time)
        
        # Emit the answer
        self.answer_submitted.emit(selected_answer, time_taken, self.clues_revealed)

class CategorySelectionWidget(QWidget):
    """Widget for selecting a question category within the main window"""
    
    category_selected = Signal(dict)
    
    def __init__(self, categories, parent=None):
        super().__init__(parent)
        self.categories = categories
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Title
        title = QLabel("Choose Your Programming Challenge")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: rgba(255, 255, 255, 0.95);
                margin-bottom: 15px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }
        """)
        layout.addWidget(title)
        
        # Description
        desc = QLabel("Select a category to start your Python logic puzzles journey!")
        desc.setAlignment(Qt.AlignCenter)
        desc.setStyleSheet("""
            QLabel {
                font-size: 16px;
                color: rgba(255, 255, 255, 0.7);
                margin-bottom: 30px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }
        """)
        layout.addWidget(desc)
        
        # Categories grid
        categories_widget = QWidget()
        categories_layout = QGridLayout(categories_widget)
        categories_layout.setSpacing(15)
        
        for i, category in enumerate(self.categories):
            button = QPushButton()
            button.setMinimumHeight(100)
            
            # Add to button (we'll set the text and handle styling)
            button.setText(f"{category['display_name']}\n{category['description']}")
            button.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 255, 255, 0.05);
                    border: 2px solid rgba(255, 255, 255, 0.2);
                    border-radius: 12px;
                    color: rgba(255, 255, 255, 0.9);
                    font-size: 13px;
                    font-weight: 600;
                    padding: 15px;
                    text-align: center;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                }
                QPushButton:hover {
                    background: rgba(255, 255, 255, 0.1);
                    border-color: rgba(100, 210, 255, 0.8);
                    color: rgba(255, 255, 255, 1.0);
                }
                QPushButton:pressed {
                    background: rgba(255, 255, 255, 0.15);
                    border-color: rgba(100, 210, 255, 1.0);
                }
            """)
            
            button.clicked.connect(lambda checked, cat=category: self.select_category(cat))
            
            row = i // 3
            col = i % 3
            categories_layout.addWidget(button, row, col)
        
        layout.addWidget(categories_widget)
        
    def select_category(self, category):
        """Handle category selection"""
        self.category_selected.emit(category)

class LogicPuzzlesView(QWidget):
    """Main view for Logic Puzzles sessions"""
    
    def __init__(self, user_data, main_window):
        super().__init__()
        self.user_data = user_data
        self.main_window = main_window
        self.current_session = None
        self.current_questions = []
        self.current_question_index = 0
        self.session_answers = []
        self.background_worker = None
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Header with back button
        header_layout = QHBoxLayout()
        
        back_button = QPushButton("← Back to Dashboard")
        back_button.setStyleSheet("""
            QPushButton {
                font-size: 14px;
                padding: 8px 15px;
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 5px;
                background-color: rgba(255, 255, 255, 0.1);
                color: rgba(255, 255, 255, 0.9);
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.2);
            }
        """)
        back_button.clicked.connect(self.go_back_to_dashboard)
        header_layout.addWidget(back_button)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Main content area (will be replaced with questions)
        self.content_area = QWidget()
        self.content_layout = QVBoxLayout(self.content_area)
        layout.addWidget(self.content_area)
        
        # Start with category selection
        self.show_category_selection()
        
    def show_category_selection(self):
        """Show category selection screen"""
        # Clear content area
        self.clear_content_area()
        
        # Get categories from database
        categories = self.get_categories_from_db()
        
        # Show category selection widget
        category_widget = CategorySelectionWidget(categories, self)
        category_widget.category_selected.connect(self.start_session)
        self.content_layout.addWidget(category_widget)
        
    def get_categories_from_db(self):
        """Get available categories from database"""
        try:
            cursor = self.main_window.database.connection.cursor()
            cursor.execute("SELECT * FROM question_categories ORDER BY id")
            rows = cursor.fetchall()
            
            categories = []
            for row in rows:
                categories.append({
                    'id': row[0],
                    'name': row[1],
                    'display_name': row[2],
                    'description': row[3]
                })
            return categories
        except Exception as e:
            logger.error(f"Error fetching categories: {e}")
            return []
    
    def start_session(self, category):
        """Start a new question session"""
        try:
            # Create session in database
            cursor = self.main_window.database.connection.cursor()
            hardware_id = HardwareIdentifier.get_hardware_id()
            cursor.execute("""
                INSERT INTO question_sessions (
                    user_id, hardware_id, target_category_id, questions_per_session
                ) VALUES (?, ?, ?, ?)
            """, (
                self.user_data.get('id'),
                hardware_id,
                category['id'],
                10  # Default 10 questions per session
            ))
            
            session_id = cursor.lastrowid
            self.main_window.database.connection.commit()
            
            self.current_session = {
                'id': session_id,
                'category': category,
                'questions_answered': 0,
                'questions_correct': 0
            }
            
            # Get existing questions for this category (to avoid duplicates)
            existing_questions = self.get_existing_questions(category['id'])
            
            # Start background question generation
            self.start_question_generation(category, existing_questions)
            
            # Show loading screen
            self.show_loading_screen()
            
        except Exception as e:
            logger.error(f"Error starting session: {e}")
            QMessageBox.critical(self, "Error", f"Failed to start session: {str(e)}")
    
    def get_existing_questions(self, category_id):
        """Get existing questions for a category to avoid duplicates"""
        try:
            cursor = self.main_window.database.connection.cursor()
            cursor.execute("""
                SELECT question_text, code_snippet FROM logic_questions 
                WHERE category_id = ? AND is_active = 1
                ORDER BY created_at DESC LIMIT 20
            """, (category_id,))
            
            rows = cursor.fetchall()
            existing = []
            for row in rows:
                existing.append({
                    'question_text': row[0],
                    'code_snippet': row[1]
                })
            return existing
        except Exception as e:
            logger.error(f"Error fetching existing questions: {e}")
            return []
    
    def start_question_generation(self, category, existing_questions):
        """Start background question generation"""
        if self.background_worker and self.background_worker.isRunning():
            self.background_worker.quit()
            self.background_worker.wait()
        
        self.background_worker = QuestionGenerationWorker(
            category_info=category,
            existing_questions=existing_questions,
            batch_size=10
        )
        self.background_worker.questions_generated.connect(self.on_questions_generated)
        self.background_worker.generation_failed.connect(self.on_generation_failed)
        self.background_worker.start()
    
    def show_loading_screen(self):
        """Show loading screen while questions are being generated"""
        self.clear_content_area()
        
        loading_label = QLabel("Generating your Python puzzles...")
        loading_label.setAlignment(Qt.AlignCenter)
        loading_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: 600;
                color: rgba(255, 255, 255, 0.9);
                margin: 50px;
            }
        """)
        self.content_layout.addWidget(loading_label)
        
        # Animated dots
        self.loading_timer = QTimer()
        self.loading_dots = 0
        self.loading_timer.timeout.connect(self.update_loading_dots)
        self.loading_timer.start(500)
        self.loading_label = loading_label
    
    def update_loading_dots(self):
        """Update loading animation"""
        self.loading_dots = (self.loading_dots + 1) % 4
        dots = "." * self.loading_dots
        self.loading_label.setText(f"Generating your Python puzzles{dots}")
    
    def on_questions_generated(self, questions):
        """Handle successful question generation"""
        if hasattr(self, 'loading_timer'):
            self.loading_timer.stop()
        
        try:
            # Save questions to database
            self.save_questions_to_db(questions)
            
            # Start the quiz
            self.current_questions = questions
            self.current_question_index = 0
            self.session_answers = []
            self.show_next_question()
            
        except Exception as e:
            logger.error(f"Error processing generated questions: {e}")
            self.on_generation_failed(f"Failed to process questions: {str(e)}")
    
    def on_generation_failed(self, error_message):
        """Handle question generation failure"""
        if hasattr(self, 'loading_timer'):
            self.loading_timer.stop()
        
        logger.error(f"Question generation failed: {error_message}")
        QMessageBox.critical(self, "Generation Failed", 
                           f"Failed to generate questions: {error_message}\n\nPlease try again.")
        self.go_back_to_dashboard()
    
    def save_questions_to_db(self, questions):
        """Save generated questions to database"""
        cursor = self.main_window.database.connection.cursor()
        
        for question in questions:
            cursor.execute("""
                INSERT INTO logic_questions (
                    category_id, question_text, code_snippet, question_type,
                    difficulty_level, option_a, option_b, option_c, option_d,
                    correct_answer, clue_1, clue_2, clue_3, generated_by_ai,
                    ai_prompt_used, generation_batch_id, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                self.current_session['category']['id'],
                question['question_text'],
                question.get('code_snippet', ''),
                question.get('question_type', 'mcq'),
                question.get('difficulty_level', 1),
                question['option_a'],
                question['option_b'],
                question['option_c'],
                question['option_d'],
                question['correct_answer'],
                question['clue_1'],
                question['clue_2'],
                question['clue_3'],
                True,
                "logic_puzzles_prompt",
                f"session_{self.current_session['id']}",
                True
            ))
        
        self.main_window.database.connection.commit()
    
    def show_next_question(self):
        """Show the next question in the session"""
        print(f"[DEBUG] show_next_question called. Index: {self.current_question_index}, Total: {len(self.current_questions)}")
        
        if self.current_question_index >= len(self.current_questions):
            print(f"[DEBUG] No more questions, showing results")
            self.show_session_results()
            return
        
        self.clear_content_area()
        
        question_data = self.current_questions[self.current_question_index]
        print(f"[DEBUG] Creating QuestionWidget for question {self.current_question_index + 1}")
        
        question_widget = QuestionWidget(
            question_data, 
            self.current_question_index + 1, 
            len(self.current_questions)
        )
        question_widget.answer_submitted.connect(self.on_answer_submitted)
        
        self.content_layout.addWidget(question_widget)
        print(f"[DEBUG] QuestionWidget added to layout")
    
    def on_answer_submitted(self, selected_answer, time_taken, clues_used):
        """Handle answer submission"""
        question_data = self.current_questions[self.current_question_index]
        correct_answer = question_data['correct_answer']
        is_correct = selected_answer == correct_answer
        
        # Record the answer
        answer_record = {
            'question_data': question_data,
            'selected_answer': selected_answer,
            'correct_answer': correct_answer,
            'is_correct': is_correct,
            'time_taken': time_taken,
            'clues_used': clues_used
        }
        self.session_answers.append(answer_record)
        
        # Save to database
        self.save_answer_to_db(answer_record)
        
        # Update session stats
        if is_correct:
            self.current_session['questions_correct'] += 1
        self.current_session['questions_answered'] += 1
        
        # Move to next question
        self.current_question_index += 1
        
        # Show feedback briefly then continue
        self.show_answer_feedback(is_correct, correct_answer, question_data)
    
    def save_answer_to_db(self, answer_record):
        """Save user's answer to database"""
        try:
            cursor = self.main_window.database.connection.cursor()
            
            # Find the question ID
            cursor.execute("""
                SELECT id FROM logic_questions 
                WHERE question_text = ? AND category_id = ?
                ORDER BY created_at DESC LIMIT 1
            """, (
                answer_record['question_data']['question_text'],
                self.current_session['category']['id']
            ))
            
            row = cursor.fetchone()
            question_id = row[0] if row else None
            
            if question_id:
                cursor.execute("""
                    INSERT INTO question_responses (
                        session_id, user_id, question_id, selected_answer,
                        is_correct, time_taken, clues_used, clues_revealed,
                        question_order
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    self.current_session['id'],
                    self.user_data.get('id'),
                    question_id,
                    answer_record['selected_answer'],
                    answer_record['is_correct'],
                    answer_record['time_taken'],
                    len(answer_record['clues_used']),
                    json.dumps(answer_record['clues_used']),
                    self.current_question_index
                ))
                
                self.main_window.database.connection.commit()
                
        except Exception as e:
            logger.error(f"Error saving answer: {e}")
    
    def show_answer_feedback(self, is_correct, correct_answer, question_data):
        """Show brief feedback before next question"""
        self.clear_content_area()
        
        # Feedback container
        feedback_container = QFrame()
        feedback_container.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
                padding: 30px;
                margin: 50px;
            }
        """)
        feedback_layout = QVBoxLayout(feedback_container)
        
        # Result emoji and text
        if is_correct:
            result_text = "🎉 Correct!"
            result_color = "rgba(46, 204, 113, 1.0)"
        else:
            result_text = "❌ Not quite right"
            result_color = "rgba(231, 76, 60, 1.0)"
        
        result_label = QLabel(result_text)
        result_label.setAlignment(Qt.AlignCenter)
        result_label.setStyleSheet(f"""
            QLabel {{
                font-size: 24px;
                font-weight: bold;
                color: {result_color};
                margin-bottom: 15px;
            }}
        """)
        feedback_layout.addWidget(result_label)
        
        if not is_correct:
            correct_text = f"The correct answer was: {correct_answer}"
            correct_label = QLabel(correct_text)
            correct_label.setAlignment(Qt.AlignCenter)
            correct_label.setStyleSheet("""
                QLabel {
                    font-size: 16px;
                    color: rgba(255, 255, 255, 0.8);
                    margin-bottom: 10px;
                }
            """)
            feedback_layout.addWidget(correct_label)
        
        # Continue button
        continue_button = QPushButton("Continue")
        continue_button.setStyleSheet("""
            QPushButton {
                font-size: 16px;
                font-weight: 600;
                padding: 12px 30px;
                border: none;
                border-radius: 8px;
                background-color: rgba(100, 210, 255, 0.8);
                color: white;
                margin-top: 20px;
            }
            QPushButton:hover {
                background-color: rgba(100, 210, 255, 1.0);
            }
        """)
        continue_button.clicked.connect(self.show_next_question)
        feedback_layout.addWidget(continue_button)
        
        self.content_layout.addWidget(feedback_container)
        
        # Auto-continue after 3 seconds
        QTimer.singleShot(3000, self.show_next_question)
    
    def show_session_results(self):
        """Show final results of the session"""
        self.clear_content_area()
        
        # Calculate results
        total_questions = len(self.session_answers)
        correct_answers = sum(1 for ans in self.session_answers if ans['is_correct'])
        percentage = (correct_answers / total_questions * 100) if total_questions > 0 else 0
        
        # Update session in database
        try:
            cursor = self.main_window.database.connection.cursor()
            cursor.execute("""
                UPDATE question_sessions SET 
                    questions_answered = ?, questions_correct = ?, 
                    score_percentage = ?, status = 'completed',
                    completed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (total_questions, correct_answers, percentage, self.current_session['id']))
            self.main_window.database.connection.commit()
        except Exception as e:
            logger.error(f"Error updating session: {e}")
        
        # Results container
        results_container = QFrame()
        results_container.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
                padding: 40px;
                margin: 20px;
            }
        """)
        results_layout = QVBoxLayout(results_container)
        
        # Title
        title = QLabel("🎯 Session Complete!")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            QLabel {
                font-size: 28px;
                font-weight: bold;
                color: rgba(255, 255, 255, 0.95);
                margin-bottom: 20px;
            }
        """)
        results_layout.addWidget(title)
        
        # Score
        score_text = f"You got {correct_answers} out of {total_questions} questions correct!"
        score_label = QLabel(score_text)
        score_label.setAlignment(Qt.AlignCenter)
        score_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                color: rgba(255, 255, 255, 0.9);
                margin-bottom: 10px;
            }
        """)
        results_layout.addWidget(score_label)
        
        # Percentage
        percentage_label = QLabel(f"{percentage:.1f}%")
        percentage_label.setAlignment(Qt.AlignCenter)
        percentage_label.setStyleSheet("""
            QLabel {
                font-size: 36px;
                font-weight: bold;
                color: rgba(100, 210, 255, 1.0);
                margin: 20px 0px;
            }
        """)
        results_layout.addWidget(percentage_label)
        
        # Action buttons
        buttons_layout = QHBoxLayout()
        
        try_again_button = QPushButton("Try Another Category")
        try_again_button.setStyleSheet("""
            QPushButton {
                font-size: 16px;
                font-weight: 600;
                padding: 12px 24px;
                border: 2px solid rgba(100, 210, 255, 0.8);
                border-radius: 8px;
                background-color: transparent;
                color: rgba(100, 210, 255, 1.0);
                margin: 10px;
            }
            QPushButton:hover {
                background-color: rgba(100, 210, 255, 0.1);
            }
        """)
        try_again_button.clicked.connect(self.show_category_selection)
        buttons_layout.addWidget(try_again_button)
        
        dashboard_button = QPushButton("Back to Dashboard")
        dashboard_button.setStyleSheet("""
            QPushButton {
                font-size: 16px;
                font-weight: 600;
                padding: 12px 24px;
                border: none;
                border-radius: 8px;
                background-color: rgba(100, 210, 255, 0.8);
                color: white;
                margin: 10px;
            }
            QPushButton:hover {
                background-color: rgba(100, 210, 255, 1.0);
            }
        """)
        dashboard_button.clicked.connect(self.go_back_to_dashboard)
        buttons_layout.addWidget(dashboard_button)
        
        results_layout.addLayout(buttons_layout)
        self.content_layout.addWidget(results_container)
    
    def clear_content_area(self):
        """Clear the content area"""
        while self.content_layout.count():
            child = self.content_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
    
    def go_back_to_dashboard(self):
        """Return to the main dashboard"""
        # Signal to parent that we want to go back to dashboard
        # This should be handled by the main window or navigation system
        if hasattr(self.main_window, 'show_dashboard'):
            self.main_window.show_dashboard()
        else:
            # Fallback: replace central widget
            from ..dashboard_view import DashboardView
            dashboard = DashboardView(self.user_data, self.main_window)
            self.main_window.setCentralWidget(dashboard) 