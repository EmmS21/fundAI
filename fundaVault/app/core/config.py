"""
config.py

Purpose: Central configuration management for the application.
Handles environment variables and app-wide settings using Pydantic BaseSettings.
"""
from pydantic_settings import BaseSettings
# from pydantic import PostgresDsn # Not strictly needed unless you want validation
from urllib.parse import quote_plus
import secrets # Keep for defaults if secrets aren't set? Reconsider.
import os
# from dotenv import load_dotenv # BaseSettings handles .env loading
from typing import Optional

# BaseSettings automatically loads from .env and environment variables

class Settings(BaseSettings):
    PROJECT_NAME: str = "User Management API"
    API_V1_STR: str = "/api/v1"

    # --- Database Settings ---
    # These will be loaded from environment (via Modal Secrets) first,
    # then potentially from .env file if specified in Config and not in env.
    DATABASE_URL: Optional[str] = None # Explicit connection string (e.g., for SQLite)
    # Make PG vars optional, only used if DATABASE_URL is not set
    POSTGRES_USER: Optional[str] = None
    POSTGRES_PASSWORD: Optional[str] = None
    POSTGRES_SERVER: Optional[str] = None
    POSTGRES_DB: Optional[str] = None

    # --- Token Settings ---
    # Load from environment/secrets, provide default only if absolutely necessary
    # Best practice: Require these to be set in the environment/secret
    SECRET_KEY: str # No default - MUST be set in Modal Secret "fundai"
    ALGORITHM: str # No default - MUST be set in Modal Secret "fundai" (e.g., HS256)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30 # Default is okay here

    # --- Device Token Settings ---
    # If this logic is still used elsewhere, make it a secret too
    # DEVICE_SECRET_KEY: str # No default - MUST be set in Modal Secret "fundai"
    # TOKEN_EXPIRE_DAYS: int = 30 # Default is okay

    # --- Admin Credentials ---
    # MUST be set in Modal Secret "fundai"
    ADMIN_EMAIL: str
    ADMIN_PASSWORD: str

    # --- Method to get the final DB URL ---
    def get_db_url(self) -> str:
        """Return DATABASE_URL if set, otherwise try to compute from PG vars."""
        if self.DATABASE_URL:
            # If DATABASE_URL is set (e.g., from Modal env/secret or .env), use it
            return self.DATABASE_URL
        elif self.POSTGRES_USER and self.POSTGRES_PASSWORD and self.POSTGRES_SERVER and self.POSTGRES_DB:
            # If DATABASE_URL isn't set, but all PG vars are, compute PG URL
            encoded_password = quote_plus(self.POSTGRES_PASSWORD)
            # Use asyncpg driver for compatibility with potential future switch
            computed_url = f"postgresql+asyncpg://{self.POSTGRES_USER}:{encoded_password}@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"
            return computed_url
        else:
            # If configuration is insufficient, raise error
            raise ValueError("Database configuration error: Set DATABASE_URL or all POSTGRES_* variables in environment/secrets.")

    class Config:
        # Tell BaseSettings to look for a .env file if needed
        # Environment variables (from Modal Secrets) take precedence
        env_file = ".env"
        env_file_encoding = 'utf-8'
        extra = 'ignore' # Ignore extra fields found in env/dotenv, don't error

# Instantiate settings - Pydantic loads from Modal Secrets (environment) first, then .env
# Validation errors will occur here if required fields (like SECRET_KEY, ADMIN_EMAIL etc.)
# are NOT set in the Modal Secret "fundai"
settings = Settings()

# Get the final DB URL to be used by the application
# This depends on what's set in the Modal environment ("fundai" secret)
effective_database_url = settings.get_db_url()

# Log the type of DB being used
db_type = "Unknown"
if effective_database_url.startswith("sqlite"):
    db_type = "SQLite"
elif effective_database_url.startswith("postgresql"):
    db_type = "PostgreSQL"

# Use a logger if available, otherwise print
# print(f"Effective Database URL Type: {db_type}")
# Consider logging this in main.py after logger setup instead.