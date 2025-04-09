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
        logger.info("Initializing Supabase client...")
        if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
             logger.error("Supabase URL or Key not configured in settings.")
             raise ValueError("Supabase URL and Key must be configured.")
        try:
            # Initialize the client using URL and Key from settings
            # You can add ClientOptions here if needed later (e.g., for timeouts)
            # from supabase.client import ClientOptions
            # options: ClientOptions = ClientOptions(postgrest_client_timeout=10)
            # _supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY, options=options)
            _supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
            logger.info("Supabase client initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}", exc_info=True)
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