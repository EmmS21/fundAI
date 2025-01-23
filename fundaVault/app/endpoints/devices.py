"""
devices.py

Purpose: Device registration and token management for offline authentication.
Controls device registration, token generation, and verification for AI model access.
"""
from fastapi import APIRouter, HTTPException
from app.db.database import get_db
from app.core.config import settings  
import uuid
from datetime import datetime, timedelta
import jwt

router = APIRouter()

CREATE_DEVICE_TABLE = """
CREATE TABLE IF NOT EXISTS devices (
    hardware_id TEXT PRIMARY KEY,
    user_id INTEGER,
    is_active BOOLEAN DEFAULT true,
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    current_token TEXT,
    token_expiry TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);
"""

@router.post("/devices/register/{user_id}")
async def register_device(user_id: int):
    """Register device for a user using hardware UUID"""
    try:
        hardware_id = str(uuid.getnode())
        db = await get_db()
        try:
            # Check if device already registered
            cursor = await db.execute(
                "SELECT * FROM devices WHERE hardware_id = ?",
                (hardware_id,)
            )
            existing_device = await cursor.fetchone()
            
            if existing_device:
                raise HTTPException(
                    status_code=400,
                    detail="Device already registered"
                )
            
            # Check subscription status
            cursor = await db.execute(
                """
                SELECT s.end_date 
                FROM subscriptions s 
                WHERE s.user_id = ? AND s.end_date > datetime('now')
                """,
                (user_id,)
            )
            subscription = await cursor.fetchone()
            if not subscription:
                raise HTTPException(
                    status_code=400,
                    detail="No active subscription found"
                )
            
            # Use settings for token generation
            expiry = datetime.utcnow() + timedelta(days=settings.TOKEN_EXPIRE_DAYS)
            token_data = {
                "hardware_id": hardware_id,
                "user_id": user_id,
                "exp": expiry.timestamp(),
                "subscription_end": subscription[0]
            }
            token = jwt.encode(
                token_data,
                settings.DEVICE_SECRET_KEY,
                algorithm="HS256"
            )
            
            await db.execute(
                """
                INSERT INTO devices 
                (hardware_id, user_id, current_token, token_expiry) 
                VALUES (?, ?, ?, ?)
                """,
                (hardware_id, user_id, token, expiry.isoformat())
            )
            await db.commit()
            
            return {
                "message": "Device registered successfully",
                "hardware_id": hardware_id,
                "user_id": user_id,
                "token": token,
                "token_expiry": expiry.isoformat()
            }
            
        finally:
            await db.close()
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to register device: {str(e)}"
        )

@router.post("/devices/{hardware_id}/refresh-token")
async def refresh_device_token(hardware_id: str):
    """Generate new token for existing device"""
    try:
        db = await get_db()
        try:
            # Get device and user info
            cursor = await db.execute(
                "SELECT user_id FROM devices WHERE hardware_id = ? AND is_active = true",
                (hardware_id,)
            )
            device = await cursor.fetchone()
            
            if not device:
                raise HTTPException(
                    status_code=404,
                    detail="Device not found or inactive"
                )

            # Get subscription info
            cursor = await db.execute(
                """
                SELECT end_date 
                FROM subscriptions 
                WHERE user_id = ?
                """,
                (device[0],)
            )
            subscription = await cursor.fetchone()
            
            if not subscription:
                raise HTTPException(
                    status_code=400,
                    detail="No subscription found"
                )
            
            expiry = datetime.utcnow() + timedelta(days=settings.TOKEN_EXPIRE_DAYS)
            token_data = {
                "hardware_id": hardware_id,
                "user_id": device[0],
                "exp": expiry.timestamp(),
                "subscription_end": subscription[0]  # Add subscription end date
            }
            new_token = jwt.encode(
                token_data,
                settings.DEVICE_SECRET_KEY,
                algorithm="HS256"
            )
            
            await db.execute(
                """
                UPDATE devices 
                SET current_token = ?, token_expiry = ?
                WHERE hardware_id = ?
                """,
                (new_token, expiry.isoformat(), hardware_id)
            )
            await db.commit()
            
            return {
                "token": new_token,
                "expiry": expiry.isoformat()
            }
            
        finally:
            await db.close()
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to refresh token: {str(e)}"
        )

@router.get("/devices/{hardware_id}/verify")
async def verify_device(hardware_id: str, token: str):
    """Verify device token for offline authentication"""
    try:
        try:
            payload = jwt.decode(
                token,
                settings.DEVICE_SECRET_KEY,
                algorithms=["HS256"]
            )
            
            if payload["hardware_id"] != hardware_id:
                return {"valid": False, "reason": "Token doesn't match device"}
                
            return {"valid": True, "payload": payload}
            
        except jwt.ExpiredSignatureError:
            return {"valid": False, "reason": "Token expired"}
        except jwt.JWTError:
            return {"valid": False, "reason": "Invalid token"}
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to verify token: {str(e)}"
        )
