from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QCheckBox, QFrame, QProgressBar, QScrollArea, QButtonGroup
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from src.core.questions import ENGINEERING_QUESTIONS, QUESTION_SECTIONS, get_random_questions

class AssessmentView(QWidget):
    assessment_completed = Signal(dict)
    
    def __init__(self):
        super().__init__()
        self.questions = get_random_questions(15)
        self.current_question = 0
        self.answers = {}
        self.setup_ui()
        self.load_question()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 20, 30, 20)
        
        # Header
        header = QLabel("Engineering Thinking Assessment")
        header.setStyleSheet("""
            QLabel {
                font-size: 28px;
                font-weight: bold;
                color: #2c3e50;
                margin-bottom: 10px;
            }
        """)
        layout.addWidget(header)
        
        # Progress section
        progress_layout = QHBoxLayout()
        
        progress_label = QLabel("Question 1 of 15")
        progress_label.setStyleSheet("font-size: 14px; color: #7f8c8d;")
        self.progress_label = progress_label
        progress_layout.addWidget(progress_label)
        
        progress_layout.addStretch()
        
        section_label = QLabel("🔍 Problem Solving & Debugging")
        section_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #3498db;")
        self.section_label = section_label
        progress_layout.addWidget(section_label)
        
        layout.addLayout(progress_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(15)
        self.progress_bar.setValue(1)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                text-align: center;
                height: 25px;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3498db, stop:1 #2980b9);
                border-radius: 6px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        layout.addSpacing(20)
        
        # Question area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)
        
        self.question_widget = QWidget()
        self.question_layout = QVBoxLayout(self.question_widget)
        
        scroll_area.setWidget(self.question_widget)
        layout.addWidget(scroll_area)
        
        # Navigation
        nav_layout = QHBoxLayout()
        
        self.prev_button = QPushButton("← Previous")
        self.prev_button.setStyleSheet("""
            QPushButton {
                font-size: 14px;
                padding: 12px 24px;
                border: 2px solid #95a5a6;
                border-radius: 8px;
                background-color: white;
                color: #2c3e50;
            }
            QPushButton:hover {
                background-color: #ecf0f1;
                border-color: #7f8c8d;
            }
            QPushButton:disabled {
                color: #bdc3c7;
                border-color: #ecf0f1;
            }
        """)
        self.prev_button.clicked.connect(self.previous_question)
        self.prev_button.setEnabled(False)
        nav_layout.addWidget(self.prev_button)
        
        nav_layout.addStretch()
        
        self.next_button = QPushButton("Next →")
        self.next_button.setStyleSheet("""
            QPushButton {
                font-size: 14px;
                font-weight: bold;
                padding: 12px 24px;
                border: none;
                border-radius: 8px;
                background-color: #3498db;
                color: white;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        self.next_button.clicked.connect(self.next_question)
        nav_layout.addWidget(self.next_button)
        
        layout.addLayout(nav_layout)
    
    def load_question(self):
        # Clear previous question
        for i in reversed(range(self.question_layout.count())):
            self.question_layout.itemAt(i).widget().setParent(None)
        
        question = self.questions[self.current_question]
        
        # Section header
        section_info = QUESTION_SECTIONS[question['section']]
        section_frame = QFrame()
        section_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3498db, stop:1 #2980b9);
                border-radius: 8px;
                margin-bottom: 20px;
            }
        """)
        
        section_layout = QVBoxLayout(section_frame)
        section_layout.setContentsMargins(20, 15, 20, 15)
        
        section_title = QLabel(f"{section_info['icon']} {question['section']}")
        section_title.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 16px;
                font-weight: bold;
            }
        """)
        section_layout.addWidget(section_title)
        
        section_desc = QLabel(section_info['description'])
        section_desc.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.9);
                font-size: 12px;
            }
        """)
        section_layout.addWidget(section_desc)
        
        self.question_layout.addWidget(section_frame)
        
        # Question
        question_frame = QFrame()
        question_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border-radius: 12px;
                padding: 25px;
                margin-bottom: 20px;
            }
        """)
        
        question_layout = QVBoxLayout(question_frame)
        
        question_text = QLabel(question['question'])
        question_text.setWordWrap(True)
        question_text.setStyleSheet("""
            QLabel {
                font-size: 16px;
                line-height: 1.6;
                color: #2c3e50;
                margin-bottom: 20px;
            }
        """)
        question_layout.addWidget(question_text)
        
        # Instructions
        instructions = QLabel("Select all that apply. Multiple answers may be correct.")
        instructions.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: #e67e22;
                font-style: italic;
                margin-bottom: 15px;
            }
        """)
        question_layout.addWidget(instructions)
        
        # Options
        self.option_checkboxes = []
        for i, option in enumerate(question['options']):
            checkbox = QCheckBox(option)
            checkbox.setStyleSheet("""
                QCheckBox {
                    font-size: 14px;
                    color: #2c3e50;
                    padding: 8px;
                    spacing: 10px;
                }
                QCheckBox::indicator {
                    width: 18px;
                    height: 18px;
                    border-radius: 9px;
                    border: 2px solid #bdc3c7;
                }
                QCheckBox::indicator:checked {
                    background-color: #3498db;
                    border-color: #3498db;
                }
                QCheckBox::indicator:hover {
                    border-color: #3498db;
                }
            """)
            
            # Load previous answer if exists
            if question['id'] in self.answers:
                if i in self.answers[question['id']]:
                    checkbox.setChecked(True)
            
            self.option_checkboxes.append(checkbox)
            question_layout.addWidget(checkbox)
        
        self.question_layout.addWidget(question_frame)
        
        # Difficulty indicator
        difficulty_frame = QFrame()
        difficulty_frame.setStyleSheet("""
            QFrame {
                background-color: #ecf0f1;
                border-radius: 6px;
                padding: 10px;
            }
        """)
        
        difficulty_layout = QHBoxLayout(difficulty_frame)
        
        difficulty_label = QLabel(f"Difficulty: {question['difficulty'].title()}")
        difficulty_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: #7f8c8d;
                font-weight: bold;
            }
        """)
        difficulty_layout.addWidget(difficulty_label)
        
        difficulty_layout.addStretch()
        
        question_num = QLabel(f"Question {self.current_question + 1}")
        question_num.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: #7f8c8d;
            }
        """)
        difficulty_layout.addWidget(question_num)
        
        self.question_layout.addWidget(difficulty_frame)
        
        # Update progress
        self.progress_label.setText(f"Question {self.current_question + 1} of 15")
        self.progress_bar.setValue(self.current_question + 1)
        
        section_display = f"{section_info['icon']} {question['section']}"
        self.section_label.setText(section_display)
        
        # Update buttons
        self.prev_button.setEnabled(self.current_question > 0)
        
        if self.current_question == len(self.questions) - 1:
            self.next_button.setText("Finish Assessment")
        else:
            self.next_button.setText("Next →")
    
    def save_current_answer(self):
        if hasattr(self, 'option_checkboxes'):
            question = self.questions[self.current_question]
            selected = []
            
            for i, checkbox in enumerate(self.option_checkboxes):
                if checkbox.isChecked():
                    selected.append(i)
            
            self.answers[question['id']] = selected
    
    def previous_question(self):
        self.save_current_answer()
        
        if self.current_question > 0:
            self.current_question -= 1
            self.load_question()
    
    def next_question(self):
        self.save_current_answer()
        
        if self.current_question < len(self.questions) - 1:
            self.current_question += 1
            self.load_question()
        else:
            self.finish_assessment()
    
    def finish_assessment(self):
        # Calculate scores
        results = self.calculate_scores()
        self.assessment_completed.emit(results)
    
    def calculate_scores(self):
        total_correct = 0
        total_possible = 0
        section_scores = {}
        
        for question in self.questions:
            question_id = question['id']
            correct_answers = set(question['correct'])
            user_answers = set(self.answers.get(question_id, []))
            
            # Calculate score for this question
            if user_answers == correct_answers:
                score = 1.0  # Perfect
            elif user_answers.issubset(correct_answers) and len(user_answers) > 0:
                score = len(user_answers) / len(correct_answers)  # Partial credit
            elif user_answers.intersection(correct_answers):
                # Some correct, some wrong - negative marking
                correct_selected = len(user_answers.intersection(correct_answers))
                wrong_selected = len(user_answers - correct_answers)
                score = max(0, (correct_selected - wrong_selected) / len(correct_answers))
            else:
                score = 0  # All wrong or no answer
            
            total_correct += score
            total_possible += 1
            
            # Section scoring
            section = question['section']
            if section not in section_scores:
                section_scores[section] = {'correct': 0, 'total': 0}
            section_scores[section]['correct'] += score
            section_scores[section]['total'] += 1
        
        overall_percentage = (total_correct / total_possible) * 100 if total_possible > 0 else 0
        
        return {
            'overall_score': overall_percentage,
            'section_scores': section_scores,
            'total_questions': len(self.questions),
            'answers': self.answers
        } 