"""
Simplified Question Widget for Logic Puzzles
Just 3 boxes: Code, Question, Options
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, 
    QFrame, QButtonGroup, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon
from qfluentwidgets import RadioButton, FluentIcon, setCustomStyleSheet
import time

class SimpleQuestionWidget(QWidget):
    """Simplified widget with just 3 boxes: Code, Question, Options"""
    
    answer_submitted = Signal(str, int, list) 
    
    def __init__(self, question_data, question_number, total_questions):
        super().__init__()
        self.question_data = question_data
        self.question_number = question_number
        self.total_questions = total_questions
        self.start_time = time.time()
        
        print(f"[DEBUG] Rendering Simple Question {question_number}: {question_data.get('question_text', 'MISSING')[:50]}...")
        
        self.setup_ui()
        
    def setup_ui(self):
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # Box 1: Code Snippet (if present)
        code_snippet = self.question_data.get('code_snippet', '')
        if code_snippet and code_snippet.lower() != 'none' and code_snippet.strip():
            code_frame = QFrame()
            code_frame.setStyleSheet("""
                QFrame {
                    background: rgba(0, 0, 0, 0.4);
                    border: 1px solid rgba(255, 255, 255, 0.2);
                    border-radius: 8px;
                    padding: 20px;
                    min-height: 100px;
                }
            """)
            code_layout = QVBoxLayout(code_frame)
            
            code_text = QLabel(code_snippet)
            code_text.setWordWrap(True)
            code_text.setStyleSheet("""
                QLabel {
                    font-family: 'Courier New', monospace;
                    font-size: 14px;
                    color: white;
                    line-height: 1.5;
                }
            """)
            code_layout.addWidget(code_text)
            layout.addWidget(code_frame)
        
        # Box 2: Question Text - direct label, no unnecessary container
        question_text = QLabel(self.question_data['question_text'])
        question_text.setWordWrap(True)
        question_text.setAlignment(Qt.AlignLeft | Qt.AlignTop)  # Force consistent alignment
        question_text.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: 600;
                color: white;
                line-height: 1.4;
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 20px;
                min-height: 80px;
            }
        """)
        layout.addWidget(question_text)
        
        # Box 3: MCQ Options - responsive sizing, no fixed height
        options_frame = QFrame()
        options_frame.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.03);
                border: 2px solid rgba(255, 255, 255, 0.2);
                border-radius: 10px;
                padding: 20px;
                margin-bottom: 15px;
            }
        """)
        options_layout = QVBoxLayout(options_frame)
        options_layout.setSpacing(8)  
        options_layout.setContentsMargins(0, 0, 0, 0)  # Remove layout margins, use pure padding 
        
        self.answer_group = QButtonGroup()
        
        options = ['A', 'B', 'C', 'D']
        for option in options:
            option_text = self.question_data[f'option_{option.lower()}']
            
            # Create QFluentWidgets RadioButton
            radio_button = RadioButton(f"{option}. {option_text}")
            radio_button.setStyleSheet("""
                RadioButton {
                    font-size: 13px;
                    color: white;
                    padding: 10px 6px;
                    min-height: 25px;
                }
            """)
            setCustomStyleSheet(radio_button, "margin-left: 5px;", "margin-left: 5px;")
            
            self.answer_group.addButton(radio_button, ord(option) - ord('A'))
            options_layout.addWidget(radio_button)
        
        # Add stretch to options layout to distribute space evenly
        options_layout.addStretch()
        
        layout.addWidget(options_frame, 1)  # Give MCQ box flexible space to prevent squashing
        
        # Add stretch to push submit button to bottom but keep separation
        layout.addStretch()
        
        # Submit button directly in layout - no unnecessary container
        self.submit_button = QPushButton("Submit Answer")
        self.submit_button.setStyleSheet("""
            QPushButton {
                font-size: 18px;
                font-weight: 600;
                padding: 18px;
                border: none;
                border-radius: 10px;
                background-color: rgba(100, 210, 255, 0.8);
                color: white;
                min-height: 20px;
                margin-top: 20px;
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
        self.submit_button.setEnabled(False)
        
        # Enable submit button when answer is selected and show success icon
        self.answer_group.buttonClicked.connect(self.on_answer_selected)
        
        layout.addWidget(self.submit_button)
    
    def on_answer_selected(self, button):
        """Handle answer selection - enable submit button and show success icon"""
        self.submit_button.setEnabled(True)
        
        # Clear all icons first
        for btn in self.answer_group.buttons():
            btn.setIcon(QIcon())  # Empty QIcon to clear
        
        # Convert FluentIcon to QIcon using .icon() method
        button.setIcon(FluentIcon.ACCEPT.icon())
        
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
        
        # Emit the answer (no clues in simplified version)
        self.answer_submitted.emit(selected_answer, time_taken, []) 