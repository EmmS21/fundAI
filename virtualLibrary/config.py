"""
config.py

Purpose: Load environment variables securely
"""
from pathlib import Path
from dotenv import load_dotenv
import os

# Get the directory where config.py is located
current_dir = Path(__file__).parent
env_path = current_dir / '.env'

# Load environment variables
load_dotenv(dotenv_path=env_path)

class Config:
    # Google Drive configs
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
    GOOGLE_PROJECT_ID = os.getenv('GOOGLE_PROJECT_ID')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
    GOOGLE_AUTH_URI = os.getenv('GOOGLE_AUTH_URI')
    GOOGLE_TOKEN_URI = os.getenv('GOOGLE_TOKEN_URI')
    GOOGLE_DRIVE_FOLDER_ID = os.getenv('GOOGLE_DRIVE_FOLDER_ID')
    
    # Firebase configs
    FIREBASE_PROJECT_ID = os.getenv('FIREBASE_PROJECT_ID')
    FIREBASE_PRIVATE_KEY_ID = os.getenv('FIREBASE_PRIVATE_KEY_ID')
    FIREBASE_PRIVATE_KEY = os.getenv('FIREBASE_PRIVATE_KEY')
    FIREBASE_CLIENT_EMAIL = os.getenv('FIREBASE_CLIENT_EMAIL')
    FIREBASE_CLIENT_ID = os.getenv('FIREBASE_CLIENT_ID')
    FIREBASE_AUTH_URI = os.getenv('FIREBASE_AUTH_URI')
    FIREBASE_TOKEN_URI = os.getenv('FIREBASE_TOKEN_URI')
    FIREBASE_AUTH_PROVIDER_CERT_URL = os.getenv('FIREBASE_AUTH_PROVIDER_CERT_URL')
    FIREBASE_CLIENT_CERT_URL = os.getenv('FIREBASE_CLIENT_CERT_URL')
    
    # Modal configs
    MODAL_TOKEN_ID = os.getenv('MODAL_TOKEN_ID')
    MODAL_TOKEN_SECRET = os.getenv('MODAL_TOKEN_SECRET')

    # Nomic configs
    NOMIC_API_KEY = os.getenv('NOMIC_API_KEY')

