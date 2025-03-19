from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                              QPushButton, QFileDialog)
from PySide6.QtCore import Qt, QSize, QTimer, QRunnable, QThreadPool, QMetaObject, Q_ARG
from PySide6.QtGui import QColor, QPixmap, QPainter, QTransform
from src.utils.constants import PRIMARY_COLOR
from src.data.database.operations import UserOperations
from src.utils.country_flags import get_country_flag
from src.core.firebase.client import FirebaseClient

class ProfileHeader(QWidget):
    def __init__(self, user_data):
        super().__init__()
        self.user_data = user_data
        self._setup_ui()
    
    def _setup_ui(self):
        # Main vertical layout
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        self.setLayout(layout)
        
        # Profile picture container with purple border
        self.profile_pic = QLabel()
        self.profile_pic.setFixedSize(100, 100)
        self.profile_pic.setStyleSheet(f"""
            QLabel {{
                background-color: {PRIMARY_COLOR};
                border-radius: 50px;
                border: 3px solid #9333EA;  /* Purple border */
                color: white;
                font-size: 36px;
            }}
        """)
        self.profile_pic.setText(self.user_data.full_name[0].upper())
        self.profile_pic.setAlignment(Qt.AlignCenter)
        
        # Load profile picture if it exists in database
        if self.user_data.profile_picture:
            print("Found profile picture in database")
            print("Image data length:", len(self.user_data.profile_picture))
            print("First few bytes:", self.user_data.profile_picture[:20])  # Look at data format
            
            pixmap = QPixmap()
            pixmap.loadFromData(self.user_data.profile_picture)
            
            # Rotate image back to original orientation
            transform = QTransform().rotate(-270)  # Adjust degrees as needed (-90, 90, 180)
            pixmap = pixmap.transformed(transform)
            
            # Create a square image by cropping to the smallest dimension
            size = min(pixmap.width(), pixmap.height())
            square_pixmap = pixmap.copy(
                (pixmap.width() - size) // 2,
                (pixmap.height() - size) // 2,
                size, size
            )
            
            # Scale to desired size (100x100)
            scaled_pixmap = square_pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            
            # Create and apply circular mask
            mask = QPixmap(100, 100)
            mask.fill(Qt.transparent)
            painter = QPainter(mask)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setBrush(Qt.white)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(0, 0, 100, 100)
            painter.end()
            
            # Apply mask to create circular image
            result = QPixmap(100, 100)
            result.fill(Qt.transparent)
            painter = QPainter(result)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setCompositionMode(QPainter.CompositionMode_Source)
            painter.drawPixmap(0, 0, mask)
            painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
            painter.drawPixmap(0, 0, scaled_pixmap)
            painter.end()
            
            self.profile_pic.setPixmap(result)
        
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
        
        # Get flag emoji for country
        country_with_flag = self.user_data.country
        if self.user_data.country:
            flag_emoji = get_country_flag(self.user_data.country)
            if flag_emoji:
                country_with_flag = f"{self.user_data.country} {flag_emoji}"
        
        location = f"{self.user_data.city}, {country_with_flag}" if self.user_data.city else country_with_flag
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
        
        # Add subscription status indicator
        self._add_subscription_indicator(layout)
        
    def _add_subscription_indicator(self, parent_layout):
        """Add subscription status indicator to the header"""
        try:
            # Create container widget
            subscription_container = QWidget()
            subscription_layout = QHBoxLayout(subscription_container)
            subscription_layout.setContentsMargins(5, 5, 5, 5)
            
            # Create status label
            status_label = QLabel("Subscription:")
            status_label.setStyleSheet("font-weight: bold;")
            
            # Create status indicator
            self.subscription_status = QLabel("Checking...")
            self.subscription_status.setStyleSheet("color: #666;")
            
            # Add to layout
            subscription_layout.addWidget(status_label)
            subscription_layout.addWidget(self.subscription_status)
            subscription_layout.addStretch()
            
            # Add to parent layout
            parent_layout.addWidget(subscription_container, alignment=Qt.AlignRight)
            
            # Check subscription status in background
            QTimer.singleShot(500, self._update_subscription_status)
            
        except Exception as e:
            print(f"Error adding subscription indicator: {e}")
    
    def _update_subscription_status(self):
        """Update the subscription status indicator"""
        try:
            # Get status in background thread to avoid UI freezing
            class SubscriptionChecker(QRunnable):
                def __init__(self, status_label):
                    super().__init__()
                    self.status_label = status_label
                    
                def run(self):
                    try:
                        firebase = FirebaseClient()
                        status = firebase.check_subscription_status()
                        
                        # Pass result to main thread
                        QMetaObject.invokeMethod(
                            self.status_label, 
                            "setText",
                            Qt.QueuedConnection,
                            Q_ARG(str, self._format_status(status))
                        )
                        QMetaObject.invokeMethod(
                            self.status_label, 
                            "setStyleSheet",
                            Qt.QueuedConnection,
                            Q_ARG(str, self._get_status_style(status))
                        )
                    except Exception as e:
                        print(f"Error in subscription checker: {e}")
                        QMetaObject.invokeMethod(
                            self.status_label,
                            "setText",
                            Qt.QueuedConnection,
                            Q_ARG(str, "Unknown")
                        )
                        QMetaObject.invokeMethod(
                            self.status_label,
                            "setStyleSheet",
                            Qt.QueuedConnection,
                            Q_ARG(str, "color: orange;")
                        )
                        
                def _format_status(self, status):
                    """Format subscription status for display"""
                    if status.get('is_active', False):
                        subscription_type = status.get('type', 'active').capitalize()
                        return f"Active ({subscription_type})"
                    else:
                        return "Inactive"
                        
                def _get_status_style(self, status):
                    """Get style for subscription status"""
                    if status.get('is_active', False):
                        return "color: green; font-weight: bold;"
                    else:
                        return "color: red; font-weight: bold;"
            
            # Start background check
            checker = SubscriptionChecker(self.subscription_status)
            QThreadPool.globalInstance().start(checker)
            
        except Exception as e:
            print(f"Error updating subscription status: {e}")
            self.subscription_status.setText("Unknown")
            self.subscription_status.setStyleSheet("color: orange;")

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
            
            # Create circular mask
            pixmap = QPixmap()
            pixmap.loadFromData(image_data)
            
            # Rotate image back to original orientation
            transform = QTransform().rotate(-90)  # Adjust degrees as needed (-90, 90, 180)
            pixmap = pixmap.transformed(transform)
            
            # This part might be causing the rotation:
            # Create a square image by cropping to the smallest dimension
            size = min(pixmap.width(), pixmap.height())
            square_pixmap = pixmap.copy(
                (pixmap.width() - size) // 2,
                (pixmap.height() - size) // 2,
                size, size
            )
            
            # Scale while preserving aspect ratio
            scaled_size = min(square_pixmap.width(), square_pixmap.height())
            scaled_pixmap = square_pixmap.scaled(
                100, 100,
                Qt.KeepAspectRatioByExpanding,
                Qt.SmoothTransformation
            )
            
            # Center crop to square
            x = (scaled_pixmap.width() - 100) // 2
            y = (scaled_pixmap.height() - 100) // 2
            scaled_pixmap = scaled_pixmap.copy(x, y, 100, 100)
            
            # Create and apply circular mask
            mask = QPixmap(100, 100)
            mask.fill(Qt.transparent)
            painter = QPainter(mask)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setBrush(Qt.white)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(0, 0, 100, 100)
            painter.end()
            
            # Apply mask to create circular image
            result = QPixmap(100, 100)
            result.fill(Qt.transparent)
            painter = QPainter(result)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setCompositionMode(QPainter.CompositionMode_Source)
            painter.drawPixmap(0, 0, mask)
            painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
            painter.drawPixmap(0, 0, scaled_pixmap)
            painter.end()
            
            self.profile_pic.setPixmap(result)
        