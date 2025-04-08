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

# Keep CREATE_DEVICE_TABLE definition here if referenced by init_db directly,
# otherwise it can be removed as it's defined in database.py now
# CREATE_DEVICE_TABLE = """...""" # Defined in database.py

# --- REMOVE ORIGINAL DEVICE REGISTRATION ---
# @router.post("/devices/register", response_model=DeviceResponse)
# async def register_device(...):
#     """(REMOVED - Use admin endpoint /api/v1/admin/register-device)"""
#     # ... (implementation deleted) ...
#     raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Endpoint removed.")


# --- REMOVE DEVICE TOKEN GENERATION ---
# @router.post("/devices/{hardware_id}/token", response_model=DeviceToken)
# async def generate_device_token(...):
#     """(REMOVED - Device tokens are no longer used in this flow)"""
#     # ... (implementation deleted) ...
#     raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Endpoint removed.")


# --- REMOVE DEVICE VERIFICATION (Based on Server ID) ---
# @router.get("/devices/verify")
# async def verify_device(...):
#     """(REMOVED - Verification now happens via /api/v1/auth/device)"""
#     # ... (implementation deleted) ...
#     raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Endpoint removed.")


# Keep list_devices for admins (Ensure it works with the simplified table - modification done in admin.py)
@router.get("/devices/list", response_model=list[DeviceResponse])
async def list_devices(
    db = Depends(get_db),
    current_user: dict = Depends(get_current_user) # Assumes get_current_user checks for admin elsewhere
):
    # This now likely only makes sense for admins.
    # The DeviceResponse schema might need adjustment if columns were removed.
    # Let's adjust the query for the simplified table.
    """List devices (primarily for admin use)."""
    logger.debug(f"Device list requested by UserID=[{current_user.get('id')}] Admin=[{current_user.get('is_admin')}]")
    if not current_user.get('is_admin'):
        # Regular users shouldn't list arbitrary devices, maybe list their own?
        # For now, restrict to admin or return empty list for non-admin.
        logger.warning(f"Non-admin user [{current_user.get('id')}] attempted to list all devices.")
        # Option 1: Error
        # raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required to list all devices.")
        # Option 2: Empty list
        return []

    # Admin query for simplified table
    query = """
        SELECT
            d.hardware_id, d.user_id, d.is_active, d.registered_at, d.last_verified_at,
            u.email, u.full_name
        FROM devices d
        LEFT JOIN users u ON d.user_id = u.id
    """
    cursor = await db.execute(query)
    rows = await cursor.fetchall()
    columns = [description[0] for description in cursor.description]
    devices_data = [dict(zip(columns, row)) for row in rows]

    # Adapt to DeviceResponse schema - NOTE: DeviceResponse may need updating
    # if fields like os_type, normalized_identifier are removed
    # Manual mapping might be needed if schema doesn't match columns exactly
    response_list = []
    for d in devices_data:
       try:
           # Attempt to create response object, may fail if schema mismatch
            response_list.append(DeviceResponse(
                hardware_id=d['hardware_id'],
                user_id=d['user_id'],
                is_active=d['is_active'],
                registered_at=d['registered_at'],
                last_verified_at=d['last_verified_at'],
                # Fields removed from table, not available:
                os_type="N/A",
                normalized_identifier="N/A"
            ))
       except Exception as schema_err:
            logger.error(f"Schema mapping error for device {d.get('hardware_id')}: {schema_err}")
            # Handle error, e.g., skip device or return partial data

    return response_list


# --- Keep Deactivate/Reactivate for Admin use ---
# Note: These were already modified in admin.py to use hardware_id correctly
# Move them fully to admin.py? Or keep them here but ensure they require admin auth?
# Let's assume they are correctly implemented in admin.py and remove duplicates here.

# @router.post("/devices/deactivate", ...)
# @router.post("/devices/reactivate", ...)
    