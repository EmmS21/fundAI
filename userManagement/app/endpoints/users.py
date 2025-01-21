"""
users.py

Purpose: User management endpoints including registration and profile management.
"""
from fastapi import APIRouter, HTTPException
from ..core.security import get_password_hash
from ..db.database import database
from ..schemas.user import UserCreate, UserResponse

router = APIRouter()

@router.post("/users/", response_model=UserResponse)
async def create_user(user: UserCreate):
    """Register a new user"""
    try:
        # Check if user exists
        query = "SELECT id FROM users WHERE email = :email"
        existing_user = await database.fetch_one(query=query, values={"email": user.email})
        
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Create new user
        hashed_password = get_password_hash(user.password)
        query = """
            INSERT INTO users (email, hashed_password)
            VALUES (:email, :hashed_password)
            RETURNING id, email, is_active, created_at
        """
        values = {"email": user.email, "hashed_password": hashed_password}
        
        user_record = await database.fetch_one(query=query, values=values)
        return UserResponse(**dict(user_record))
        
    except Exception as e:
        print(f"Error creating user: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
