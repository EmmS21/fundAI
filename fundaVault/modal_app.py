import modal
from modal import Image, App
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("modal_api_entrypoint")

# Create Modal app
app = App("user-management-api")

# Define the Modal Secret
funda_vault_secrets = modal.Secret.from_name("fundai")

# Include all necessary packages and add local files/dirs to the image
image = (
    Image.debian_slim()
    .pip_install([
        "fastapi>=0.100.0,<0.110.0",    
        "pydantic-settings>=2.0.0,<3.0.0",  
        "python-dotenv>=0.21.0,<0.22.0",
        "python-multipart>=0.0.6,<0.1.0",
        "email-validator>=2.0.0",
        "aiosqlite>=0.17.0,<0.18.0",
        "asyncpg>=0.25.0,<0.29.0",
        "PyJWT>=2.6.0,<2.7.0",
        "passlib[bcrypt]>=1.7.4,<1.8.0",
        "python-jose[cryptography]>=3.3.0,<4.0.0"
    ])
    .add_local_dir("app", remote_path="/root/app")
    .add_local_file(".env", remote_path="/root/.env")
)

# The correct pattern for Modal ASGI apps
@app.function(image=image, secrets=[funda_vault_secrets])
@modal.asgi_app()
def api():
    logger.info("--- Starting api() function ---")
    
    # Log current environment for debugging
    import os
    import sys
    logger.info(f"Current directory: {os.getcwd()}")
    logger.info(f"Sys Path: {sys.path}")
    
    # Import the app factory
    logger.info("Attempting to import config...")
    from app.core.config import Settings
    settings = Settings()
    logger.info(f"Config loaded. Effective DB URL type: {'SQLite' if settings.DATABASE_URL and 'sqlite' in settings.DATABASE_URL else 'PostgreSQL'}")
    
    logger.info("Attempting to import app.main...")
    # Import and create the app
    from fastapi import FastAPI
    
    # Create a new FastAPI app
    fastapi_app = FastAPI(
        title="FundaVault User Management API"
    )
    
    # Add middleware first
    from app.main import configure_middleware
    configure_middleware(fastapi_app)
    
    # Include routers
    from app.endpoints import devices, users, subscriptions, admin, auth
    
    fastapi_app.include_router(users.router, prefix="/api/v1", tags=["Users"])
    fastapi_app.include_router(devices.router, prefix="/api/v1", tags=["Devices"])
    fastapi_app.include_router(subscriptions.router, prefix="/api/v1", tags=["Subscriptions"])
    fastapi_app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])
    fastapi_app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
    
    # Add startup event
    from app.db.database import init_db
    
    @fastapi_app.on_event("startup")
    async def startup():
        await init_db()
    
    # Add root endpoint
    @fastapi_app.get("/")
    async def root():
        """Root endpoint for basic health check"""
        from starlette.responses import JSONResponse
        # Try a JSON response with explicit content type
        return JSONResponse(
            content={"status": "online"},
            status_code=200
        )
    
    logger.info("FastAPI app initialized successfully.")
    logger.info("About to return FastAPI app instance from api().")
    
    # Return the FastAPI app
    return fastapi_app