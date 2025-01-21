"""
users.py

Purpose: User management endpoints including registration and profile management.
"""
from fastapi import APIRouter, HTTPException
from ..core.security import get_password_hash
from ..db.database import get_db
from ..schemas.user import UserCreate, UserResponse
from datetime import datetime

router = APIRouter()

@router.post("/users/", response_model=UserResponse)
async def create_user(user: UserCreate):
    """Register a new user"""
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
