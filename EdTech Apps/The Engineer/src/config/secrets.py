"""
Secrets management for The Engineer AI Tutor
Handles API keys and sensitive configuration
"""

import os
from pathlib import Path
from typing import Optional

def load_env_file():
    """Load environment variables from .env file if it exists"""
    env_file = Path(".env")
    if env_file.exists():
        try:
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip()
        except Exception:
            pass  # Fail silently if .env file can't be read

# Load .env file on import
load_env_file()

def get_groq_api_key() -> Optional[str]:
    """Get Groq API key from environment variables"""
    return os.getenv('GROQ_API_KEY')

def get_openai_api_key() -> Optional[str]:
    """Get OpenAI API key from environment variables"""
    return os.getenv('OPENAI_API_KEY')

def get_encryption_key() -> Optional[str]:
    """Get encryption key from environment variables"""
    return os.getenv('ENCRYPTION_KEY')

def is_cloud_ai_available() -> bool:
    """Check if any cloud AI service is configured"""
    return bool(get_groq_api_key() or get_openai_api_key()) 