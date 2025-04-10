"""
subscriptions.py

Purpose: Manage user subscriptions, including creation, renewal, and status checks.
"""
from fastapi import APIRouter, HTTPException, Depends, status
from app.db.database import get_db
from datetime import datetime, timedelta, timezone
from supabase import Client as SupabaseClient
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/subscriptions/{user_id}", status_code=status.HTTP_201_CREATED)
async def create_subscription(
    user_id: int,
    db: SupabaseClient = Depends(get_db)
):
    """Create a new monthly subscription for user using Supabase client."""
    logger.info(f"Attempting to create subscription for UserID=[{user_id}]")
    try:
        # 1. Check if user exists
        logger.debug(f"Checking user existence for UserID=[{user_id}]")
        user_check_response = db.table('users')\
                                .select('id', count='exact')\
                                .eq('id', user_id)\
                                .limit(1)\
                                .execute()
        # Log the raw response object (might reveal internal attributes)
        logger.debug(f"User check response object: {user_check_response!r}")

        if user_check_response is None:
             logger.error(f"User check query returned None unexpectedly for UserID=[{user_id}]")
             raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error during user check.")
        if user_check_response.count == 0:
            logger.warning(f"Subscription creation failed: User not found. UserID=[{user_id}]")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
        logger.debug(f"User check passed for UserID=[{user_id}]")

        # 2. Check if subscription exists
        logger.debug(f"Checking existing subscription for UserID=[{user_id}]")
        sub_check_response = db.table('subscriptions')\
                               .select('id')\
                               .eq('user_id', user_id)\
                               .maybe_single()\
                               .execute()
        logger.debug(f"Subscription check response object: {sub_check_response!r}")

        if sub_check_response is None:
            logger.error(f"Subscription check query returned None unexpectedly for UserID=[{user_id}]. This likely follows a non-2xx HTTP status from Supabase.")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error during subscription check (Query failed).")

        if sub_check_response.data is not None:
            logger.warning(f"Subscription creation failed: Already exists. UserID=[{user_id}]")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Subscription already exists for this user."
            )
        logger.debug(f"Subscription check passed (no existing found) for UserID=[{user_id}]")

        # 3. Create subscription
        logger.debug(f"Proceeding to create subscription for UserID=[{user_id}]")
        start_date = datetime.now(timezone.utc)
        end_date = start_date + timedelta(days=30)
        insert_data = {
            'user_id': user_id,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat()
        }
        insert_response = db.table('subscriptions').insert(insert_data).execute()
        logger.debug(f"Insert subscription response object: {insert_response!r}")

        if insert_response is None:
            logger.error(f"Subscription insert query returned None unexpectedly for UserID=[{user_id}]")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error during subscription insert.")

        if not insert_response.data:
             logger.error(f"Subscription insert for UserID=[{user_id}] failed unexpectedly (no data returned).")
             raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to confirm subscription creation.")

        created_sub = insert_response.data[0]
        logger.info(f"Subscription created successfully: SubID=[{created_sub.get('id')}] UserID=[{user_id}]")

        return {
            "message": "Subscription created successfully",
            "user_id": user_id,
            "subscription_id": created_sub.get('id'),
            "start_date": created_sub.get('start_date'),
            "end_date": created_sub.get('end_date')
        }

    except HTTPException as http_exc:
        logger.warning(f"HTTPException during subscription creation for UserID=[{user_id}]: {http_exc.detail} (Status: {http_exc.status_code})")
        raise http_exc
    except Exception as e:
        logger.error(f"Error during subscription creation for UserID=[{user_id}]: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error during subscription creation.")

