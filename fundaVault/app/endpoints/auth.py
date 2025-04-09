"""
auth.py

Purpose: Endpoints related to non-admin authentication, specifically device auth.
"""
from fastapi import APIRouter, HTTPException, Depends, status
from datetime import datetime, timezone
import logging
from supabase import Client as SupabaseClient

from app.db.database import get_db
from app.schemas.auth import DeviceAuthRequest, DeviceAuthResponse # Import new schemas

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/device", response_model=DeviceAuthResponse)
async def authenticate_device(
    auth_request: DeviceAuthRequest,
    db: SupabaseClient = Depends(get_db)
):
    """
    Authenticate a user based on the provided client hardware ID.
    Checks if the device is registered, active, and linked to an active subscription.
    """
    hardware_id = auth_request.hardware_id
    logger.info(f"Device authentication attempt: HardwareID=[{hardware_id}]")

    try:
        # 1. Check if device exists and is active
        device_response = db.table('devices')\
                            .select('user_id, is_active')\
                            .eq('hardware_id', hardware_id)\
                            .limit(1)\
                            .execute()

        # Use hasattr for safer error checking
        device_has_error = hasattr(device_response, 'error') and device_response.error
        if device_has_error:
            logger.error(f"Error checking device {hardware_id}: {device_response.error}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error checking device.")

        if not device_response.data:
            logger.warning(f"Device auth failed: Hardware ID not found. HardwareID=[{hardware_id}]")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not registered.")

        device_data = device_response.data[0]
        user_id = device_data['user_id']
        is_active = device_data['is_active']

        if not is_active:
            logger.warning(f"Device auth failed: Device is inactive. HardwareID=[{hardware_id}] UserID=[{user_id}]")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Device is inactive.")

        # 2. Check user's subscription status (assuming subscriptions table exists and works)
        # Use timezone-aware comparison if possible, Supabase often uses UTC
        now_utc = datetime.now(timezone.utc).isoformat()
        subscription_response = db.table('subscriptions')\
                                  .select('id')\
                                  .eq('user_id', user_id)\
                                  .gt('end_date', now_utc)\
                                  .limit(1)\
                                  .execute() # Check for active subscription ending after now

        # Use hasattr for safer error checking
        subscription_has_error = hasattr(subscription_response, 'error') and subscription_response.error
        if subscription_has_error:
            logger.error(f"Error checking subscription for user {user_id}: {subscription_response.error}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error checking subscription.")

        if not subscription_response.data:
            logger.warning(f"Device auth failed: No active subscription found. HardwareID=[{hardware_id}] UserID=[{user_id}]")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Active subscription required.")

        # 3. Get user email for response
        user_response = db.table('users')\
                          .select('email')\
                          .eq('id', user_id)\
                          .limit(1)\
                          .execute()

        # Use hasattr for safer error checking
        user_has_error = hasattr(user_response, 'error') and user_response.error
        if user_has_error:
            logger.error(f"Error fetching user email for user {user_id}: {user_response.error}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error fetching user details.")

        if not user_response.data:
            # Should not happen if FK constraint is working, but check anyway
            logger.error(f"Device auth inconsistency: User not found for registered device. UserID=[{user_id}] HardwareID=[{hardware_id}]")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal data inconsistency.")

        user_email = user_response.data[0]['email']

        # Optional: Update last_verified_at timestamp
        update_response = db.table('devices')\
                            .update({'last_verified_at': datetime.now(timezone.utc).isoformat()})\
                            .eq('hardware_id', hardware_id)\
                            .execute()

        # Use hasattr for safer error checking
        update_has_error = hasattr(update_response, 'error') and update_response.error
        if update_has_error:
             # Log the error but don't necessarily fail the auth for this
             logger.error(f"Failed to update last_verified_at for device {hardware_id}: {update_response.error}")
        # No need for commit/rollback with Supabase client library

        logger.info(f"Device authentication successful: HardwareID=[{hardware_id}] UserID=[{user_id}]")
        return DeviceAuthResponse(authenticated=True, user_id=user_id, email=user_email)

    except HTTPException as http_exc:
        # No db.rollback() needed here
        raise http_exc
    except Exception as e:
        # No db.rollback() needed here
        logger.error(f"Device authentication failed unexpectedly: HardwareID=[{hardware_id}] Error=[{e}]", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Device authentication failed due to an internal error.")
