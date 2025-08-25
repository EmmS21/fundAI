"""
UI Utilities for The Engineer AI Tutor
Shared UI components and utilities
"""

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel

def create_offline_warning_banner(layout):
    """
    Create an offline warning banner and add it to the given layout.
    
    Args:
        layout: The QVBoxLayout to add the warning banner to
    """
    try:
        import sys
        import os
        # Add src to path if not already there
        if 'src' not in sys.path:
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
        
        from utils.network_utils import is_online, can_reach_groq
        
        # First check basic network connectivity
        if is_online() and can_reach_groq():
            # User is online and can reach Groq, don't show warning
            return
        
        # If we get here, user is offline or can't reach Groq
        # Try to check Groq client availability, but don't fail if import fails
        try:
            from core.ai.groq_client import GroqProgrammingClient
            groq_available = GroqProgrammingClient().is_available()
            if groq_available:
                # Groq is available, don't show warning
                return
        except ImportError:
            # Groq client import failed, continue with warning
            pass
        
        # Show offline warning
        warning_frame = QFrame()
        warning_frame.setStyleSheet("""
            QFrame {
                background-color: #f39c12;
                border-radius: 8px;
                padding: 15px;
                margin-bottom: 10px;
            }
        """)
        
        warning_layout = QHBoxLayout(warning_frame)
        
        # Warning icon
        warning_icon = QLabel("⚠️")
        warning_icon.setStyleSheet("""
            QLabel {
                font-size: 18px;
                color: white;
                margin-right: 10px;
            }
        """)
        warning_layout.addWidget(warning_icon)
        
        # Warning message
        warning_text = QLabel("You're currently offline. Project generation will use experimental local AI. For best results, connect to the internet.")
        warning_text.setWordWrap(True)
        warning_text.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: white;
                font-weight: 500;
            }
        """)
        warning_layout.addWidget(warning_text)
        
        layout.addWidget(warning_frame)
        
    except ImportError:
        # If network utils not available, don't show warning (assume everything is fine)
        pass
    except Exception as e:
        # For any other error, don't show warning (assume everything is fine)
        pass 