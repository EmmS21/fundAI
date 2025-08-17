"""
The Engineer AI Tutor - Project Wizard View
Wizard to guide users through AI-assisted project creation
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QScrollArea, QButtonGroup, QRadioButton, QTextEdit, QProgressBar,
    QTextBrowser
)
from PySide6.QtCore import Qt, Signal, QThread, QTimer
from PySide6.QtGui import QFont
from core.ai.project_generator import ProjectGenerator
import re
import logging

logger = logging.getLogger(__name__)

# Import database operations
from data.database.operations import db_manager, ProjectOperations

class ProjectGenerationWorker(QThread):
    """Worker thread for generating projects using AI"""
    
    project_generated = Signal(str)  # Emits generated project description
    generation_failed = Signal(str)  # Emits error message
    
    def __init__(self, user_scores, selected_language, user_data, use_local_only=False):
        super().__init__()
        self.user_scores = user_scores
        self.selected_language = selected_language
        self.user_data = user_data
        self.use_local_only = use_local_only
    
    def run(self):
        """Run project generation in background thread"""
        try:
            generator = ProjectGenerator()
            
            if not generator.is_available():
                self.generation_failed.emit("No AI services available for project generation")
                return
            
            project_description = generator.generate_project(
                self.user_scores, 
                self.selected_language, 
                self.user_data,
                self.use_local_only
            )
            
            if project_description:
                self.project_generated.emit(project_description)
            else:
                self.generation_failed.emit("Failed to generate project. Please try again.")
                
        except Exception as e:
            self.generation_failed.emit(f"Error generating project: {str(e)}")

class TaskHeadersWorker(QThread):
    """Worker thread for generating task headers using AI"""
    
    headers_generated = Signal(str)  # Emits generated task headers
    headers_failed = Signal(str)     # Emits error message
    
    def __init__(self, project_description, selected_language, use_local_only=False):
        super().__init__()
        self.project_description = project_description
        self.selected_language = selected_language
        self.use_local_only = use_local_only
    
    def run(self):
        """Run task headers generation in background thread"""
        try:
            generator = ProjectGenerator()
            
            if not generator.is_available():
                self.headers_failed.emit("No AI services available for task headers")
                return
            
            task_headers = generator.generate_task_headers(
                self.project_description,
                self.selected_language,
                self.use_local_only
            )
            
            if task_headers:
                self.headers_generated.emit(task_headers)
            else:
                self.headers_failed.emit("Failed to generate task headers. Please try again.")
                
        except Exception as e:
            self.headers_failed.emit(f"Error generating task headers: {str(e)}")

class TaskDetailWorker(QThread):
    """Worker thread for generating individual task details using AI"""
    
    detail_generated = Signal(int, str, str)  # Emits task_number, task_name, task_detail
    detail_failed = Signal(int, str, str)     # Emits task_number, task_name, error_message
    
    def __init__(self, task_name, task_number, project_description, selected_language, use_local_only=False):
        super().__init__()
        self.task_name = task_name
        self.task_number = task_number
        self.project_description = project_description
        self.selected_language = selected_language
        self.use_local_only = use_local_only
    
    def run(self):
        """Run task detail generation in background thread"""
        try:
            generator = ProjectGenerator()
            
            if not generator.is_available():
                self.detail_failed.emit(self.task_number, self.task_name, "No AI services available")
                return
            
            task_detail = generator.generate_task_detail(
                self.task_name,
                self.task_number,
                self.project_description,
                self.selected_language,
                self.use_local_only
            )
            
            if task_detail:
                self.detail_generated.emit(self.task_number, self.task_name, task_detail)
            else:
                self.detail_failed.emit(self.task_number, self.task_name, "Failed to generate task details")
                
        except Exception as e:
            self.detail_failed.emit(self.task_number, self.task_name, f"Error: {str(e)}")

class ProjectWizardView(QWidget):
    """Wizard for setting up AI-assisted project building"""
    
    project_started = Signal(dict)  
    
    def __init__(self, user_data, main_window):
        super().__init__()
        self.user_data = user_data
        self.main_window = main_window
        self.current_step = 0
        self.project_config = {}
        
        # Initialize database operations
        self.project_ops = ProjectOperations(db_manager)
        self.current_project_id = None
        
        # Check for existing active project
        self.check_existing_project()
        
        self.setup_ui()
    
    def check_existing_project(self):
        """Check if user has an existing active project"""
        if not self.user_data or not self.user_data.get('id'):
            return
        
        existing_project = self.project_ops.get_active_project(self.user_data['id'])
        if existing_project:
            self.current_project_id = existing_project['id']
            self.project_config = existing_project
            # Don't set current_step = 2, always start with introduction
            self.current_task_number = existing_project['current_task_number']
            self.task_names = existing_project['task_names']
            logger.info(f"Loaded existing project: {existing_project['title']}")
    
    def show_existing_project_task(self):
        """Show the current task for an existing project"""
        if not hasattr(self, 'current_task_number') or not self.task_names:
            self.show_introduction()
            return
        
        # Check if we have task details for current task
        current_task_name = self.task_names[self.current_task_number - 1]
        current_task_detail = self.project_config.get('task_details', {}).get(self.current_task_number)
        
        if current_task_detail:
            # Show the complete task
            self.show_complete_current_task(current_task_name, current_task_detail)
        else:
            # Generate the current task details
            self.generate_and_show_current_task()
    
    def save_project_to_database(self):
        """Save current project to database"""
        if not self.user_data or not self.user_data.get('id'):
            return None
        
        # Extract title from project description
        project_lines = self.project_config.get('project_description', '').split('\n')
        title = 'AI Generated Project'
        for line in project_lines:
            if 'Project Title' in line or 'Title' in line:
                title = line.split(':')[-1].strip() if ':' in line else line.strip()
                break
        
        project_data = {
            'title': title,
            'description': self.project_config.get('project_description', ''),
            'language': self.project_config.get('language', 'Python'),
            'difficulty_level': 'junior',  # Default
            'domain': 'software',  # Default
            'project_description': self.project_config.get('project_description', ''),
            'task_headers': self.project_config.get('task_headers', ''),
            'task_names': self.task_names if hasattr(self, 'task_names') else [],
            'task_details': self.project_config.get('task_details', {}),
            'current_task_number': self.current_task_number if hasattr(self, 'current_task_number') else 1,
            'user_scores': self.project_config.get('user_scores', {})
        }
        
        if self.current_project_id:
            # Update existing project
            self.project_ops.update_project_progress(
                self.current_project_id, 
                self.current_task_number,
                self.project_config.get('task_details', {})
            )
        else:
            # Save new project
            self.current_project_id = self.project_ops.save_project(
                self.user_data['id'], 
                project_data
            )
        
        return self.current_project_id
    
    def add_skip_project_button(self, layout):
        """Add a skip project button to allow starting fresh"""
        skip_button = QPushButton("🔄 Start New Project")
        skip_button.setStyleSheet("""
            QPushButton {
                font-size: 14px;
                color: rgba(255, 255, 255, 0.8);
                background-color: transparent;
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 8px;
                padding: 10px 20px;
                margin-top: 20px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
        """)
        skip_button.clicked.connect(self.skip_current_project)
        layout.addWidget(skip_button)
    
    def skip_current_project(self):
        """Skip current project and start fresh"""
        if self.current_project_id:
            self.project_ops.skip_project(self.current_project_id)
        
        # Reset state
        self.current_project_id = None
        self.project_config = {}
        self.current_step = 0
        self.current_task_number = 1
        
        # Show introduction again
        self.show_introduction()
    
    def setup_ui(self):
        """Setup the wizard UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(30)
        
        # Header
        self.create_header(layout)
        
        # Content area with scroll
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background-color: rgba(255, 255, 255, 0.1);
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background-color: rgba(255, 255, 255, 0.3);
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: rgba(255, 255, 255, 0.5);
            }
        """)
        
        self.content_area = QFrame()
        self.content_area.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.05);
                border-radius: 15px;
                padding: 30px;
            }
        """)
        
        self.scroll_area.setWidget(self.content_area)
        layout.addWidget(self.scroll_area)
        
        # Navigation buttons
        self.create_navigation(layout)
        
        # Initialize state
        self.showing_timer = False
        
        # Create persistent elements
        self.create_persistent_elements()
        
        
        # Show appropriate step based on existing project
        if self.current_step == 2 and hasattr(self, 'task_names') and self.task_names:
            # User has existing project, show current task
            self.show_existing_project_task()
        else:
            # Show first step
            self.show_introduction()
    
    def create_header(self, layout):
        """Create wizard header"""
        header_layout = QVBoxLayout()
        
        title = QLabel("AI Project Tutor")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            QLabel {
                font-size: 32px;
                font-weight: 700;
                color: rgba(255, 255, 255, 0.95);
                margin-bottom: 10px;
            }
        """)
        header_layout.addWidget(title)
        
        subtitle = QLabel("Learn to code by building real projects")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("""
            QLabel {
                font-size: 16px;
                color: rgba(255, 255, 255, 0.7);
                margin-bottom: 20px;
            }
        """)
        header_layout.addWidget(subtitle)
        
        layout.addLayout(header_layout)
    
    def create_persistent_elements(self):
        """Create simple timer that will replace empty content area"""
        # Just a timer - nothing else
        self.timer_label = QLabel("Time elapsed: 00:00")
        self.timer_label.setAlignment(Qt.AlignCenter)
        self.timer_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                color: rgba(255, 255, 255, 0.8);
                padding: 40px;
            }
        """)
        
        # Rich text browser for project content - will hold AI output with proper formatting
        self.project_content = QTextBrowser()
        self.project_content.setReadOnly(True)
        self.project_content.setOpenExternalLinks(False)
        self.project_content.setStyleSheet("""
            QTextBrowser {
                font-size: 14px;
                line-height: 1.6;
                color: rgba(255, 255, 255, 0.9);
                background-color: transparent;
                border: none;
                padding: 20px;
            }
            QTextBrowser b {
                color: rgba(255, 255, 255, 1.0);
                font-size: 16px;
                font-weight: bold;
            }
            QTextBrowser i {
                color: rgba(255, 255, 255, 0.8);
                font-style: italic;
            }
            QTextBrowser pre {
                background-color: rgba(0, 0, 0, 0.3);
                border-radius: 5px;
                padding: 10px;
                font-family: 'Courier New', monospace;
                color: rgba(255, 255, 255, 0.95);
            }
            QTextBrowser ul {
                margin-left: 20px;
                margin-top: 10px;
                margin-bottom: 10px;
            }
            QTextBrowser li {
                margin-bottom: 5px;
                color: rgba(255, 255, 255, 0.9);
            }
        """)
    
    def update_visibility(self):
        """Show either timer OR project content in same area"""
        if self.showing_timer:
            self.timer_label.setVisible(True)
            self.project_content.setVisible(False)
        else:
            self.timer_label.setVisible(False)
            self.project_content.setVisible(True)
    
    def create_navigation(self, layout):
        """Create navigation buttons"""
        nav_layout = QHBoxLayout()
        
        self.back_button = QPushButton("← Back")
        self.back_button.setStyleSheet("""
            QPushButton {
                font-size: 14px;
                color: rgba(255, 255, 255, 0.7);
                background-color: transparent;
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 8px;
                padding: 12px 24px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
            QPushButton:disabled {
                opacity: 0.3;
            }
        """)
        self.back_button.clicked.connect(self.previous_step)
        self.back_button.setEnabled(False)
        nav_layout.addWidget(self.back_button)
        
        nav_layout.addStretch()
        
        self.next_button = QPushButton("Next →")
        self.next_button.setStyleSheet("""
            QPushButton {
                font-size: 14px;
                color: white;
                background-color: #3498db;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:disabled {
                background-color: rgba(255, 255, 255, 0.1);
                color: rgba(255, 255, 255, 0.3);
            }
        """)
        self.next_button.clicked.connect(self.next_step)
        nav_layout.addWidget(self.next_button)
        
        layout.addLayout(nav_layout)
    
    def show_introduction(self):
        """Show introduction step"""
        self.clear_content()
        content_layout = QVBoxLayout(self.content_area)
        
        title = QLabel("How This AI Tutor Works")
        title.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: 600;
                color: rgba(255, 255, 255, 0.95);
                margin-bottom: 20px;
            }
        """)
        content_layout.addWidget(title)
        
        # Introduction paragraph
        intro_para = QLabel("This is an AI Tutor that works together with Cursor (the coding editor) to help you learn how to code by building actual, working projects. Instead of just reading about code, you'll be writing real programs and understanding what each part does.")
        intro_para.setWordWrap(True)
        intro_para.setStyleSheet("""
            QLabel {
                font-size: 14px;
                line-height: 1.6;
                color: rgba(255, 255, 255, 0.8);
                background-color: rgba(255, 255, 255, 0.05);
                border-radius: 10px;
                padding: 20px;
                margin-bottom: 15px;
            }
        """)
        content_layout.addWidget(intro_para)
        
        # "Here's what you need to know" header
        know_header = QLabel("Here's what you need to know before we start:")
        know_header.setWordWrap(True)
        know_header.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: 600;
                color: rgba(255, 255, 255, 0.9);
                margin: 15px 0px 10px 20px;
            }
        """)
        content_layout.addWidget(know_header)
        
        # Create each point with bold heading and regular text
        points = [
            ("1. This AI will explain everything step by step", "As you build your project, the AI will explain what each piece of code does and why we're writing it that way. Think of it like having a patient teacher sitting next to you."),
            ("2. Keep a notebook handy", "Seriously, get a physical notebook or open a notes app on your computer. Write down new concepts, code patterns you learn, and things that confused you. Writing things down helps your brain remember them better."),
            ("3. The point is to learn, not to finish quickly", "Don't rush through this. The goal isn't to build the project as fast as possible - it's to understand what you're doing. Take breaks when you need to. Ask questions about anything that doesn't make sense."),
            ("4. Ask for explanations at your level", "When something is confusing, try asking the AI to \"explain this like I'm 12\" or \"explain this like I'm 16\" or even \"explain this like I'm 5\". The AI can adjust how it explains things based on what you need."),
            ("5. Explain things back", "After the AI teaches you something, try explaining it back in your own words. This is one of the best ways to make sure you actually understand it, not just memorizing it."),
            ("6. Double-check everything by researching", "AI is really helpful, but it's not perfect. When you learn something new, look it up on Google or other websites to make sure it's correct. This also helps you see different ways people explain the same concept."),
            ("7. It's okay to disagree with the AI", "If something the AI tells you doesn't seem right, or you found different information online, speak up! Ask questions like \"But I read that...\" or \"This doesn't seem right because...\". Learning to question information is an important skill for any engineer."),
            ("8. You should already know programming basics", "This AI Tutor assumes you already understand the fundamentals of programming - things like variables, loops, functions, and basic syntax. Our projects will primarily use Python (for backend/server code) and JavaScript (for frontend/web interfaces and some backend). If you're completely new to programming, we recommend starting with Codecademy or Scratch to learn the absolute basics first. Don't worry though - the skills you learn in one language easily transfer to others!")
        ]
        
        for heading, description in points:
            # Create container for each point
            point_frame = QFrame()
            point_frame.setStyleSheet("""
                QFrame {
                    background-color: rgba(255, 255, 255, 0.03);
                    border-radius: 8px;
                    padding: 15px;
                    margin: 5px 0px;
                }
            """)
            point_layout = QVBoxLayout(point_frame)
            point_layout.setSpacing(8)
            
            # Bold heading
            heading_label = QLabel(heading)
            heading_font = QFont()
            heading_font.setBold(True)
            heading_font.setPointSize(14)
            heading_label.setFont(heading_font)
            heading_label.setStyleSheet("""
                QLabel {
                    color: rgba(255, 255, 255, 0.95);
                }
            """)
            point_layout.addWidget(heading_label)
            
            # Regular description
            desc_label = QLabel(description)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet("""
                QLabel {
                    font-size: 13px;
                    line-height: 1.5;
                    color: rgba(255, 255, 255, 0.8);
                    margin-left: 15px;
                }
            """)
            point_layout.addWidget(desc_label)
            
            content_layout.addWidget(point_frame)
        
        content_layout.addStretch()
        
        # Initially hide the next button until user scrolls to bottom
        self.next_button.setText("I Understand →")
        self.next_button.setVisible(False)
        
        # Connect scroll area to check if user has scrolled to bottom
        self.scroll_area.verticalScrollBar().valueChanged.connect(self.check_scroll_position)
    
    def show_language_selection(self):
        """Show programming language selection"""
        self.clear_content()
        content_layout = QVBoxLayout(self.content_area)
        
        title = QLabel("Choose Your Programming Language")
        title.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: 600;
                color: rgba(255, 255, 255, 0.95);
                margin-bottom: 20px;
            }
        """)
        content_layout.addWidget(title)
        
        subtitle = QLabel("What programming language would you like to learn today? Each language has different strengths and is used for different types of projects.")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("""
            QLabel {
                font-size: 16px;
                color: rgba(255, 255, 255, 0.7);
                margin-bottom: 30px;
            }
        """)
        content_layout.addWidget(subtitle)
        
        # Language options
        self.language_group = QButtonGroup()
        languages = [
            ("Python", "", "Perfect for beginners. Used to build websites, analyze data, create AI programs, and automate tasks. Many companies like Instagram and Spotify use Python."),
            ("JavaScript", "", "The language that makes websites interactive. Every website you visit uses JavaScript. It's also used to build mobile apps and even desktop programs."),
            ("Java", "", "A very popular language used by big companies like Netflix and LinkedIn. Great for building large applications that need to handle millions of users."),
            ("C++", "", "A powerful language used to build video games, operating systems, and programs that need to run really fast. Companies like Google and Microsoft use it."),
            ("C", "", "The foundation that many other languages are built on. Learning C teaches you exactly how computers work at a low level. It's used in embedded systems and operating systems."),
            ("Go", "", "A newer language created by Google. It's designed to be simple but powerful, used for building web servers and cloud applications."),
            ("Rust", "", "A systems programming language that prevents common bugs and security issues. Used by companies like Dropbox and Mozilla for high-performance applications."),
            ("TypeScript", "", "JavaScript but with extra features that help prevent bugs in large projects. Used by companies like Microsoft and Slack for complex web applications.")
        ]
        
        for i, (lang, icon, description) in enumerate(languages):
            lang_frame = self.create_language_option(lang, icon, description)
            content_layout.addWidget(lang_frame)
        
        content_layout.addStretch()
        
        self.back_button.setEnabled(True)
        self.next_button.setText("Next →")
        self.next_button.setVisible(True)  # Make sure button is visible on language selection
        self.next_button.setEnabled(False)  # Enable when selection made
    
    def create_language_option(self, language, icon, description):
        """Create a language selection option"""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 10px;
                padding: 15px;
                margin: 5px 0px;
            }
            QFrame:hover {
                background-color: rgba(255, 255, 255, 0.08);
            }
        """)
        
        layout = QHBoxLayout(frame)
        
        # Radio button
        radio = QRadioButton()
        radio.setStyleSheet("""
            QRadioButton::indicator {
                width: 18px;
                height: 18px;
            }
            QRadioButton::indicator::unchecked {
                border: 2px solid rgba(255, 255, 255, 0.3);
                border-radius: 9px;
                background-color: transparent;
            }
            QRadioButton::indicator::checked {
                border: 2px solid #3498db;
                border-radius: 9px;
                background-color: #3498db;
            }
        """)
        radio.toggled.connect(lambda checked: self.on_language_selected(language) if checked else None)
        self.language_group.addButton(radio)
        layout.addWidget(radio)
        
        # Content
        content_layout = QVBoxLayout()
        
        lang_header = QHBoxLayout()
        lang_label = QLabel(language)
        lang_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: 600;
                color: rgba(255, 255, 255, 0.95);
            }
        """)
        lang_header.addWidget(lang_label)
        lang_header.addStretch()
        
        desc_label = QLabel(description)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("""
            QLabel {
                font-size: 13px;
                color: rgba(255, 255, 255, 0.7);
                margin-top: 5px;
            }
        """)
        
        content_layout.addLayout(lang_header)
        content_layout.addWidget(desc_label)
        layout.addLayout(content_layout)
        
        return frame
    
    def on_language_selected(self, language):
        """Handle language selection"""
        self.project_config['language'] = language
        self.next_button.setEnabled(True)
    
    # def show_project_generation(self):
    #     """Show project generation step with AI loading"""
    #     self.clear_content()
    #     content_layout = QVBoxLayout(self.content_area)
        
    #     title = QLabel("Generating Your Project")
    #     title.setStyleSheet("""
    #         QLabel {
    #             font-size: 24px;
    #             font-weight: 600;
    #             color: rgba(255, 255, 255, 0.95);
    #             margin-bottom: 20px;
    #         }
    #     """)
    #     content_layout.addWidget(title)
        
    #     # Status message (will be updated by timer)
    #     self.status_label = QLabel("🤖 AI is analyzing your assessment scores...")
    #     self.status_label.setWordWrap(True)
    #     self.status_label.setStyleSheet("""
    #         QLabel {
    #             font-size: 16px;
    #             color: rgba(255, 255, 255, 0.8);
    #             margin-bottom: 15px;
    #         }
    #     """)
    #     content_layout.addWidget(self.status_label)
        
    #     # Timer label (shows immediately)
    #     self.timer_label = QLabel("Time elapsed: 00:00")
    #     self.timer_label.setStyleSheet("""
    #         QLabel {
    #             font-size: 14px;
    #             color: rgba(255, 255, 255, 0.6);
    #             margin-bottom: 20px;
    #         }
    #     """)
    #     content_layout.addWidget(self.timer_label)
        
    #     # Progress bar
    #     self.progress_bar = QProgressBar()
    #     self.progress_bar.setRange(0, 0)  # Indeterminate progress
    #     self.progress_bar.setStyleSheet("""
    #         QProgressBar {
    #             border: 1px solid rgba(255, 255, 255, 0.3);
    #             border-radius: 8px;
    #             background-color: rgba(255, 255, 255, 0.1);
    #             height: 20px;
    #         }
    #         QProgressBar::chunk {
    #             background-color: #3498db;
    #             border-radius: 7px;
    #         }
    #     """)
    #     content_layout.addWidget(self.progress_bar)
        
    #     content_layout.addStretch()
        
    #     # Hide navigation buttons during generation
    #     self.next_button.setVisible(False)
    #     self.back_button.setEnabled(False)
        
    #     self.content_area.repaint()
        
    #     # START TIMER IMMEDIATELY before starting AI generation
    #     self.start_status_timer()
        
    #     # Start AI generation with a longer delay to ensure timer is visible
    #     QTimer.singleShot(2000, self.start_project_generation)  # 2 second delay to test timer visibility
    
    def start_project_generation(self):
        """Start the AI project generation process for one randomly selected language"""
        import random
        
        # Prepare user scores and data
        user_scores = self.project_config.get('user_scores', {})
        
        # Randomly select either Python or JavaScript
        selected_language = random.choice(['Python', 'JavaScript'])
        
        # Store the selected language
        self.project_config['language'] = selected_language
        
        # Start worker thread for the selected language (local AI only)
        self.generation_worker = ProjectGenerationWorker(
            user_scores, selected_language, self.user_data, use_local_only=True
        )
        self.generation_worker.project_generated.connect(lambda desc: self.on_project_generated(selected_language, desc))
        self.generation_worker.generation_failed.connect(lambda err: self.on_generation_failed(selected_language, err))
        self.generation_worker.start()
    
    def on_project_generated(self, language, project_description):
        """Replace timer with AI project output in same content area"""
        if hasattr(self, 'status_timer'):
            self.status_timer.stop()
        
        # Switch from timer to project content
        self.showing_timer = False
        self.update_visibility()
        
        # Extract only the structured project content starting from "Project Title"
        structured_content = self.extract_structured_content(project_description)
        # Convert markdown-style formatting to HTML and set project content (only AI output)
        formatted_description = self.convert_markdown_to_html(structured_content)
        self.project_content.setHtml(formatted_description)
        
        self.project_config['language'] = language
        self.project_config['project_description'] = project_description
        
        self.next_button.setText("Step 1 →")
        self.next_button.setVisible(True)
        self.next_button.setEnabled(True)
        self.back_button.setEnabled(True)
    
    def on_generation_failed(self, language, error_message):
        """Handle failed project generation"""
        # Stop the status timer
        if hasattr(self, 'status_timer'):
            self.status_timer.stop()
        
        # Hide progress bar and timer
        self.progress_bar.setVisible(False)
        if hasattr(self, 'timer_label'):
            self.timer_label.setVisible(False)
        
        print(f"Failed to generate {language} project: {error_message}")
        
        self.status_label.setText(f"Failed to generate {language} project. Please try again.")
        self.status_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                color: rgba(255, 100, 100, 0.9);
                margin-bottom: 30px;
            }
        """)
        
        # Show retry option
        retry_button = QPushButton("Try Again")
        retry_button.setStyleSheet("""
            QPushButton {
                font-size: 14px;
                color: white;
                background-color: #e74c3c;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        retry_button.clicked.connect(self.start_project_generation)
        
        layout = self.content_area.layout()
        layout.insertWidget(layout.count() - 1, retry_button)  # Insert before stretch
        
        self.back_button.setEnabled(True)
    
    def start_status_timer(self):
        """Start simple timer that counts elapsed time"""
        self.timer_seconds = 0
        
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(1000)  # Update every second
    
    def update_status(self):
        """Update just the timer display"""
        minutes = self.timer_seconds // 60
        seconds = self.timer_seconds % 60
        
        self.timer_label.setText(f"Time elapsed: {minutes:02d}:{seconds:02d}")
        self.timer_seconds += 1
    
    def extract_structured_content(self, text):
        """
        Extracts only the structured project content starting from "1. **Project Title**"
        and ignoring any AI reasoning or preamble before the actual project description.
        
        The expected structure starts with:
        1. **Project Title**: ...
        2. **Problem Statement**: ...
        etc.
        """
        # Look for the start of structured content - either numbered or just the Project Title header
        patterns = [
            r'1\.\s*\*\*Project Title\*\*:.*', 
            r'\*\*Project Title\*\*:.*',        
            r'Project Title:.*',                
            r'1\.\s*Project Title:.*'           
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                # Extract everything from this point to the end
                structured_content = text[match.start():]
                return structured_content.strip()
        
        # If no structured pattern is found, return the original text
        # (fallback in case AI doesn't follow the expected format)
        return text.strip()
    
    def extract_structured_task_content(self, text):
        """
        Extracts task breakdown content starting from "**Task 1:**"
        """
        patterns = [
            r'\*\*Task 1:\*\*.*',      
            r'Task 1:.*',              
            r'1\.\s*Task:.*',          
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                structured_content = text[match.start():]
                return structured_content.strip()
        
        # Fallback: return original text
        return text.strip()
    
    def convert_task_markdown_to_html(self, text):
        """
        Converts task breakdown markdown to HTML with specialized formatting for:
        - Task headers (**Task 1:** -> h2)
        - Section headers (**Task Overview:** -> h3)
        - AI prompts (quoted text -> styled code blocks)
        - Review questions
        """
        # Task headers like "**Task 1:** Task Name" -> h2
        text = re.sub(r'\*\*Task (\d+):\*\*(.*?)(?=\n|\*\*|$)', r'<h2>Task \1:\2</h2>', text)
        
        # Section headers like "**Task Overview:**" -> h3
        section_headers = [
            'Task Overview', 'Learning Goals', 'AI Prompts to Start Building', 
            'AI Prompts for Understanding Code', 'AI Prompts for Concepts', 'Review Questions'
        ]
        for header in section_headers:
            text = re.sub(rf'\*\*{header}:\*\*', rf'<h3>{header}:</h3>', text)
        
        # AI prompts (quoted strings) -> styled code blocks
        text = re.sub(r'"([^"]+)"', r'<code>"\1"</code>', text)
        
        # Handle remaining bold text
        text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
        
        # Bullet points
        text = re.sub(r'^[-*]\s+(.+)$', r'<li>\1</li>', text, flags=re.MULTILINE)
        
        # Wrap consecutive list items in <ul> tags
        text = re.sub(r'(<li>.*</li>)', r'<ul>\1</ul>', text, flags=re.DOTALL)
        text = re.sub(r'</ul>\s*<ul>', '', text)
        
        # Task separators (---) -> styled dividers
        text = re.sub(r'^---\s*$', r'<hr style="border: 1px solid rgba(255, 255, 255, 0.2); margin: 30px 0;">', text, flags=re.MULTILINE)
        
        # Line breaks
        text = text.replace('\n\n', '<br/><br/>')
        text = text.replace('\n', '<br/>')
        
        return text
    
    def convert_markdown_to_html(self, text):
        """
        Converts markdown-like formatting to HTML.
        Specifically handles the AI output format with numbered headers and bold text.
        """
        # Handle numbered headers like "1. **Project Title**:" -> proper HTML headers
        text = re.sub(r'(\d+)\.\s*\*\*(.*?)\*\*:', r'<h3 style="color: rgba(255, 255, 255, 1.0); margin-top: 20px; margin-bottom: 10px;">\1. \2</h3>', text)
        
        # Handle remaining bold text (for emphasis within content)
        text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
        text = re.sub(r'\_\_(.*?)\_\_', r'<b>\1</b>', text)
        
        # Italic
        text = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'<i>\1</i>', text)
        text = re.sub(r'(?<!_)_([^_]+)_(?!_)', r'<i>\1</i>', text)
        
        # Code blocks (triple backticks)
        text = re.sub(r'```(.*?)```', r'<pre><code>\1</code></pre>', text, flags=re.DOTALL)
        
        # Inline code (single backticks)
        text = re.sub(r'`([^`]+)`', r'<code style="background-color: rgba(0, 0, 0, 0.2); padding: 2px 4px; border-radius: 3px;">\1</code>', text)
        
        # Bullet points
        text = re.sub(r'^[-*]\s+(.+)$', r'<li>\1</li>', text, flags=re.MULTILINE)
        
        # Wrap consecutive list items in <ul> tags
        text = re.sub(r'(<li>.*</li>)', r'<ul>\1</ul>', text, flags=re.DOTALL)
        text = re.sub(r'</ul>\s*<ul>', '', text)  # Remove duplicate ul tags
        
        # Line breaks (convert \n to <br/> but preserve structure)
        text = text.replace('\n\n', '<br/><br/>')
        text = text.replace('\n', '<br/>')
        
        return text
    
    def clear_content(self):
        """Clear the content area"""
        if self.content_area.layout():
            while self.content_area.layout().count():
                child = self.content_area.layout().takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
            self.content_area.layout().deleteLater()
    
    def next_step(self):
        """Go to next step"""
        if self.current_step == 0:
            # User clicked "I Understand" from introduction
            self.current_step = 1
            self.show_project_generation()
        elif self.current_step == 1:
            # Go from project generation to task breakdown
            self.current_step = 2
            self.show_task_breakdown()
        elif self.current_step == 2:
            # Move to next task or complete project
            if hasattr(self, 'current_task_number') and self.current_task_number < len(self.task_names):
                self.current_task_number += 1
                # Save progress to database
                if self.current_project_id:
                    self.project_ops.update_project_progress(
                        self.current_project_id, 
                        self.current_task_number
                    )
                self.generate_and_show_current_task()
            else:
                # All tasks completed - mark project as complete
                if self.current_project_id:
                    self.project_ops.complete_project(self.current_project_id)
                self.complete_wizard()
    
    def show_project_generation(self):
        """Show timer in existing QScrollArea, then replace with AI output"""
        # Don't clear content - use existing QScrollArea
        # Add timer and project content directly to the QScrollArea
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # Add timer and project content to scroll area
        scroll_layout.addWidget(self.timer_label)
        scroll_layout.addWidget(self.project_content)
        scroll_layout.addStretch()
        
        # Set this widget as the QScrollArea content
        self.scroll_area.setWidget(scroll_widget)
        
        # Show timer immediately in QScrollArea
        self.showing_timer = True
        self.update_visibility()
        
        self.next_button.setVisible(False)
        self.back_button.setEnabled(False)
        
        self.start_status_timer()
        QTimer.singleShot(100, self.start_project_generation)
    
    def show_task_breakdown(self):
        """Show task breakdown generation step"""
        # Use existing scroll area and replace content with task breakdown loading
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # Title
        title = QLabel("Breaking Down Your Project")
        title.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: 600;
                color: rgba(255, 255, 255, 0.95);
                margin-bottom: 20px;
            }
        """)
        scroll_layout.addWidget(title)
        
        # Status message
        self.breakdown_status_label = QLabel("AI is breaking your project into learning tasks...")
        self.breakdown_status_label.setWordWrap(True)
        self.breakdown_status_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                color: rgba(255, 255, 255, 0.8);
                margin-bottom: 15px;
            }
        """)
        scroll_layout.addWidget(self.breakdown_status_label)
        
        # Timer label for task breakdown
        self.breakdown_timer_label = QLabel("Time elapsed: 00:00")
        self.breakdown_timer_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: rgba(255, 255, 255, 0.6);
                margin-bottom: 20px;
            }
        """)
        scroll_layout.addWidget(self.breakdown_timer_label)
        
        # Progress bar
        self.breakdown_progress_bar = QProgressBar()
        self.breakdown_progress_bar.setRange(0, 0)  # Indeterminate progress
        self.breakdown_progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 8px;
                background-color: rgba(255, 255, 255, 0.1);
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #3498db;
                border-radius: 7px;
            }
        """)
        scroll_layout.addWidget(self.breakdown_progress_bar)
        
        scroll_layout.addStretch()
        
        # Set this widget as the QScrollArea content
        self.scroll_area.setWidget(scroll_widget)
        
        # Hide navigation buttons during generation
        self.next_button.setVisible(False)
        self.back_button.setEnabled(False)
        
        # Start task breakdown timer and generation
        self.start_breakdown_timer()
        QTimer.singleShot(1000, self.start_task_breakdown_generation)
    
    def start_breakdown_timer(self):
        """Start timer for task breakdown generation"""
        self.breakdown_timer_seconds = 0
        
        self.breakdown_status_timer = QTimer()
        self.breakdown_status_timer.timeout.connect(self.update_breakdown_status)
        self.breakdown_status_timer.start(1000)  # Update every second
    
    def update_breakdown_status(self):
        """Update the breakdown timer display"""
        minutes = self.breakdown_timer_seconds // 60
        seconds = self.breakdown_timer_seconds % 60
        
        self.breakdown_timer_label.setText(f"Time elapsed: {minutes:02d}:{seconds:02d}")
        self.breakdown_timer_seconds += 1
    
    def start_task_breakdown_generation(self):
        """Start the AI task headers generation process (Phase 1)"""
        # Get the project description and language from project_config
        project_description = self.project_config.get('project_description', '')
        selected_language = self.project_config.get('language', 'Python')
        
        # Start worker thread for task headers (local AI only)
        self.headers_worker = TaskHeadersWorker(
            project_description, selected_language, use_local_only=True
        )
        self.headers_worker.headers_generated.connect(self.on_task_headers_generated)
        self.headers_worker.headers_failed.connect(self.on_task_headers_failed)
        self.headers_worker.start()
    
    def on_task_headers_generated(self, task_headers):
        """Handle successful task headers generation (Phase 1 complete)"""
        if hasattr(self, 'breakdown_status_timer'):
            self.breakdown_status_timer.stop()
        
        logger.info(f"Task headers generated: {task_headers}")
        
        # Parse task names from headers
        self.task_names = self.parse_task_names(task_headers)
        
        if not self.task_names:
            self.on_task_headers_failed(f"Could not parse task names from AI response. AI returned: {task_headers[:200]}...")
            return
        
        # Store the headers and initialize current task tracking
        self.project_config['task_headers'] = task_headers
        self.project_config['task_details'] = {}
        self.current_task_number = 1
        
        # Save project to database
        self.save_project_to_database()
        
        # Generate and show only the first task details
        self.generate_and_show_current_task()
    
    def parse_task_names(self, task_headers):
        """Extract task names from headers - handle various AI response formats"""
        import re
        task_names = []
        
        # Multiple patterns to handle different AI response formats
        patterns = [
            r'\*\*Task\s+(\d+):\*\*\s*(.+?)(?=\n|\*\*|$)',  
            r'Task\s+(\d+):\s*(.+?)(?=\n|Task\s+\d+|$)',    
            r'(\d+)\.\s*(.+?)(?=\n|\d+\.|$)',               
            r'Step\s+(\d+):\s*(.+?)(?=\n|Step\s+\d+|$)',    
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, task_headers, re.IGNORECASE | re.MULTILINE)
            if matches:
                for task_num, task_name in matches:
                    task_names.append((int(task_num), task_name.strip()))
                break
        
        # If no structured format found, just create simple task names
        if not task_names:
            lines = [line.strip() for line in task_headers.split('\n') if line.strip()]
            for i, line in enumerate(lines[:4], 1):  # Take first 4 non-empty lines
                if line:  # Skip empty lines
                    task_names.append((i, line))
        
        # Sort by task number and return just the names
        task_names.sort(key=lambda x: x[0])
        return [name for _, name in task_names]
    
    def generate_and_show_current_task(self):
        """Generate and display the current task details"""
        if self.current_task_number > len(self.task_names):
            # All tasks completed
            self.show_project_completion()
            return
        
        # Show loading for current task
        self.show_current_task_loading()
        
        # Generate current task details
        current_task_name = self.task_names[self.current_task_number - 1]
        project_description = self.project_config.get('project_description', '')
        selected_language = self.project_config.get('language', 'Python')
        
        # Start worker for current task
        self.current_task_worker = TaskDetailWorker(
            current_task_name, self.current_task_number, 
            project_description, selected_language, use_local_only=True
        )
        self.current_task_worker.detail_generated.connect(self.on_current_task_generated)
        self.current_task_worker.detail_failed.connect(self.on_current_task_failed)
        self.current_task_worker.start()
    
    def show_current_task_loading(self):
        """Show loading screen for current task"""
        current_task_name = self.task_names[self.current_task_number - 1]
        
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # Task progress indicator
        progress_label = QLabel(f"Task {self.current_task_number} of {len(self.task_names)}")
        progress_label.setAlignment(Qt.AlignCenter)
        progress_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                color: rgba(255, 255, 255, 0.7);
                margin-bottom: 10px;
            }
        """)
        scroll_layout.addWidget(progress_label)
        
        # Current task header
        task_header = QLabel(f"**Task {self.current_task_number}:** {current_task_name}")
        task_header.setAlignment(Qt.AlignCenter)
        task_header.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: rgba(255, 255, 255, 1.0);
                margin-bottom: 20px;
                padding: 20px;
                background-color: rgba(255, 255, 255, 0.05);
                border-radius: 12px;
            }
        """)
        scroll_layout.addWidget(task_header)
        
        # Loading message
        loading_label = QLabel("🔄 Generating detailed instructions for this task...")
        loading_label.setAlignment(Qt.AlignCenter)
        loading_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                color: rgba(255, 255, 255, 0.8);
                margin: 40px;
            }
        """)
        scroll_layout.addWidget(loading_label)
        
        scroll_layout.addStretch()
        
        # Set this widget as the QScrollArea content
        self.scroll_area.setWidget(scroll_widget)
        
        # Hide navigation during loading
        self.next_button.setVisible(False)
        self.back_button.setEnabled(True)
    
    def show_task_headers_with_loading_details(self):
        """Show task headers immediately with placeholders for details being generated"""
        # Create new scroll widget
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # Store references to detail areas for updating
        self.task_detail_areas = {}
        
        for i, task_name in enumerate(self.task_names, 1):
            # Task header
            task_header = QLabel(f"**Task {i}:** {task_name}")
            task_header.setStyleSheet("""
                QLabel {
                    font-size: 18px;
                    font-weight: bold;
                    color: rgba(255, 255, 255, 1.0);
                    margin-top: 20px;
                    margin-bottom: 10px;
                    padding: 10px;
                    background-color: rgba(255, 255, 255, 0.05);
                    border-radius: 8px;
                }
            """)
            scroll_layout.addWidget(task_header)
            
            # Detail area (initially shows loading)
            detail_area = QTextBrowser()
            detail_area.setReadOnly(True)
            detail_area.setMaximumHeight(300)
            detail_area.setStyleSheet("""
                QTextBrowser {
                    font-size: 14px;
                    line-height: 1.6;
                    color: rgba(255, 255, 255, 0.8);
                    background-color: rgba(255, 255, 255, 0.02);
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 8px;
                    padding: 15px;
                    margin-bottom: 20px;
                }
            """)
            detail_area.setHtml(f"<i>🔄 Generating details for Task {i}...</i>")
            scroll_layout.addWidget(detail_area)
            
            # Store reference for updating
            self.task_detail_areas[i] = detail_area
        
        scroll_layout.addStretch()
        
        # Set this widget as the QScrollArea content
        self.scroll_area.setWidget(scroll_widget)
        
        # Update navigation
        self.next_button.setText("Begin First Task →")
        self.next_button.setVisible(True)
        self.next_button.setEnabled(True)
        self.back_button.setEnabled(True)
    
    def start_generating_task_details(self):
        """Start generating details for each task (Phase 2)"""
        project_description = self.project_config.get('project_description', '')
        selected_language = self.project_config.get('language', 'Python')
        
        for i, task_name in enumerate(self.task_names, 1):
            # Start worker for this task
            worker = TaskDetailWorker(
                task_name, i, project_description, selected_language, use_local_only=True
            )
            worker.detail_generated.connect(self.on_task_detail_generated)
            worker.detail_failed.connect(self.on_task_detail_failed)
            worker.start()
            
            # Store worker reference
            self.task_detail_workers[i] = worker
    
    def on_task_detail_generated(self, task_number, task_name, task_detail):
        """Handle successful generation of individual task details"""
        logger.info(f"Task {task_number} details generated")
        
        # Store the detail
        self.project_config['task_details'][task_number] = task_detail
        
        # Save progress to database
        if self.current_project_id:
            self.project_ops.update_project_progress(
                self.current_project_id, 
                self.current_task_number,
                {task_number: task_detail}
            )
        
        # Format and update the UI
        formatted_detail = self.convert_task_detail_to_html(task_detail)
        
        if task_number in self.task_detail_areas:
            self.task_detail_areas[task_number].setHtml(formatted_detail)
    
    def on_task_detail_failed(self, task_number, task_name, error_message):
        """Handle failed generation of individual task details"""
        logger.error(f"Task {task_number} detail generation failed: {error_message}")
        
        if task_number in self.task_detail_areas:
            self.task_detail_areas[task_number].setHtml(
                f"<span style='color: rgba(255, 100, 100, 0.9);'>❌ Failed to generate details: {error_message}</span>"
            )
    
    def convert_task_detail_to_html(self, task_detail):
        """Convert individual task detail to HTML"""
        # Extract and format the task detail content
        structured_content = self.extract_task_detail_content(task_detail)
        return self.convert_task_markdown_to_html(structured_content)
    
    def extract_task_detail_content(self, text):
        """Extract task detail content starting from 'What You'll Build'"""
        patterns = [
            r'\*\*What You\'ll Build:\*\*.*',
            r'What You\'ll Build:.*',
            r'\*\*Task Overview:\*\*.*',  # Fallback
            r'Task Overview:.*'  # Fallback
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                return text[match.start():].strip()
        
        return text.strip()
    
    def on_current_task_generated(self, task_number, task_name, task_detail):
        """Handle successful generation of current task details"""
        logger.info(f"Current task {task_number} details generated")
        
        # Store the detail
        self.project_config['task_details'][task_number] = task_detail
        
        # Show the complete task with evaluation prompt
        self.show_complete_current_task(task_name, task_detail)
    
    def on_current_task_failed(self, task_number, task_name, error_message):
        """Handle failed generation of current task details"""
        logger.error(f"Current task {task_number} generation failed: {error_message}")
        
        # Show error and retry option
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        error_label = QLabel(f"❌ Failed to generate Task {task_number} details")
        error_label.setAlignment(Qt.AlignCenter)
        error_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                color: rgba(255, 100, 100, 0.9);
                margin: 40px;
            }
        """)
        scroll_layout.addWidget(error_label)
        
        retry_button = QPushButton("Try Again")
        retry_button.setStyleSheet("""
            QPushButton {
                font-size: 14px;
                color: white;
                background-color: #e74c3c;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        retry_button.clicked.connect(self.generate_and_show_current_task)
        scroll_layout.addWidget(retry_button)
        
        scroll_layout.addStretch()
        self.scroll_area.setWidget(scroll_widget)
        
        self.back_button.setEnabled(True)
    
    def show_complete_current_task(self, task_name, task_detail):
        """Show the complete current task with evaluation prompt for Cursor"""
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        progress_label = QLabel(f"Task {self.current_task_number} of {len(self.task_names)}")
        progress_label.setAlignment(Qt.AlignCenter)
        progress_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: rgba(255, 255, 255, 0.6);
                margin-bottom: 10px;
            }
        """)
        scroll_layout.addWidget(progress_label)
        
        # Task header
        task_header = QLabel(f"Task {self.current_task_number}: {task_name}")
        task_header.setAlignment(Qt.AlignCenter)
        task_header.setStyleSheet("""
            QLabel {
                font-size: 22px;
                font-weight: bold;
                color: rgba(255, 255, 255, 1.0);
                margin-bottom: 20px;
                padding: 15px;
                background-color: rgba(255, 255, 255, 0.05);
                border-radius: 10px;
            }
        """)
        scroll_layout.addWidget(task_header)
        
        # Task details
        task_browser = QTextBrowser()
        task_browser.setReadOnly(True)
        task_browser.setOpenExternalLinks(False)
        task_browser.setStyleSheet("""
            QTextBrowser {
                font-size: 14px;
                line-height: 1.6;
                color: rgba(255, 255, 255, 0.9);
                background-color: rgba(255, 255, 255, 0.02);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 20px;
                margin-bottom: 20px;
            }
            QTextBrowser h3 {
                color: rgba(255, 255, 255, 1.0);
                font-size: 16px;
                margin-top: 20px;
                margin-bottom: 10px;
            }
            QTextBrowser ul {
                margin-left: 20px;
            }
            QTextBrowser li {
                margin-bottom: 8px;
            }
            QTextBrowser code {
                background-color: rgba(0, 0, 0, 0.3);
                padding: 2px 6px;
                border-radius: 4px;
                font-family: 'Courier New', monospace;
            }
        """)
        
        # Format and set task details
        formatted_detail = self.convert_task_detail_to_html(task_detail)
        task_browser.setHtml(formatted_detail)
        scroll_layout.addWidget(task_browser)
        
        # Cursor evaluation section
        self.add_cursor_evaluation_section(scroll_layout, task_name)
        
        # Add skip project option
        self.add_skip_project_button(scroll_layout)
        
        scroll_layout.addStretch()
        self.scroll_area.setWidget(scroll_widget)
        
        # Update navigation
        if self.current_task_number < len(self.task_names):
            next_step = self.current_task_number + 1
            self.next_button.setText(f"Step {next_step} →")
        else:
            self.next_button.setText("Complete Project →")
        
        self.next_button.setVisible(True)
        self.next_button.setEnabled(True)
        self.back_button.setEnabled(True)
    
    def add_cursor_evaluation_section(self, layout, task_name):
        """Add the Cursor AI evaluation section"""
        # Section header
        eval_header = QLabel("📋 Task Evaluation with Cursor AI")
        eval_header.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: rgba(255, 255, 255, 1.0);
                margin-top: 30px;
                margin-bottom: 15px;
                padding: 12px;
                background-color: rgba(52, 152, 219, 0.2);
                border-radius: 8px;
            }
        """)
        layout.addWidget(eval_header)
        
        # Instructions
        instructions = QLabel(
            "When you've completed this task, copy the prompt below and paste it into Cursor AI. "
            "Cursor will evaluate your work and help you learn!"
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: rgba(255, 255, 255, 0.8);
                margin-bottom: 15px;
                padding: 10px;
            }
        """)
        layout.addWidget(instructions)
        
        # Generate evaluation prompt
        project_description = self.project_config.get('project_description', '')
        selected_language = self.project_config.get('language', 'Python')
        evaluation_prompt = self.create_cursor_evaluation_prompt(task_name, project_description, selected_language)
        
        # Copyable prompt area
        prompt_area = QTextEdit()
        prompt_area.setReadOnly(True)
        prompt_area.setPlainText(evaluation_prompt)
        prompt_area.setMaximumHeight(200)
        prompt_area.setStyleSheet("""
            QTextEdit {
                font-family: 'Courier New', monospace;
                font-size: 12px;
                color: rgba(255, 255, 255, 0.9);
                background-color: rgba(0, 0, 0, 0.3);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 6px;
                padding: 12px;
            }
        """)
        layout.addWidget(prompt_area)
        
        # Copy button
        copy_button = QPushButton("📋 Copy Prompt for Cursor")
        copy_button.setStyleSheet("""
            QPushButton {
                font-size: 14px;
                color: white;
                background-color: #2ecc71;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                margin-top: 10px;
            }
            QPushButton:hover {
                background-color: #27ae60;
            }
        """)
        copy_button.clicked.connect(lambda: self.copy_to_clipboard(evaluation_prompt))
        layout.addWidget(copy_button)
    
    def create_cursor_evaluation_prompt(self, task_name, project_description, selected_language):
        """Create an evaluation prompt for Cursor AI"""
        return f"""Please evaluate my progress on this coding task and help me learn:

