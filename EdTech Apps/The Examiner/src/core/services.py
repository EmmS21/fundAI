"""
Central registry for application services.

This module serves as a central point for accessing application services,
helping to prevent circular imports between modules while maintaining
top-level imports.

During application initialization, these service variables will be set
to their respective singleton instances.
"""

# These will be set during application initialization
sync_service = None
cache_manager = None
network_monitor = None
mongodb_client = None
queue_manager = None 