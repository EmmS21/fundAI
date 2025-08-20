"""
Network utilities for AI routing decisions
"""

import socket
import logging

logger = logging.getLogger(__name__)

def is_online() -> bool:
    """
    Quick connectivity check using DNS resolution
    Returns True if internet is available, False otherwise
    """
    try:
        # Test DNS resolution to Google's public DNS (fast and reliable)
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return True
    except OSError:
        return False

def can_reach_groq() -> bool:
    """
    Check if Groq API endpoint is reachable
    Returns True if Groq service is accessible, False otherwise
    """
    try:
        # Simple socket connection to Groq's domain
        socket.create_connection(("api.groq.com", 443), timeout=3)
        return True
    except OSError:
        return False 