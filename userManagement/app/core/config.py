"""
config.py

Purpose: Central configuration management for the application.
Handles environment variables and app-wide settings.
"""
from pydantic_settings import BaseSettings
from urllib.parse import quote_plus
from typing import Optional
import secrets

class Settings(BaseSettings):
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Educational Platform Backend"
    
    # Security
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 43200  
    
    # Database
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    DATABASE_URL: Optional[str] = None

    class Config:
        env_file = ".env"

    def compute_db_url(self) -> str:
        """Compute PostgreSQL database URL with URL-encoded password"""
        if not self.DATABASE_URL:
            encoded_password = quote_plus(self.POSTGRES_PASSWORD)
            
            # Build URL with GSSAPI disabled
            self.DATABASE_URL = (
                f"postgresql://{self.POSTGRES_USER}:{encoded_password}"
                f"@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"
                "?sslmode=require&gssencmode=disable"
            )
        return self.DATABASE_URL
    
settings = Settings()
