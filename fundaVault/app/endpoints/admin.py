"""
admin.py

Purpose: Admin-specific endpoints for managing users, devices, and subscriptions.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime
from jose import jwt, JWTError
from pydantic import BaseModel
import logging

from app.core.jwt import oauth2_scheme
from app.db.database import get_db
from app.core.config import settings
from app.core.security import verify_admin_credentials, create_access_token, get_password_hash
from app.schemas.admin import DeviceRegistrationRequest, AdminLogin

router = APIRouter()
logger = logging.getLogger(__name__)

# Add this class for request validation
class AdminLogin(BaseModel):
    email: str
    password: str

@router.post("/login")
async def admin_login(login_data: AdminLogin):
    """Admin login endpoint"""
    logger.info(f"Admin login attempt: Email=[{login_data.email}]")
    if verify_admin_credentials(login_data.email, login_data.password):
        access_token = create_access_token(
            data={"sub": login_data.email, "is_admin": True},
            expires_delta=None  # No expiration for admin tokens
        )
        logger.info(f"Admin login successful: Email=[{login_data.email}]")
        return {"access_token": access_token, "token_type": "bearer"}
    logger.warning(f"Admin login failed: Invalid credentials. Email=[{login_data.email}]")
    raise HTTPException(
        status_code=401,
        detail="Invalid admin credentials"
    )

async def verify_admin(token: str = Depends(oauth2_scheme)):
    """Dependency to verify admin access"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Admin access required"
    )
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        if not payload.get("is_admin"):
            logger.warning("Admin verification failed: Token is not an admin token.")
            raise credentials_exception
        logger.debug("Admin verification successful.")
        return payload
    except JWTError as e:
        logger.warning(f"Admin verification failed: Invalid token. Error=[{e}]")
        raise credentials_exception

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
        d.hardware_id,
        d.user_id,
        d.is_active,
        d.registered_at,
        d.last_verified_at,
        u.email,
        u.full_name
    FROM devices d
    LEFT JOIN users u ON d.user_id = u.id
    """
    cursor = await db.execute(query)
    rows = await cursor.fetchall()
    columns = [description[0] for description in cursor.description]
    devices = [dict(zip(columns, row)) for row in rows]
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

@router.post("/register-device", status_code=status.HTTP_201_CREATED, dependencies=[Depends(verify_admin)])
async def admin_register_device(
    device_data: DeviceRegistrationRequest,
    db = Depends(get_db)
):
    """
    Admin endpoint to register a client's hardware ID and associate it with a user.
    Creates the user if they don't exist based on email.
    """
    logger.info(f"Admin attempting to register device: HardwareID=[{device_data.hardware_id}] Email=[{device_data.email}]")
    try:
        # 1. Check if hardware_id is already registered
        cursor = await db.execute("SELECT user_id FROM devices WHERE hardware_id = ?", (device_data.hardware_id,))
        existing_device = await cursor.fetchone()
        if existing_device:
            logger.warning(f"Device registration failed: Hardware ID [{device_data.hardware_id}] already registered to User ID [{existing_device[0]}].")
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Hardware ID already registered.")

        # 2. Find or Create User
        cursor = await db.execute("SELECT id, email FROM users WHERE email = ?", (device_data.email,))
        user = await cursor.fetchone()
        user_id: int
        if user:
            user_id = user[0]
            logger.info(f"Found existing user: UserID=[{user_id}] Email=[{device_data.email}]")
            # Optional: Check if this user already has another active device?
            cursor = await db.execute("SELECT hardware_id FROM devices WHERE user_id = ? AND is_active = TRUE", (user_id,))
            existing_user_device = await cursor.fetchone()
            if existing_user_device:
                 logger.warning(f"User [{user_id}] already has an active device [{existing_user_device[0]}]. Registration failed for new device [{device_data.hardware_id}].")
                 # Decide policy: Allow multiple devices, or block? Blocking for now.
                 raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already has an active device registered.")
        else:
            logger.info(f"User not found, creating new user: Email=[{device_data.email}]")
            # Create user with dummy password hash (user won't use it)
            dummy_hash = get_password_hash("DEFAULT_PASSWORD_PLACEHOLDER") # Or generate random
            cursor = await db.execute(
                """INSERT INTO users (email, hashed_password, full_name, address, city, country, is_active)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    device_data.email, dummy_hash, device_data.full_name,
                    device_data.address, device_data.city, device_data.country, True
                )
            )
            user_id = cursor.lastrowid
            logger.info(f"New user created: UserID=[{user_id}] Email=[{device_data.email}]")

        # 3. Register the Device
        now = datetime.now()
        await db.execute(
            """INSERT INTO devices (hardware_id, user_id, is_active, registered_at, last_verified_at)
               VALUES (?, ?, ?, ?, ?)""",
            (device_data.hardware_id, user_id, True, now.isoformat(), now.isoformat())
        )
        await db.commit()
        logger.info(f"Device registered successfully: HardwareID=[{device_data.hardware_id}] UserID=[{user_id}]")

        return {
            "message": "Device registered successfully",
            "hardware_id": device_data.hardware_id,
            "user_id": user_id,
            "email": device_data.email
        }

    except HTTPException:
        await db.rollback() # Rollback on expected errors
        raise
    except Exception as e:
        await db.rollback() # Rollback on unexpected errors
        logger.error(f"Admin device registration failed unexpectedly: HardwareID=[{device_data.hardware_id}] Error=[{e}]", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Device registration failed due to an internal error.")

@router.post("/devices/{hardware_id}/deactivate", dependencies=[Depends(verify_admin)])
async def deactivate_device(hardware_id: str, db = Depends(get_db)):
    """Deactivate a device by hardware ID"""
    logger.info(f"Admin attempting to deactivate device: HardwareID=[{hardware_id}]")
    cursor = await db.execute("SELECT user_id FROM devices WHERE hardware_id = ?", (hardware_id,))
    device = await cursor.fetchone()
    if not device:
        logger.warning(f"Deactivation failed: Device not found. HardwareID=[{hardware_id}]")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")

    await db.execute(
        "UPDATE devices SET is_active = FALSE WHERE hardware_id = ?",
        (hardware_id,)
    )
    await db.commit()
    logger.info(f"Device deactivated successfully: HardwareID=[{hardware_id}]")
    return {"message": f"Device {hardware_id} deactivated"}

@router.post("/devices/{hardware_id}/activate", dependencies=[Depends(verify_admin)])
async def activate_device(hardware_id: str, db = Depends(get_db)):
    """Activate a device by hardware ID"""
    logger.info(f"Admin attempting to activate device: HardwareID=[{hardware_id}]")
    cursor = await db.execute("SELECT user_id FROM devices WHERE hardware_id = ?", (hardware_id,))
    device = await cursor.fetchone()
    if not device:
        logger.warning(f"Activation failed: Device not found. HardwareID=[{hardware_id}]")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")

    await db.execute(
        "UPDATE devices SET is_active = TRUE, last_verified_at = ? WHERE hardware_id = ?",
        (datetime.now().isoformat(), hardware_id,)
    )
    await db.commit()
    logger.info(f"Device activated successfully: HardwareID=[{hardware_id}]")
    return {"message": f"Device {hardware_id} activated"} 