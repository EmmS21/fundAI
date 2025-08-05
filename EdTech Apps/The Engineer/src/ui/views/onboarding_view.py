"""
The Engineer AI Tutor - Onboarding View
Engineering thinking assessment with pseudo code focus
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QTextEdit, QFrame, QProgressBar,
    QScrollArea
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

class OnboardingView(QWidget):
    """Engineering thinking assessment for young learners"""
    
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.current_question = 0
        self.answers = {}
        
        # Engineering thinking questions (pseudo code focused)
        self.questions = [
            {
                'id': 'problem_solving',
                'title': 'Breaking Down Problems',
                'question': """
Imagine you want to make a sandwich for lunch. 

How would you explain to a robot (step by step) how to make a peanut butter and jelly sandwich?

Think about EVERY small step - robots need very detailed instructions!
                """,
                'hint': "Think about: getting ingredients, opening jars, spreading, putting together..."
            },
            {
                'id': 'logical_thinking',
                'title': 'Logical Thinking',
                'question': """
You have a magic box that can sort things. 

If you put in a list of your friends' names, how would you tell the magic box to arrange them? What different ways could you sort them?

Describe at least 2 different ways to organize the list.
                """,
                'hint': "Think about: alphabetical order, height, age, birthday..."
            },
            {
                'id': 'pattern_recognition',
                'title': 'Finding Patterns',
                'question': """
Look at this sequence: 2, 4, 8, 16, 32, ?

What comes next? More importantly - can you explain WHY that's the pattern?

Now, if you had to teach someone else to recognize this type of pattern, what would you tell them to look for?
                """,
                'hint': "Think about: what's happening between each number? How would you describe the rule?"
            },
            {
                'id': 'system_thinking',
                'title': 'How Things Work Together',
                'question': """
Think about your school's library system.

Describe how you think the library keeps track of all the books and who has borrowed them. What would happen if someone returns a book late?

How would you design a simple system to help the librarian?
                """,
                'hint': "Think about: tracking, rules, what information is needed..."
            },
            {
                'id': 'debugging_mindset',
                'title': 'Finding and Fixing Problems',
                'question': """
Your friend says their phone "isn't working." 

What questions would you ask them to figure out what's wrong? List at least 5 questions you'd ask to understand the problem better.

