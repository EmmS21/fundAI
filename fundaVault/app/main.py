"""
main.py

Purpose: FastAPI application initialization and router configuration.
"""
from fastapi import FastAPI, Request, Response
from fastapi.routing import APIRoute
from starlette.responses import JSONResponse, PlainTextResponse, Response, StreamingResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from app.endpoints import devices, users, subscriptions, admin, auth
from app.db.database import init_db, get_db
import logging
import logging.config
import os
import time
import inspect
import pprint
from typing import List, Dict, Set, Any, Callable, Optional
import sys # For recursion depth check
import threading
import traceback

# --- Configure Logging ---
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=log_level,
    format='%(asctime)s.%(msecs)03d - %(levelname)s - [%(name)s:%(lineno)d] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# --- CRITICAL FIX: Patch jsonable_encoder to catch infinite recursion ---
# We need to patch this before FastAPI app is created
from fastapi.encoders import jsonable_encoder as original_jsonable_encoder

_recursion_tracking = threading.local()

def safe_jsonable_encoder(*args, **kwargs):
    """
    Wrapper for jsonable_encoder that prevents infinite recursion by tracking
    objects that have been seen before.
    """
    if not hasattr(_recursion_tracking, 'seen_ids'):
        _recursion_tracking.seen_ids = set()
        _recursion_tracking.depth = 0
        _recursion_tracking.path = []
    
    # The first arg should be the object to encode
    if args and args[0] is not None and not isinstance(args[0], (str, int, float, bool, type(None))):
        obj_id = id(args[0])
        if obj_id in _recursion_tracking.seen_ids:
            # We've seen this exact object before, potential circular reference
            logger.warning(f"CIRCULAR REFERENCE DETECTED during serialization. Path: {'.'.join(_recursion_tracking.path)}")
            # Return a safe placeholder instead of recursing
            return {"$circular_ref": True, "id": obj_id}
        
        # Track this object
        _recursion_tracking.seen_ids.add(obj_id)
        _recursion_tracking.depth += 1
        
        # Add path info for better debugging
        if hasattr(args[0], '__class__'):
            _recursion_tracking.path.append(f"{args[0].__class__.__name__}@{obj_id}")
        else:
            _recursion_tracking.path.append(f"unknown@{obj_id}")
        
        # Check max depth to avoid stack overflow
        if _recursion_tracking.depth > 50:  # Arbitrary but reasonable limit
            logger.warning(f"MAX DEPTH EXCEEDED during serialization. Path: {'.'.join(_recursion_tracking.path)}")
            # Pop from recursion tracking before returning
            _recursion_tracking.seen_ids.remove(obj_id)
            _recursion_tracking.depth -= 1
            _recursion_tracking.path.pop()
            return {"$max_depth": True, "path": '.'.join(_recursion_tracking.path)}
    
    try:
        # Call the original encoder
        result = original_jsonable_encoder(*args, **kwargs)
        
        # Clean up tracking for this object
        if args and args[0] is not None and not isinstance(args[0], (str, int, float, bool, type(None))):
            obj_id = id(args[0])
            if obj_id in _recursion_tracking.seen_ids:
                _recursion_tracking.seen_ids.remove(obj_id)
            _recursion_tracking.depth -= 1
            _recursion_tracking.path.pop()
            
            # Reset tracking if we're back at the root
            if _recursion_tracking.depth == 0:
                _recursion_tracking.seen_ids = set()
                _recursion_tracking.path = []
        
        return result
    except Exception as e:
        # Log the error with path information
        logger.error(f"Error in jsonable_encoder: {type(e).__name__} - {str(e)} - Path: {'.'.join(_recursion_tracking.path)}")
        
        # Clean up tracking for this object
        if args and args[0] is not None and not isinstance(args[0], (str, int, float, bool, type(None))):
            obj_id = id(args[0])
            if obj_id in _recursion_tracking.seen_ids:
                _recursion_tracking.seen_ids.remove(obj_id)
            _recursion_tracking.depth -= 1
            _recursion_tracking.path.pop()
        
        # Reset tracking on error
        _recursion_tracking.seen_ids = set()
        _recursion_tracking.depth = 0
        _recursion_tracking.path = []
        
        raise

# Replace FastAPI's jsonable_encoder with our safe version
import fastapi.encoders
fastapi.encoders.jsonable_encoder = safe_jsonable_encoder

logger.info("--- Initializing FastAPI app ---")
app = FastAPI(title="FundaVault User Management API")
logger.info("FastAPI app initialized.")

