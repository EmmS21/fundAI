"""
device.py

Purpose: Define Pydantic models for device-related request/response validation.
"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class DeviceBase(BaseModel):
    user_id: int

class DeviceRegister(DeviceBase):
    pass

class DeviceResponse(DeviceBase):
    hardware_id: str
    os_type: str
    normalized_identifier: str
    is_active: bool
    registered_at: datetime
    last_verified_at: Optional[datetime]

    class Config:
        from_attributes = True

class DeviceToken(BaseModel):
    token: str
    expires_at: datetime

class DeviceDeactivate(BaseModel):
    hardware_id: str