PROJECT CONTEXT:
{project_description.split('.')[0] if project_description else 'Learning project'}

CURRENT TASK: {task_name}
LANGUAGE: {selected_language}

INSTRUCTIONS:
1. Look at my current code and files
2. Check if I've completed the task requirements
3. Rate my progress (0-100%) and explain what I did well
4. Explain the software engineering concepts I used (explain like I'm 12-18 years old)
5. Give me a list of things to study next with specific resources

Please be encouraging and educational. Help me understand not just what I built, but why it works and how it connects to real software engineering.

RESPOND WITH:
- **Progress Rating:** [0-100%] and why
- **What You Built:** Summary of my work
- **Engineering Concepts:** Explain the concepts I used
- **Next Steps:** 3-4 things to study with resources
- **Encouragement:** What I did well and how to improve

Please analyze my files now and give me feedback!"""
    
    def copy_to_clipboard(self, text):
        """Copy text to system clipboard"""
        from PySide6.QtGui import QGuiApplication
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(text)
        
        # Show brief confirmation (could add a tooltip or status message)
        logger.info("Evaluation prompt copied to clipboard")
    
    def on_task_headers_failed(self, error_message):
        """Handle failed task breakdown generation"""
        if hasattr(self, 'breakdown_status_timer'):
            self.breakdown_status_timer.stop()
        
        # Show detailed error message
        logger.error(f"Task breakdown failed: {error_message}")
        self.breakdown_status_label.setText(f"Failed to generate task breakdown.\n\nError: {error_message}\n\nThis might be due to local AI limitations. The project description might be too complex for the local model.")
        self.breakdown_status_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: rgba(255, 100, 100, 0.9);
                margin-bottom: 30px;
            }
        """)
        
        # Hide progress bar and timer
        self.breakdown_progress_bar.setVisible(False)
        self.breakdown_timer_label.setVisible(False)
        
        # Add retry button
        retry_button = QPushButton("Try Again")
        retry_button.setStyleSheet("""
            QPushButton {
                font-size: 14px;
                color: white;
                background-color: #e74c3c;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        retry_button.clicked.connect(self.show_task_breakdown)
        
        # Add retry button to layout
        scroll_widget = self.scroll_area.widget()
        if scroll_widget and scroll_widget.layout():
            scroll_widget.layout().addWidget(retry_button)
        
        self.back_button.setEnabled(True)
    
    def show_project_content_again(self):
        """Re-display the project content when going back from task breakdown"""
        # Get the project content and language from project_config
        project_description = self.project_config.get('project_description', '')
        selected_language = self.project_config.get('language', 'Python')
        
        # Extract and format the project content
        structured_content = self.extract_structured_content(project_description)
        formatted_description = self.convert_markdown_to_html(structured_content)
        
        # Create new scroll widget with project content
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # Create QTextBrowser for project display
        project_browser = QTextBrowser()
        project_browser.setReadOnly(True)
        project_browser.setOpenExternalLinks(False)
        project_browser.setStyleSheet("""
            QTextBrowser {
                font-size: 14px;
                line-height: 1.6;
                color: rgba(255, 255, 255, 0.9);
                background-color: transparent;
                border: none;
                padding: 20px;
            }
            QTextBrowser b {
                color: rgba(255, 255, 255, 1.0);
                font-size: 16px;
                font-weight: bold;
            }
            QTextBrowser h3 {
                color: rgba(255, 255, 255, 1.0);
                margin-top: 20px;
                margin-bottom: 10px;
            }
            QTextBrowser ul {
                margin-left: 20px;
                margin-top: 10px;
                margin-bottom: 10px;
            }
            QTextBrowser li {
                margin-bottom: 5px;
                color: rgba(255, 255, 255, 0.9);
            }
        """)
        project_browser.setHtml(formatted_description)
        scroll_layout.addWidget(project_browser)
        
        # Set this widget as the QScrollArea content
        self.scroll_area.setWidget(scroll_widget)
        
        # Update navigation buttons
        self.next_button.setText("Start Building →")
        self.next_button.setVisible(True)
        self.next_button.setEnabled(True)
        self.back_button.setEnabled(True)
    
    def previous_step(self):
        """Go to previous step"""
        if self.current_step == 1:
            # Don't go back to introduction/terms - go back to dashboard instead
            self.main_window.show_dashboard()
        elif self.current_step == 2:
            # Go back to previous task or project view
            if hasattr(self, 'current_task_number') and self.current_task_number > 1:
                self.current_task_number -= 1
                # Update database
                if self.current_project_id:
                    self.project_ops.update_project_progress(
                        self.current_project_id, 
                        self.current_task_number
                    )
                # Show previous task
                self.show_existing_project_task()
            else:
                # Go back to project description
                self.show_project_content_again()
    
    def check_scroll_position(self):
        """Check if user has scrolled to the bottom and show/hide next button accordingly"""
        if self.current_step == 0:  # Only apply this to the introduction step
            scrollbar = self.scroll_area.verticalScrollBar()
            # Check if scrolled to bottom (with small tolerance)
            at_bottom = scrollbar.value() >= scrollbar.maximum() - 10
            self.next_button.setVisible(at_bottom)
    
    def complete_wizard(self):
        """Complete the wizard and start project"""
        # Add user scores to project config
        if self.user_data:
            self.project_config['user_scores'] = {
                'initial_assessment_score': self.user_data.get('overall_score', 0),
                'section_scores': self.user_data.get('section_scores', {}),
                'user_id': self.user_data.get('id'),
                'username': self.user_data.get('username')
            }
        
        self.project_started.emit(self.project_config) 