# --- Helper function to safely inspect objects for debugging ---
def safe_repr(obj, max_depth=3, _current_depth=0):
    """Get a safe representation of an object, avoiding infinite recursion."""
    if _current_depth >= max_depth:
        return f"<Max depth reached: {type(obj).__name__}>"
    
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return repr(obj)
    
    if isinstance(obj, dict):
        items = []
        for k, v in list(obj.items())[:10]:  # Limit to first 10 items
            items.append(f"{safe_repr(k, max_depth, _current_depth + 1)}: {safe_repr(v, max_depth, _current_depth + 1)}")
        if len(obj) > 10:
            items.append("... (truncated)")
        return "{" + ", ".join(items) + "}"
    
    if isinstance(obj, (list, tuple, set)):
        items = [safe_repr(x, max_depth, _current_depth + 1) for x in list(obj)[:10]]
        if len(obj) > 10:
            items.append("... (truncated)")
        if isinstance(obj, list):
            return "[" + ", ".join(items) + "]"
        elif isinstance(obj, tuple):
            return "(" + ", ".join(items) + ")"
        else:  # set
            return "{" + ", ".join(items) + "}"
    
    # For other objects, just show type and id
    return f"<{type(obj).__name__} id={id(obj)}>"

# --- Find circular references in objects ---
def detect_circular_refs(obj, _seen=None, _path=None):
    """
    Detect circular references in an object.
    Returns a list of paths to circular references.
    """
    if _seen is None:
        _seen = {}
    if _path is None:
        _path = []
    
    obj_id = id(obj)
    if obj_id in _seen:
        return [_path + [f"CIRCULAR -> {_seen[obj_id]}"]]
    
    circular_paths = []
    
    # Only check certain types that can contain references
    if isinstance(obj, dict):
        _seen[obj_id] = "dict"
        for k, v in obj.items():
            if isinstance(v, (dict, list, tuple, set)) or hasattr(v, "__dict__"):
                circular_paths.extend(detect_circular_refs(v, _seen.copy(), _path + [f"dict[{safe_repr(k, 1)}]"]))
    
    elif isinstance(obj, (list, tuple)):
        _seen[obj_id] = "list/tuple"
        for i, v in enumerate(obj):
            if isinstance(v, (dict, list, tuple, set)) or hasattr(v, "__dict__"):
                circular_paths.extend(detect_circular_refs(v, _seen.copy(), _path + [f"[{i}]"]))
    
    elif hasattr(obj, "__dict__"):
        _seen[obj_id] = f"{type(obj).__name__}"
        for k, v in obj.__dict__.items():
            if isinstance(v, (dict, list, tuple, set)) or hasattr(v, "__dict__"):
                circular_paths.extend(detect_circular_refs(v, _seen.copy(), _path + [f"{type(obj).__name__}.{k}"]))
    
    return circular_paths

# --- Extract middleware configuration to a function ---
def configure_middleware(app: FastAPI):
    """Configure middleware for the FastAPI app"""
    
    class SimpleLogMiddleware(BaseHTTPMiddleware):
        async def dispatch(
            self, request: Request, call_next: RequestResponseEndpoint
        ) -> Response:
            request_id = id(request)
            start_time = time.time()
            log_prefix = f"Request ID [{request_id}] - {request.method} {request.url.path}"
            logger.info(f"{log_prefix} - Received request.")

            # --- Log Request Details ---
            try:
                # Safe attributes to log
                logger.debug(f"{log_prefix} - Request URL: {request.url}")
                logger.debug(f"{log_prefix} - Request Headers: {[(k.decode('latin-1'), '***' if k.lower() in [b'authorization', b'cookie'] else v.decode('latin-1')) for k, v in request.headers.raw]}") # Decode and mask sensitive
                logger.debug(f"{log_prefix} - Request Client: {request.client}")
                # Avoid logging request.app or request.scope directly as they can be complex
                logger.debug(f"{log_prefix} - Request State Before: {request.state.__dict__ if hasattr(request, 'state') else 'N/A'}")
            except Exception as req_log_err:
                logger.warning(f"{log_prefix} - Error logging request details: {req_log_err}")
            # --- End Request Logging ---

            response = None
            try:
                logger.debug(f"{log_prefix} - Calling next handler...")
                response = await call_next(request)
                logger.debug(f"{log_prefix} - Handler returned response.")
                process_time = time.time() - start_time
                # Ensure headers exist before trying to add to them
                if not hasattr(response, 'headers'):
                    logger.warning(f"{log_prefix} - Response object lacks headers attribute (Type: {type(response).__name__})")
                else:
                    response.headers["X-Process-Time"] = str(process_time)

                # --- Log Response Details ---
                status_code = response.status_code if hasattr(response, 'status_code') else 'N/A'
                logger.info(f"{log_prefix} - Preparing Response: Status={status_code}, Type={type(response).__name__}")
                try:
                    # Safe header logging
                    if hasattr(response, 'headers'):
                        header_log = [f"{k}: {'***' if k.lower() in ['set-cookie'] else v}" for k, v in response.headers.items()]
                        logger.debug(f"{log_prefix} - Response Headers: {header_log}")
                    else:
                        logger.debug(f"{log_prefix} - Response has no headers attribute.")
                except Exception as header_err:
                    logger.warning(f"{log_prefix} - Could not log response headers: {header_err}")
                # --- End Response Logging ---

                logger.info(f"{log_prefix} - Request finished successfully. Status={status_code} Time={process_time:.4f}s")
                return response

            except Exception as e:
                process_time = time.time() - start_time
                status_code = response.status_code if response and hasattr(response, 'status_code') else 500
                logger.error(
                    f"{log_prefix} - Request failed after {process_time:.4f}s. Status={status_code} Error: {e}",
                    exc_info=True
                )
                # Check recursion depth if RecursionError
                if isinstance(e, RecursionError):
                    try:
                        # This might also fail if stack is too deep
                        depth = len(sys.exc_info()[2].tb_frame.f_back.f_code.co_filename) # Crude depth check
                        logger.critical(f"{log_prefix} - RECURSION DETECTED IN MIDDLEWARE EXCEPTION HANDLER. Approx Depth: {depth}")
                    except:
                        logger.critical(f"{log_prefix} - RECURSION DETECTED IN MIDDLEWARE EXCEPTION HANDLER. Depth check failed.")
                raise

    app.add_middleware(SimpleLogMiddleware)
    logger.info("SimpleLogMiddleware added successfully.")

