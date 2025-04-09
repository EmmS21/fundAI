"""
admin.py

Purpose: Admin-specific endpoints for managing users, devices, and subscriptions.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime
from jose import jwt, JWTError # Keep for verify_admin
from pydantic import BaseModel
import logging
from supabase import Client as SupabaseClient # Import Supabase client type hint
from typing import List # For type hinting response models if needed

from app.core.jwt import oauth2_scheme
from app.db.database import get_db # Import the updated get_db providing SupabaseClient
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
async def get_all_users(db: SupabaseClient = Depends(get_db)):
    """Get all users in the system"""
    try:
        logger.info("Fetching all users from Supabase...") # Log entry
        response = db.table('users').select('*').execute()
        logger.info(f"Supabase response data for GET /users: {response.data}")

        # Refined error check: Check if error attribute exists and is truthy
        has_error = hasattr(response, 'error') and response.error
        if has_error:
            logger.error(f"Error fetching users: {response.error}")
            raise HTTPException(status_code=500, detail=f"Failed to fetch users: {response.error}")

        # If no error, return the data (response.data is a list)
        logger.info(f"Successfully fetched {len(response.data)} users.") # Log success count
        return {"users": response.data}

    except Exception as e:
        # Catch other unexpected errors (e.g., network issues, client init failure)
        logger.error(f"Unexpected error fetching users: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch users")

@router.get("/subscriptions", dependencies=[Depends(verify_admin)])
async def get_all_subscriptions(db: SupabaseClient = Depends(get_db)):
    """Get all subscriptions with user details (email, full_name)"""
    try:
        # Fetch subscriptions
        subs_response = db.table('subscriptions').select('*').execute()
        if subs_response.error:
             logger.error(f"Error fetching subscriptions: {subs_response.error}")
             raise HTTPException(status_code=500, detail="Failed to fetch subscriptions")
        subscriptions = subs_response.data

        if not subscriptions:
             return {"subscriptions": []}

        # Fetch corresponding user details
        user_ids = list(set(sub['user_id'] for sub in subscriptions if sub.get('user_id')))
        if not user_ids: # Handle case where subscriptions might have null user_id (though schema prevents it)
             logger.warning("No valid user IDs found in subscriptions fetched.")
             return {"subscriptions": subscriptions} # Return subs without user details

        users_response = db.table('users').select('id, email, full_name').in_('id', user_ids).execute()
        if users_response.error:
            logger.error(f"Error fetching user details for subscriptions: {users_response.error}")
            # Return subscriptions without user details as fallback? Or error out? Erroring out for now.
            raise HTTPException(status_code=500, detail="Failed to fetch user details for subscriptions")

        users_map = {user['id']: user for user in users_response.data}

        # Combine data
        combined_data = []
        for sub in subscriptions:
            user_info = users_map.get(sub.get('user_id'))
            sub_with_user = sub.copy()
            if user_info:
                sub_with_user['email'] = user_info.get('email')
                sub_with_user['full_name'] = user_info.get('full_name')
            else:
                 sub_with_user['email'] = None
                 sub_with_user['full_name'] = None
            combined_data.append(sub_with_user)

        return {"subscriptions": combined_data}

    except Exception as e:
        logger.error(f"Unexpected error fetching subscriptions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch subscriptions")

@router.get("/devices", dependencies=[Depends(verify_admin)])
async def get_all_devices(db: SupabaseClient = Depends(get_db)):
    """Get all registered devices with user details (email, full_name)"""
    try:
        # Fetch devices
        devices_response = db.table('devices').select('*').execute()
        if devices_response.error:
             logger.error(f"Error fetching devices: {devices_response.error}")
             raise HTTPException(status_code=500, detail="Failed to fetch devices")
        devices = devices_response.data

        if not devices:
             return {"devices": []}

        # Fetch corresponding user details
        user_ids = list(set(dev['user_id'] for dev in devices if dev.get('user_id')))
        if not user_ids:
             logger.warning("No valid user IDs found in devices fetched.")
             return {"devices": devices} # Return devices without user details

        users_response = db.table('users').select('id, email, full_name').in_('id', user_ids).execute()
        if users_response.error:
            logger.error(f"Error fetching user details for devices: {users_response.error}")
            raise HTTPException(status_code=500, detail="Failed to fetch user details for devices")

        users_map = {user['id']: user for user in users_response.data}

        # Combine data
        combined_data = []
        for dev in devices:
            user_info = users_map.get(dev.get('user_id'))
            dev_with_user = dev.copy()
            if user_info:
                dev_with_user['email'] = user_info.get('email')
                dev_with_user['full_name'] = user_info.get('full_name')
            else:
                dev_with_user['email'] = None
                dev_with_user['full_name'] = None
            combined_data.append(dev_with_user)

        return {"devices": combined_data}

    except Exception as e:
        logger.error(f"Unexpected error fetching devices: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch devices")

@router.post("/users/{user_id}/deactivate", dependencies=[Depends(verify_admin)])
async def deactivate_user(user_id: int, db: SupabaseClient = Depends(get_db)):
    """Deactivate a user account"""
    try:
        response = db.table('users').update({'is_active': False}).eq('id', user_id).execute()
        if response.error:
             logger.error(f"Error deactivating user {user_id}: {response.error}")
             # Consider specific error checking (e.g., user not found?)
             raise HTTPException(status_code=500, detail=f"Failed to deactivate user: {response.error}")
        if not response.data: # Check if any row was actually updated
             logger.warning(f"Attempted to deactivate non-existent user ID: {user_id}")
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User {user_id} not found")

        logger.info(f"User {user_id} deactivated successfully.")
        return {"message": f"User {user_id} deactivated"}
    except HTTPException as http_exc:
        raise http_exc # Re-raise specific HTTP exceptions
    except Exception as e:
        logger.error(f"Unexpected error deactivating user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to deactivate user")

@router.post("/users/{user_id}/activate", dependencies=[Depends(verify_admin)])
async def activate_user(user_id: int, db: SupabaseClient = Depends(get_db)):
    """Activate a user account"""
    try:
        response = db.table('users').update({'is_active': True}).eq('id', user_id).execute()
        if response.error:
             logger.error(f"Error activating user {user_id}: {response.error}")
             raise HTTPException(status_code=500, detail=f"Failed to activate user: {response.error}")
        if not response.data:
             logger.warning(f"Attempted to activate non-existent user ID: {user_id}")
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User {user_id} not found")

        logger.info(f"User {user_id} activated successfully.")
        return {"message": f"User {user_id} activated"}
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Unexpected error activating user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to activate user")

@router.get("/stats", dependencies=[Depends(verify_admin)])
async def get_system_stats(db: SupabaseClient = Depends(get_db)):
    """Get system statistics"""
    try:
        users_resp = db.table('users').select('id', count='exact').limit(0).execute()
        devices_resp = db.table('devices').select('hardware_id', count='exact').limit(0).execute()
        subs_resp = db.table('subscriptions').select('id', count='exact').limit(0).execute()

        # Basic error check (could be more granular)
        if users_resp.error or devices_resp.error or subs_resp.error:
             logger.error(f"Error fetching stats - Users: {users_resp.error}, Devices: {devices_resp.error}, Subs: {subs_resp.error}")
             raise HTTPException(status_code=500, detail="Failed to retrieve system statistics")

        return {
            "total_users": users_resp.count,
            "total_devices": devices_resp.count,
            "active_subscriptions": subs_resp.count, # Assuming this table only holds active subs now
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        logger.error(f"Unexpected error getting system stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve system statistics")

@router.delete("/users/{user_id}", dependencies=[Depends(verify_admin)], status_code=status.HTTP_200_OK)
async def delete_user(user_id: int, db: SupabaseClient = Depends(get_db)):
    """Delete a user and associated data (assuming ON DELETE CASCADE)"""
    try:
        # ON DELETE CASCADE in FKs should handle devices and subscriptions
        response = db.table('users').delete().eq('id', user_id).execute()

        if response.error:
             logger.error(f"Error deleting user {user_id}: {response.error}")
             # Check if it's a foreign key issue or other problem
             raise HTTPException(status_code=500, detail=f"Failed to delete user: {response.error}")
        if not response.data: # Check if a row was actually deleted
             logger.warning(f"Attempted to delete non-existent user ID: {user_id}")
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User {user_id} not found")

        logger.info(f"User {user_id} and associated data deleted successfully.")
        return {"message": f"User {user_id} and associated data deleted"}

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Unexpected error deleting user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete user")

@router.post("/register-device", status_code=status.HTTP_201_CREATED, dependencies=[Depends(verify_admin)])
async def admin_register_device(
    device_data: DeviceRegistrationRequest,
    db: SupabaseClient = Depends(get_db)
):
    """
    Admin endpoint using Supabase client.
    Registers a device, creates user if needed (simplified schema).
    """
    logger.info(f"Admin attempting to register device: HardwareID=[{device_data.hardware_id}] Email=[{device_data.email}]")

    try:
        # 1. Check if hardware_id exists
        response = db.table('devices').select('user_id').eq('hardware_id', device_data.hardware_id).limit(1).execute()
        # Check for explicit error first
        has_error = hasattr(response, 'error') and response.error
        if has_error:
             logger.error(f"Error checking for existing device {device_data.hardware_id}: {response.error}")
             raise HTTPException(status_code=500, detail=f"Database error checking device: {response.error}")
        # If no error, check if data was returned (meaning device exists)
        if response.data:
            logger.warning(f"Device registration failed: Hardware ID [{device_data.hardware_id}] already registered to User ID [{response.data[0]['user_id']}].")
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Hardware ID already registered.")

        # 2. Find or Create User
        response = db.table('users').select('id').eq('email', device_data.email).limit(1).execute()
        # Check for explicit error first
        has_error = hasattr(response, 'error') and response.error
        if has_error:
             logger.error(f"Error checking for existing user {device_data.email}: {response.error}")
             raise HTTPException(status_code=500, detail=f"Database error checking user: {response.error}")

        user_id: int | None = None
        if response.data: # User found
            user_id = response.data[0]['id']
            logger.info(f"Found existing user: UserID=[{user_id}] Email=[{device_data.email}]")
            # Check if this user already has another active device
            response = db.table('devices').select('hardware_id').eq('user_id', user_id).eq('is_active', True).limit(1).execute()
            # Check for error fetching active device
            has_error = hasattr(response, 'error') and response.error
            if has_error:
                 logger.error(f"Error checking active devices for user {user_id}: {response.error}")
                 raise HTTPException(status_code=500, detail=f"Database error checking active devices: {response.error}")
            # If no error, check if data exists
            if response.data:
                 existing_hw_id = response.data[0]['hardware_id']
                 logger.warning(f"User [{user_id}] already has an active device [{existing_hw_id}]. Registration failed for new device [{device_data.hardware_id}].")
                 raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already has an active device registered.")
        else: # User not found, create new user
            logger.info(f"User not found, creating new user: Email=[{device_data.email}]")
            dummy_hash = get_password_hash("DEFAULT_PASSWORD_PLACEHOLDER")
            user_data = {k: v for k, v in {
                'email': device_data.email, 'hashed_password': dummy_hash,
                'full_name': device_data.full_name, 'address': device_data.address,
                'city': device_data.city, 'country': device_data.country,
                'is_active': True
            }.items() if v is not None}

            response = db.table('users').insert(user_data).execute()

            # Check for errors and retrieve the new user ID (Refined Check)
            has_error = hasattr(response, 'error') and response.error
            if has_error or not response.data or len(response.data) == 0:
                error_detail = response.error if has_error else 'Unknown insert error or no data returned'
                logger.error(f"Failed to insert new user or retrieve ID for email {device_data.email}. Error: {error_detail}")
                raise HTTPException(status_code=500, detail=f"Failed to create user record: {error_detail}")
            user_id = response.data[0]['id']
            logger.info(f"New user created: UserID=[{user_id}] Email=[{device_data.email}]")

        # 3. Register the Device (Simplified Schema)
        device_insert_data = {
            'hardware_id': device_data.hardware_id,
            'user_id': user_id
        }
        response = db.table('devices').insert(device_insert_data).execute()

        # Check for insert errors (Refined Check)
        has_error = hasattr(response, 'error') and response.error
        # Also check if data is missing, as insert should return the inserted row
        if has_error or not response.data or len(response.data) == 0:
             error_detail = response.error if has_error else 'Unknown insert error or no data returned'
             logger.error(f"Failed to insert device {device_data.hardware_id} for user {user_id}. Error: {error_detail}")
             raise HTTPException(status_code=500, detail=f"Failed to register device: {error_detail}")

        # Log success
        logger.info(f"Device registered successfully: HardwareID=[{device_data.hardware_id}] UserID=[{user_id}]")

        # Return success response
        return {
            "message": "Device registered successfully",
            "hardware_id": device_data.hardware_id,
            "user_id": user_id,
            "email": device_data.email
        }

    except HTTPException as http_exc:
        # Log and re-raise known HTTP exceptions
        logger.warning(f"HTTPException during admin device registration: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        # Log unexpected errors
        logger.error(f"Admin device registration failed unexpectedly: HardwareID=[{device_data.hardware_id}] Error=[{e}]", exc_info=True)
        raise HTTPException(status_code=500, detail="Device registration failed due to an internal error.")

@router.post("/devices/{hardware_id}/deactivate", dependencies=[Depends(verify_admin)])
async def deactivate_device(hardware_id: str, db: SupabaseClient = Depends(get_db)):
    """Deactivate a device by hardware ID"""
    try:
        response = db.table('devices').update({'is_active': False}).eq('hardware_id', hardware_id).execute()
        if response.error:
             logger.error(f"Error deactivating device {hardware_id}: {response.error}")
             raise HTTPException(status_code=500, detail=f"Failed to deactivate device: {response.error}")
        if not response.data:
             logger.warning(f"Attempted to deactivate non-existent device: {hardware_id}")
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")

        logger.info(f"Device {hardware_id} deactivated successfully.")
        return {"message": f"Device {hardware_id} deactivated"}
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Unexpected error deactivating device {hardware_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to deactivate device")

@router.post("/devices/{hardware_id}/activate", dependencies=[Depends(verify_admin)])
async def activate_device(hardware_id: str, db: SupabaseClient = Depends(get_db)):
    """Activate a device by hardware ID"""
    try:
        # Check if user already has an active device before activating new one
        # 1. Find user_id for the target device
        target_device = db.table('devices').select('user_id').eq('hardware_id', hardware_id).limit(1).execute()
        if not target_device.data:
            logger.warning(f"Attempted to activate non-existent device: {hardware_id}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
        user_id = target_device.data[0]['user_id']

        # 2. Check if this user has another active device
        active_device = db.table('devices').select('hardware_id').eq('user_id', user_id).eq('is_active', True).neq('hardware_id', hardware_id).limit(1).execute() # neq = not equal
        if active_device.data:
             other_hw_id = active_device.data[0]['hardware_id']
             logger.warning(f"Cannot activate device {hardware_id}: User {user_id} already has active device {other_hw_id}.")
             raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"User already has an active device ({other_hw_id}). Deactivate it first.")

        # 3. Activate the target device
        response = db.table('devices').update({'is_active': True}).eq('hardware_id', hardware_id).execute()
        if response.error:
             logger.error(f"Error activating device {hardware_id}: {response.error}")
             raise HTTPException(status_code=500, detail=f"Failed to activate device: {response.error}")
        # Check if update happened (response.data should contain updated record)
        if not response.data:
             # This case should technically be caught by the first check, but good to be safe
             logger.warning(f"Attempted to activate non-existent device (post-check): {hardware_id}")
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")

        logger.info(f"Device {hardware_id} activated successfully.")
        return {"message": f"Device {hardware_id} activated"}
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Unexpected error activating device {hardware_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to activate device") 