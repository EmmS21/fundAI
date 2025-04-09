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
import logging

logger = logging.getLogger(__name__) # Keep module-level logger

# BaseSettings automatically loads from .env and environment variables

class Settings(BaseSettings):
    PROJECT_NAME: str = "User Management API"
    API_V1_STR: str = "/api/v1"

    # --- Supabase Settings ---
    # Loaded from Modal Secret "fundai" or .env file
    SUPABASE_URL: str
    SUPABASE_KEY: str

    # --- Token Settings ---
    SECRET_KEY: str # No default - MUST be set in Modal Secret "fundai" or .env
    ALGORITHM: str # No default - MUST be set in Modal Secret "fundai" or .env (e.g., HS256)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440 # Default is 24 hours

    # --- Admin Credentials ---
    # MUST be set in Modal Secret "fundai" or .env
    ADMIN_EMAIL: str
    ADMIN_PASSWORD: str

    # Removed get_db_url method and all old DB connection string vars (DATABASE_URL, POSTGRES_*)

    class Config:
        # Tell BaseSettings to look for a .env file if needed
        # Environment variables (from Modal Secrets) take precedence
        env_file = ".env"
        env_file_encoding = 'utf-8'
        extra = 'ignore' # Ignore extra fields found in env/dotenv, don't error

# Instantiate settings - Pydantic loads from Modal Secrets (environment) first, then .env
# Validation errors will occur here if required fields (SUPABASE_URL, SUPABASE_KEY, etc.)
# are NOT set in the Modal Secret "fundai" or a .env file.
try:
    settings = Settings()
    # Log confirmation (optional) - Log partial URL for basic check, avoid logging full key
    logger.info(f"Configuration loaded. Using Supabase URL starting with: {settings.SUPABASE_URL[:20]}...")
except Exception as e:
    logger.error(f"CRITICAL: Failed to load settings. Error: {e}", exc_info=True)
    # Optionally raise the error to prevent app startup with bad config
    # raise e