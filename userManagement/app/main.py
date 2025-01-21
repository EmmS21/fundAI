"""
main.py

Purpose: FastAPI application initialization and router configuration.
"""
from fastapi import FastAPI
from pydantic import BaseModel
from .db.database import init_db, get_db
import aiosqlite
from .endpoints import devices, users, subscriptions  
# Define the request model
class UserCreate(BaseModel):
    email: str
    password: str

app = FastAPI()

@app.on_event("startup")
async def startup():
    """Initialize database and create all tables at startup"""
    await init_db()
    db = await get_db()
    try:
        # Create all tables
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
        
        # Create devices table
        await db.execute(devices.CREATE_DEVICE_TABLE)
        await db.commit()
    finally:
        await db.close()

@app.post("/api/v1/users/")
async def create_user(user: UserCreate): 
    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO users (email, hashed_password) VALUES (?, ?)",
            (user.email, user.password)
        )
        await db.commit()
        return {"message": "User created"}
    except aiosqlite.IntegrityError:
        return {"error": "Email already exists"}
    finally:
        await db.close()

# Include router
app.include_router(users.router, prefix="/api/v1")
app.include_router(devices.router, prefix="/api/v1")
app.include_router(subscriptions.router, prefix="/api/v1")