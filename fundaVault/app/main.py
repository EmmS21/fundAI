"""
main.py

Purpose: FastAPI application initialization and router configuration.
"""
from fastapi import FastAPI
from app.db.database import init_db, get_db
from app.endpoints import devices, users, subscriptions
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI()

@app.on_event("startup")
async def startup():
    """Initialize database and create all tables at startup"""
    logger.debug("Starting up FastAPI application")
    try:
        await init_db()
        logger.debug("Database initialized")
        
        db = await get_db()
        try:
            # Create all tables
            logger.debug("Creating tables")
            await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                hashed_password TEXT NOT NULL,
                full_name TEXT,
                address TEXT,
                city TEXT,
                country TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)
            logger.debug("Users table created")
            
            await db.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE,
                start_date TIMESTAMP NOT NULL,
                end_date TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            );
            """)
            logger.debug("Subscriptions table created")
            
            # Create devices table
            await db.execute(devices.CREATE_DEVICE_TABLE)
            logger.debug("Devices table created")
            
            await db.commit()
            logger.debug("All tables committed")
            
        finally:
            await db.close()
            
    except Exception as e:
        logger.error("Error during startup: %s", str(e), exc_info=True)
        raise

logger.debug("Including routers")
# Include routers with proper prefix
app.include_router(users.router, prefix="/api/v1")
app.include_router(devices.router, prefix="/api/v1")
app.include_router(subscriptions.router, prefix="/api/v1")
logger.debug("Routers included")

@app.get("/")
async def root():
    """Root endpoint for testing"""
    logger.debug("Root endpoint called")
    return {
        "status": "online",
        "version": "1.0.0",
        "endpoints": [
            "/api/v1/users",
            "/api/v1/devices",
            "/api/v1/subscriptions"
        ]
    }