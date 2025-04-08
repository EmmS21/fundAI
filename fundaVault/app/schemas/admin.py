"""
admin.py (schemas)

Purpose: Define Pydantic models for admin-specific request/response validation.
"""
from pydantic import BaseModel, EmailStr
from typing import Optional

# Existing AdminLogin can remain if needed for /admin/login
class AdminLogin(BaseModel):
    email: str
    password: str

# New Schema for Admin Device Registration
class DeviceRegistrationRequest(BaseModel):
    hardware_id: str # Client-provided ID
    email: EmailStr
    full_name: str
    address: Optional[str] = None 
    city: Optional[str] = None
    country: Optional[str] = None
