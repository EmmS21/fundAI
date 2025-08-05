from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton, 
    QHBoxLayout, QFrame, QGridLayout, QDialog, QScrollArea, QInputDialog
)
from PySide6.QtCore import Qt
from core.ai_manager import AIManager
from core.database import Database
from ui.assessment_view import AssessmentView
from ui.dashboard_view import DashboardView

class ScoreDetailDialog(QDialog):
    def __init__(self, section_name, percentage, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{section_name} - Score Details")
        self.setMinimumSize(400, 300)
        self.setup_ui(section_name, percentage)
    
    def setup_ui(self, section_name, percentage):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Title
        title = QLabel(section_name)
        title.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #2c3e50;
                margin-bottom: 10px;
            }
        """)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Score
        score_label = QLabel(f"Your Score: {percentage:.1f}%")
        score_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #3498db;
                margin-bottom: 20px;
            }
        """)
        score_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(score_label)
        
        # Simple interpretation based on score
        interpretation_text = self.get_simple_interpretation(section_name, percentage)
        
        interpretation_label = QLabel(interpretation_text)
        interpretation_label.setWordWrap(True)
        interpretation_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #2c3e50;
                line-height: 1.6;
                background-color: #f8f9fa;
                padding: 15px;
                border-radius: 8px;
            }
        """)
        layout.addWidget(interpretation_label)
        
        # Close button
        close_button = QPushButton("Close")
        close_button.setStyleSheet("""
            QPushButton {
                font-size: 14px;
                padding: 12px 30px;
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 6px;
                margin-top: 20px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)
    
    def get_simple_interpretation(self, section_name, percentage):
        """Get a simple text interpretation of the score"""
        
        # Determine score range
        if percentage >= 90:
            level = "Excellent"
            description = "You have outstanding skills in this area!"
        elif percentage >= 75:
            level = "Strong"
            description = "You have good understanding and skills in this area."
        elif percentage >= 60:
            level = "Good"    
            description = "You have a solid foundation with room to grow."
        elif percentage >= 45:
            level = "Basic"
            description = "You understand the basics but need more practice."
        elif percentage >= 25:
            level = "Developing"
            description = "You're starting to understand these concepts. Focus and practice will help you improve."
        elif percentage > 0:
            level = "Beginning"
            description = "You got some answers right! This shows you have potential to learn these skills."
        else:
            level = "Starting Point"
            description = "You didn't get any answers correct this time, but that's okay - everyone learns at their own pace."
        
        # Section-specific feedback
        if "Overall" in section_name:
            if percentage >= 75:
                specific = f"Your overall engineering thinking shows you're ready for {'advanced' if percentage >= 90 else 'intermediate'} programming projects."
            elif percentage >= 45:
                specific = "You're ready for beginner programming projects with guidance and practice."
            elif percentage > 0:
                specific = "We'll start with basic programming concepts and build up your engineering skills step by step."
            else:
                specific = "Don't worry! We'll begin with the fundamentals and help you develop engineering thinking."
        elif "Debugging" in section_name:
            if percentage >= 75:
                specific = f"Your problem-solving approach {'excels at systematic debugging' if percentage >= 90 else 'shows good logical thinking'}."
            elif percentage >= 45:
                specific = "Your debugging skills can be improved with practice and structured approaches."
            elif percentage > 0:
                specific = "We'll teach you systematic debugging techniques starting with simple problems."
            else:
                specific = "We'll help you learn how to approach problems step-by-step."
        elif "Planning" in section_name:
            if percentage >= 75:
                specific = f"Your collaboration skills {'are excellent for team projects' if percentage >= 90 else 'show good potential'}."
            elif percentage >= 45:
                specific = "Your teamwork and planning skills will develop through practice."
            elif percentage > 0:
                specific = "We'll help you learn project planning and collaboration basics."
            else:
                specific = "We'll start with simple teamwork concepts and project organization."
        elif "Systems" in section_name:
            if percentage >= 75:
                specific = f"Your systems thinking {'shows strong architectural understanding' if percentage >= 90 else 'demonstrates good data concepts'}."
            elif percentage >= 45:
                specific = "Your understanding of systems and data will grow with experience."
            elif percentage > 0:
                specific = "We'll help you understand how data flows through systems."
            else:
                specific = "We'll start with basic data organization and simple system concepts."
        else:
            specific = "This shows how you approach engineering challenges."
        
        return f"{level} ({percentage:.1f}%)\n\n{description}\n\n{specific}"

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("The Engineer - AI Tutor")
        self.setMinimumSize(900, 700)
        
        self.ai_manager = AIManager()
        self.database = Database()
        self.current_user = None
        
        self.setup_ui()
    
    def check_existing_user(self):
        """Check if there's an existing user who has completed the assessment"""
        if not self.database.is_connected():
            return None
        
        try:
            # Get the most recent user who has completed assessment
            cursor = self.database.connection.cursor()
            cursor.execute("""
                SELECT * FROM users 
                WHERE overall_score IS NOT NULL 
                ORDER BY assessment_completed_at DESC 
                LIMIT 1
            """)
            row = cursor.fetchone()
            
            if row:
                user_data = dict(row)
                # Load section scores from JSON
                if user_data['section_scores']:
                    import json
                    user_data['section_scores'] = json.loads(user_data['section_scores'])
                
                print(f"Found existing user: {user_data['username']} with score {user_data['overall_score']:.1f}%")
                return user_data
            
            return None
        except Exception as e:
            print(f"Error checking existing user: {e}")
            return None
    
    def setup_ui(self):
        # Check if user has already completed assessment
        existing_user = self.check_existing_user()
        
        if existing_user:
            # User has completed assessment - go straight to dashboard
            self.current_user = existing_user
            self.show_dashboard()
        else:
            # New user - show assessment
            self.assessment_view = AssessmentView()
            self.assessment_view.assessment_completed.connect(self.handle_assessment_results)
            self.setCentralWidget(self.assessment_view)
    
    def handle_assessment_results(self, results):
        print(f"Assessment completed! Overall score: {results['overall_score']:.1f}%")
        
        # Store results and show results view
        self.assessment_results = results
        self.show_results(results)
    
    def show_results(self, results):
        results_widget = QWidget()
        layout = QVBoxLayout(results_widget)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(25)
        
        # Title
        title = QLabel("Assessment Complete!")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            QLabel {
                font-size: 32px;
                font-weight: bold;
                color: #2c3e50;
                margin-bottom: 10px;
            }
        """)
        layout.addWidget(title)
        
        # Subtitle
        subtitle = QLabel("Here's how you think like an engineer:")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("""
            QLabel {
                font-size: 16px;
                color: #7f8c8d;
                margin-bottom: 30px;
            }
        """)
        layout.addWidget(subtitle)
        
        # Overall score box - full width
        overall_box = self.create_overall_score_box(results['overall_score'])
        layout.addWidget(overall_box)
        
        # Section scores - 3 boxes in a row
        section_layout = QHBoxLayout()
        section_layout.setSpacing(15)
        
        for section, scores in results['section_scores'].items():
            percentage = (scores['correct'] / scores['total']) * 100
            score_box = self.create_section_score_box(section, percentage)
            section_layout.addWidget(score_box)
        
        layout.addLayout(section_layout)
        
        # Start building button
        start_button = QPushButton("🚀 Start Building")
        start_button.setStyleSheet("""
            QPushButton {
                font-size: 18px;
                font-weight: bold;
                color: white;
                background-color: #27ae60;
                border: none;
                border-radius: 12px;
                padding: 18px 40px;
                margin-top: 30px;
            }
            QPushButton:hover {
                background-color: #229954;
                transform: translateY(-2px);
            }
        """)
        start_button.clicked.connect(self.start_building)
        layout.addWidget(start_button)
        
        self.setCentralWidget(results_widget)
    
    def create_overall_score_box(self, percentage):
        score_frame = QFrame()
        score_frame.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border: 2px solid #bdc3c7;
                border-radius: 12px;
                height: 120px;
                margin: 10px 0px;
            }}
            QFrame:hover {{
                background-color: black;
                border-color: black;
            }}
        """)
        score_frame.setCursor(Qt.PointingHandCursor)
        score_frame.mousePressEvent = lambda event: self.show_overall_score_details(percentage)
        
        layout = QVBoxLayout(score_frame)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(2)
        
        # Icon and title at top
        header_layout = QHBoxLayout()
        header_layout.setAlignment(Qt.AlignCenter)
        
        icon_label = QLabel("🎯")
        icon_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                border: none;
                background: transparent;
            }
        """)
        header_layout.addWidget(icon_label)
        
        title_label = QLabel("Overall Score")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                font-weight: bold;
                color: black;
                border: none;
                background: transparent;
                margin-left: 3px;
            }
        """)
        header_layout.addWidget(title_label)
        
        layout.addLayout(header_layout)
        
        # Add stretch to push percentage to center
        layout.addStretch()
        
        # Percentage in center
        percent_label = QLabel(f"{percentage:.1f}%")
        percent_label.setAlignment(Qt.AlignCenter)
        percent_label.setStyleSheet("""
            QLabel {
                font-size: 32px;
                font-weight: bold;
                color: black;
                border: none;
                background: transparent;
            }
        """)
        layout.addWidget(percent_label)
        
        # Add stretch to balance
        layout.addStretch()
        
        # Store references for hover effect
        score_frame.icon_label = icon_label
        score_frame.title_label = title_label
        score_frame.percent_label = percent_label
        score_frame.enterEvent = lambda event: self.set_overall_hover_style(score_frame, True)
        score_frame.leaveEvent = lambda event: self.set_overall_hover_style(score_frame, False)
        
        return score_frame
    
    def create_section_score_box(self, section_name, percentage):
        score_frame = QFrame()
        score_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 2px solid #bdc3c7;
                border-radius: 12px;
                height: 120px;
                margin: 10px 0px;
            }
            QFrame:hover {
                background-color: black;
                border-color: black;
            }
        """)
        score_frame.setCursor(Qt.PointingHandCursor)
        score_frame.mousePressEvent = lambda event: self.show_score_details(section_name, percentage)
        
        # Get appropriate icon for section
        section_icons = {
            'Problem Solving & Debugging': '🐛',
            'Planning & Collaboration': '🤝', 
            'Data & Systems Thinking': '💾'
        }
        
        # Get short names for display
        section_short_names = {
            'Problem Solving & Debugging': 'Debugging',
            'Planning & Collaboration': 'Planning', 
            'Data & Systems Thinking': 'Systems'
        }
        
        layout = QVBoxLayout(score_frame)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(2)
        
        # Icon and title at top
        header_layout = QHBoxLayout()
        header_layout.setAlignment(Qt.AlignCenter)
        
        icon_label = QLabel(section_icons.get(section_name, '📊'))
        icon_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                border: none;
                background: transparent;
            }
        """)
        header_layout.addWidget(icon_label)
        
        title_label = QLabel(section_short_names.get(section_name, section_name))
        title_label.setStyleSheet("""
            QLabel {
                font-size: 10px;
                font-weight: bold;
                color: black;
                border: none;
                background: transparent;
                margin-left: 3px;
            }
        """)
        header_layout.addWidget(title_label)
        
        layout.addLayout(header_layout)
        
        # Add stretch to push percentage to center
        layout.addStretch()
        
        # Percentage in center
        percent_label = QLabel(f"{percentage:.1f}%")
        percent_label.setAlignment(Qt.AlignCenter)
        percent_label.setStyleSheet("""
            QLabel {
                font-size: 22px;
                font-weight: bold;
                color: black;
                border: none;
                background: transparent;
            }
        """)
        layout.addWidget(percent_label)
        
        # Add stretch to balance
        layout.addStretch()
        
        # Store references for hover effect
        score_frame.icon_label = icon_label
        score_frame.title_label = title_label
        score_frame.percent_label = percent_label
        score_frame.enterEvent = lambda event: self.set_section_hover_style(score_frame, True)
        score_frame.leaveEvent = lambda event: self.set_section_hover_style(score_frame, False)
        
        return score_frame
    
    def set_overall_hover_style(self, frame, is_hover):
        if is_hover:
            # Black background, white text
            frame.icon_label.setStyleSheet("""
                QLabel {
                    font-size: 18px;
                    border: none;
                    background: transparent;
                }
            """)
            frame.title_label.setStyleSheet("""
                QLabel {
                    font-size: 12px;
                    font-weight: bold;
                    color: white;
                    border: none;
                    background: transparent;
                    margin-left: 3px;
                }
            """)
            frame.percent_label.setStyleSheet("""
                QLabel {
                    font-size: 32px;
                    font-weight: bold;
                    color: white;
                    border: none;
                    background: transparent;
                }
            """)
        else:
            # White background, black text
            frame.icon_label.setStyleSheet("""
                QLabel {
                    font-size: 18px;
                    border: none;
                    background: transparent;
                }
            """)
            frame.title_label.setStyleSheet("""
                QLabel {
                    font-size: 12px;
                    font-weight: bold;
                    color: black;
                    border: none;
                    background: transparent;
                    margin-left: 3px;
                }
            """)
            frame.percent_label.setStyleSheet("""
                QLabel {
                    font-size: 32px;
                    font-weight: bold;
                    color: black;
                    border: none;
                    background: transparent;
                }
            """)
    
    def set_section_hover_style(self, frame, is_hover):
        if is_hover:
            # Black background, white text
            frame.icon_label.setStyleSheet("""
                QLabel {
                    font-size: 16px;
                    border: none;
                    background: transparent;
                }
            """)
            frame.title_label.setStyleSheet("""
                QLabel {
                    font-size: 10px;
                    font-weight: bold;
                    color: white;
                    border: none;
                    background: transparent;
                    margin-left: 3px;
                }
            """)
            frame.percent_label.setStyleSheet("""
                QLabel {
                    font-size: 22px;
                    font-weight: bold;
                    color: white;
                    border: none;
                    background: transparent;
                }
            """)
        else:
            # White background, black text
            frame.icon_label.setStyleSheet("""
                QLabel {
                    font-size: 16px;
                    border: none;
                    background: transparent;
                }
            """)
            frame.title_label.setStyleSheet("""
                QLabel {
                    font-size: 10px;
                    font-weight: bold;
                    color: black;
                    border: none;
                    background: transparent;
                    margin-left: 3px;
                }
            """)
            frame.percent_label.setStyleSheet("""
                QLabel {
                    font-size: 22px;
                    font-weight: bold;
                    color: black;
                    border: none;
                    background: transparent;
                }
            """)
    
    def show_overall_score_details(self, percentage):
        dialog = ScoreDetailDialog("Overall Engineering Score", percentage, self)
        dialog.exec()
    
    def show_score_details(self, section_name, percentage):
        dialog = ScoreDetailDialog(section_name, percentage, self)
        dialog.exec()
    
    def start_building(self):
        # Only create user and store results if this is a new assessment
        if hasattr(self, 'assessment_results') and not self.current_user:
            # Prompt user for their name
            name, ok = QInputDialog.getText(
                self, 
                'Welcome!', 
                'What\'s your name?',
                text='Student'
            )
            
            if not ok or not name.strip():
                name = 'Student'
            
            # Prompt for age
            age, ok = QInputDialog.getInt(
                self,
                'About You',
                'How old are you?',
                15,  # default value
                12,  # minimum value
                18   # maximum value
            )
            
            if not ok:
                age = 15
            
            # Create user
            user_id = self.database.create_user(name.strip(), age)
            
            if user_id:
                # Store assessment results
                success = self.database.store_assessment_results(user_id, self.assessment_results)
                
                if success:
                    # Get the complete user data from database
                    self.current_user = self.database.get_user_by_id(user_id)
                    print(f"Created new user: {name} (ID: {user_id}) with score {self.assessment_results['overall_score']:.1f}%")
                else:
                    print("Failed to store assessment results")
                    return
            else:
                print("Failed to create user")
                return
        
        # Navigate to dashboard
        self.show_dashboard()
    
    def show_dashboard(self):
        self.dashboard_view = DashboardView(self.current_user, self)
        self.setCentralWidget(self.dashboard_view) 