"""
config.py

Purpose: Central configuration management for the application.
Handles environment variables and app-wide settings.
"""
from pydantic_settings import BaseSettings
from urllib.parse import quote_plus
import secrets
import os
from dotenv import load_dotenv

# Load environment variables from .env file
def load_env_vars():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(os.path.dirname(os.path.dirname(current_dir)), '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
        return {
            "POSTGRES_SERVER": os.getenv("POSTGRES_SERVER"),
            "POSTGRES_USER": os.getenv("POSTGRES_USER"),
            "POSTGRES_PASSWORD": os.getenv("POSTGRES_PASSWORD"),
            "POSTGRES_DB": os.getenv("POSTGRES_DB")
        }
    return {}

class Settings(BaseSettings):
    PROJECT_NAME: str = "User Management API"
    API_V1_STR: str = "/api/v1"
    
    # Database settings (Supabase)
    POSTGRES_USER: str = ""
    POSTGRES_PASSWORD: str = ""
    POSTGRES_SERVER: str = ""
    POSTGRES_DB: str = ""
    DATABASE_URL: str | None = None

    # Token settings
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    SECRET_KEY: str = secrets.token_urlsafe(32)

    # Local settings for device tokens
    DEVICE_SECRET_KEY: str = secrets.token_urlsafe(32)
    TOKEN_EXPIRE_DAYS: int = 30

    # Admin credentials
    ADMIN_EMAIL: str = ""
    ADMIN_PASSWORD: str = ""

    def compute_db_url(self) -> str:
        """Compute PostgreSQL database URL"""
        if not self.DATABASE_URL:
            encoded_password = quote_plus(self.POSTGRES_PASSWORD)
            self.DATABASE_URL = (
                f"postgresql://{self.POSTGRES_USER}:{encoded_password}"
                f"@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"
            )
        return self.DATABASE_URL

    class Config:
        env_file = ".env"

# Load environment variables
env_vars = load_env_vars()
settings = Settings(**env_vars)