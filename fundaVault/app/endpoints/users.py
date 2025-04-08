"""
users.py

Purpose: User management endpoints including registration and profile management.
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm
from app.core.security import get_password_hash, verify_password, create_access_token
from app.db.database import get_db
from app.schemas.user import UserCreate, UserResponse
from datetime import datetime
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/users/", response_model=UserResponse)
async def create_user(user: UserCreate):
    """Register a new user"""
    logger.info(f"Direct user registration attempt: Email=[{user.email}]")
    try:
        db = await get_db()
        try:
            # Check if user exists
            cursor = await db.execute(
                "SELECT id FROM users WHERE email = ?",
                (user.email,)
            )
            if await cursor.fetchone():
                raise HTTPException(
                    status_code=400,
                    detail="Email already registered"
                )
            
            # Create new user
            cursor = await db.execute(
                """
                INSERT INTO users 
                (email, hashed_password, full_name, address, city, country) 
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    user.email,
                    get_password_hash(user.password),
                    user.full_name,
                    user.address,
                    user.city,
                    user.country
                )
            )
            await db.commit()
            
            # Get created user
            user_id = cursor.lastrowid
            cursor = await db.execute(
                "SELECT * FROM users WHERE id = ?",
                (user_id,)
            )
            user_data = await cursor.fetchone()
            
            return {
                "id": user_id,
                "email": user_data[1],
                "full_name": user_data[3],
                "address": user_data[4],
                "city": user_data[5],
                "country": user_data[6],
                "created_at": user_data[7]
            }
            
        finally:
            await db.close()
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create user: {str(e)}"
        )

@router.get("/users/{user_id}/status")
async def get_user_status(user_id: int):
    """Get comprehensive user status including history"""
    try:
        db = await get_db()
        try:
            # Get subscription status
            cursor = await db.execute(
                """
                SELECT start_date, end_date 
                FROM subscriptions 
                WHERE user_id = ?
                """,
                (user_id,)
            )
            subscription = await cursor.fetchone()
            
            # Get device info
            cursor = await db.execute(
                """
                SELECT hardware_id, is_active, registered_at
                FROM devices 
                WHERE user_id = ?
                """,
                (user_id,)
            )
            device = await cursor.fetchone()
            
            # Get subscription history
            cursor = await db.execute(
                """
                SELECT start_date, end_date, action, created_at
                FROM subscription_history
                WHERE user_id = ?
                ORDER BY created_at DESC
                """,
                (user_id,)
            )
            history = await cursor.fetchall()
            
            return {
                "subscription": {
                    "active": subscription and datetime.fromisoformat(subscription[1]) > datetime.utcnow(),
                    "current": {
                        "start_date": subscription and subscription[0],
                        "end_date": subscription and subscription[1]
                    } if subscription else None
                },
                "device": {
                    "registered": bool(device),
                    "hardware_id": device and device[0],
                    "is_active": device and device[1],
                    "registered_at": device and device[2]
                } if device else None,
                "history": [
                    {
                        "start_date": h[0],
                        "end_date": h[1],
                        "action": h[2],
                        "timestamp": h[3]
                    } for h in history
                ]
            }
            
        finally:
            await db.close()
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get user status: {str(e)}"
        )

@router.get("/users/list")
async def list_users(db = Depends(get_db)):
    """List all users (for testing)"""
    cursor = await db.execute("SELECT id, email, full_name, created_at FROM users")
    users = await cursor.fetchall()
    return [
        {
            "id": user[0],
            "email": user[1],
            "full_name": user[2],
            "created_at": user[3]
        }
        for user in users
    ]
