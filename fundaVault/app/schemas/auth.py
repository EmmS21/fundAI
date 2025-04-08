"""
auth.py (schemas)

Purpose: Define Pydantic models for device authentication.
"""
from pydantic import BaseModel

class DeviceAuthRequest(BaseModel):
    hardware_id: str

class DeviceAuthResponse(BaseModel):
    authenticated: bool
    user_id: int
    email: str
