"""
devices.py

Purpose: Device registration and token management for offline authentication.
Controls device registration, token generation, and verification for AI model access.
"""
from fastapi import APIRouter, HTTPException, Depends
from app.db.database import get_db
from app.core.config import settings
from app.core.hardware_id import HardwareIdentifier
from app.core.jwt import get_current_user
from app.schemas.device import DeviceRegister, DeviceResponse, DeviceToken, DeviceDeactivate
import jwt
from datetime import datetime, timedelta
import logging

router = APIRouter()

logger = logging.getLogger(__name__)

CREATE_DEVICE_TABLE = """
CREATE TABLE IF NOT EXISTS devices (
    hardware_id TEXT PRIMARY KEY,
    user_id INTEGER,
    os_type TEXT NOT NULL,
    raw_identifier TEXT NOT NULL,
    normalized_identifier TEXT NOT NULL,
    is_active BOOLEAN DEFAULT true,
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_verified_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);
"""

@router.post("/devices/register", response_model=DeviceResponse)
async def register_device(
    device: DeviceRegister,
    db = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Register a device for the current user"""
    try:
        logger.debug("=== Starting device registration ===")
        logger.debug(f"Current user: {current_user}")
        logger.debug(f"Device registration request: {device}")
        
        # Validate user permissions
        if not current_user.get('is_admin'):
            if device.user_id != current_user.get('id'):
                logger.error(f"User ID mismatch: {device.user_id} != {current_user.get('id')}")
                raise HTTPException(
                    status_code=403,
                    detail="Cannot register device for another user"
                )

        # Get hardware identifier details
        hardware_info = HardwareIdentifier.get_hardware_id()
        device_details = {
            "os_type": hardware_info[0],
            "raw_id": hardware_info[1],
            "normalized_id": hardware_info[2]
        }
        logger.debug(f"Hardware ID obtained: {device_details}")

        # Check if device is already registered
        cursor = await db.execute(
            "SELECT user_id FROM devices WHERE normalized_identifier = ?",
            (device_details["normalized_id"],)
        )
        existing_device = await cursor.fetchone()
        if existing_device:
            logger.error(f"Device already registered: {device_details['normalized_id']}")
            raise HTTPException(
                status_code=400,
                detail="Device already registered"
            )

        # Check if user already has a registered device
        cursor = await db.execute(
            "SELECT hardware_id FROM devices WHERE user_id = ? AND is_active = TRUE",
            (device.user_id,)
        )
        if await cursor.fetchone():
            logger.error(f"User {device.user_id} already has a registered device")
            raise HTTPException(
                status_code=400,
                detail="User already has a registered device"
            )

        # Register the device
        now = datetime.now()
        registration_data = {
            "hardware_id": device_details["normalized_id"],
            "user_id": device.user_id,
            "os_type": device_details["os_type"],
            "raw_identifier": device_details["raw_id"],
            "normalized_identifier": device_details["normalized_id"],
            "is_active": True,
            "registered_at": now.isoformat(),
            "last_verified_at": now.isoformat()
        }

        await db.execute("""
            INSERT INTO devices (
                hardware_id,
                user_id,
                os_type,
                raw_identifier,
                normalized_identifier,
                is_active,
                registered_at,
                last_verified_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            registration_data["hardware_id"],
            registration_data["user_id"],
            registration_data["os_type"],
            registration_data["raw_identifier"],
            registration_data["normalized_identifier"],
            registration_data["is_active"],
            registration_data["registered_at"],
            registration_data["last_verified_at"]
        ))
        await db.commit()

        return {
            "user_id": registration_data["user_id"],
            "hardware_id": registration_data["hardware_id"],
            "os_type": registration_data["os_type"],
            "normalized_identifier": registration_data["normalized_identifier"],
            "is_active": registration_data["is_active"],
            "registered_at": now,
            "last_verified_at": now
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Device registration failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Device registration failed: {str(e)}"
        )

