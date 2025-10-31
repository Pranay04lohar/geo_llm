"""
Search Services Module

This module provides location resolution and environmental context search services.
All services use direct API calls (Nominatim, Tavily) without HTTP overhead.

Services:
- Nominat

imClient: Location search and geocoding
- LocationResolver: Enhanced location resolution with context
- ResultProcessor: Process and format search results
"""

# Import services for direct use
try:
    from app.search_service.services.nominatim_client import NominatimClient
except ImportError as e:
    print(f"Warning: Could not import NominatimClient: {e}")
    NominatimClient = None

try:
    from app.search_service.services.location_resolver import LocationResolver
except ImportError as e:
    print(f"Warning: Could not import LocationResolver: {e}")
    LocationResolver = None

try:
    from app.search_service.services.result_processor import ResultProcessor
except ImportError as e:
    print(f"Warning: Could not import ResultProcessor: {e}")
    ResultProcessor = None

__all__ = [
    "NominatimClient",
    "LocationResolver",
    "ResultProcessor",
]