@app.on_event("startup")
async def startup():
    """Initialize database and create all tables at startup"""
    logger.info("--- Running startup event ---")
    db = None
    try:
        logger.info("Calling init_db...")
        await init_db()
        logger.info("init_db finished.")
        logger.info("Verifying table existence...")
        db = await get_db()
        cursor = await db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='devices'")
        if await cursor.fetchone():
            logger.info("Verified 'devices' table exists.")
        else:
            logger.warning("'devices' table not found after init_db.")
        logger.info("Table verification finished.")
    except Exception as e:
        logger.error(f"Error during application startup event: {e}", exc_info=True)
        raise
    finally:
        if db:
            logger.debug("Closing DB connection from startup.")
            await db.close()
    logger.info("--- Startup event finished ---")

# --- Add Logging Around Router Inclusion ---
logger.info("--- Starting router inclusion ---")

try:
    logger.info("Including users router...")
    app.include_router(users.router, prefix="/api/v1", tags=["Users"])
    logger.info("Included users router.")

    logger.info("Including devices router...")
    app.include_router(devices.router, prefix="/api/v1", tags=["Devices"])
    logger.info("Included devices router.")

    logger.info("Including subscriptions router...")
    app.include_router(subscriptions.router, prefix="/api/v1", tags=["Subscriptions"])
    logger.info("Included subscriptions router.")

    logger.info("Including admin router...")
    app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])
    logger.info("Included admin router.")

    logger.info("Including auth router...")
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
    logger.info("Included auth router.")

except Exception as router_err:
    logger.error(f"Error during router inclusion: {router_err}", exc_info=True)
    # If router inclusion fails, the app likely won't serve requests properly anyway
    raise

logger.info("--- Finished router inclusion ---")

@app.get("/")
async def root():
    """Root endpoint for basic health check"""
    logger.info("--- Executing root endpoint '/' ---")
    # Using simplest possible response to avoid serialization issues
    return PlainTextResponse("API Online")

@app.get("/routes", tags=["Debug"], include_in_schema=False)
async def list_routes():
    """
    Lists all registered API endpoint paths and methods.
    """
    logger.info("--- Executing /routes endpoint ---")
    routes_info = []
    try:
        logger.debug("Iterating through app.routes...")
        for i, route in enumerate(app.routes):
            if isinstance(route, APIRoute):
                 logger.debug(f"Processing route {i}: Path={route.path}")
                 routes_info.append({
                     "path": route.path,
                     "methods": sorted(list(route.methods)),
                 })
        logger.info(f"Collected {len(routes_info)} API routes.")
        return JSONResponse({"routes": routes_info})
    except Exception as e:
        logger.error(f"Error collecting routes in /routes endpoint: {e}", exc_info=True)
        return JSONResponse({"error": "Failed to list routes"}, status_code=500)

# --- Log after all setup in main.py ---
logger.info("--- app/main.py module execution finished ---")