How would you go about solving it step by step?
                """,
                'hint': "Think about: gathering information, testing ideas, checking obvious things first..."
            }
        ]
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the onboarding UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Header with progress
        header_layout = QHBoxLayout()
        
        # Title
        title = QLabel("Engineering Thinking Assessment")
        title.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #2c3e50;
            }
        """)
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Progress
        progress_label = QLabel("Question 1 of 5")
        progress_label.setStyleSheet("font-size: 14px; color: #7f8c8d;")
        header_layout.addWidget(progress_label)
        self.progress_label = progress_label
        
        layout.addLayout(header_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(len(self.questions))
        self.progress_bar.setValue(1)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                text-align: center;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #3498db;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        layout.addSpacing(20)
        
        # Question area (scrollable)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        question_widget = QWidget()
        self.question_layout = QVBoxLayout(question_widget)
        
        scroll_area.setWidget(question_widget)
        layout.addWidget(scroll_area)
        
        # Navigation buttons
        nav_layout = QHBoxLayout()
        
        self.back_button = QPushButton("← Previous")
        self.back_button.setStyleSheet("""
            QPushButton {
                font-size: 14px;
                padding: 10px 20px;
                border: 2px solid #95a5a6;
                border-radius: 5px;
                background-color: white;
                color: #2c3e50;
            }
            QPushButton:hover {
                background-color: #ecf0f1;
            }
            QPushButton:disabled {
                color: #bdc3c7;
                border-color: #ecf0f1;
            }
        """)
        self.back_button.clicked.connect(self.previous_question)
        self.back_button.setEnabled(False)
        nav_layout.addWidget(self.back_button)
        
        nav_layout.addStretch()
        
        self.next_button = QPushButton("Next →")
        self.next_button.setStyleSheet("""
            QPushButton {
                font-size: 14px;
                font-weight: bold;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
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
        
        # Load first question
        self.load_question()
    
    def load_question(self):
        """Load the current question"""
        # Clear previous question
        for i in reversed(range(self.question_layout.count())):
            self.question_layout.itemAt(i).widget().setParent(None)
        
        question = self.questions[self.current_question]
        
        # Question title
        title = QLabel(question['title'])
        title.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #2c3e50;
                margin-bottom: 10px;
            }
        """)
        self.question_layout.addWidget(title)
        
        # Question text
        question_text = QLabel(question['question'].strip())
        question_text.setWordWrap(True)
        question_text.setStyleSheet("""
            QLabel {
                font-size: 14px;
                line-height: 1.6;
                color: #2c3e50;
                background-color: #f8f9fa;
                border-radius: 8px;
                padding: 20px;
                margin-bottom: 15px;
            }
        """)
        self.question_layout.addWidget(question_text)
        
        # Hint
        hint = QLabel(f"💡 Hint: {question['hint']}")
        hint.setWordWrap(True)
        hint.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: #f39c12;
                font-style: italic;
                margin-bottom: 15px;
            }
        """)
        self.question_layout.addWidget(hint)
        
        # Answer area
        answer_label = QLabel("Your thoughts:")
        answer_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #2c3e50;")
        self.question_layout.addWidget(answer_label)
        
        self.answer_input = QTextEdit()
        self.answer_input.setPlaceholderText("Share your thinking here... There are no wrong answers!")
        self.answer_input.setMinimumHeight(150)
        self.answer_input.setStyleSheet("""
            QTextEdit {
                font-size: 14px;
                padding: 15px;
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                line-height: 1.5;
            }
            QTextEdit:focus {
                border-color: #3498db;
            }
        """)
        
        # Load previous answer if exists
        if question['id'] in self.answers:
            self.answer_input.setText(self.answers[question['id']])
        
        self.question_layout.addWidget(self.answer_input)
        
        # Update progress
        self.progress_label.setText(f"Question {self.current_question + 1} of {len(self.questions)}")
        self.progress_bar.setValue(self.current_question + 1)
        
        # Update buttons
        self.back_button.setEnabled(self.current_question > 0)
        
        if self.current_question == len(self.questions) - 1:
            self.next_button.setText("Finish Assessment")
        else:
            self.next_button.setText("Next →")
    
    def save_current_answer(self):
        """Save the current question's answer"""
        if hasattr(self, 'answer_input'):
            question_id = self.questions[self.current_question]['id']
            self.answers[question_id] = self.answer_input.toPlainText().strip()
    
    def previous_question(self):
        """Go to previous question"""
        self.save_current_answer()
        
        if self.current_question > 0:
            self.current_question -= 1
            self.load_question()
    
    def next_question(self):
        """Go to next question or finish assessment"""
        self.save_current_answer()
        
        if self.current_question < len(self.questions) - 1:
            self.current_question += 1
            self.load_question()
        else:
            self.finish_assessment()
    
    def finish_assessment(self):
        """Complete the assessment and get AI evaluation"""
        # Save all answers to database
        user_id = self.main_window.current_user['id']
        
        for question in self.questions:
            question_id = question['id']
            answer = self.answers.get(question_id, '')
            
            if answer:  # Only save non-empty answers
                self.main_window.db_manager.save_assessment_response(
                    user_id, question_id, question['question'], answer
                )
        
        # Show loading state
        self.show_evaluation_loading()
        
        # Get AI evaluation (async-like with timer)
        QTimer.singleShot(1000, self.get_ai_evaluation)
    
    def show_evaluation_loading(self):
        """Show loading screen while AI evaluates"""
        # Clear layout
        for i in reversed(range(self.question_layout.count())):
            self.question_layout.itemAt(i).widget().setParent(None)
        
        # Loading message
        loading_label = QLabel("🤖 AI is analyzing your responses...")
        loading_label.setAlignment(Qt.AlignCenter)
        loading_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                color: #3498db;
                margin: 50px;
            }
        """)
        self.question_layout.addWidget(loading_label)
        
        # Disable navigation
        self.next_button.setEnabled(False)
        self.back_button.setEnabled(False)
    
    def get_ai_evaluation(self):
        """Get AI evaluation of responses"""
        try:
            # Get evaluation from AI
            evaluation = self.main_window.ai_manager.evaluate_engineering_thinking(self.answers)
            
            # Save evaluation to database
            user_id = self.main_window.current_user['id']
            self.main_window.db_manager.update_user_assessment(user_id, evaluation)
            
            # Store in current user
            self.main_window.current_user.update(evaluation)
            
            # Show results
            self.show_evaluation_results(evaluation)
            
        except Exception as e:
            # Handle errors gracefully
            evaluation = {
                'level': 'beginner',
                'confidence': 0.5,
                'strengths': 'Shows good problem-solving potential',
                'areas_to_improve': 'Continue practicing logical thinking',
                'next_steps': 'Start with basic engineering concepts'
            }
            self.show_evaluation_results(evaluation)
    
    def show_evaluation_results(self, evaluation):
        """Show the evaluation results"""
        # Clear layout
        for i in reversed(range(self.question_layout.count())):
            self.question_layout.itemAt(i).widget().setParent(None)
        
        # Results title
        title = QLabel("Your Engineering Thinking Profile")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #2c3e50;
                margin-bottom: 20px;
            }
        """)
        self.question_layout.addWidget(title)
        
        # Level
        level_text = evaluation.get('level', 'beginner').title()
        level_label = QLabel(f"Your Level: {level_text}")
        level_label.setAlignment(Qt.AlignCenter)
        level_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #3498db;
                background-color: #ecf0f1;
                border-radius: 8px;
                padding: 15px;
                margin-bottom: 20px;
            }
        """)
        self.question_layout.addWidget(level_label)
        
        # Strengths
        strengths_frame = self.create_result_section("🌟 Your Strengths", evaluation.get('strengths', ''))
        self.question_layout.addWidget(strengths_frame)
        
        # Areas to improve
        improve_frame = self.create_result_section("🎯 Areas to Develop", evaluation.get('areas_to_improve', ''))
        self.question_layout.addWidget(improve_frame)
        
        # Next steps
        next_frame = self.create_result_section("🚀 Your Learning Path", evaluation.get('next_steps', ''))
        self.question_layout.addWidget(next_frame)
        
        # Continue button
        continue_button = QPushButton("Continue to Dashboard")
        continue_button.setStyleSheet("""
            QPushButton {
                font-size: 16px;
                font-weight: bold;
                color: white;
                background-color: #27ae60;
                border: none;
                border-radius: 8px;
                padding: 15px 30px;
                margin-top: 20px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        continue_button.clicked.connect(self.main_window.show_dashboard)
        self.question_layout.addWidget(continue_button)
        
        # Hide navigation
        self.next_button.hide()
        self.back_button.hide()
    
    def create_result_section(self, title, content):
        """Create a result section frame"""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border-radius: 8px;
                padding: 15px;
                margin-bottom: 15px;
            }
        """)
        
        layout = QVBoxLayout(frame)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #2c3e50;
                margin-bottom: 10px;
            }
        """)
        layout.addWidget(title_label)
        
        content_label = QLabel(content)
        content_label.setWordWrap(True)
        content_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #2c3e50;
                line-height: 1.5;
            }
        """)
        layout.addWidget(content_label)
        
        return frame 