"""
config.py

Purpose: Central configuration management for the application.
Handles environment variables and app-wide settings.
"""
from pydantic_settings import BaseSettings
from urllib.parse import quote_plus
import secrets  # for generating secure random string

class Settings(BaseSettings):
    PROJECT_NAME: str = "User Management API"
    API_V1_STR: str = "/api/v1"
    
    # Database settings (Supabase)
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_SERVER: str
    POSTGRES_DB: str
    DATABASE_URL: str | None = None

    # Local settings for device tokens
    DEVICE_SECRET_KEY: str = secrets.token_urlsafe(32)  # Generate random secure key
    TOKEN_EXPIRE_DAYS: int = 30

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

settings = Settings()