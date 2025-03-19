from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, 
                              QLabel, QPushButton, QSpacerItem, 
                              QSizePolicy)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap, QIcon
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class SubscriptionAlertDialog(QDialog):
    """Dialog for showing subscription alerts and status"""
    
    def __init__(self, subscription_data=None, parent=None):
        super().__init__(parent)
        self.subscription_data = subscription_data
        self.setWindowTitle("Subscription Status")
        self.setMinimumWidth(400)
        self.setStyleSheet("""
            QDialog {
                background-color: white;
            }
            QLabel#TitleLabel {
                font-size: 18px;
                font-weight: bold;
                color: #333333;
                margin-bottom: 10px;
            }
            QLabel#MessageLabel {
                font-size: 14px;
                color: #555555;
                margin-bottom: 15px;
            }
            QPushButton {
                background-color: #4285f4;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #357ae8;
            }
            QLabel#StatusActive {
                color: green;
                font-weight: bold;
            }
            QLabel#StatusExpired {
                color: red;
                font-weight: bold;
            }
            QLabel#StatusExpiring {
                color: orange;
                font-weight: bold;
            }
        """)
        
        self._setup_ui()
        
    def _setup_ui(self):
        """Set up the dialog UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        
        # Add icon and title
        header_layout = QHBoxLayout()
        
        # Create icon label
        icon_label = QLabel()
        icon = QIcon.fromTheme('dialog-information')
        if not icon.isNull():
            icon_label.setPixmap(icon.pixmap(QSize(32, 32)))
        else:
            # Fallback if theme icon not available
            icon_label.setText("ℹ️")
            icon_label.setStyleSheet("font-size: 24px;")
        
        # Title and subtitle
        title_layout = QVBoxLayout()
        title = QLabel("Subscription Status")
        title.setObjectName("TitleLabel")
        title_layout.addWidget(title)
        
        # Add title layout to header
        header_layout.addWidget(icon_label)
        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        
        # Add header to main layout
        layout.addLayout(header_layout)
        
        # Status message
        self.message_label = QLabel(self._get_status_message())
        self.message_label.setObjectName("MessageLabel")
        self.message_label.setWordWrap(True)
        layout.addWidget(self.message_label)
        
        # Detailed status
        if self.subscription_data:
            status_layout = QVBoxLayout()
            
            # Subscription type
            type_layout = QHBoxLayout()
            type_label = QLabel("Type:")
            type_label.setStyleSheet("font-weight: bold;")
            type_value = QLabel(self._get_subscription_type())
            type_layout.addWidget(type_label)
            type_layout.addWidget(type_value)
            type_layout.addStretch()
            status_layout.addLayout(type_layout)
            
            # Status
            status_layout = QHBoxLayout()
            status_label = QLabel("Status:")
            status_label.setStyleSheet("font-weight: bold;")
            status_value = QLabel(self._get_status_text())
            status_value.setObjectName(self._get_status_object_name())
            status_layout.addWidget(status_label)
            status_layout.addWidget(status_value)
            status_layout.addStretch()
            status_layout.addLayout(status_layout)
            
            # Expiry date if available
            if self._get_expiry_date():
                expiry_layout = QHBoxLayout()
                expiry_label = QLabel("Expires:")
                expiry_label.setStyleSheet("font-weight: bold;")
                expiry_value = QLabel(self._get_expiry_date())
                expiry_layout.addWidget(expiry_label)
                expiry_layout.addWidget(expiry_value)
                expiry_layout.addStretch()
                status_layout.addLayout(expiry_layout)
            
            layout.addLayout(status_layout)
        
        # Add buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        ok_button = QPushButton("OK")
        ok_button.setMinimumWidth(80)
        ok_button.clicked.connect(self.accept)
        button_layout.addWidget(ok_button)
        
        layout.addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Minimum, QSizePolicy.Expanding))
        layout.addLayout(button_layout)
    
    def _get_status_message(self):
        """Get main status message based on subscription data"""
        if not self.subscription_data:
            return "Unable to retrieve subscription information. Please check your connection and try again."
            
        if self.subscription_data.get('is_active', False):
            return "Your subscription is active. You have full access to all features and content."
        else:
            return "Your subscription is not active. Please contact support to access premium content."
    
    def _get_subscription_type(self):
        """Get subscription type from data"""
        if not self.subscription_data:
            return "Unknown"
            
        subscription_type = self.subscription_data.get('type', 'none')
        return subscription_type.capitalize()
    
    def _get_status_text(self):
        """Get status text from subscription data"""
        if not self.subscription_data:
            return "Unknown"
            
        if self.subscription_data.get('is_active', False):
            # Check if expiring soon
            expiry_date = self.subscription_data.get('expiry_date')
            if expiry_date:
                try:
                    # Parse the expiry date string to datetime
                    if isinstance(expiry_date, str):
                        expiry_dt = datetime.fromisoformat(expiry_date.replace('Z', '+00:00'))
                    else:
                        # Assume it's already a datetime or timestamp
                        expiry_dt = datetime.fromtimestamp(expiry_date)
                        
                    # Check if expiring within 7 days
                    days_left = (expiry_dt - datetime.now()).days
                    if days_left <= 7:
                        return f"Expiring soon ({days_left} days)"
                except Exception:
                    pass
                    
            return "Active"
        else:
            return "Expired"
    
    def _get_status_object_name(self):
        """Get object name for styling status text"""
        if not self.subscription_data:
            return ""
            
        if self.subscription_data.get('is_active', False):
            # Check if expiring soon
            expiry_date = self.subscription_data.get('expiry_date')
            if expiry_date:
                try:
                    # Parse the expiry date string to datetime
                    if isinstance(expiry_date, str):
                        expiry_dt = datetime.fromisoformat(expiry_date.replace('Z', '+00:00'))
                    else:
                        # Assume it's already a datetime or timestamp
                        expiry_dt = datetime.fromtimestamp(expiry_date)
                        
                    # Check if expiring within 7 days
                    days_left = (expiry_dt - datetime.now()).days
                    if days_left <= 7:
                        return "StatusExpiring"
                except Exception:
                    pass
                    
            return "StatusActive"
        else:
            return "StatusExpired"
    
    def _get_expiry_date(self):
        """Format expiry date for display"""
        if not self.subscription_data:
            return None
            
        expiry_date = self.subscription_data.get('expiry_date')
        if not expiry_date:
            return None
            
        try:
            # Parse the expiry date string to datetime
            if isinstance(expiry_date, str):
                expiry_dt = datetime.fromisoformat(expiry_date.replace('Z', '+00:00'))
            else:
                # Assume it's already a datetime or timestamp
                expiry_dt = datetime.fromtimestamp(expiry_date)
                
            # Format date for display
            return expiry_dt.strftime("%d %b %Y")
        except Exception as e:
            logger.error(f"Error formatting expiry date: {e}")
            return str(expiry_date)

# Utility function to display subscription alert
def show_subscription_alert(parent=None):
    """Show subscription alert dialog"""
    try:
        from src.core.firebase.client import FirebaseClient
        
        # Get subscription status
        firebase = FirebaseClient()
        subscription = firebase.check_subscription_status()
        
        # Show dialog
        dialog = SubscriptionAlertDialog(subscription, parent)
        dialog.exec()
        
    except Exception as e:
        logger.error(f"Error showing subscription alert: {e}")
        # Show error dialog
        dialog = SubscriptionAlertDialog(None, parent)
        dialog.exec() 