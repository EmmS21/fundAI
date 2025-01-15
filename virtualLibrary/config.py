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
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
    GOOGLE_PROJECT_ID = os.getenv('GOOGLE_PROJECT_ID')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
    GOOGLE_AUTH_URI = os.getenv('GOOGLE_AUTH_URI')
    GOOGLE_TOKEN_URI = os.getenv('GOOGLE_TOKEN_URI')
    GOOGLE_DRIVE_FOLDER_ID = os.getenv('GOOGLE_DRIVE_FOLDER_ID')

