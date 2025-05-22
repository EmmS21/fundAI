import logging
from supabase import create_client, Client as SupabaseClient # Use supabase-py
from app.core.config import settings # Import settings

logger = logging.getLogger(__name__)

# Global variable to hold the Supabase client instance
_supabase_client: SupabaseClient | None = None

def get_supabase_client() -> SupabaseClient:
    """Initializes and returns the singleton Supabase client instance."""
    global _supabase_client
    if _supabase_client is None:
        # MODIFIED FOR DEBUGGING - MORE AGGRESSIVE LOGGING / EARLY EXIT
        logger.critical("--- ENTERING get_supabase_client (MODDED FOR DEBUG) ---")
        
        # Use getattr for safer access and to provide a default if not found
        supabase_url_from_settings = getattr(settings, 'SUPABASE_URL', 'SETTINGS_ATTRIBUTE_NOT_FOUND')
        supabase_key_from_settings = getattr(settings, 'SUPABASE_KEY', 'SETTINGS_ATTRIBUTE_NOT_FOUND')

        logger.critical(f"DEBUG: settings.SUPABASE_URL resolved to: '{supabase_url_from_settings}' (type: {type(supabase_url_from_settings)})")
        
        # For the key, just log its presence and type, not its value, but indicate if it was found in settings
        key_status = 'SETTINGS_ATTRIBUTE_NOT_FOUND'
        if supabase_key_from_settings != 'SETTINGS_ATTRIBUTE_NOT_FOUND':
            key_status = f"Key found in settings (type: {type(supabase_key_from_settings)}), non-empty: {bool(supabase_key_from_settings)}"
        logger.critical(f"DEBUG: settings.SUPABASE_KEY status: {key_status}")

        if supabase_url_from_settings == 'SETTINGS_ATTRIBUTE_NOT_FOUND' or not supabase_url_from_settings:
            logger.critical("CRITICAL ERROR: SUPABASE_URL is missing from settings or is empty.")
            raise ValueError("CRITICAL ERROR VIA DEBUG: SUPABASE_URL not properly configured in settings.")
        
        if supabase_key_from_settings == 'SETTINGS_ATTRIBUTE_NOT_FOUND' or not supabase_key_from_settings:
            logger.critical("CRITICAL ERROR: SUPABASE_KEY is missing from settings or is empty.")
            raise ValueError("CRITICAL ERROR VIA DEBUG: SUPABASE_KEY not properly configured in settings.")
        # END MODIFIED FOR DEBUGGING

        # Original logic proceeds if checks above pass
        logger.info(f"Initializing Supabase client with URL: {supabase_url_from_settings} and Key: (Key is present)") # Avoid logging key
        try:
            # Initialize the client using URL and Key from settings
            _supabase_client = create_client(supabase_url_from_settings, supabase_key_from_settings)
            logger.info("Supabase client object potentially created.") # Changed log message

            # Add a quick test after creation
            if _supabase_client:
                logger.info(f"Supabase client appears to be a valid object: type={type(_supabase_client)}")
            else:
                # This case should ideally not be reached if create_client raises exceptions on failure
                logger.error("CRITICAL: create_client returned None without raising an exception!")
                raise ValueError("Supabase client creation resulted in None unexpectedly.")

        except Exception as e:
            logger.error(f"Failed to initialize Supabase client during create_client call: {e}", exc_info=True)
            raise # Critical error if client can't be created
            
    return _supabase_client

# Dependency function for FastAPI endpoints
async def get_db() -> SupabaseClient:
    """
    FastAPI dependency that provides the initialized Supabase client.
    The client manages its own underlying connections.
    """
    try:
        client = get_supabase_client()
        # Basic yield. Could add a lightweight 'ping' or health check if needed.
        yield client
    except Exception as e:
        # Log errors during dependency resolution (e.g., client init failure)
        logger.error(f"Error getting Supabase client for dependency: {e}", exc_info=True)
        # Re-raise to let FastAPI handle the error (usually results in a 500 response)
        raise


# init_db is no longer needed for schema creation.
# Kept as a placeholder because modal_app.py imports it.
async def init_db():
    """
    Placeholder function called on startup. Logs that schema is managed manually.
    Can be used to test connection or pre-fetch data if needed.
    """
    logger.info("Skipping automatic database schema initialization (managed manually in Supabase).")
    # --- Optional: Connection Test ---
    # You might want to uncomment this block to test the connection during startup.
    # Be aware this adds a slight delay to startup time.
    # try:
    #     logger.info("Testing Supabase connection during startup...")
    #     client = get_supabase_client()
    #     # Example: Perform a simple read to test connection (check if 'users' table exists)
    #     # This uses PostgREST syntax provided by the Supabase client
    #     response = client.table('users').select('id', count='exact').limit(0).execute()
    #     # You might want to check response.count here if needed
    #     logger.info(f"Supabase connection test successful during init. User count (limit 0): {response.count}")
    # except Exception as e:
    #     logger.error(f"Supabase connection test failed during init: {e}", exc_info=True)
    #     # Decide if failure to connect at startup should stop the app
    #     # raise e
    # --- End Optional Connection Test ---


# Removed asyncpg pool logic and close_db_pool function as they are not needed for supabase-py client.