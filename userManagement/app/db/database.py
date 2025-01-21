import aiosqlite
import os

DATABASE_URL = "app.db"

# Simple connection function
async def get_db():
    return await aiosqlite.connect(DATABASE_URL)

CREATE_USERS_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL
);
"""

# Initialize database
async def init_db():
    db = await get_db()
    try:
        await db.execute(CREATE_USERS_TABLE)
        await db.commit()
    finally:
        await db.close()