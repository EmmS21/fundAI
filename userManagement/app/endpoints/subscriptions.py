"""
subscriptions.py

Purpose: Manage user subscriptions, including creation, renewal, and status checks.
"""
from fastapi import APIRouter, HTTPException
from ..db.database import get_db
from datetime import datetime, timedelta

router = APIRouter()

@router.post("/subscriptions/{user_id}")
async def create_subscription(user_id: int):
    """Create a new monthly subscription for user"""
    try:
        db = await get_db()
        try:
            # Check if subscription exists
            cursor = await db.execute(
                "SELECT id FROM subscriptions WHERE user_id = ?",
                (user_id,)
            )
            if await cursor.fetchone():
                raise HTTPException(
                    status_code=400,
                    detail="Subscription already exists"
                )
            
            # Create subscription
            start_date = datetime.utcnow()
            end_date = start_date + timedelta(days=30)  
            
            await db.execute(
                """
                INSERT INTO subscriptions 
                (user_id, start_date, end_date) 
                VALUES (?, ?, ?)
                """,
                (user_id, start_date.isoformat(), end_date.isoformat())
            )
            await db.commit()
            
            return {
                "message": "Subscription created",
                "user_id": user_id,
                "start_date": start_date,
                "end_date": end_date
            }
            
        finally:
            await db.close()
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create subscription: {str(e)}"
        )

@router.get("/subscriptions/{user_id}/status")
async def get_subscription_status(user_id: int):
    """Check subscription status for user"""
    try:
        db = await get_db()
        try:
            cursor = await db.execute(
                """
                SELECT start_date, end_date 
                FROM subscriptions 
                WHERE user_id = ?
                """,
                (user_id,)
            )
            subscription = await cursor.fetchone()
            
            if not subscription:
                return {"active": False, "reason": "No subscription found"}
            
            end_date = datetime.fromisoformat(subscription[1])
            is_active = end_date > datetime.utcnow()
            
            return {
                "active": is_active,
                "end_date": end_date,
                "days_remaining": (end_date - datetime.utcnow()).days
            }
            
        finally:
            await db.close()
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check subscription: {str(e)}"
        )
