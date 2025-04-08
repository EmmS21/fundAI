"""
jwt.py

Purpose: Authentication dependencies and utilities for FastAPI endpoints.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt, ExpiredSignatureError, JWSError
import logging
import re # For masking

from app.db.database import get_db
from app.core.config import settings

# Configure logger for this module
logger = logging.getLogger(__name__) 

# Define oauth2 scheme (tokenUrl should point to your actual login endpoint)
# Corrected tokenUrl based on likely endpoint in users.py or admin.py
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/admin/login") 

# Function to mask Bearer tokens
def mask_token(token: str | None) -> str:
    if not token: return "None"
    # Handle potential "Bearer <token>" format
    parts = token.split()
    actual_token = parts[-1] # Take the last part
    if len(actual_token) > 8:
        return f"{actual_token[:4]}...{actual_token[-4:]}"
    return actual_token # Return as is if too short to mask meaningfully

# This function is now primarily for verifying ADMIN tokens
async def get_current_user(
    db = Depends(get_db),
    token: str = Depends(oauth2_scheme) # Uses admin login tokenUrl
):
    """Dependency to get current authenticated ADMIN from JWT token."""
    # NOTE: This function is now mostly relevant for admin verification,
    # as regular users authenticate via device ID.
    # Consider renaming to verify_admin_token or similar if only used for admins.

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate admin credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    masked = mask_token(token)
    logger.info(f"Attempting ADMIN token validation. Token=[{masked}]")

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM] # Use ALGORITHM from settings
            # Add audience/issuer validation if needed via options parameter
        )
        logger.debug(f"Admin token successfully decoded. Payload=[{payload}] Token=[{masked}]")

        email: str = payload.get("sub")
        is_admin: bool = payload.get("is_admin", False)

        if email is None:
            logger.warning(f"Admin token validation failed: 'sub' (email) claim missing. Payload=[{payload}] Token=[{masked}]")
            raise credentials_exception

        if not is_admin:
             logger.warning(f"Admin token validation failed: 'is_admin' claim is missing or false. Payload=[{payload}] Token=[{masked}]")
             raise HTTPException(
                 status_code=status.HTTP_403_FORBIDDEN, # Use 403 for authorization failure
                 detail="Admin privileges required.",
                 headers={"WWW-Authenticate": "Bearer"},
             )

        # Return admin representation
        logger.info(f"Admin token validated successfully. Email=[{email}] Token=[{masked}]")
        return {
            "id": 0, # Placeholder ID for admin
            "email": email,
            "is_admin": True,
            "full_name": "Admin User" # Placeholder name
        }

    except ExpiredSignatureError:
        logger.warning(f"Admin token validation failed: Token has expired. Token=[{masked}]")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # --- Removed specific JWTClaimsError catch ---
    # General JWTError will catch invalid signature, format, and potentially claim errors
    except JWTError as e:
        logger.warning(f"Admin token validation failed: JWTError (Invalid Signature/Format/Claims?). Error=[{e}] Token=[{masked}]")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e: # Catch unexpected errors
        logger.error(f"Unexpected error during admin token validation. Error=[{e}] Token=[{masked}]", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An internal error occurred during authentication.",
        )
