"""
The Engineer AI Tutor - Project Wizard View
Wizard to guide users through AI-assisted project creation
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QScrollArea, QButtonGroup, QRadioButton, QTextEdit, QProgressBar,
    QTextBrowser, QToolTip, QStackedWidget
)

try:
    from qfluentwidgets import TabBar, InfoBar, InfoBarPosition
    TAB_BAR_AVAILABLE = True
    FLYOUT_AVAILABLE = True
except ImportError:
    TAB_BAR_AVAILABLE = False
    FLYOUT_AVAILABLE = False
from PySide6.QtCore import Qt, Signal, QThread, QTimer
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont, QTextCursor
from core.ai.project_generator import ProjectGenerator
from ..utils import create_offline_warning_banner
import re
import logging

logger = logging.getLogger(__name__)

# Import database operations
from data.database.operations import db_manager, ProjectOperations

class ProjectGenerationWorker(QThread):
    """Worker thread for generating projects using AI"""
    
    project_generated = Signal(str)  # Emits generated project description
    generation_failed = Signal(str)  # Emits error message
    
    def __init__(self, user_scores, selected_language, user_data, use_local_only=False, project_theme=None):
        super().__init__()
        self.user_scores = user_scores
        self.selected_language = selected_language
        self.user_data = user_data
        self.use_local_only = use_local_only
        self.project_theme = project_theme
    
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
                self.use_local_only,
                self.project_theme
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
        logger.info(f"🔧 TaskHeadersWorker.run() STARTED")
        logger.info(f"🧵 Thread object: {self}")
        logger.info(f"📝 Project description length: {len(self.project_description)} chars")
        logger.info(f"🔧 Language: {self.selected_language}")
        logger.info(f"🏠 Use local only: {self.use_local_only}")
        
        try:
            logger.info(f"🏗️ Creating ProjectGenerator instance")
            generator = ProjectGenerator()
            
            logger.info(f"🔍 Checking if AI generator is available")
            if not generator.is_available():
                logger.error(f"❌ No AI services available for task headers")
                self.headers_failed.emit("No AI services available for task headers")
                return
            
            logger.info(f"✅ AI generator is available, starting task headers generation")
            logger.info(f"📤 Calling generator.generate_task_headers()")
            
            task_headers = generator.generate_task_headers(
                self.project_description,
                self.selected_language,
                self.use_local_only
            )
            
            logger.info(f"📥 generate_task_headers() returned")
            logger.info(f"📏 Response length: {len(task_headers) if task_headers else 0} chars")
            logger.info(f"📄 Response content: {task_headers[:200] if task_headers else 'None'}...")
            
            if task_headers:
                logger.info(f"✅ Task headers generated successfully, emitting signal")
                logger.info(f"📤 EMITTING headers_generated signal with {len(task_headers)} chars")
                self.headers_generated.emit(task_headers)
                logger.info(f"✅ headers_generated signal EMITTED successfully")
            else:
                logger.error(f"❌ Task headers generation returned empty/None")
                logger.error(f"📤 EMITTING headers_failed signal")
                self.headers_failed.emit("Failed to generate task headers. Please try again.")
                logger.error(f"✅ headers_failed signal EMITTED successfully")
                
        except Exception as e:
            logger.error(f"💥 EXCEPTION in TaskHeadersWorker: {str(e)}")
            logger.error(f"🔍 Exception type: {type(e).__name__}")
            import traceback
            logger.error(f"📜 Full traceback: {traceback.format_exc()}")
            logger.error(f"📤 EMITTING headers_failed signal due to exception")
            self.headers_failed.emit(f"Error generating task headers: {str(e)}")
            logger.error(f"✅ headers_failed signal EMITTED due to exception")
        
        logger.info(f"🏁 TaskHeadersWorker.run() COMPLETED")

class TaskDetailWorker(QThread):
    """Worker thread for generating individual task details using AI"""
    
    detail_generated = Signal(int, str, str)  # Emits task_number, task_name, task_detail
    detail_failed = Signal(int, str, str)     # Emits task_number, task_name, error_message
    detail_streaming = Signal(int, str, str)  # Emits task_number, task_name, partial_content
    
    def __init__(self, task_name, task_number, project_description, selected_language, use_local_only=False):
        super().__init__()
        self.task_name = task_name
        self.task_number = task_number
        self.project_description = project_description
        self.selected_language = selected_language
        self.use_local_only = use_local_only
    
    def run(self):
        """Run task detail generation in background thread"""
        logger.info(f"🔧 TaskDetailWorker.run() STARTED")
        logger.info(f"🧵 Thread object: {self}")
        logger.info(f"🎯 Task name: {self.task_name}")
        logger.info(f"🔢 Task number: {self.task_number}")
        logger.info(f"📝 Project description length: {len(self.project_description)} chars")
        logger.info(f"🔧 Language: {self.selected_language}")
        logger.info(f"🏠 Use local only: {self.use_local_only}")
        
        try:
            logger.info(f"🏗️ Creating ProjectGenerator instance")
            generator = ProjectGenerator()
            
            # Set up streaming callback
            def streaming_callback(partial_content):
                self.detail_streaming.emit(self.task_number, self.task_name, partial_content)
            
            generator.set_streaming_callback(streaming_callback)
            
            logger.info(f"🔍 Checking if AI generator is available")
            if not generator.is_available():
                logger.error(f"❌ No AI services available for task details")
                self.detail_failed.emit(self.task_number, self.task_name, "No AI services available")
                return
            
            logger.info(f"✅ AI generator is available, starting task detail generation")
            logger.info(f"📤 Calling generator.generate_task_detail()")
            
            # Custom generation with streaming
            from core.ai.project_prompts import create_task_detail_prompt, extract_json_from_reasoning_response
            prompt = create_task_detail_prompt(self.task_name, self.task_number, self.project_description, self.selected_language)
            
            # Use generator's smart routing (cloud first when online, then local)
            def qt_safe_callback(partial_content):
                # Emit signal from worker thread - Qt will marshal to main thread
                self.detail_streaming.emit(self.task_number, self.task_name, partial_content)
            
            generator.set_streaming_callback(qt_safe_callback)
            
            # Let the generator decide which AI to use based on connectivity
            task_detail = generator.generate_task_detail(
                self.task_name, 
                self.task_number, 
                self.project_description, 
                self.selected_language,
                use_local_only=False  # Allow smart routing
            )
            
            logger.info(f"📥 generate_task_detail() returned")
            logger.info(f"📏 Response length: {len(task_detail) if task_detail else 0} chars")
            logger.info(f"📄 Response content: {task_detail[:200] if task_detail else 'None'}...")
            
            if task_detail:
                logger.info(f"✅ Task detail generated successfully, emitting signal")
                logger.info(f"📤 EMITTING detail_generated signal - task {self.task_number}: {self.task_name}")
                logger.info(f"📤 Signal data: {len(task_detail)} chars")
                self.detail_generated.emit(self.task_number, self.task_name, task_detail)
                logger.info(f"✅ detail_generated signal EMITTED successfully")
            else:
                logger.error(f"❌ Task detail generation returned empty/None")
                logger.error(f"📤 EMITTING detail_failed signal - task {self.task_number}: {self.task_name}")
                self.detail_failed.emit(self.task_number, self.task_name, "Failed to generate task details")
                logger.error(f"✅ detail_failed signal EMITTED successfully")
                
        except Exception as e:
            logger.error(f"💥 EXCEPTION in TaskDetailWorker: {str(e)}")
            logger.error(f"🔍 Exception type: {type(e).__name__}")
            import traceback
            logger.error(f"📜 Full traceback: {traceback.format_exc()}")
            logger.error(f"📤 EMITTING detail_failed signal due to exception")
            self.detail_failed.emit(self.task_number, self.task_name, f"Error: {str(e)}")
            logger.error(f"✅ detail_failed signal EMITTED due to exception")
        
        logger.info(f"🏁 TaskDetailWorker.run() COMPLETED")

class BackgroundTaskGenerator(QThread):
    """Worker thread for sequentially generating remaining empty task details"""
    
    task_generated = Signal(int, str) 
    all_tasks_complete = Signal()
    
    def __init__(self, task_names, existing_task_details, project_description, selected_language, current_task_number, project_id, project_ops, total_tasks=None):
        super().__init__()
        self.task_names = task_names
        self.existing_task_details = existing_task_details
        self.project_description = project_description
        self.selected_language = selected_language
        self.current_task_number = current_task_number
        self.project_id = project_id
        self.project_ops = project_ops
        self.total_tasks = total_tasks
    
    def run(self):
        """Generate remaining empty tasks sequentially"""
        print(f"🔴 BackgroundTaskGenerator.run() started")
        print(f"🔴 total_tasks: {self.total_tasks}")
        print(f"🔴 current_task_number: {self.current_task_number}")
        print(f"🔴 existing_task_details: {list(self.existing_task_details.keys())}")
        
        try:
            generator = ProjectGenerator()
            
            if not generator.is_available():
                return
            
            # Use total_tasks from AI response instead of task_names length
            total_to_generate = self.total_tasks or len(self.task_names)
            
            for task_number in range(1, total_to_generate + 1):
                if task_number == self.current_task_number or self.existing_task_details.get(task_number):
                    continue
                
                task_name = f"Task {task_number}"                
                task_detail = generator.generate_task_detail(
                    task_name, task_number, self.project_description, self.selected_language, use_local_only=False
                )
                
                if task_detail:
                    from src.core.ai.project_prompts import extract_task_json_from_response
                    clean_json = extract_task_json_from_response(task_detail)
                    
                    self.project_ops.update_project_progress(
                        self.project_id, self.current_task_number, {task_number: clean_json}
                    )
                    self.task_generated.emit(task_number, clean_json)
                else:
                    print(f"🔴 Failed to generate task {task_number}")
            
            print(f"🔴 Background generation complete")
            self.all_tasks_complete.emit()
            
        except Exception as e:
            logger.error(f"Background task generation failed: {e}")

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
            self.task_names = existing_project['task_names']
            
            # Find the first uncompleted task instead of trusting stored current_task_number
            self.current_task_number = self.find_first_uncompleted_task()
            print(f"🔍 DEBUG: Loaded existing project: {existing_project['title']}")
            print(f"🔍 DEBUG: Current task number set to: {self.current_task_number}")
            print(f"🔍 DEBUG: Task names: {self.task_names}")
            logger.info(f"Loaded existing project: {existing_project['title']}")
            logger.info(f"Current task number set to: {self.current_task_number}")
    
    def find_first_uncompleted_task(self):
        """Find the first task that hasn't been completed"""
        
        if not self.current_project_id or not self.task_names:
            return 1
        
        
        # Check each task in order
        for task_number in range(1, len(self.task_names) + 1):
            is_completed = self.project_ops.is_task_completed(self.current_project_id, task_number)
            if not is_completed:
                return task_number
        
        return len(self.task_names)
    
    def show_existing_project_task(self):
        """Show the current task for an existing project"""
        
        if not hasattr(self, 'current_task_number') or not self.task_names:
            self.generate_and_show_current_task()
            return
        
        current_task_name = self.task_names[self.current_task_number - 1]
        current_task_detail = self.project_config.get('task_details', {}).get(self.current_task_number)
        
        
        # Mark task as in_progress when user starts viewing it
        if self.current_project_id:
            self.project_ops.update_task_status(
                self.current_project_id, 
                self.current_task_number, 
                'in_progress'
            )
        
        if current_task_detail:
            self.show_complete_current_task(current_task_name, current_task_detail)
            self.start_background_task_generation()
        else:
            self.generate_and_show_current_task()
    
    def start_background_task_generation(self):
        """Start background generation of remaining empty tasks"""
        if not hasattr(self, 'current_project_id') or not self.current_project_id:
            return
        
        if hasattr(self, 'background_generator') and self.background_generator.isRunning():
            return 
        
        self.background_generator = BackgroundTaskGenerator(
            self.task_names,
            self.project_config.get('task_details', {}),
            self.project_config.get('project_description', ''),
            self.project_config.get('language', 'Python'),
            self.current_task_number,
            self.current_project_id,
            self.project_ops
        )
        self.background_generator.task_generated.connect(self.on_background_task_generated)
        self.background_generator.start()
    
    def on_background_task_generated(self, task_number, task_detail):
        """Handle background task generation completion"""
        if 'task_details' not in self.project_config:
            self.project_config['task_details'] = {}
        self.project_config['task_details'][task_number] = task_detail
        logger.info(f"Background generated task {task_number}")
    
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
        skip_button = QPushButton("Start New Project")
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
        if self.current_project_id and hasattr(self, 'task_names') and self.task_names:
            # User has existing project, show choice between continue or restart
            self.show_project_choice()
        else:
            # Show first step
            self.show_introduction()
    
    def create_header(self, layout):
        """Create wizard header"""
        header_layout = QVBoxLayout()
        
        # Check for offline warning
        create_offline_warning_banner(header_layout)
        
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
        
        # Add Complete Task button (initially hidden)
        self.complete_button = QPushButton("Mark Task as Complete")
        self.complete_button.setStyleSheet("""
            QPushButton {
                font-size: 14px;
                color: white;
                background-color: #27AE60;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            QPushButton:disabled {
                background-color: rgba(255, 255, 255, 0.1);
                color: rgba(255, 255, 255, 0.3);
            }
        """)
        self.complete_button.clicked.connect(self.complete_current_task)
        self.complete_button.setVisible(False)
        nav_layout.addWidget(self.complete_button)
        
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
        # Create fresh scroll widget like all other methods
        scroll_widget = QWidget()
        content_layout = QVBoxLayout(scroll_widget)
        
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
        
        # Set the scroll widget as the scroll area content
        self.scroll_area.setWidget(scroll_widget)
        
        # Initially hide the next button until user scrolls to bottom
        self.next_button.setText("I Understand →")
        self.next_button.setVisible(False)
        self.complete_button.setVisible(False)  # Hide complete button on introduction
        
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
        self.complete_button.setVisible(False)  # Hide complete button on language selection
    
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
        
        # Prepare user scores and data from actual user data
        user_scores = self.user_data if self.user_data else {}
        
        # Randomly select either Python or JavaScript
        selected_language = random.choice(['Python', 'JavaScript'])
        
        # Add variety by randomly selecting a project theme
        project_themes = [
            "local entrepreneurship and small business solutions",
            "community health and wellness tracking", 
            "educational tools for rural schools",
            "agricultural productivity and farming assistance",
            "local transportation and logistics coordination",
            "environmental conservation and sustainability",
            "community communication and social connection",
            "financial literacy and micro-savings tools"
        ]
        selected_theme = random.choice(project_themes)
        
        # Store the selected language and theme
        self.project_config['language'] = selected_language
        self.project_config['theme'] = selected_theme
        
        # Start worker thread for the selected language (cloud first when online)
        self.generation_worker = ProjectGenerationWorker(
            user_scores, selected_language, self.user_data, use_local_only=False, project_theme=selected_theme
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
        
        # For new projects, start with Task 1
        self.next_button.setText("Task 1 →")
        self.next_button.setVisible(True)
        self.next_button.setEnabled(True)
        self.back_button.setEnabled(True)
    
    def on_generation_failed(self, language, error_message):
        """Handle failed project generation"""
        # Stop the status timer
        if hasattr(self, 'status_timer'):
            self.status_timer.stop()
        
        # Hide progress bar and timer
        if hasattr(self, 'breakdown_progress_bar'):
            self.breakdown_progress_bar.setVisible(False)
        if hasattr(self, 'timer_label'):
            self.timer_label.setVisible(False)
        
        print(f"Failed to generate {language} project: {error_message}")
        
        # Create status_label if it doesn't exist
        if not hasattr(self, 'status_label'):
            self.status_label = QLabel()
            self.status_label.setAlignment(Qt.AlignCenter)
            self.status_label.setWordWrap(True)
        
        self.status_label.setText(f"Failed to generate {language} project. Please try again.")
        self.status_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                color: rgba(255, 100, 100, 0.9);
                margin-bottom: 30px;
                padding: 15px;
                background-color: rgba(255, 100, 100, 0.1);
                border-radius: 8px;
                border: 1px solid rgba(255, 100, 100, 0.3);
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
        
        # Safely add widgets to layout
        try:
            layout = self.content_area.layout()
            if layout:
                # Add status label if not already in layout
                if hasattr(self, 'status_label') and self.status_label.parent() != self.content_area:
                    layout.insertWidget(0, self.status_label)
                # Add retry button
                layout.insertWidget(layout.count() - 1, retry_button)  # Insert before stretch
        except RuntimeError as e:
            print(f"Layout error (objects may be deleted): {e}")
            # Create a simple fallback UI
            scroll_widget = QWidget()
            scroll_layout = QVBoxLayout(scroll_widget)
            scroll_layout.addWidget(self.status_label)
            scroll_layout.addWidget(retry_button)
            scroll_layout.addStretch()
            try:
                self.scroll_area.setWidget(scroll_widget)
            except:
                print("Could not create fallback UI")
        
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
        print(f"🚀 NEXT_STEP BUTTON CLICKED!")
        print(f"🚀 continuing_existing_project: {getattr(self, 'continuing_existing_project', 'NOT SET')}")
        print(f"🚀 current_step: {getattr(self, 'current_step', 'NOT SET')}")
        print(f"🚀 current_task_number: {getattr(self, 'current_task_number', 'NOT SET')}")
        print(f"🚀 task_names: {getattr(self, 'task_names', 'NOT SET')}")
        print(f"🚀 len(task_names): {len(getattr(self, 'task_names', []))}")
        
        if getattr(self, 'continuing_existing_project', False):
            print(f"🚀 Branch 1: continuing_existing_project = True")
            self.show_existing_project_task()
            self.continuing_existing_project = False  
            return
            
        if self.current_step == 0:
            print(f"🚀 Branch 2: current_step = 0")
            # User clicked "I Understand" from introduction
            if self.current_project_id and not self.project_config.get('is_completed', False) and self.project_config.get('status') != 'skipped':
                print(f"🚀 Branch 2a: show_project_choice")
                self.show_project_choice()
            else:
                print(f"🚀 Branch 2b: show_project_generation")
                # No existing project, proceed with project generation
                self.current_step = 1
                self.show_project_generation()
        elif self.current_step == 1:
            print(f"🚀 Branch 3: current_step = 1")
            # Go from project generation to task breakdown
            self.current_step = 2
            self.show_task_breakdown()
        elif self.current_step == 2:
            print(f"🚀 Branch 4: current_step = 2")
            # Move to next task or complete project
            
            total_tasks_from_ai = len(self.task_names)  
            try:
                import json
                current_task_detail = self.project_config.get('task_details', {}).get(self.current_task_number, '')
                if current_task_detail:
                    task_data = json.loads(current_task_detail)
                    if 'total_project_tasks' in task_data:
                        total_tasks_from_ai = task_data['total_project_tasks']
                        print(f"🚀 Using total_project_tasks from AI: {total_tasks_from_ai}")
            except:
                print(f"🚀 Could not get total_project_tasks from AI, using fallback: {total_tasks_from_ai}")
            
            if hasattr(self, 'current_task_number') and self.current_task_number < total_tasks_from_ai:
                self.current_task_number += 1
                if self.current_project_id:
                    self.project_ops.update_project_progress(
                        self.current_project_id, 
                        self.current_task_number
                    )
                self.show_existing_project_task()
            else:
                if self.current_project_id:
                    self.project_ops.complete_project(self.current_project_id)
                self.complete_wizard()
        else:
            print(f"🚀 Branch 5: Unknown current_step = {self.current_step}")
    
    def show_project_generation(self):
        """Show timer in existing QScrollArea, then replace with AI output"""
        if self.current_project_id and self.project_config.get('project_description'):
            self.show_project_choice()
            return
        
        # No cached project, generate new one
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
        self.complete_button.setVisible(False)  # Hide complete button during project generation
        
        self.start_status_timer()
        QTimer.singleShot(100, self.start_project_generation)
    
    def show_project_choice(self):
        """Show choice between continuing existing project or starting new one"""
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # Title
        title = QLabel("Project Found")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: 600;
                color: rgba(255, 255, 255, 0.95);
                margin-bottom: 20px;
            }
        """)
        scroll_layout.addWidget(title)
        
        # Current project info
        if self.task_names and hasattr(self, 'current_task_number') and self.current_task_number <= len(self.task_names):
            current_task_name = self.task_names[self.current_task_number - 1]
            notice_text = QLabel(f"You have an active project in progress.\nCurrently on: {current_task_name}")
        else:
            project_title = self.project_config.get('title', 'Untitled Project')
            notice_text = QLabel(f"You have an active project: {project_title}\nReady to generate tasks.")
        notice_text.setAlignment(Qt.AlignCenter)
        notice_text.setWordWrap(True)
        notice_text.setStyleSheet("""
            QLabel {
                font-size: 16px;
                color: rgba(255, 255, 255, 0.8);
                margin-bottom: 30px;
                padding: 20px;
                background-color: rgba(255, 255, 255, 0.05);
                border-radius: 10px;
            }
        """)
        scroll_layout.addWidget(notice_text)
        
        # Choice buttons
        button_layout = QHBoxLayout()
        
        continue_btn = QPushButton("Continue Project")
        continue_btn.setStyleSheet("""
            QPushButton {
                font-size: 16px;
                color: white;
                background-color: #2ecc71;
                border: none;
                border-radius: 8px;
                padding: 15px 30px;
                margin: 10px;
            }
            QPushButton:hover {
                background-color: #27ae60;
            }
        """)
        continue_btn.clicked.connect(self.continue_existing_project)
        button_layout.addWidget(continue_btn)
        
        restart_btn = QPushButton("Start New Project")
        restart_btn.setStyleSheet("""
            QPushButton {
                font-size: 16px;
                color: rgba(255, 255, 255, 0.8);
                background-color: transparent;
                border: 2px solid rgba(255, 255, 255, 0.3);
                border-radius: 8px;
                padding: 15px 30px;
                margin: 10px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
        """)
        restart_btn.clicked.connect(self.start_new_project)
        button_layout.addWidget(restart_btn)
        
        scroll_layout.addLayout(button_layout)
        scroll_layout.addStretch()
        
        # Set this widget as the QScrollArea content
        self.scroll_area.setWidget(scroll_widget)
        
        # Hide navigation buttons
        self.next_button.setVisible(False)
        self.back_button.setEnabled(True)
    
    def continue_existing_project(self):
        """Continue with existing project by showing cached content"""
        print(f"🟢 continue_existing_project() called")
        print(f"🟢 current_task_number before: {getattr(self, 'current_task_number', 'NOT SET')}")
        
        # Set state to track that we're viewing continued project
        self.viewing_continued_project = True
        self.continuing_existing_project = True
        
        # Switch from choice to project content
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # Create a new QTextBrowser for project content instead of reusing the deleted one
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
        
        # Add project browser to scroll area
        scroll_layout.addWidget(project_browser)
        scroll_layout.addStretch()
        
        # Set this widget as the QScrollArea content
        self.scroll_area.setWidget(scroll_widget)
        
        # Extract and format the cached project content
        structured_content = self.extract_structured_content(self.project_config['project_description'])
        formatted_description = self.convert_markdown_to_html(structured_content)
        project_browser.setHtml(formatted_description)
        
        # Set current step to 2 so next_step() will proceed to task breakdown
        self.current_step = 2
        
        # Set button to show the current incomplete task number
        task_number = getattr(self, 'current_task_number', 1)
        self.next_button.setText(f"Task {task_number} →")
        self.next_button.setVisible(True)
        self.next_button.setEnabled(True)
        self.back_button.setEnabled(True)
    
    def start_new_project(self):
        """Start a new project by skipping current and generating new one"""
        if self.current_project_id:
            self.project_ops.skip_project(self.current_project_id)
        
        # Reset state
        self.current_project_id = None
        self.project_config = {
            'task_details': {}  
        }
        self.current_task_number = 1
        self.current_step = 1  
        
        # Generate new project
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # Recreate project_content if it was deleted
        if not self.project_content or not self.project_content.parent():
            self.project_content = QTextBrowser()
            self.project_content.setStyleSheet("""
                QTextBrowser {
                    background-color: rgba(255, 255, 255, 0.05);
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 10px;
                    padding: 20px;
                    color: rgba(255, 255, 255, 0.9);
                    font-size: 14px;
                    line-height: 1.6;
                }
            """)
        
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
        
        # Safety check to prevent crashes if widget was deleted
        if hasattr(self, 'breakdown_timer_label') and self.breakdown_timer_label:
            try:
                self.breakdown_timer_label.setText(f"Time elapsed: {minutes:02d}:{seconds:02d}")
            except RuntimeError:
                # Widget was deleted, stop the timer
                if hasattr(self, 'breakdown_status_timer'):
                    self.breakdown_status_timer.stop()
        
        self.breakdown_timer_seconds += 1
    
    def start_task_breakdown_generation(self):
        """Start generating task breakdown using AI"""
        logger.info(f"🚀 start_task_breakdown_generation() CALLED")
        
        # Show loading state
        self.show_task_breakdown_loading()
        
        # Skip headers generation - go directly to first task detail
        current_task_name = "Task 1"  # We'll get the real name from the AI response
        self.current_task_number = 1
        project_description = self.project_config.get('project_description', '')
        selected_language = self.project_config.get('language', 'Python')
        
        logger.info(f"🎯 Generating first task detail directly")
        
        # Start worker for first task
        self.current_task_worker = TaskDetailWorker(
            current_task_name, self.current_task_number, 
            project_description, selected_language, use_local_only=False
        )
        
        # Connect signals
        self.current_task_worker.detail_generated.connect(self.on_current_task_generated)
        self.current_task_worker.detail_failed.connect(self.on_current_task_failed)
        self.current_task_worker.detail_streaming.connect(self.on_current_task_streaming)
        
        self.current_task_worker.start()
        
        logger.info(f"✅ TaskDetailWorker thread started successfully")
    
    def show_task_breakdown_loading(self):
        """Show loading screen for task breakdown generation"""
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # Title
        title = QLabel("Generating Task Breakdown")
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
        self.breakdown_status_label = QLabel("AI is generating task breakdown...")
        self.breakdown_status_label.setWordWrap(True)
        self.breakdown_status_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                color: rgba(255, 255, 255, 0.8);
                margin-bottom: 15px;
            }
        """)
        scroll_layout.addWidget(self.breakdown_status_label)
        
        # Timer label for breakdown generation
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
    
    def start_generating_task_details(self):
        """Start generating details for each task (Phase 2)"""
        project_description = self.project_config.get('project_description', '')
        selected_language = self.project_config.get('language', 'Python')
        
        for i, task_name in enumerate(self.task_names, 1):
            # Start worker for this task
            worker = TaskDetailWorker(
                task_name, i, project_description, selected_language, use_local_only=False
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
    
    def create_task_card(self, layout, task_detail, task_data=None):
        """Create a card-style display for task details"""
        import json
        
        try:
            # Parse the JSON task detail if not already provided
            if task_data is None:
                task_data = json.loads(task_detail)
            
            # Create card frame
            card_frame = QFrame()
            card_frame.setStyleSheet("""
                QFrame {
                    background-color: rgba(255, 255, 255, 0.05);
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 12px;
                    margin: 10px 0px;
                    padding: 20px;
                }
            """)
            
            card_layout = QVBoxLayout(card_frame)
            
            # Description
            description = task_data.get('description', 'No description available')
            description_label = QLabel(description)
            description_label.setWordWrap(True)
            description_label.setStyleSheet("""
                QLabel {
                    font-size: 16px;
                    line-height: 1.5;
                    color: rgba(255, 255, 255, 0.9);
                    margin-bottom: 15px;
                }
            """)
            card_layout.addWidget(description_label)
            
            # Add engineering concepts as pill buttons
            if 'engineering_concepts' in task_data:
                try:
                    from qfluentwidgets import PillPushButton
                    
                    # Create horizontal layout for pill buttons
                    pills_layout = QHBoxLayout()
                    pills_layout.setSpacing(8)
                    
                    for concept in task_data['engineering_concepts']:
                        pill_button = PillPushButton(concept)
                        pill_button.setMaximumWidth(300)  # Increased width
                        
                        font = pill_button.font()
                        font.setPointSize(9)  # Smaller font size
                        pill_button.setFont(font)
                        
                        pills_layout.addWidget(pill_button)
                    
                    pills_layout.addStretch()
                    card_layout.addLayout(pills_layout)
                    
                except ImportError:
                    # Fallback: show as regular labels if library not available
                    for concept in task_data['engineering_concepts']:
                        concept_label = QLabel(f"• {concept}")
                        concept_label.setStyleSheet("""
                            QLabel {
                                font-size: 12px;
                                color: rgba(255, 255, 255, 0.8);
                                margin-left: 10px;
                                margin-bottom: 4px;
                            }
                        """)
                        card_layout.addWidget(concept_label)
            
            layout.addWidget(card_frame)
            
        except (json.JSONDecodeError, Exception) as e:
            # Fallback - create a simple card with error info
            card_frame = QFrame()
            card_frame.setStyleSheet("""
                QFrame {
                    background-color: rgba(255, 255, 255, 0.05);
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 12px;
                    margin: 10px 0px;
                    padding: 20px;
                }
            """)
            
            card_layout = QVBoxLayout(card_frame)
            error_label = QLabel(f"Task Details (JSON Parse Error: {str(e)})")
            error_label.setStyleSheet("""
                QLabel {
                    font-size: 16px;
                    color: rgba(255, 255, 255, 0.8);
                }
            """)
            card_layout.addWidget(error_label)
            layout.addWidget(card_frame)

    def create_task_tabs(self, layout, task_data, task_detail):
        """Create tab bar with cursor prompts, test commands, and practical content"""
        from qfluentwidgets import TabBar
        
        # Create tab bar
        tab_bar = TabBar()
        tab_bar.addTab('tab1', 'Cursor Prompts')
        tab_bar.addTab('tab2', 'Test Commands') 
        tab_bar.addTab('tab3', 'Practical')
        
        # Create stacked widget for tab content
        tab_content = QStackedWidget()
        
        # Tab 1: Cursor Prompts
        prompts_widget = QWidget()
        prompts_layout = QVBoxLayout(prompts_widget)
        if 'cursor_prompts' in task_data:
            for prompt in task_data['cursor_prompts']:
                prompt_container = self.create_copyable_prompt_widget(prompt)
                prompts_layout.addWidget(prompt_container)
        tab_content.addWidget(prompts_widget)
        
        # Tab 2: Test Commands
        commands_widget = QWidget()
        commands_layout = QVBoxLayout(commands_widget)
        if 'test_commands' in task_data:
            for command in task_data['test_commands']:
                command_label = QLabel(command)
                command_label.setWordWrap(True)
                command_label.setStyleSheet("""
                    QLabel {
                        padding: 10px;
                        margin: 5px;
                        background-color: rgba(255, 255, 255, 0.05);
                        border-radius: 6px;
                        color: rgba(255, 255, 255, 0.9);
                        font-family: 'Courier New', monospace;
                    }
                """)
                commands_layout.addWidget(command_label)
        tab_content.addWidget(commands_widget)
        
        # Tab 3: Practical (Real World Connection)
        practical_widget = QWidget()
        practical_layout = QVBoxLayout(practical_widget)
        if 'real_world_connection' in task_data:
            practical_label = QLabel(task_data['real_world_connection'])
            practical_label.setWordWrap(True)
            practical_label.setStyleSheet("""
                QLabel {
                    padding: 15px;
                    background-color: rgba(255, 255, 255, 0.05);
                    border-radius: 6px;
                    color: rgba(255, 255, 255, 0.9);
                    font-size: 14px;
                    line-height: 1.5;
                }
            """)
            practical_layout.addWidget(practical_label)
        tab_content.addWidget(practical_widget)
        
        # Connect tab changes
        tab_bar.currentChanged.connect(tab_content.setCurrentIndex)
        
        # Add to layout
        layout.addWidget(tab_bar)
        layout.addWidget(tab_content)

    def create_copyable_prompt_widget(self, prompt_text):
        """Create a hover-reveal copy button widget for cursor prompts"""
        
        # Custom widget class for hover detection
        class HoverCopyWidget(QFrame):
            def __init__(self, prompt_text, parent=None):
                super().__init__(parent)
                self.prompt_text = prompt_text
                self.copy_button = None
                self.setup_ui()
            
            def setup_ui(self):
                # Container styling
                self.setStyleSheet("""
                    QFrame {
                        padding: 10px;
                        margin: 5px;
                        background-color: rgba(255, 255, 255, 0.05);
                        border-radius: 6px;
                        border: 1px solid transparent;
                    }
                    QFrame:hover {
                        background-color: rgba(255, 255, 255, 0.08);
                        border: 1px solid rgba(255, 255, 255, 0.1);
                    }
                """)
                
                # Layout: text takes most space, button on right
                layout = QHBoxLayout(self)
                layout.setContentsMargins(10, 10, 10, 10)
                
                # Prompt text
                self.prompt_label = QLabel(self.prompt_text)
                self.prompt_label.setWordWrap(True)
                self.prompt_label.setStyleSheet("""
                    QLabel {
                        color: rgba(255, 255, 255, 0.9);
                        background: transparent;
                        border: none;
                        padding: 0px;
                        margin: 0px;
                    }
                """)
                layout.addWidget(self.prompt_label, 1)  # Take most space
                
                # Copy button (initially hidden)
                try:
                    from qfluentwidgets import ToolButton
                    from qfluentwidgets.common.icon import FluentIcon
                    
                    self.copy_button = ToolButton(FluentIcon.COPY)
                    self.copy_button.setToolTip("Copy to clipboard")
                    self.copy_button.setVisible(False)  
                    self.copy_button.clicked.connect(self.copy_to_clipboard)
                    layout.addWidget(self.copy_button, 0)  
                except ImportError:
                    # Fallback: regular button
                    self.copy_button = QPushButton("📋")
                    self.copy_button.setFixedSize(30, 30)
                    self.copy_button.setVisible(False)
                    self.copy_button.clicked.connect(self.copy_to_clipboard)
                    layout.addWidget(self.copy_button, 0)
            
            def enterEvent(self, event):
                """Show copy button on hover"""
                if self.copy_button:
                    self.copy_button.setVisible(True)
                super().enterEvent(event)
            
            def leaveEvent(self, event):
                """Hide copy button when hover ends"""
                if self.copy_button:
                    self.copy_button.setVisible(False)
                super().leaveEvent(event)
            
            def copy_to_clipboard(self):
                """Copy prompt text to system clipboard"""
                try:
                    QApplication.clipboard().setText(self.prompt_text)
                    # Visual feedback - change icon to checkmark with blue background
                    if self.copy_button:
                        try:
                            from qfluentwidgets.common.icon import FluentIcon
                            
                            # Store original state
                            original_tooltip = self.copy_button.toolTip()
                            
                            # Change to success state
                            self.copy_button.setIcon(FluentIcon.ACCEPT)
                            self.copy_button.setToolTip("Copied!")
                            self.copy_button.setStyleSheet("""
                                QToolButton {
                                    background-color: #2196F3;
                                    border-radius: 4px;
                                    padding: 4px;
                                }
                                QToolButton:hover {
                                    background-color: #1976D2;
                                }
                            """)
                            
                            # Reset after 1.5 seconds
                            def reset_button():
                                if self.copy_button:
                                    self.copy_button.setIcon(FluentIcon.COPY)
                                    self.copy_button.setToolTip(original_tooltip)
                                    self.copy_button.setStyleSheet("")  
                            
                            QTimer.singleShot(1500, reset_button)
                            
                        except ImportError:
                            # Fallback for regular button
                            original_text = self.copy_button.text()
                            self.copy_button.setText("✓")
                            self.copy_button.setStyleSheet("""
                                QPushButton {
                                    background-color: #2196F3;
                                    color: white;
                                    border-radius: 4px;
                                }
                            """)
                            QTimer.singleShot(1500, lambda: (
                                self.copy_button.setText(original_text),
                                self.copy_button.setStyleSheet("")
                            ))
                except Exception as e:
                    print(f"Copy failed: {e}")
        
        return HoverCopyWidget(prompt_text)

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
            r'\*\*Task Overview:\*\*.*',  
            r'Task Overview:.*'  
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                return text[match.start():].strip()
        
        return text.strip()
    
    def on_current_task_generated(self, task_number, task_name, task_detail):
        """Handle successful generation of current task details"""
        
        logger.info(f"TASK DETAIL API RESPONSE RECEIVED")
        logger.info(f"Task {task_number}: {task_name}")
        
        from src.core.ai.project_prompts import extract_task_json_from_response
        clean_json = extract_task_json_from_response(task_detail)
        
        # Debug: Print what AI returned for total_project_tasks
        try:
            import json
            task_data = json.loads(clean_json)
            total_tasks = task_data.get('total_project_tasks')
            print(f"🔍 AI returned total_project_tasks: {total_tasks}")
        except:
            print("🔍 Could not parse AI response for total_project_tasks")
        
        self.project_config['task_details'][task_number] = clean_json
        
        # Extract total project tasks FIRST, before showing the task
        if not hasattr(self, 'task_names') or not self.task_names:
            try:
                import json
                task_data = json.loads(clean_json)
                total_tasks = task_data.get('total_project_tasks', 7)
                if isinstance(total_tasks, int) and 7 <= total_tasks <= 12:
                    self.task_names = [f"Task {i}" for i in range(1, total_tasks + 1)]
                    print(f"✅ Created {total_tasks} tasks: {self.task_names}")
                else:
                    self.task_names = [f"Task {i}" for i in range(1, 8)]  # 7 tasks fallback
            except Exception as e:
                self.task_names = [f"Task {i}" for i in range(1, 8)]  # 7 tasks fallback
                print(f"❌ Error creating task list: {e}")
        
        if self.current_project_id:
            self.project_ops.update_project_progress(
                self.current_project_id, 
                self.current_task_number,
                self.project_config.get('task_details', {})
            )
        self.show_complete_current_task(task_name, clean_json)
        
        # Start background job AFTER task is saved and UI updated
        self.start_background_task_generation()
    
    def set_total_tasks_from_json(self, task_json):
        """Extract total task count from AI response and generate task headers"""
        try:
            import json
            task_data = json.loads(task_json) if isinstance(task_json, str) else task_json
            
            # Check if AI provided total_project_tasks
            if 'total_project_tasks' in task_data:
                total_tasks = task_data.get('total_project_tasks')
                
                # Validate (minimum 7, maximum 12)
                if isinstance(total_tasks, int) and 7 <= total_tasks <= 12:
                    logger.info(f"AI specified {total_tasks} total tasks for this project")
                    # Generate task headers using existing system
                    self.generate_task_headers_for_total_count(total_tasks)
                    return
                else:
                    logger.warning(f"AI provided invalid total_project_tasks: {total_tasks}")
            
            # Fallback: Use default task header generation
            logger.info("No valid total_project_tasks from AI, using existing task header generation")
            self.generate_task_headers_for_total_count(7)  # Minimum fallback
                
        except Exception as e:
            logger.error(f"Error extracting total tasks from JSON: {e}")
            self.generate_task_headers_for_total_count(7)  # Minimum fallback
    
    def generate_task_headers_for_total_count(self, total_tasks: int):
        """Generate task headers using existing AI system for the specified count"""
        try:
            # Use existing task header generation but specify the count needed
            project_description = self.project_config.get('project_description', '')
            selected_language = self.project_config.get('language', 'Python')
            
            # Create modified prompt that asks for specific number of tasks
            from core.ai.project_prompts import create_task_headers_prompt
            headers_prompt = create_task_headers_prompt(project_description, selected_language, total_tasks)
            
            # Generate headers using existing system
            generator = ProjectGenerator()
            task_headers = generator.generate_task_headers_with_prompt(headers_prompt)
            
            if task_headers:
                self.parse_and_set_task_names(task_headers, total_tasks)
            else:
                logger.error("Failed to generate task headers, using fallback")
                self.use_fallback_task_names(total_tasks)
                
        except Exception as e:
            logger.error(f"Error generating task headers: {e}")
            self.use_fallback_task_names(total_tasks)
    
    def use_fallback_task_names(self, total_tasks: int):
        """Simple fallback task names"""
        self.task_names = [f"Task {i}" for i in range(1, total_tasks + 1)]
        self.project_config['task_names'] = self.task_names
        logger.info(f"Using fallback: {total_tasks} tasks")
    
    def parse_and_set_task_names(self, task_headers: str, expected_count: int):
        """Parse task headers response and extract task names"""
        # Simple parsing - extract task names from headers response
        # This will use existing parsing logic for task headers
        import re
        tasks = re.findall(r'\*\*Task \d+:\*\*(.*?)(?=\*\*Task|\Z)', task_headers, re.DOTALL)
        
        if len(tasks) >= expected_count:
            self.task_names = [task.strip().split('\n')[0] for task in tasks[:expected_count]]
            self.project_config['task_names'] = self.task_names
            logger.info(f"Extracted {len(self.task_names)} task names from headers")
        else:
            self.use_fallback_task_names(expected_count)
    
    def on_current_task_failed(self, task_number, task_name, error_message):
        """Handle failed generation of current task details"""

        logger.error(f"🎯 Task {task_number}: {task_name}")
        logger.error(f"💥 Error: {error_message}")
        
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
        logger.info(f"🎨 RENDERING COMPLETE TASK UI")
        logger.info(f"🎯 Task name: {task_name}")
        logger.info(f"📏 Task detail length: {len(task_detail)} chars")
        logger.info(f"📋 Task number: {self.current_task_number}")
        
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        import json
        print(f"🔍 DEBUG: self.task_names = {getattr(self, 'task_names', 'NOT SET')}")
        print(f"🔍 DEBUG: len(self.task_names) = {len(getattr(self, 'task_names', []))}")
        
        # Get total tasks from AI response instead of task_names array
        total_tasks_from_ai = len(getattr(self, 'task_names', []))  # fallback
        task_title = task_name
        
        try:
            task_data = json.loads(task_detail)
            # Get total tasks directly from AI's response
            if 'total_project_tasks' in task_data:
                total_tasks_from_ai = task_data['total_project_tasks']
                print(f"🔍 DEBUG: Using total_project_tasks from AI: {total_tasks_from_ai}")
            
            if 'ticket_number' in task_data:
                ticket_display = f"Ticket {task_data['ticket_number']}"
            else:
                ticket_display = f"Task {self.current_task_number} of {total_tasks_from_ai}"
                
            if 'title' in task_data:
                task_title = task_data['title']
        except (json.JSONDecodeError, Exception):
            ticket_display = f"Task {self.current_task_number} of {total_tasks_from_ai}"
        
        # Create horizontal layout for ticket info and story points
        ticket_info_layout = QHBoxLayout()
        
        progress_label = QLabel(ticket_display)
        progress_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: rgba(255, 255, 255, 0.6);
            }
        """)
        ticket_info_layout.addWidget(progress_label)
        
        try:
            if 'task_data' in locals() and task_data:
                # story_points is nested under description
                story_points = None
                if 'description' in task_data and isinstance(task_data['description'], dict):
                    story_points = task_data['description'].get('story_points')
                elif 'story_points' in task_data:
                    story_points = task_data['story_points']
                
                if story_points:
                    # Create custom label class with manual tooltip
                    class StoryPointsLabel(QLabel):
                        def __init__(self, text, parent=None):
                            super().__init__(text, parent)
                            self.tooltip_text = ""
                            
                        def set_custom_tooltip(self, text):
                            self.tooltip_text = text
                            
                        def enterEvent(self, event):
                            print("[DEBUG] Mouse entered story points widget!")
                            if self.tooltip_text:
                                # Show tooltip manually at cursor position
                                QToolTip.showText(event.globalPos(), self.tooltip_text, self)
                            super().enterEvent(event)
                            
                        def leaveEvent(self, event):
                            print("[DEBUG] Mouse left story points widget!")
                            QToolTip.hideText()
                            super().leaveEvent(event)
                    
                    story_points_label = StoryPointsLabel(f"⭐ {story_points} Story Points")
                    
                    # Set custom tooltip instead of Qt's built-in tooltip
                    tooltip_text = ("Story Points estimate how much effort this task requires.\n"
                                  "• 1-2 points: Quick task (15-30 minutes)\n"
                                  "• 3-5 points: Medium task (30-60 minutes)\n" 
                                  "• 6+ points: Complex task (1+ hours)")
                    story_points_label.set_custom_tooltip(tooltip_text)
                    # Ensure widget can receive mouse events
                    story_points_label.setEnabled(True)
                # Simplified styling to avoid mouse event conflicts
                story_points_label.setStyleSheet("""
                    QLabel {
                        background-color: rgba(52, 152, 219, 0.8);
                        color: white;
                        padding: 4px 8px;
                        border-radius: 12px;
                        font-size: 12px;
                        font-weight: bold;
                        margin-left: 10px;
                    }
                    QLabel:hover {
                        background-color: rgba(52, 152, 219, 1.0);
                    }
                """)
                ticket_info_layout.addWidget(story_points_label)
        except:
            pass
        
        ticket_info_layout.addStretch()
        ticket_info_layout.setAlignment(Qt.AlignCenter)
        
        # Add some margin
        ticket_widget = QWidget()
        ticket_widget.setLayout(ticket_info_layout)
        ticket_widget.setStyleSheet("margin-bottom: 10px;")
        scroll_layout.addWidget(ticket_widget)
        
        # Task header - use the title from JSON
        task_header = QLabel(task_title)
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
        
        rendered_new_cursor_ui = False
        try:
            if 'task_data' in locals() and isinstance(task_data, dict) \
               and 'cursor_system_prompt' in task_data and 'steps' in task_data:
                self.render_cursor_prompts(scroll_layout, task_data)
                rendered_new_cursor_ui = True
                try:
                    if task_data.get('steps') and isinstance(task_data['steps'], list) and task_data['steps'][0].get('title'):
                        task_header.setText(task_data['steps'][0]['title'])
                except Exception:
                    pass
        except Exception:
            pass
        
        # Create task card - pass the already parsed data if available
        if not rendered_new_cursor_ui:
            if 'task_data' in locals():
                self.create_task_card(scroll_layout, task_detail, task_data)
            else:
                self.create_task_card(scroll_layout, task_detail)
        
        # Create tab bar for task content
        if not rendered_new_cursor_ui:
            if TAB_BAR_AVAILABLE and 'task_data' in locals():
                self.create_task_tabs(scroll_layout, task_data, task_detail)
            else:
                # Fallback: original task browser
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
            """)
                formatted_detail = self.convert_task_detail_to_html(task_detail)
                task_browser.setHtml(formatted_detail)
                scroll_layout.addWidget(task_browser)
        
        # Cursor evaluation section
        self.add_cursor_evaluation_section(scroll_layout, task_name)
        
        # Add skip project option
        self.add_skip_project_button(scroll_layout)
        
        scroll_layout.addStretch()
        self.scroll_area.setWidget(scroll_widget)
        
        # Update navigation - show complete button and control next button
        task_completed = self.project_ops.is_task_completed(self.current_project_id, self.current_task_number) if self.current_project_id else False
        task_completed = task_completed if task_completed is not None else False
        self.update_task_navigation(task_completed)
        
        if self.current_task_number < total_tasks_from_ai:
            next_task = self.current_task_number + 1
            self.next_button.setText(f"Task {next_task} →")
        else:
            self.next_button.setText("Complete Project →")
        
        self.next_button.setVisible(True)
        self.next_button.setEnabled(task_completed)
        self.back_button.setEnabled(True)
    
    def update_task_navigation(self, task_completed):
        """Update the navigation buttons based on task completion status"""
        if task_completed:
            # Task is completed - hide complete button, show completed status in button text
            self.complete_button.setText("Task Completed")
            self.complete_button.setEnabled(False)
            self.complete_button.setStyleSheet("""
                QPushButton {
                    font-size: 14px;
                    color: #27AE60;
                    background-color: rgba(39, 174, 96, 0.1);
                    border: 2px solid #27AE60;
                    border-radius: 8px;
                    padding: 12px 24px;
                }
            """)
        else:
            # Task is not completed - show complete button
            self.complete_button.setText("Mark Task as Complete")
            self.complete_button.setEnabled(True)
            self.complete_button.setStyleSheet("""
                QPushButton {
                    font-size: 14px;
                    color: white;
                    background-color: #27AE60;
                    border: none;
                    border-radius: 8px;
                    padding: 12px 24px;
                }
                QPushButton:hover {
                    background-color: #229954;
                }
            """)
        
        # Always show the complete button when viewing a task
        self.complete_button.setVisible(True)
    
    def add_complete_task_button(self, layout):
        """Add Complete Task button"""
        # Check if task is already completed
        task_completed = self.project_ops.is_task_completed(self.current_project_id, self.current_task_number) if self.current_project_id else False
        
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(0, 20, 0, 20)
        
        if task_completed:
            # Show completed status
            complete_label = QLabel("Task Completed")
            complete_label.setAlignment(Qt.AlignCenter)
            complete_label.setStyleSheet("""
                QLabel {
                    font-size: 16px;
                    font-weight: bold;
                    color: #27AE60;
                    padding: 15px 30px;
                    background-color: rgba(39, 174, 96, 0.1);
                    border: 2px solid #27AE60;
                    border-radius: 25px;
                }
            """)
            button_layout.addWidget(complete_label)
        else:
            # Show complete button
            complete_button = QPushButton("Mark Task as Complete")
            complete_button.setStyleSheet("""
                QPushButton {
                    font-size: 16px;
                    font-weight: bold;
                    color: white;
                    background-color: #27AE60;
                    border: none;
                    border-radius: 25px;
                    padding: 15px 30px;
                    margin: 10px;
                }
                QPushButton:hover {
                    background-color: #229954;
                    transform: translateY(-1px);
                }
                QPushButton:pressed {
                    background-color: #1E8449;
                }
            """)
            complete_button.clicked.connect(self.complete_current_task)
            button_layout.addWidget(complete_button)
        
        layout.addWidget(button_container)
    
    def complete_current_task(self):
        """Mark the current task as completed"""
        if self.current_project_id and hasattr(self, 'current_task_number'):
            # Update task status to completed
            success = self.project_ops.update_task_status(
                self.current_project_id, 
                self.current_task_number, 
                'completed'
            )
            
            if success:
                # Update navigation to show completed status and enable next button
                self.update_task_navigation(task_completed=True)
                self.next_button.setEnabled(True)
    
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
        
        # Generate evaluation prompt with current task details
        project_description = self.project_config.get('project_description', '')
        selected_language = self.project_config.get('language', 'Python')
        current_task_detail = self.project_config.get('task_details', {}).get(self.current_task_number, '')
        evaluation_prompt = self.create_cursor_evaluation_prompt(task_name, project_description, selected_language, current_task_detail)
        
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
        copy_button = QPushButton("Copy Prompt for Cursor")
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
    
    def create_cursor_evaluation_prompt(self, task_name, project_description, selected_language, current_task_detail=""):
        """Create an educational evaluation prompt for Cursor AI with full context"""
        
        clean_project_desc = project_description
        if project_description:
            import re
            patterns = [
                r'1\.\s*\*\*Project Title\*\*:.*', 
                r'\*\*Project Title\*\*:.*',        
                r'Project Title:.*'
            ]
            for pattern in patterns:
                match = re.search(pattern, project_description, re.DOTALL | re.IGNORECASE)
                if match:
                    clean_project_desc = project_description[match.start():]
                    break
        
        # Parse task details to extract key information
        task_context = ""
        if current_task_detail:
            try:
                import json
                task_data = json.loads(current_task_detail)
                
                # Extract system prompt and steps if available
                if 'cursor_system_prompt' in task_data:
                    task_context += f"\nSYSTEM PROMPT:\n{task_data['cursor_system_prompt']}\n"
                
                if 'steps' in task_data and isinstance(task_data['steps'], list):
                    task_context += "\nTASK STEPS:\n"
                    for i, step in enumerate(task_data['steps'], 1):
                        step_title = step.get('title', f'Step {i}')
                        step_intent = step.get('intent', '')
                        task_context += f"{i}. {step_title}"
                        if step_intent:
                            task_context += f" - {step_intent}"
                        task_context += "\n"
                        
                        # Include acceptance criteria
                        cursor_prompt = step.get('cursor_prompt', {})
                        acceptance_criteria = cursor_prompt.get('acceptance_criteria', [])
                        if acceptance_criteria:
                            task_context += "   Acceptance Criteria:\n"
                            for criterion in acceptance_criteria:
                                task_context += f"   - {criterion}\n"
                
            except (json.JSONDecodeError, Exception):
                # Fallback to raw task detail
                task_context = f"\nTASK DETAILS:\n{current_task_detail[:500]}..." if len(current_task_detail) > 500 else f"\nTASK DETAILS:\n{current_task_detail}"
        
        return f"""Please evaluate my progress on this coding task and help me learn:

=== PROJECT CONTEXT ===
{clean_project_desc if clean_project_desc else 'Educational coding project'}

=== CURRENT TASK ===
Task: {task_name}
Language: {selected_language}
Task Number: {self.current_task_number} of {len(getattr(self, 'task_names', []))}
{task_context}

=== EDUCATIONAL EVALUATION INSTRUCTIONS ===
As an AI tutor for a student aged 12-18, please:

1. **Analyze my code and files** to understand what I've built
2. **Check task completion** against the requirements above
3. **Rate my progress** (0-100%) with specific reasoning
4. **Teach me concepts** - Explain the software engineering concepts I used in simple terms
5. **Provide study resources** - Give me specific websites, tutorials, or topics to study next
6. **Connect to real-world** - Explain how this code relates to actual software engineering

=== RESPONSE FORMAT ===
Please structure your response as follows:

**Progress Rating:** [0-100%] 
- What percentage complete am I and why?
- What specific requirements did I meet or miss?

**What You Built:**
- Summary of the code/files I created
- Key functions or components I implemented

**Engineering Concepts You Used:**
- Explain each concept in simple terms (like I'm 12-18 years old)
- Why these concepts matter in software engineering
- How they solve real problems

**Study Next (with specific resources):**
- 3-4 specific topics to learn next
- Include links to tutorials, documentation, or learning sites
- Explain why each topic will help me grow as a developer

**Encouragement & Growth:**
- What I did well and should be proud of
- Specific areas where I can improve
- How this task prepares me for more advanced programming

**🔗 Real-World Connection:**
- How this type of code is used in actual software companies
- What kinds of projects use these concepts
- Career paths that build on these skills

Please analyze my files now and give me detailed educational feedback!"""
    
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
        if hasattr(self, 'viewing_continued_project') and self.viewing_continued_project:
            self.viewing_continued_project = False
            self.show_project_choice()
        elif self.current_step == 1:
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
        """Complete the wizard - redirect to dashboard and show success flyout"""
        
        # Show success flyout
        if FLYOUT_AVAILABLE:
            try:
                InfoBar.success(
                    title='Project Completed!',
                    content="Congratulations! You've successfully completed your project. Great work!",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP_RIGHT,
                    duration=4000,  # 4 seconds
                    parent=self.main_window
                )
            except Exception as e:
                logger.error(f"Failed to show success flyout: {e}")
        
        if hasattr(self.main_window, 'show_dashboard'):
            QTimer.singleShot(100, self._redirect_and_refresh_dashboard)
        else:
            logger.error("Main window doesn't have show_dashboard method")
            
        logger.info("Project completed successfully - redirected to dashboard")
    
    def _redirect_and_refresh_dashboard(self):
        """Redirect to dashboard and refresh the project stats"""
        self.main_window.show_dashboard()
        
        if hasattr(self.main_window, 'dashboard_view') and hasattr(self.main_window.dashboard_view, 'refresh_project_stats'):
            QTimer.singleShot(200, self.main_window.dashboard_view.refresh_project_stats) 
    def start_background_task_generation(self):
        """Start background generation of remaining empty tasks"""
        if not hasattr(self, 'current_project_id') or not self.current_project_id:
            return
        
        if hasattr(self, 'background_generator') and self.background_generator.isRunning():
            return 
        
        total_tasks = len(self.task_names)  # fallback
        task_1_detail = self.project_config.get('task_details', {}).get(1, '')
        try:
            import json
            task_data = json.loads(task_1_detail)
            if 'total_project_tasks' in task_data:
                total_tasks = task_data['total_project_tasks']
                print(f"🔴 Using total_project_tasks from Task 1: {total_tasks}")
            else:
                print(f"🔴 No total_project_tasks in Task 1, using fallback: {total_tasks}")
        except Exception as e:
            print(f"🔴 Could not parse Task 1 for total_project_tasks: {e}")
            pass
        
        self.background_generator = BackgroundTaskGenerator(
            self.task_names,
            self.project_config.get('task_details', {}),
            self.project_config.get('project_description', ''),
            self.project_config.get('language', 'Python'),
            self.current_task_number,
            self.current_project_id,
            self.project_ops,
            total_tasks
        )
        self.background_generator.task_generated.connect(self.on_background_task_generated)
        self.background_generator.start() 
    
    def on_current_task_streaming(self, task_number, task_name, partial_content):
        """Handle streaming updates for current task generation"""
        logger.info(f"📡 Streaming update - Task {task_number}: {len(partial_content)} chars")
        print(f"[STREAM] Task {task_number}: {len(partial_content)} characters generated")
        print(f"[STREAM] Content preview: {partial_content[:200]}...")
        print(f"[STREAM] Content ending: ...{partial_content[-100:]}")
        
        # Update UI with streaming content
        if not hasattr(self, 'streaming_text_browser'):
            # Create streaming UI on first update
            self._create_streaming_ui(task_number, task_name)
        
        # Update the text browser with current content
        self.streaming_text_browser.setPlainText(partial_content)
        
        # Auto-scroll to bottom to show latest content
        cursor = self.streaming_text_browser.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.streaming_text_browser.setTextCursor(cursor)
    
    def _create_streaming_ui(self, task_number, task_name):
        """Create UI elements for displaying streaming content"""
        from PySide6.QtWidgets import QTextBrowser, QVBoxLayout, QWidget, QLabel
        
        # Create new scroll widget for streaming content
        scroll_widget = QWidget()
        layout = QVBoxLayout(scroll_widget)
        
        # Task header
        header = QLabel(f"Task {task_number}: {task_name}")
        header.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: bold;
                color: rgba(255, 255, 255, 1.0);
                margin-bottom: 15px;
                padding: 10px;
                background-color: rgba(255, 255, 255, 0.05);
                border-radius: 8px;
            }
        """)
        layout.addWidget(header)
        
        # Streaming text browser
        self.streaming_text_browser = QTextBrowser()
        self.streaming_text_browser.setReadOnly(True)
        self.streaming_text_browser.setStyleSheet("""
            QTextBrowser {
                font-size: 14px;
                font-family: 'Courier New', monospace;
                line-height: 1.4;
                color: rgba(255, 255, 255, 0.9);
                background-color: rgba(0, 0, 0, 0.3);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 8px;
                padding: 15px;
            }
        """)
        layout.addWidget(self.streaming_text_browser)
        
        # Replace current scroll area content
        self.scroll_area.setWidget(scroll_widget)
    
    def generate_and_show_current_task(self):
        """Generate and display the current task details"""
        logger.info(f"🎬 STARTING TASK DETAIL GENERATION")
        logger.info(f"📋 Current task number: {self.current_task_number}")
        
        # Show loading for current task
        self.show_current_task_loading()
        
        # Generate current task details
        current_task_name = f"Task {self.current_task_number}"  # Don't reference task_names array
        project_description = self.project_config.get('project_description', '')
        selected_language = self.project_config.get('language', 'Python')
        
        logger.info(f"🎯 Generating details for task: {current_task_name}")
        logger.info(f"🔧 Using language: {selected_language}")
        logger.info(f"📝 Project description length: {len(project_description)} chars")
        
        # Start worker for current task
        logger.info(f"🏗️ Creating TaskDetailWorker instance")
        self.current_task_worker = TaskDetailWorker(
            current_task_name, self.current_task_number, 
            project_description, selected_language, use_local_only=False
        )
        
        logger.info(f"🔗 Connecting TaskDetailWorker signals")
        self.current_task_worker.detail_generated.connect(self.on_current_task_generated)
        self.current_task_worker.detail_failed.connect(self.on_current_task_failed)
        self.current_task_worker.detail_streaming.connect(self.on_current_task_streaming)
        
        logger.info(f"🚀 Starting TaskDetailWorker thread")
        self.current_task_worker.start()
        
        logger.info(f"✅ TaskDetailWorker thread started successfully")

    def show_current_task_loading(self):
        """Show loading screen for current task generation"""
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # Simple loading message
        loading_label = QLabel("Generating task details...")
        loading_label.setAlignment(Qt.AlignCenter)
        loading_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
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

    def render_cursor_prompts(self, layout, task_data):
        """Render the new cursor prompt schema: system prompt + steps with system_role, prompt, and acceptance criteria.
        Also provide a single copy button to copy the entire composed prompt (including section titles)."""
        try:
            combined_lines = []
            
            # system_prompt = task_data.get('cursor_system_prompt', '')
            # # Reuse copyable prompt widget for system prompt
            # sys_prompt_widget = self.create_copyable_prompt_widget(system_prompt)
            # layout.addWidget(sys_prompt_widget)
            
            
            # Steps
            steps = task_data.get('steps', [])
            if isinstance(steps, list):
                for idx, step in enumerate(steps, start=1):
                    # Step container
                    step_frame = QFrame()
                    step_frame.setStyleSheet("""
                        QFrame {
                            background-color: rgba(255, 255, 255, 0.04);
                            border: 1px solid rgba(255, 255, 255, 0.08);
                            border-radius: 10px;
                            padding: 12px;
                            margin: 8px 0px;
                        }
                    """)
                    step_layout = QVBoxLayout(step_frame)
                    step_layout.setSpacing(8)
                    
                    # Step title
                    step_title = step.get('title') or f"Step {idx}"
                    step_intent = step.get('intent')
                    title_label = QLabel(f"Step {idx}: {step_title}")
                    title_label.setStyleSheet("""
                        QLabel {
                            font-size: 15px;
                            font-weight: 600;
                            color: rgba(255, 255, 255, 0.95);
                        }
                    """)
                    step_layout.addWidget(title_label)
                    
                    if step_intent:
                        intent_label = QLabel(step_intent)
                        intent_label.setWordWrap(True)
                        intent_label.setStyleSheet("""
                            QLabel {
                                font-size: 13px;
                                color: rgba(255, 255, 255, 0.75);
                                margin-left: 4px;
                            }
                        """)
                        step_layout.addWidget(intent_label)
                    
                    cp = step.get('cursor_prompt', {}) if isinstance(step, dict) else {}
                    system_role = cp.get('system_role', '')
                    step_prompt = cp.get('prompt', '')
                    ac_list = cp.get('acceptance_criteria', []) or []
                    

                    
                    step_combined = "System role: " + (system_role or "") + "\n\n" \
                                  + "Prompt: " + (step_prompt or "") + "\n\n" \
                                  + "Acceptance criteria:\n" + "\n".join(f"- {c}" for c in ac_list)
                    
                    step_copy_widget = self.create_copyable_prompt_widget(step_combined)
                    step_layout.addWidget(step_copy_widget)
                    
                    combined_lines.append(f"\nStep {idx}: {step_title}")
                    if step_intent:
                        combined_lines.append(f"Intent: {step_intent}")
                    combined_lines.append("System role:")
                    combined_lines.append(system_role or "")
                    combined_lines.append("Prompt:")
                    combined_lines.append(step_prompt or "")
                    combined_lines.append("Acceptance Criteria:")
                    if isinstance(ac_list, list) and ac_list:
                        combined_lines.extend([f"- {c}" for c in ac_list])
                    else:
                        combined_lines.append("(none provided)")
                    
                    layout.addWidget(step_frame)
            
            # Copy entire composed prompt (one go)
            combined_text = "\n\n".join(combined_lines)
            # full_copy_btn = QPushButton("📋 Copy Entire Prompt")
            # full_copy_btn.setStyleSheet("""
            #     QPushButton {
            #         font-size: 14px;
            #         color: white;
            #         background-color: #2ecc71;
            #         border: none;
            #         border-radius: 6px;
            #         padding: 10px 16px;
            #         margin-top: 12px;
            #     }
            #     QPushButton:hover { background-color: #27ae60; }
            # """)
            # full_copy_btn.clicked.connect(lambda checked=False, text=combined_text: self.copy_to_clipboard(text))
            # layout.addWidget(full_copy_btn)
        
        except Exception as e:
            logger.error(f"Error rendering cursor prompts: {e}")