@router.post("/devices/{hardware_id}/token", response_model=DeviceToken)
async def generate_device_token(
    hardware_id: str,
    db = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Generate a new device token"""
    try:
        # Verify device exists and belongs to user
        cursor = await db.execute("""
            SELECT d.*, u.id as user_id
            FROM devices d
            JOIN users u ON d.user_id = u.id
            WHERE d.hardware_id = ? AND d.is_active = TRUE
        """, (hardware_id,))
        device = await cursor.fetchone()

        if not device:
            raise HTTPException(
                status_code=404,
                detail="Device not found or inactive"
            )

        if device['user_id'] != current_user['id']:
            raise HTTPException(
                status_code=403,
                detail="Device belongs to another user"
            )

        # Verify hardware identifier - only use what we need
        _, _, normalized_id = HardwareIdentifier.get_hardware_id()
        if normalized_id != device['normalized_identifier']:
            raise HTTPException(
                status_code=403,
                detail="Hardware verification failed"
            )

        # Check subscription status
        cursor = await db.execute("""
            SELECT end_date 
            FROM subscriptions 
            WHERE user_id = ? AND end_date > ?
        """, (current_user['id'], datetime.now().isoformat()))
        subscription = await cursor.fetchone()

        if not subscription:
            raise HTTPException(
                status_code=403,
                detail="No active subscription found"
            )

        # Use subscription end date for token expiration
        subscription_end = datetime.fromisoformat(subscription[0])
        expires_at = min(
            subscription_end,
            datetime.now() + timedelta(days=settings.TOKEN_EXPIRE_DAYS)
        )

        # Generate token
        token_data = {
            "sub": str(device['user_id']),
            "hardware_id": hardware_id,
            "os_type": _,
            "normalized_id": normalized_id,
            "exp": expires_at
        }
        token = jwt.encode(
            token_data,
            settings.DEVICE_SECRET_KEY,
            algorithm="HS256"
        )

        # Update device record
        await db.execute("""
            UPDATE devices 
            SET current_token = ?, 
                token_expiry = ?,
                last_verified_at = ?
            WHERE hardware_id = ?
        """, (token, expires_at, datetime.now(), hardware_id))
        await db.commit()

        return {
            "token": token,
            "expires_at": expires_at
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Token generation failed: {str(e)}"
        )

@router.get("/devices/verify")
async def verify_device(
    db = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Verify current device hardware identifier"""
    try:
        os_type, raw_id, normalized_id = HardwareIdentifier.get_hardware_id()  # type: ignore # pylint: disable=unused-variable
        logger.debug(f"Hardware ID obtained - OS: {os_type}, Raw ID: {raw_id}, Normalized ID: {normalized_id}")

        cursor = await db.execute("""
            SELECT * FROM devices 
            WHERE normalized_identifier = ? 
            AND user_id = ? 
            AND is_active = TRUE
        """, (normalized_id, current_user['id']))
        device = await cursor.fetchone()

        if not device:
            return {"verified": False, "reason": "Device not registered"}

        return {
            "verified": True,
            "hardware_id": device['hardware_id'],
            "os_type": device['os_type'],
            "last_verified": device['last_verified_at']
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Device verification failed: {str(e)}"
        )

@router.get("/devices/list", response_model=list[DeviceResponse])
async def list_devices(
    db = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """List all devices for admin or user's own devices"""
    try:
        logger.debug("=== Listing devices ===")
        logger.debug(f"Current user: {current_user}")
        
        if current_user.get('is_admin'):
            cursor = await db.execute("""
                SELECT 
                    hardware_id,
                    user_id,
                    os_type,
                    raw_identifier,
                    normalized_identifier,
                    is_active,
                    registered_at,
                    last_verified_at
                FROM devices
            """)
        else:
            cursor = await db.execute("""
                SELECT 
                    hardware_id,
                    user_id,
                    os_type,
                    raw_identifier,
                    normalized_identifier,
                    is_active,
                    registered_at,
                    last_verified_at
                FROM devices 
                WHERE user_id = ?
            """, (current_user['id'],))
            
        rows = await cursor.fetchall()
        devices = []
        for row in rows:
            devices.append({
                'hardware_id': row[0],
                'user_id': row[1],
                'os_type': row[2],
                'raw_identifier': row[3],
                'normalized_identifier': row[4],
                'is_active': bool(row[5]),
                'registered_at': row[6],
                'last_verified_at': row[7]
            })
        
        return devices
        
    except Exception as e:
        logger.error(f"Failed to list devices: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list devices: {str(e)}"
        )

@router.post("/admin/reset-devices-table")
async def reset_devices_table(
    db = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Reset devices table with correct schema (admin only)"""
    if not current_user.get('is_admin'):
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )
        
    try:
        # Drop existing table
        await db.execute("DROP TABLE IF EXISTS devices")
        
        # Create table with correct schema
        await db.execute("""
        CREATE TABLE devices (
            hardware_id TEXT PRIMARY KEY,
            user_id INTEGER,
            os_type TEXT NOT NULL,
            raw_identifier TEXT NOT NULL,
            normalized_identifier TEXT NOT NULL,
            is_active BOOLEAN DEFAULT true,
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_verified_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        """)
        
        await db.commit()
        return {"message": "Devices table reset successfully"}
        
    except Exception as e:
        logger.error(f"Failed to reset devices table: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reset devices table: {str(e)}"
        )

@router.post("/devices/deactivate", response_model=DeviceResponse)
async def deactivate_device(
    device: DeviceDeactivate,
    db = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Deactivate a device"""
    try:
        # Check if device exists
        cursor = await db.execute("""
            SELECT user_id, hardware_id, os_type, normalized_identifier, 
                   is_active, registered_at, last_verified_at 
            FROM devices 
            WHERE hardware_id = ?
        """, (device.hardware_id,))
        existing_device = await cursor.fetchone()
        
        if not existing_device:
            raise HTTPException(
                status_code=404,
                detail="Device not found"
            )

        # Unpack tuple values
        user_id, hw_id, os_type, norm_id, _, reg_at, _ = existing_device
        # Only admin or device owner can deactivate
        if not current_user.get('is_admin') and user_id != current_user.get('id'):
            raise HTTPException(
                status_code=403,
                detail="Not authorized to deactivate this device"
            )

        # Deactivate the device
        now = datetime.now()
        await db.execute("""
            UPDATE devices 
            SET is_active = FALSE,
                last_verified_at = ?
            WHERE hardware_id = ?
        """, (now.isoformat(), device.hardware_id))
        await db.commit()

        return {
            "user_id": user_id,
            "hardware_id": hw_id,
            "os_type": os_type,
            "normalized_identifier": norm_id,
            "is_active": False,
            "registered_at": reg_at,
            "last_verified_at": now
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Device deactivation failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Device deactivation failed: {str(e)}"
        )

@router.post("/devices/reactivate", response_model=DeviceResponse)
async def reactivate_device(
    device: DeviceDeactivate,  # We can reuse this schema
    db = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Reactivate a device (admin only)"""
    try:
        # Only admin can reactivate devices
        if not current_user.get('is_admin'):
            raise HTTPException(
                status_code=403,
                detail="Only administrators can reactivate devices"
            )

        # Check if device exists
        cursor = await db.execute("""
            SELECT user_id, hardware_id, os_type, normalized_identifier, 
                   is_active, registered_at, last_verified_at 
            FROM devices 
            WHERE hardware_id = ?
        """, (device.hardware_id,))
        existing_device = await cursor.fetchone()
        
        if not existing_device:
            raise HTTPException(
                status_code=404,
                detail="Device not found"
            )

        # Unpack tuple values
        user_id, hw_id, os_type, norm_id, _, reg_at, _ = existing_device
        # Reactivate the device
        now = datetime.now()
        await db.execute("""
            UPDATE devices 
            SET is_active = TRUE,
                last_verified_at = ?
            WHERE hardware_id = ?
        """, (now.isoformat(), device.hardware_id))
        await db.commit()

        return {
            "user_id": user_id,
            "hardware_id": hw_id,
            "os_type": os_type,
            "normalized_identifier": norm_id,
            "is_active": True,
            "registered_at": reg_at,
            "last_verified_at": now
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Device reactivation failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Device reactivation failed: {str(e)}"
        )
    