from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                              QPushButton, QFileDialog)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QPixmap, QPainter, QPainterPath
from src.utils.constants import PRIMARY_COLOR
from src.data.database.operations import UserOperations

class CircularImageLabel(QLabel):
    def __init__(self, size=100):
        super().__init__()
        self.setFixedSize(size, size)
        self.radius = size // 2
        self.pixmap = None
        
    def setPixmap(self, pixmap):
        self.pixmap = pixmap
        self.update()
        
    def paintEvent(self, event):
        if not self.pixmap:
            # Draw default circular background with initial
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Draw purple background
            path = QPainterPath()
            path.addEllipse(0, 0, self.width(), self.height())
            painter.setClipPath(path)
            painter.fillPath(path, QColor(PRIMARY_COLOR))
            
            # Draw border
            painter.setPen(QColor("#9333EA"))
            painter.drawEllipse(1, 1, self.width()-2, self.height()-2)
            
            # Draw text if no image
            if self.text():
                painter.setPen(QColor("white"))
                painter.drawText(self.rect(), Qt.AlignCenter, self.text())
        else:
            # Draw circular image
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Create circular path
            path = QPainterPath()
            path.addEllipse(0, 0, self.width(), self.height())
            painter.setClipPath(path)
            
            # Scale pixmap to fit
            scaled_pixmap = self.pixmap.scaled(self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            
            # Center the pixmap
            x = (scaled_pixmap.width() - self.width()) // 2
            y = (scaled_pixmap.height() - self.height()) // 2
            painter.drawPixmap(-x, -y, scaled_pixmap)
            
            # Draw border
            painter.setPen(QColor("#9333EA"))
            painter.drawEllipse(1, 1, self.width()-2, self.height()-2)

class ProfileHeader(QWidget):
    def __init__(self, user_data):
        super().__init__()
        self.user_data = user_data
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        self.setLayout(layout)
        
        # Use CircularImageLabel instead of QLabel
        self.profile_pic = CircularImageLabel()
        
        # Load profile picture if it exists in database
        if self.user_data.profile_picture:
            pixmap = QPixmap()
            pixmap.loadFromData(self.user_data.profile_picture)
            self.profile_pic.setPixmap(pixmap)
        else:
            self.profile_pic.setText(self.user_data.full_name[0].upper())
        
        # Camera icon button
        camera_button = QPushButton("📷")
        camera_button.setFixedSize(32, 32)
        camera_button.setStyleSheet("""
            QPushButton {
                background-color: white;
                border-radius: 16px;
                color: #9333EA;
                font-size: 16px;
                border: none;
            }
            QPushButton:hover {
                background-color: #f3f4f6;
            }
        """)
        camera_button.clicked.connect(self._handle_image_upload)
        
        # Container for profile pic and camera button
        pic_container = QWidget()
        pic_layout = QHBoxLayout(pic_container)
        pic_layout.setAlignment(Qt.AlignCenter)
        
        # Create a wrapper widget to position the camera button
        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.addWidget(self.profile_pic)
        
        # Position camera button at bottom-right of profile pic
        camera_button.setParent(wrapper)
        camera_button.move(70, 70)  # Adjust these values to position the camera icon
        
        pic_layout.addWidget(wrapper)
        
        # Name label (centered)
        name_label = QLabel(self.user_data.full_name)
        name_label.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #1a1a1a;
            }
        """)
        name_label.setAlignment(Qt.AlignCenter)
        
        # Location container
        location_container = QWidget()
        location_layout = QHBoxLayout(location_container)
        location_layout.setAlignment(Qt.AlignCenter)
        
        # Location icon
        location_icon = QLabel("📍")  # Using emoji as placeholder, you might want to use a proper icon
        location_icon.setStyleSheet("""
            QLabel {
                font-size: 16px;
                color: #666666;
            }
        """)
        
        # Location text
        location = f"{self.user_data.city}, {self.user_data.country}" if self.user_data.city else self.user_data.country
        location_label = QLabel(location)
        location_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                color: #666666;
            }
        """)
        
        location_layout.addWidget(location_icon)
        location_layout.addWidget(location_label)
        
        # Add all widgets to main layout
        layout.addWidget(pic_container)
        layout.addWidget(name_label)
        layout.addWidget(location_container)
        
    def _handle_image_upload(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Select Profile Picture",
            "",
            "Images (*.png *.jpg *.jpeg)"
        )
        
        if file_name:
            # Read the image file as bytes
            with open(file_name, 'rb') as f:
                image_data = f.read()
            
            # Save to database
            UserOperations.update_user_profile_picture(self.user_data.id, image_data)
            
            # Update UI
            pixmap = QPixmap()
            pixmap.loadFromData(image_data)
            scaled_pixmap = pixmap.scaled(100, 100, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            self.profile_pic.setPixmap(scaled_pixmap)
        