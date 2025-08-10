"""
The Engineer AI Tutor - Project Wizard View
Wizard to guide users through AI-assisted project creation
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QScrollArea, QButtonGroup, QRadioButton, QTextEdit, QProgressBar
)
from PySide6.QtCore import Qt, Signal, QThread, QTimer
from PySide6.QtGui import QFont
from core.ai.project_generator import ProjectGenerator

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

class ProjectWizardView(QWidget):
    """Wizard for setting up AI-assisted project building"""
    
    project_started = Signal(dict)  # Emits project configuration
    
    def __init__(self, user_data, main_window):
        super().__init__()
        self.user_data = user_data
        self.main_window = main_window
        self.current_step = 0
        self.project_config = {}
        self.setup_ui()
    
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
        
        # Simple label for project content - will hold AI output
        self.project_content = QLabel()
        self.project_content.setWordWrap(True)
        self.project_content.setAlignment(Qt.AlignTop)
        self.project_content.setStyleSheet("""
            QLabel {
                font-size: 14px;
                line-height: 1.6;
                color: rgba(255, 255, 255, 0.9);
                padding: 20px;
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
    
    def show_project_generation(self):
        """Show project generation step with AI loading"""
        self.clear_content()
        content_layout = QVBoxLayout(self.content_area)
        
        title = QLabel("Generating Your Project")
        title.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: 600;
                color: rgba(255, 255, 255, 0.95);
                margin-bottom: 20px;
            }
        """)
        content_layout.addWidget(title)
        
        # Status message (will be updated by timer)
        self.status_label = QLabel("🤖 AI is analyzing your assessment scores...")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                color: rgba(255, 255, 255, 0.8);
                margin-bottom: 15px;
            }
        """)
        content_layout.addWidget(self.status_label)
        
        # Timer label (shows immediately)
        self.timer_label = QLabel("⏱️ Time elapsed: 00:00")
        self.timer_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: rgba(255, 255, 255, 0.6);
                margin-bottom: 20px;
            }
        """)
        content_layout.addWidget(self.timer_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.progress_bar.setStyleSheet("""
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
        content_layout.addWidget(self.progress_bar)
        
        content_layout.addStretch()
        
        # Hide navigation buttons during generation
        self.next_button.setVisible(False)
        self.back_button.setEnabled(False)
        
        self.content_area.repaint()
        
        # START TIMER IMMEDIATELY before starting AI generation
        self.start_status_timer()
        
        # Start AI generation with a longer delay to ensure timer is visible
        QTimer.singleShot(2000, self.start_project_generation)  # 2 second delay to test timer visibility
    
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
        
        # Set project content directly - replaces timer in same space
        self.project_content.setText(f"<h3>Your {language} Project is Ready!</h3><br/>{project_description}")
        
        self.project_config['language'] = language
        self.project_config['project_description'] = project_description
        
        self.next_button.setText("Start Building →")
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
        
        self.timer_label.setText(f"⏱️ Time elapsed: {minutes:02d}:{seconds:02d}")
        self.timer_seconds += 1
    


    
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
            # Skip language selection, go directly to project generation
            self.current_step = 1
            self.show_project_generation()
        elif self.current_step == 1:
            # Complete the wizard with generated project
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
    
    def previous_step(self):
        """Go to previous step"""
        if self.current_step == 1:
            # Don't go back to introduction/terms - go back to dashboard instead
            self.main_window.show_dashboard()
    
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