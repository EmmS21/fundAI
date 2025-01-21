"""
user.py

Purpose: Define Pydantic models for user-related request/response validation
and API documentation.
"""
from pydantic import BaseModel, EmailStr
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    address: str
    city: str
    country: str

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True  
