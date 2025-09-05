"""
Simplified Question Widget for Logic Puzzles
Just 3 boxes: Code, Question, Options
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QButtonGroup, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QColor
from qfluentwidgets import RadioButton, FluentIcon, setCustomStyleSheet, ToolButton, ToolTip
import time

class SimpleQuestionWidget(QWidget):
    """Simplified widget with just 3 boxes: Code, Question, Options"""
    
    answer_submitted = Signal(str, int, list) 
    
    def __init__(self, question_data, question_number, total_questions, parent_view=None):
        super().__init__()
        self.question_data = question_data
        self.question_number = question_number
        self.total_questions = total_questions
        self.start_time = time.time()
        self.parent_view = parent_view  # Reference to LogicPuzzlesView
        
        # Clue tracking
        self.clues_used = 0
        self.max_clues = 2
        self.clues_revealed = []
        
        print(f"[DEBUG] Rendering Simple Question {question_number}: {question_data.get('question_text', 'MISSING')[:50]}...")
        print(f"[DEBUG] Option lengths: A={len(question_data.get('option_a', ''))}, B={len(question_data.get('option_b', ''))}, C={len(question_data.get('option_c', ''))}, D={len(question_data.get('option_d', ''))}")
        print(f"[DEBUG] Option A content: {question_data.get('option_a', 'MISSING')}")
        print(f"[DEBUG] Option B content: {question_data.get('option_b', 'MISSING')}")
        print(f"[DEBUG] Option C content: {question_data.get('option_c', 'MISSING')}")
        print(f"[DEBUG] Option D content: {question_data.get('option_d', 'MISSING')}")
        
        self.setup_ui()
        
    def setup_ui(self):
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        layout = QVBoxLayout(self)
        # Remove custom margins - let parent layout handle positioning
        layout.setContentsMargins(0, 20, 0, 20)  # Only vertical spacing, no horizontal margins
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
        
        # Box 2: Question Text with Help Icon
        question_container = QFrame()
        question_container.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 20px;
                min-height: 80px;
            }
        """)
        question_container_layout = QVBoxLayout(question_container)
        question_container_layout.setContentsMargins(0, 0, 0, 0)
        question_container_layout.setSpacing(10)
        
        # Container for revealed clues - positioned at the very top to overlay question
        self.clues_container = QVBoxLayout()
        question_container_layout.addLayout(self.clues_container)
        
        # Question header with text and help icon
        question_header = QHBoxLayout()
        question_header.setContentsMargins(0, 0, 0, 0)
        
        question_text = QLabel(self.question_data['question_text'])
        question_text.setWordWrap(True)
        question_text.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        question_text.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: 600;
                color: white;
                line-height: 1.4;
                background: transparent;
                border: none;
                padding: 0px;
            }
        """)
        question_header.addWidget(question_text)
        
        # Help icon for clues
        self.help_button = ToolButton(FluentIcon.HELP)
        self.help_button.setFixedSize(32, 32)
        self.help_button.clicked.connect(self.show_clue)
        self.update_help_button_state()
        question_header.addWidget(self.help_button, 0, Qt.AlignTop)
        
        question_container_layout.addLayout(question_header)
        
        # Update parent's clue status if available
        if self.parent_view and hasattr(self.parent_view, 'clue_status_label'):
            self.update_parent_clue_status()
        
        layout.addWidget(question_container)
        
        # Box 3: Clue Display (conditional - only when clues are revealed)
        self.clues_frame = QFrame()
        self.clues_frame.setStyleSheet("""
            QFrame {
                background: rgba(100, 210, 255, 0.1);
                border: 1px solid rgba(100, 210, 255, 0.3);
                border-radius: 8px;
                padding: 15px;
                margin: 10px 0px;
            }
        """)
        self.clues_layout = QVBoxLayout(self.clues_frame)
        self.clues_layout.setSpacing(10)
        layout.addWidget(self.clues_frame)
        self.clues_frame.hide()  # Hidden by default
        
        # Box 4: MCQ Options - responsive sizing, no fixed height
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
                    padding: 10px 6px;
                    min-height: 25px;
                }
            """)
            radio_button.setTextColor(QColor("white"), QColor("white"))
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
        
        # Emit the answer with clues used
        self.answer_submitted.emit(selected_answer, time_taken, self.clues_revealed)
    
    def show_clue(self):
        """Show the next available clue"""
        if self.clues_used >= self.max_clues:
            return
        
        # Disable button immediately to prevent multiple clicks
        self.help_button.setEnabled(False)
        
        # Get the next clue
        clue_key = f'clue_{self.clues_used + 1}'
        clue_text = self.question_data.get(clue_key, '')
        
        if not clue_text:
            # No more clues available
            return
        
        # Add clue to revealed list
        self.clues_revealed.append(self.clues_used)
        self.clues_used += 1
        
        # Add clue text and close button directly to the outer container
        clue_text_widget = QWidget()
        clue_text_layout = QHBoxLayout(clue_text_widget)
        clue_text_layout.setContentsMargins(0, 0, 0, 0)
        
        clue_label = QLabel(f"💡 Clue {self.clues_used}: {clue_text}")
        clue_label.setWordWrap(True)
        clue_label.setStyleSheet("""
            QLabel {
                font-size: 13px;
                color: rgba(255, 255, 255, 0.9);
                background: transparent;
                border: none;
            }
        """)
        clue_text_layout.addWidget(clue_label)
        
        # Close button for outer container
        close_button = QPushButton("×")
        close_button.setFixedSize(20, 20)
        close_button.setStyleSheet("""
            QPushButton {
                font-size: 14px;
                font-weight: bold;
                color: rgba(255, 255, 255, 0.8);
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 10px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.2);
                color: white;
            }
        """)
        close_button.clicked.connect(lambda: self.close_clues_container())
        clue_text_layout.addWidget(close_button, 0, Qt.AlignTop)
        
        # Add to clues frame and show it
        self.clues_layout.addWidget(clue_text_widget)
        self.clues_frame.show()
        
        # Make help button unclickable until container is closed
        self.help_button.setEnabled(False)
        
        # Update status
        self.update_parent_clue_status()
    
    def close_clues_container(self):
        """Close the entire clues container and re-enable help button"""
        self.clues_frame.hide()
        # Clear all clues from container
        while self.clues_layout.count():
            item = self.clues_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        # Re-enable help button
        self.update_help_button_state()
    
    def update_parent_clue_status(self):
        """Update the parent view's clue status label"""
        if self.parent_view and hasattr(self.parent_view, 'clue_status_label'):
            remaining = self.max_clues - self.clues_used
            status_text = f"Clues: {self.clues_used}/{self.max_clues} • {remaining} remaining"
            self.parent_view.clue_status_label.setText(status_text)
            self.parent_view.clue_status_label.show()
    
    def update_help_button_state(self):
        """Update help button appearance based on clues available"""
        if self.clues_used >= self.max_clues:
            self.help_button.setEnabled(False)
            self.help_button.setToolTip("No more clues available")
        else:
            self.help_button.setEnabled(True)
            remaining = self.max_clues - self.clues_used
            self.help_button.setToolTip(f"Click for a hint ({remaining} clue{'s' if remaining != 1 else ''} remaining)") 