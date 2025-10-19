"""
Service URL Configuration for Monolithic Deployment

In monolithic deployment, all services run on the same host.
Use environment variable to set the base URL, defaulting to localhost for development.
"""

import os

# Base URL for all services (same host in monolithic deployment)
BASE_URL = os.getenv("SERVICE_BASE_URL", "http://localhost:8000")

# Service endpoints
GEE_SERVICE_URL = BASE_URL
SEARCH_SERVICE_URL = BASE_URL
RAG_SERVICE_URL = BASE_URL
CORE_AGENT_URL = BASE_URL

# For internal calls within the same app, we can use relative paths
# But for HTTP requests, we need the full URL
def get_service_url() -> str:
    """Get the base service URL for internal HTTP calls"""
    return BASE_URL