@router.get("/subscriptions/{user_id}/status")
async def get_subscription_status(
    user_id: int,
    db: SupabaseClient = Depends(get_db)
):
    """Check subscription status for user using Supabase client."""
    logger.info(f"Checking subscription status for UserID=[{user_id}]")
    try:
        # Fetch subscription details - .execute() might raise APIError on failure
        response = db.table('subscriptions')\
                     .select('start_date, end_date')\
                     .eq('user_id', user_id)\
                     .maybe_single()\
                     .execute() # maybe_single returns one or None based on rows found

        # Log the raw response
        logger.debug(f"Get status response object for UserID=[{user_id}]: {response!r}")

        # Defensive check if the response object itself is None (e.g., after 406 error)
        if response is None:
            logger.error(f"Get status query returned None unexpectedly for UserID=[{user_id}].")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error checking subscription status (received None).")

        subscription_data = response.data

        # Check if data is None (meaning maybe_single found no matching row)
        if subscription_data is None:
            logger.info(f"No subscription found for UserID=[{user_id}]")
            return {"active": False, "reason": "No subscription found"}

        # If data exists, proceed to check dates
        try:
            end_date_str = subscription_data.get('end_date')
            if not end_date_str:
                logger.error(f"Subscription record for UserID=[{user_id}] is missing end_date.")
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Subscription data incomplete.")

            # Parse end_date, making it timezone-aware (assuming UTC from Supabase timestamptz)
            if end_date_str.endswith('Z'):
                 end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
            elif '+' in end_date_str: # Already has offset
                 end_date = datetime.fromisoformat(end_date_str)
            else: # Assume UTC if no timezone info
                 logger.warning(f"Subscription end_date for UserID=[{user_id}] lacks timezone info. Assuming UTC.")
                 end_date = datetime.fromisoformat(end_date_str).replace(tzinfo=timezone.utc)

        except (TypeError, ValueError, KeyError) as parse_error:
             logger.error(f"Error processing subscription dates for UserID=[{user_id}]: {parse_error}. Data: {subscription_data}", exc_info=True)
             raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal error processing subscription dates.")

        # Compare with current time (timezone-aware)
        now_utc = datetime.now(timezone.utc)
        is_active = end_date > now_utc
        days_remaining = (end_date - now_utc).days if is_active else 0

        logger.info(f"Subscription status for UserID=[{user_id}]: Active={is_active}, EndDate={end_date.isoformat()}")
        return {
            "active": is_active,
            "start_date": subscription_data.get('start_date'), # Include start_date if available
            "end_date": end_date.isoformat(), # Return consistent ISO format
            "days_remaining": days_remaining
            # Remove "reason" if active=True
        }

    except HTTPException as http_exc:
        # Log details before re-raising known HTTP errors
        logger.warning(f"HTTPException during subscription status check for UserID=[{user_id}]: {http_exc.detail} (Status: {http_exc.status_code})")
        raise http_exc
    except Exception as e:
        # Catch Supabase APIError or any other unexpected Python errors
        logger.error(f"Error checking subscription status for UserID=[{user_id}]: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error checking subscription status."
        )

@router.post("/subscriptions/{user_id}/renew")
async def renew_subscription(
    user_id: int,
    db: SupabaseClient = Depends(get_db)
):
    """Renew user subscription for another month using Supabase client."""
    logger.info(f"Attempting to renew subscription for UserID=[{user_id}]")
    try:
        sub_response = db.table('subscriptions')\
                         .select('id, end_date')\
                         .eq('user_id', user_id)\
                         .maybe_single()\
                         .execute()

        if sub_response.error:
             logger.error(f"Error fetching current subscription for renewal UserID=[{user_id}]: {sub_response.error}")
             raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error finding subscription.")

        current_sub = sub_response.data
        if not current_sub:
            logger.warning(f"Subscription renewal failed: No subscription found. UserID=[{user_id}]")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No subscription found to renew."
            )

        try:
            current_end_str = current_sub['end_date']
            if current_end_str.endswith('Z'):
                 current_end = datetime.fromisoformat(current_end_str.replace('Z', '+00:00'))
            elif '+' in current_end_str:
                 current_end = datetime.fromisoformat(current_end_str)
            else:
                 logger.warning(f"Subscription current_end for UserID=[{user_id}] lacks timezone info. Assuming UTC.")
                 current_end = datetime.fromisoformat(current_end_str).replace(tzinfo=timezone.utc)
        except (TypeError, ValueError, KeyError) as parse_error:
             logger.error(f"Error parsing current_end '{current_sub.get('end_date')}' for renewal UserID=[{user_id}]: {parse_error}")
             raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal error processing subscription date for renewal.")

        new_end = current_end + timedelta(days=30)

        update_response = db.table('subscriptions')\
                            .update({'end_date': new_end.isoformat()})\
                            .eq('id', current_sub['id'])\
                            .execute()

        if update_response.error:
             logger.error(f"Error updating subscription end_date for UserID=[{user_id}], SubID=[{current_sub['id']}]: {update_response.error}")
             raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update subscription end date.")

        if not update_response.data:
             logger.error(f"Subscription update for UserID=[{user_id}], SubID=[{current_sub['id']}] did not return data despite no error.")
             raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to confirm subscription renewal.")

        logger.info(f"Subscription renewed successfully: SubID=[{current_sub['id']}] UserID=[{user_id}] NewEndDate=[{new_end.isoformat()}]")
        return {
            "message": "Subscription renewed successfully",
            "user_id": user_id,
            "subscription_id": current_sub['id'],
            "new_end_date": new_end.isoformat()
        }

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Unexpected error renewing subscription for UserID=[{user_id}]: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while renewing the subscription."
        )
