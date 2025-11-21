"""
Application Settings
Central configuration management for MoneyWise Academy
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings:
    """Application configuration settings"""
    
    # Application Info
    APP_NAME = "MoneyWise Academy"
    APP_VERSION = "1.0.0"
    APP_AUTHOR = "fundAI"
    
    # Directories
    HOME_DIR = Path.home()
    APP_DIR = HOME_DIR / '.moneywise'
    DATA_DIR = APP_DIR / 'data'
    LOGS_DIR = APP_DIR / 'logs'
    CACHE_DIR = APP_DIR / 'cache'
    MODELS_DIR = HOME_DIR / 'Documents' / 'models' / 'llama'
    
    # Ensure directories exist
    @classmethod
    def ensure_directories(cls):
        """Create application directories if they don't exist"""
        for directory in [cls.APP_DIR, cls.DATA_DIR, cls.LOGS_DIR, cls.CACHE_DIR]:
            directory.mkdir(parents=True, exist_ok=True)
    
    # Database
    DATABASE_PATH = DATA_DIR / 'moneywise.db'
    
    # AI Configuration
    LOCAL_AI_ENABLED = True
    LOCAL_MODEL_PATH = MODELS_DIR / 'DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M.gguf'
    CLOUD_AI_ENABLED = True
    AI_TEMPERATURE = 0.7
    AI_MAX_TOKENS = 1000
    
    # Network
    NETWORK_CHECK_INTERVAL = 30  
    SYNC_INTERVAL = 300  
    
    # UI
    WINDOW_WIDTH = 1200
    WINDOW_HEIGHT = 800
    THEME = "light"  
    
    # Feature Flags
    ENABLE_VOICE_INPUT = False
    ENABLE_EXPORT_REPORTS = True
    ENABLE_GAMIFICATION = True
    
    @classmethod
    def get_groq_api_key(cls):
        """Get Groq API key from environment"""
        return os.getenv('GROQ_API_KEY', '')
    
    @classmethod
    def get_mongodb_uri(cls):
        """Get MongoDB connection URI from environment"""
        return os.getenv('MONGODB_URI', '')
    
    @classmethod
    def get_firebase_config(cls):
        """Get Firebase configuration from environment"""
        return {
            'api_key': os.getenv('FIREBASE_API_KEY', ''),
            'project_id': os.getenv('FIREBASE_PROJECT_ID', ''),
            'storage_bucket': os.getenv('FIREBASE_STORAGE_BUCKET', ''),
        }


Settings.ensure_directories()

