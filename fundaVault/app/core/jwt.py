"""
jwt.py

Purpose: Authentication dependencies and utilities for FastAPI endpoints.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from ..db.database import get_db
from ..core.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

async def get_current_user(
    db = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    """Dependency to get current authenticated user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not token:
        raise credentials_exception
        
    try:
        # Decode JWT token
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=["HS256"]
        )
        
        # Check user_id before database query
        user_id = payload.get("sub")
        if not user_id:
            raise credentials_exception
            
        # Get user from database using raw SQL
        cursor = await db.execute(
            "SELECT * FROM users WHERE id = ?", 
            (user_id,)
        )
        user = await cursor.fetchone()
        
        if not user:
            raise credentials_exception
            
        return user
            
    except JWTError:
        raise credentials_exception
