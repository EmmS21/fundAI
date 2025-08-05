from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QGridLayout, QLineEdit, QSpinBox, QDialog, QFormLayout, QFileDialog
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPixmap
import shutil
from pathlib import Path

class ProfileEditDialog(QDialog):
    profile_updated = Signal(dict)
    
    def __init__(self, user_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Profile")
        self.setMinimumSize(300, 200)
        self.user_data = user_data
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Edit Your Profile")
        title.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #2c3e50;
                margin-bottom: 20px;
            }
        """)
        layout.addWidget(title)
        
        # Form
        form_layout = QFormLayout()
        
        # Name input
        self.name_input = QLineEdit()
        self.name_input.setText(self.user_data.get('username', ''))
        self.name_input.setStyleSheet("""
            QLineEdit {
                font-size: 14px;
                padding: 8px;
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                margin-bottom: 10px;
            }
            QLineEdit:focus {
                border-color: #3498db;
            }
        """)
        form_layout.addRow("Name:", self.name_input)
        
        # Age input
        self.age_input = QSpinBox()
        self.age_input.setRange(12, 18)
        self.age_input.setValue(self.user_data.get('age', 15))
        self.age_input.setStyleSheet("""
            QSpinBox {
                font-size: 14px;
                padding: 8px;
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                margin-bottom: 10px;
            }
            QSpinBox:focus {
                border-color: #3498db;
            }
        """)
        form_layout.addRow("Age:", self.age_input)
        
        layout.addLayout(form_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        cancel_button = QPushButton("Cancel")
        cancel_button.setStyleSheet("""
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
        """)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        save_button = QPushButton("Save")
        save_button.setStyleSheet("""
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
        """)
        save_button.clicked.connect(self.save_profile)
        button_layout.addWidget(save_button)
        
        layout.addLayout(button_layout)
    
    def save_profile(self):
        updated_data = {
            'username': self.name_input.text().strip(),
            'age': self.age_input.value()
        }
        
        if updated_data['username']:
            self.profile_updated.emit(updated_data)
            self.accept()

class DashboardView(QWidget):
    def __init__(self, user_data, main_window):
        super().__init__()
        self.user_data = user_data or {}
        self.main_window = main_window
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(25)
        
        # Header
        header_layout = QHBoxLayout()
        
        welcome_label = QLabel("🚀 Welcome to The Engineer!")
        welcome_label.setStyleSheet("""
            QLabel {
                font-size: 28px;
                font-weight: bold;
                color: #2c3e50;
            }
        """)
        header_layout.addWidget(welcome_label)
        
        header_layout.addStretch()
        
        # Profile edit button
        edit_button = QPushButton("✏️ Edit Profile")
        edit_button.setStyleSheet("""
            QPushButton {
                font-size: 14px;
                padding: 8px 16px;
                border: 2px solid #3498db;
                border-radius: 6px;
                background-color: white;
                color: #3498db;
            }
            QPushButton:hover {
                background-color: #3498db;
                color: white;
            }
        """)
        edit_button.clicked.connect(self.edit_profile)
        header_layout.addWidget(edit_button)
        
        layout.addLayout(header_layout)
        
        # Profile section - allows content to flow over
        profile_frame = QFrame()
        profile_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3498db, stop:1 #2980b9);
                border-radius: 15px;
                padding: 30px;
                margin-bottom: 20px;
                min-height: 200px;
            }
        """)
        
        profile_layout = QHBoxLayout(profile_frame)
        profile_layout.setSpacing(40)
        profile_layout.setAlignment(Qt.AlignCenter)
        
        # Profile picture section
        picture_layout = QVBoxLayout()
        picture_layout.setAlignment(Qt.AlignCenter)
        
        # Profile picture - bigger and more prominent
        self.profile_picture = QLabel()
        self.profile_picture.setFixedSize(180, 180)
        self.profile_picture.setStyleSheet("""
            QLabel {
                border: 4px solid white;
                border-radius: 90px;
                background-color: rgba(255, 255, 255, 0.2);
            }
        """)
        self.profile_picture.setAlignment(Qt.AlignCenter)
        self.profile_picture.setScaledContents(False)
        
        # Load existing profile picture or show default
        self.load_profile_picture()
        
        picture_layout.addWidget(self.profile_picture)
        
        # Upload button
        upload_button = QPushButton("📷")
        upload_button.setStyleSheet("""
            QPushButton {
                font-size: 16px;
                padding: 8px;
                background-color: rgba(255, 255, 255, 0.2);
                color: white;
                border: 2px solid white;
                border-radius: 20px;
                margin-top: 8px;
                min-width: 40px;
                max-width: 40px;
                min-height: 40px;
                max-height: 40px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.4);
                transform: scale(1.05);
            }
        """)
        upload_button.clicked.connect(self.upload_profile_picture)
        picture_layout.addWidget(upload_button)
        
        profile_layout.addLayout(picture_layout)
        
        # Profile info - clean, no labels
        info_layout = QVBoxLayout()
        info_layout.setAlignment(Qt.AlignVCenter)
        info_layout.setSpacing(15)
        
        # Name only
        self.name_value = QLabel(self.user_data.get('username', 'Student'))
        self.name_value.setWordWrap(True)
        self.name_value.setAlignment(Qt.AlignLeft)
        self.name_value.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 24px;
                font-weight: bold;
                margin-bottom: 5px;
            }
        """)
        info_layout.addWidget(self.name_value)
        
        # Score only
        score_value = f"{self.user_data.get('overall_score', 0):.1f}%"
        self.score_value = QLabel(score_value)
        self.score_value.setAlignment(Qt.AlignLeft)
        self.score_value.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.9);
                font-size: 28px;
                font-weight: bold;
            }
        """)
        info_layout.addWidget(self.score_value)
        
        profile_layout.addLayout(info_layout)
        profile_layout.addStretch()
        
        layout.addWidget(profile_frame)
        
        # Coming soon section
        coming_soon_frame = QFrame()
        coming_soon_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border-radius: 12px;
                padding: 30px;
            }
        """)
        
        coming_soon_layout = QVBoxLayout(coming_soon_frame)
        
        coming_soon_title = QLabel("🔧 Your Learning Journey Starts Here!")
        coming_soon_title.setAlignment(Qt.AlignCenter)
        coming_soon_title.setStyleSheet("""
            QLabel {
                font-size: 22px;
                font-weight: bold;
                color: #2c3e50;
                margin-bottom: 15px;
            }
        """)
        coming_soon_layout.addWidget(coming_soon_title)
        
        description = QLabel("""
