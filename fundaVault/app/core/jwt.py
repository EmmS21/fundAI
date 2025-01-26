"""
jwt.py

Purpose: Authentication dependencies and utilities for FastAPI endpoints.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
import logging

from ..db.database import get_db
from ..core.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)  # Set logging level to DEBUG

async def get_current_user(
    db = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    """Dependency to get current authenticated user from JWT token."""
    try:
        logger.debug("=== Starting token validation ===")
        logger.debug(f"Received token: {token[:20]}...")
        
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=["HS256"]
        )
        logger.debug(f"Decoded payload: {payload}")
        
        # Check if this is an admin token
        is_admin = payload.get("is_admin", False)
        email = payload.get("sub")
        user_id = payload.get("id")
        
        if is_admin:
            return {
                "id": 0,
                "email": email,
                "is_admin": True,
                "full_name": "Admin User"
            }
        
        # For regular users, lookup by ID
        cursor = await db.execute(
            """
            SELECT id, email, full_name, address, city, country, created_at 
            FROM users WHERE id = ?
            """, 
            (user_id,)
        )
        user = await cursor.fetchone()
        
        if not user:
            logger.error(f"No user found for ID: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"No user found for ID: {user_id}"
            )
        
        # Convert SQLite row to dictionary with explicit column names
        user_dict = {
            "id": user[0],
            "email": user[1],
            "full_name": user[2],
            "address": user[3],
            "city": user[4],
            "country": user[5],
            "created_at": user[6],
            "is_admin": False
        }
        
        return user_dict
        
    except JWTError as e:
        logger.error(f"JWT Error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"JWT validation failed: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.exception("Full traceback:")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}"
        )
