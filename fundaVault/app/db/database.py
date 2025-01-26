import aiosqlite

DATABASE_URL = "app.db"

# Simple connection function
async def get_db():
    return await aiosqlite.connect(DATABASE_URL)

CREATE_USERS_TABLE = """
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
"""

CREATE_SUBSCRIPTIONS_TABLE = """
CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE,
    start_date TIMESTAMP NOT NULL,
    end_date TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);
"""

CREATE_SUBSCRIPTION_HISTORY_TABLE = """
CREATE TABLE IF NOT EXISTS subscription_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    start_date TIMESTAMP NOT NULL,
    end_date TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    action TEXT NOT NULL,  -- 'created' or 'renewed'
    FOREIGN KEY (user_id) REFERENCES users (id)
);
"""

CREATE_DEVICES_TABLE = """
CREATE TABLE IF NOT EXISTS devices (
    hardware_id TEXT PRIMARY KEY,
    user_id INTEGER,
    os_type TEXT NOT NULL,
    raw_identifier TEXT NOT NULL,
    normalized_identifier TEXT NOT NULL,
    is_active BOOLEAN DEFAULT true,
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_verified_at TIMESTAMP,
    current_token TEXT,
    token_expiry TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);
"""

# Initialize database
async def init_db():
    db = await get_db()
    try:
        await db.execute(CREATE_USERS_TABLE)
        await db.execute(CREATE_SUBSCRIPTIONS_TABLE)
        await db.execute(CREATE_SUBSCRIPTION_HISTORY_TABLE)
        await db.execute(CREATE_DEVICES_TABLE)
        await db.commit()
    finally:
        await db.close()