Based on your assessment results, we're preparing personalized projects for you!

🎯 Coming Soon:
• Custom coding challenges matching your skill level
• Step-by-step tutorials for building real applications
• Project-based learning with immediate feedback
• Progress tracking as you develop your skills

Your engineering thinking assessment helps us create the perfect learning path just for you.
        """)
        description.setAlignment(Qt.AlignCenter)
        description.setWordWrap(True)
        description.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #2c3e50;
                line-height: 1.6;
                margin: 15px;
            }
        """)
        coming_soon_layout.addWidget(description)
        
        # Action cards grid
        cards_layout = QGridLayout()
        cards_layout.setSpacing(15)
        
        # Cards data
        cards = [
            {
                'icon': '🧩',
                'title': 'Logic Puzzles',
                'description': 'Sharpen your problem-solving skills',
                'color': '#e74c3c'
            },
            {
                'icon': '🏗️',
                'title': 'Build Projects',
                'description': 'Create real applications step by step',
                'color': '#f39c12'
            },
            {
                'icon': '🤖',
                'title': 'Code Practice',
                'description': 'Learn programming fundamentals',
                'color': '#9b59b6'
            },
            {
                'icon': '📊',
                'title': 'Track Progress',
                'description': 'See your skills grow over time',
                'color': '#1abc9c'
            }
        ]
        
        for i, card_data in enumerate(cards):
            card = self.create_feature_card(card_data)
            row = i // 2
            col = i % 2
            cards_layout.addWidget(card, row, col)
        
        coming_soon_layout.addLayout(cards_layout)
        
        layout.addWidget(coming_soon_frame)
        
        # Footer
        footer_label = QLabel("Get ready to build amazing things!")
        footer_label.setAlignment(Qt.AlignCenter)
        footer_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                color: #7f8c8d;
                font-style: italic;
                margin-top: 20px;
            }
        """)
        layout.addWidget(footer_label)
    
    def create_feature_card(self, card_data):
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border-left: 4px solid {card_data['color']};
                border-radius: 8px;
                padding: 20px;
                min-height: 100px;
            }}
            QFrame:hover {{
                background-color: #f8f9fa;
                transform: translateY(-2px);
            }}
        """)
        
        layout = QVBoxLayout(card)
        
        # Icon and title
        header_layout = QHBoxLayout()
        
        icon = QLabel(card_data['icon'])
        icon.setStyleSheet("""
            QLabel {
                font-size: 24px;
                margin-right: 10px;
            }
        """)
        header_layout.addWidget(icon)
        
        title = QLabel(card_data['title'])
        title.setStyleSheet(f"""
            QLabel {{
                font-size: 16px;
                font-weight: bold;
                color: {card_data['color']};
            }}
        """)
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Description
        description = QLabel(card_data['description'])
        description.setWordWrap(True)
        description.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: #7f8c8d;
                margin-top: 5px;
            }
        """)
        layout.addWidget(description)
        
        return card
    
    def edit_profile(self):
        dialog = ProfileEditDialog(self.user_data, self)
        dialog.profile_updated.connect(self.update_profile)
        dialog.exec()
    
    def load_profile_picture(self):
        """Load and display the user's profile picture"""
        picture_path = self.user_data.get('profile_picture', '')
        
        if picture_path and Path(picture_path).exists():
            # Load user's profile picture
            pixmap = QPixmap(picture_path)
            if not pixmap.isNull():
                # Create a square version that fits properly
                circular_pixmap = self.create_proper_circular_image(pixmap, 180)
                self.profile_picture.setPixmap(circular_pixmap)
                # Simple border styling only
                self.profile_picture.setStyleSheet("""
                    QLabel {
                        border: 4px solid white;
                        border-radius: 90px;
                    }
                """)
                return
        
        # Show default avatar
        self.profile_picture.clear()
        self.profile_picture.setText("👤")
        self.profile_picture.setStyleSheet("""
            QLabel {
                border: 4px solid white;
                border-radius: 90px;
                background-color: rgba(255, 255, 255, 0.2);
                font-size: 72px;
                color: white;
            }
        """)
    
    def create_proper_circular_image(self, source_pixmap, size):
        """Create a properly circular cropped image like the example"""
        from PySide6.QtGui import QPainter, QBrush, QPainterPath
        
        # Create final result pixmap
        result = QPixmap(size, size)
        result.fill(Qt.transparent)
        
        # Scale the image to fill the entire circle (crop if needed)
        scaled = source_pixmap.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        
        # Center the scaled image if it's larger than the target size
        x = (size - scaled.width()) // 2
        y = (size - scaled.height()) // 2
        
        # Create the painter and set up for circular clipping
        painter = QPainter(result)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Create circular clipping path
        path = QPainterPath()
        path.addEllipse(0, 0, size, size)
        painter.setClipPath(path)
        
        # Draw the image
        painter.drawPixmap(x, y, scaled)
        painter.end()
        
        return result
    

    
    def upload_profile_picture(self):
        """Handle profile picture upload"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Profile Picture",
            "",
            "Image Files (*.png *.jpg *.jpeg *.gif *.bmp)"
        )
        
        if file_path:
            try:
                # Create profile pictures directory
                profile_dir = Path("data/profile_pictures")
                profile_dir.mkdir(exist_ok=True)
                
                # Copy file to our directory with user ID in filename
                user_id = self.user_data.get('id', 'unknown')
                file_extension = Path(file_path).suffix
                new_filename = f"user_{user_id}_profile{file_extension}"
                new_path = profile_dir / new_filename
                
                # Copy the file
                shutil.copy2(file_path, new_path)
                
                # Update database
                if 'id' in self.user_data:
                    success = self.main_window.database.update_user_profile(
                        self.user_data['id'],
                        profile_picture=str(new_path)
                    )
                    
                    if success:
                        # Update local data
                        self.user_data['profile_picture'] = str(new_path)
                        
                        # Update UI
                        self.load_profile_picture()
                        
                        print(f"Profile picture updated: {new_path}")
                    else:
                        print("Failed to update profile picture in database")
                
            except Exception as e:
                print(f"Error uploading profile picture: {e}")
    
    def update_profile(self, updated_data):
        # Update database
        if 'id' in self.user_data:
            success = self.main_window.database.update_user_profile(
                self.user_data['id'],
                updated_data['username'],
                updated_data['age']
            )
            
            if success:
                # Update local data
                self.user_data.update(updated_data)
                
                # Update UI
                self.name_value.setText(updated_data['username'])
                
                print(f"Profile updated: {updated_data}")
            else:
                print("Failed to update profile in database") 