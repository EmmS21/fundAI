"""
auth.py

Purpose: Endpoints related to non-admin authentication, specifically device auth.
"""
from fastapi import APIRouter, HTTPException, Depends, status
from datetime import datetime
import logging

from app.db.database import get_db
from app.schemas.auth import DeviceAuthRequest, DeviceAuthResponse # Import new schemas

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/device", response_model=DeviceAuthResponse)
async def authenticate_device(
    auth_request: DeviceAuthRequest,
    db = Depends(get_db)
):
    """
    Authenticate a user based on the provided client hardware ID.
    Checks if the device is registered, active, and linked to an active subscription.
    """
    hardware_id = auth_request.hardware_id
    logger.info(f"Device authentication attempt: HardwareID=[{hardware_id}]")

    try:
        # 1. Check if device exists and is active
        cursor = await db.execute(
            "SELECT user_id, is_active FROM devices WHERE hardware_id = ?",
            (hardware_id,)
        )
        device = await cursor.fetchone()

        if not device:
            logger.warning(f"Device auth failed: Hardware ID not found. HardwareID=[{hardware_id}]")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not registered.")

        user_id = device[0]
        is_active = bool(device[1])

        if not is_active:
            logger.warning(f"Device auth failed: Device is inactive. HardwareID=[{hardware_id}] UserID=[{user_id}]")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Device is inactive.")

        # 2. Check user's subscription status
        now_iso = datetime.now().isoformat()
        cursor = await db.execute(
            "SELECT end_date FROM subscriptions WHERE user_id = ? AND end_date > ?",
            (user_id, now_iso)
        )
        subscription = await cursor.fetchone()

        if not subscription:
            logger.warning(f"Device auth failed: No active subscription found. HardwareID=[{hardware_id}] UserID=[{user_id}]")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Active subscription required.")

        # 3. Get user email for response
        cursor = await db.execute("SELECT email FROM users WHERE id = ?", (user_id,))
        user = await cursor.fetchone()
        if not user:
             # Should not happen if FK constraint is working, but check anyway
             logger.error(f"Device auth inconsistency: User not found for registered device. UserID=[{user_id}] HardwareID=[{hardware_id}]")
             raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal data inconsistency.")

        user_email = user[0]

        # Optional: Update last_verified_at timestamp
        await db.execute(
            "UPDATE devices SET last_verified_at = ? WHERE hardware_id = ?",
            (datetime.now().isoformat(), hardware_id)
        )
        await db.commit()

        logger.info(f"Device authentication successful: HardwareID=[{hardware_id}] UserID=[{user_id}]")
        return DeviceAuthResponse(authenticated=True, user_id=user_id, email=user_email)

    except HTTPException:
        await db.rollback() # Rollback on expected errors like 404/403
        raise
    except Exception as e:
        await db.rollback() # Rollback on unexpected errors
        logger.error(f"Device authentication failed unexpectedly: HardwareID=[{hardware_id}] Error=[{e}]", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Device authentication failed due to an internal error.")
