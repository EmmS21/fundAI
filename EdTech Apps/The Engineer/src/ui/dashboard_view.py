from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QGridLayout, QLineEdit, QSpinBox, QDialog, QFormLayout, QFileDialog, QSizePolicy, QInputDialog
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPixmap, QPainter, QPainterPath
import shutil
from pathlib import Path

class CircularImageWidget(QWidget):
    def __init__(self, size=116, parent=None):
        super().__init__(parent)
        self.size = size
        self.pixmap = None
        self.setFixedSize(size, size)
        self.setCursor(Qt.PointingHandCursor)
        
    def setPixmap(self, pixmap):
        self.pixmap = pixmap
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        if self.pixmap:
            # Create circular clipping path
            path = QPainterPath()
            path.addEllipse(0, 0, self.size, self.size)
            painter.setClipPath(path)
            
            # Draw the image
            painter.drawPixmap(0, 0, self.size, self.size, self.pixmap)
        else:
            # Draw camera icon when no image
            painter.setPen(Qt.NoPen)
            painter.setBrush(Qt.white)
            painter.setOpacity(0.1)
            painter.drawEllipse(0, 0, self.size, self.size)
            
            # Draw camera icon
            painter.setOpacity(0.7)
            painter.setPen(Qt.white)
            font = painter.font()
            font.setPointSize(self.size // 4)  # 2x bigger than before
            painter.setFont(font)
            
            # Center the camera icon
            painter.drawText(self.rect(), Qt.AlignCenter, "📷")
        
        painter.end()
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.upload_profile_picture()
            
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
                user_id = self.parent().user_data.get('id', 'unknown')
                file_extension = Path(file_path).suffix
                new_filename = f"user_{user_id}_profile{file_extension}"
                new_path = profile_dir / new_filename
                
                # Copy the file
                shutil.copy2(file_path, new_path)
                
                # Update database
                if 'id' in self.parent().user_data:
                    success = self.parent().main_window.database.update_user_profile(
                        self.parent().user_data['id'],
                        profile_picture=str(new_path)
                    )
                    
                    if success:
                        # Update local data
                        self.parent().user_data['profile_picture'] = str(new_path)
                        
                        # Update UI
                        self.parent().load_profile_picture()
                        
                        print(f"Profile picture updated: {new_path}")
                    else:
                        print("Failed to update profile picture in database")
                
            except Exception as e:
                print(f"Error uploading profile picture: {e}")

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
        
        welcome_label = QLabel("The Engineer!")
        welcome_label.setStyleSheet("""
            QLabel {
                font-size: 26px;
                font-weight: 600;
                color: rgba(255, 255, 255, 0.9);
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }
        """)
        header_layout.addWidget(welcome_label)
        
        header_layout.addStretch()
        
        # Profile edit button


        
        layout.addLayout(header_layout)
        
        profile_frame = QFrame()
        profile_frame.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.05);
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
                padding: 20px;
                margin-bottom: 25px;
            }
        """)
        
        profile_layout = QHBoxLayout(profile_frame)
        profile_layout.setSpacing(15)
        profile_layout.setAlignment(Qt.AlignVCenter)
        
        self.profile_picture = CircularImageWidget(116)
        
        self.load_profile_picture()
        

        
        profile_layout.addWidget(self.profile_picture, 1)
        
        self.name_value = QLabel(self.user_data.get('username', 'Student'))
        self.name_value.setWordWrap(False)
        self.name_value.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.name_value.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.name_value.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.95);
                font-size: 16px;
                font-weight: 600;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }
        """)
        self.name_value.mousePressEvent = self.edit_name
        profile_layout.addWidget(self.name_value, 0)
        
        score_value = f"{self.user_data.get('overall_score', 0):.1f}%"
        self.score_value = QLabel(score_value)
        self.score_value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.score_value.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.score_value.setStyleSheet("""
            QLabel {
                color: rgba(100, 210, 255, 0.9);
                font-size: 18px;
                font-weight: 700;
                font-family: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, 'Courier New', monospace;
            }
        """)
        profile_layout.addWidget(self.score_value, 0)
        
        layout.addWidget(profile_frame)
        
        # Two simple QLabel boxes
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(20)
        
        logic_label = QLabel("🧩 Logic Puzzles")
        logic_label.setAlignment(Qt.AlignCenter)
        logic_label.setStyleSheet("""
            QLabel {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 10px;
                padding: 20px;
                font-size: 16px;
                font-weight: 600;
                color: rgba(255, 255, 255, 0.9);
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }
            QLabel:hover {
                background: rgba(255, 255, 255, 0.1);
                border-color: rgba(255, 255, 255, 0.2);
            }
        """)
        
        build_label = QLabel("🏗️ Build Projects")
        build_label.setAlignment(Qt.AlignCenter)
        build_label.setStyleSheet("""
            QLabel {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 10px;
                padding: 20px;
                font-size: 16px;
                font-weight: 600;
                color: rgba(255, 255, 255, 0.9);
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }
            QLabel:hover {
                background: rgba(255, 255, 255, 0.1);
                border-color: rgba(255, 255, 255, 0.2);
            }
        """)
        
        bottom_layout.addWidget(logic_label)
        bottom_layout.addWidget(build_label)
        
        layout.addLayout(bottom_layout)
        
        # Footer
        footer_label = QLabel("FundaAI - Learn by building")
        footer_label.setAlignment(Qt.AlignCenter)
        footer_label.setStyleSheet("""
            QLabel {
                font-size: 15px;
                color: rgba(255, 255, 255, 0.6);
                font-style: italic;
                margin-top: 20px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }
        """)
        layout.addWidget(footer_label)
    

    
    def edit_name(self, event):
        if event.button() == Qt.LeftButton:
            current_name = self.user_data.get('username', 'Student')
            new_name, ok = QInputDialog.getText(
                self, 
                "Edit Name", 
                "Enter your name:",
                text=current_name
            )
            if ok and new_name.strip():
                self.user_data['username'] = new_name.strip()
                self.name_value.setText(new_name.strip())
                if 'id' in self.user_data:
                    self.main_window.database.update_user_profile(
                        self.user_data['id'],
                        username=new_name.strip()
                    )
    
    def load_profile_picture(self):
        """Load and display the user's profile picture"""
        picture_path = self.user_data.get('profile_picture', '')
        
        if picture_path and Path(picture_path).exists():
            # Load user's profile picture
            pixmap = QPixmap(picture_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(116, 116, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                self.profile_picture.setPixmap(scaled_pixmap)
                return
        
        # Show default avatar - clear the widget
        self.profile_picture.pixmap = None
        self.profile_picture.update()
    
    def create_proper_circular_image(self, source_pixmap, size=116):
        """Create a properly circular cropped image"""
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