"""
admin.py

Purpose: Admin-specific endpoints for managing users, devices, and subscriptions.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime
from jose import jwt, JWTError
from pydantic import BaseModel

from app.core.jwt import oauth2_scheme
from app.db.database import get_db
from app.core.config import settings
from app.core.security import verify_admin_credentials, create_access_token

router = APIRouter()

# Add this class for request validation
class AdminLogin(BaseModel):
    email: str
    password: str

@router.post("/login")
async def admin_login(login_data: AdminLogin):
    """Admin login endpoint"""
    if verify_admin_credentials(login_data.email, login_data.password):
        access_token = create_access_token(
            data={"sub": login_data.email, "is_admin": True},
            expires_delta=None  # No expiration for admin tokens
        )
        return {"access_token": access_token, "token_type": "bearer"}
    raise HTTPException(
        status_code=401,
        detail="Invalid admin credentials"
    )

async def verify_admin(token: str = Depends(oauth2_scheme)):
    """Dependency to verify admin access"""
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=["HS256"]
        )
        if not payload.get("is_admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin token"
        )

@router.get("/users", dependencies=[Depends(verify_admin)])
async def get_all_users(db = Depends(get_db)):
    """Get all users in the system"""
    cursor = await db.execute("SELECT * FROM users")
    users = await cursor.fetchall()
    return {"users": users}

@router.get("/subscriptions", dependencies=[Depends(verify_admin)])
async def get_all_subscriptions(db = Depends(get_db)):
    """Get all subscriptions with user details"""
    query = """
    SELECT 
        s.*, 
        u.email, 
        u.full_name
    FROM subscriptions s
    JOIN users u ON s.user_id = u.id
    """
    cursor = await db.execute(query)
    subscriptions = await cursor.fetchall()
    return {"subscriptions": subscriptions}

@router.get("/devices", dependencies=[Depends(verify_admin)])
async def get_all_devices(db = Depends(get_db)):
    """Get all registered devices with user details"""
    query = """
    SELECT 
        d.*, 
        u.email, 
        u.full_name
    FROM devices d
    JOIN users u ON d.user_id = u.id
    """
    cursor = await db.execute(query)
    devices = await cursor.fetchall()
    return {"devices": devices}

@router.post("/users/{user_id}/deactivate", dependencies=[Depends(verify_admin)])
async def deactivate_user(user_id: int, db = Depends(get_db)):
    """Deactivate a user account"""
    await db.execute(
        "UPDATE users SET is_active = FALSE WHERE id = ?",
        (user_id,)
    )
    await db.commit()
    return {"message": f"User {user_id} deactivated"}

@router.post("/users/{user_id}/activate", dependencies=[Depends(verify_admin)])
async def activate_user(user_id: int, db = Depends(get_db)):
    """Activate a user account"""
    await db.execute(
        "UPDATE users SET is_active = TRUE WHERE id = ?",
        (user_id,)
    )
    await db.commit()
    return {"message": f"User {user_id} activated"}

@router.get("/stats", dependencies=[Depends(verify_admin)])
async def get_system_stats(db = Depends(get_db)):
    """Get system statistics"""
    async def count_table(table: str) -> int:
        cursor = await db.execute(f"SELECT COUNT(*) FROM {table}")
        result = await cursor.fetchone()
        return result[0]

    return {
        "total_users": await count_table("users"),
        "total_devices": await count_table("devices"),
        "active_subscriptions": await count_table("subscriptions"),
        "timestamp": datetime.utcnow()
    }

@router.delete("/users/{user_id}", dependencies=[Depends(verify_admin)])
async def delete_user(user_id: int, db = Depends(get_db)):
    """Delete a user and associated data"""
    try:
        # Delete related records first
        await db.execute("DELETE FROM subscriptions WHERE user_id = ?", (user_id,))
        await db.execute("DELETE FROM devices WHERE user_id = ?", (user_id,))
        await db.execute("DELETE FROM users WHERE id = ?", (user_id,))
        await db.commit()
        return {"message": f"User {user_id} and associated data deleted"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete user: {str(e)}"
        ) 