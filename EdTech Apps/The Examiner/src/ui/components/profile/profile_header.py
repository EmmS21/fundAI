from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                              QPushButton, QFileDialog)
from PySide6.QtCore import Qt, QSize, QTimer, QRunnable, QThreadPool, QMetaObject, Q_ARG
from PySide6.QtGui import QColor, QPixmap, QPainter, QTransform
from src.utils.constants import PRIMARY_COLOR
from src.data.database.operations import UserOperations
from src.utils.country_flags import get_country_flag
from src.core.firebase.client import FirebaseClient
from src.core.mongodb.client import MongoDBClient
from src.data.cache.cache_manager import CacheManager, CacheStatus, CacheProgressStatus
from datetime import datetime
import logging
import os
from src.core import services

logger = logging.getLogger(__name__)

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
        
        # Horizontal layout for status indicators
        status_layout = QHBoxLayout()
        status_layout.setAlignment(Qt.AlignCenter)
        status_layout.setSpacing(10)
        
        # Add subscription status indicator
        self._add_subscription_indicator(status_layout)
        
        # Add status layout to main layout
        layout.addLayout(status_layout)
        
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
                    """Get subscription status from Firebase in a background thread"""
                    try:
                        # First check - is MongoDB connected? If so, we know subscription is active
                        mongo_client = MongoDBClient()
                        
                        if mongo_client.initialized and mongo_client.connected:
                            # If MongoDB is connected, subscription is definitely active
                            logger.info("MongoDB is connected - subscription is active")
                            self.status_label.setText("Active")
                            self.status_label.setStyleSheet("""
                                padding: 3px 8px;
                                border-radius: 10px;
                                font-size: 12px;
                                font-weight: bold;
                                background-color: #e7f5e7;
                                color: #1e7e34;
                                border: 1px solid #a3d9a3;
                            """)
                            return
                            
                        # Fallback to Firebase check if MongoDB isn't available
                        firebase = FirebaseClient()
                        data = firebase.check_subscription_status()
                        
                        if 'error' in data:
                            logger.error(f"Error checking subscription: {data['error']}")
                            self.status_label.setText("Unknown")
                            self.status_label.setStyleSheet("""
                                padding: 3px 8px;
                                border-radius: 10px;
                                font-size: 12px;
                                font-weight: bold;
                                background-color: #e9ecef;
                                color: #495057;
                                border: 1px solid #ced4da;
                            """)
                            return
                            
                        # Extract subscription info from response (handle nested structure)
                        if 'fields' in data:
                            fields = data['fields']
                        else:
                            fields = data
                            
                        subscription_type = None
                        is_expired = False
                        
                        # Extract subscription type - handle both formats
                        if 'subscribed' in fields:
                            sub_field = fields['subscribed']
                            if isinstance(sub_field, dict) and 'stringValue' in sub_field:
                                subscription_type = sub_field['stringValue'].lower()
                            elif isinstance(sub_field, str):
                                subscription_type = sub_field.lower()
                                
                        # Check expiration if we found a subscription type
                        if subscription_type in ["trial", "annual", "monthly"]:
                            # Check expiration date if available
                            if 'sub_end' in fields:
                                try:
                                    # Handle different date formats
                                    end_field = fields['sub_end']
                                    date_str = None
                                    
                                    if isinstance(end_field, dict) and 'stringValue' in end_field:
                                        date_str = end_field['stringValue']
                                    elif isinstance(end_field, str):
                                        date_str = end_field
                                        
                                    # Only try to parse if we have a non-empty string
                                    if date_str and len(date_str.strip()) > 0:
                                        # Remove Z or timezone offset if present
                                        if date_str.endswith('Z'):
                                            date_str = date_str[:-1]
                                        sub_end = datetime.fromisoformat(date_str)
                                        is_expired = datetime.now() > sub_end
                                except ValueError as e:
                                    logger.error(f"Error parsing date: {e}")
                                    # Continue with default expiration status
                            
                            # Determine final status
                            if is_expired:
                                status_text = "Expired"
                                status_style = """
                                    padding: 3px 8px;
                                    border-radius: 10px;
                                    font-size: 12px;
                                    font-weight: bold;
                                    background-color: #f8d7da;
                                    color: #721c24;
                                    border: 1px solid #f5c6cb;
                                """
                            else:
                                status_text = "Active"
                                status_style = """
                                    padding: 3px 8px;
                                    border-radius: 10px;
                                    font-size: 12px;
                                    font-weight: bold;
                                    background-color: #e7f5e7;
                                    color: #1e7e34;
                                    border: 1px solid #a3d9a3;
                                """
                        else:
                            status_text = "Inactive"
                            status_style = """
                                padding: 3px 8px;
                                border-radius: 10px;
                                font-size: 12px;
                                font-weight: bold;
                                background-color: #f8d7da;
                                color: #721c24;
                                border: 1px solid #f5c6cb;
                            """
                            
                        logger.info(f"Subscription status: {status_text}")
                        self.status_label.setText(status_text)
                        self.status_label.setStyleSheet(status_style)
                        
                    except Exception as e:
                        logger.error(f"Error in subscription checker: {e}")
                        self.status_label.setText("Unknown")
                        self.status_label.setStyleSheet("""
                            padding: 3px 8px;
                            border-radius: 10px;
                            font-size: 12px;
                            font-weight: bold;
                            background-color: #e9ecef;
                            color: #495057;
                            border: 1px solid #ced4da;
                        """)
            
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
        
    def _format_status(self, status):
        """Format the status text for display"""
        status_map = {
            "active": "Active",
            "expired": "Expired",
            "inactive": "Inactive",
            "unknown": "Unknown"
        }
        return status_map.get(status, "Unknown")
        
    def _get_status_style(self, status):
        """Get the CSS style for the status label"""
        base_style = """
            padding: 3px 8px;
            border-radius: 10px;
            font-size: 12px;
            font-weight: bold;
        """
        
        if status == "active":
            return base_style + """
                background-color: #e7f5e7;
                color: #1e7e34;
                border: 1px solid #a3d9a3;
            """
        elif status == "expired":
            return base_style + """
                background-color: #f8d7da;
                color: #721c24;
                border: 1px solid #f5c6cb;
            """
        elif status == "inactive":
            return base_style + """
                background-color: #f8d7da;
                color: #721c24;
                border: 1px solid #f5c6cb;
            """
        else:  # unknown
            return base_style + """
                background-color: #e9ecef;
                color: #495057;
                border: 1px solid #ced4da;
            """
        