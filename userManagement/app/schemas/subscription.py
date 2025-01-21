"""
subscription.py

Purpose: Define Pydantic models for subscription-related request/response validation.
"""
from pydantic import BaseModel
from datetime import datetime

class SubscriptionBase(BaseModel):
    user_id: int
    start_date: datetime
    end_date: datetime

class SubscriptionCreate(SubscriptionBase):
    pass

class SubscriptionResponse(SubscriptionBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
