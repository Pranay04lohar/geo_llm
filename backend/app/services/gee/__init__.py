"""
GEE Services Module

This module provides direct access to Google Earth Engine analysis services.
All services are self-contained and can be called directly without HTTP overhead.

Services:
- NDVIService: Vegetation health analysis using Sentinel-2
- LSTService: Land Surface Temperature analysis using MODIS
- LULCService: Land Use Land Cover classification using Dynamic World
- WaterService: Water body analysis using JRC Global Surface Water

Helper classes:
- ROIHandler: Region of Interest extraction and validation
"""

import logging
import os
import json

# Setup logger BEFORE any functions that use it
logger = logging.getLogger(__name__)

# Import services for direct use
try:
    from .ndvi_service import NDVIService
except ImportError as e:
    print(f"Warning: Could not import NDVIService: {e}")
    NDVIService = None

try:
    from .lst_service import LSTService
except ImportError as e:
    print(f"Warning: Could not import LSTService: {e}")
    LSTService = None

try:
    from .lulc_service import LULCService
except ImportError as e:
    print(f"Warning: Could not import LULCService: {e}")
    LULCService = None

try:
    from .water_service import WaterService
except ImportError as e:
    print(f"Warning: Could not import WaterService: {e}")
    WaterService = None

try:
    from .roi_handler import ROIHandler
except ImportError as e:
    print(f"Warning: Could not import ROIHandler: {e}")
    ROIHandler = None

# def initialize_gee() -> bool:
#     """Initialize Google Earth Engine using service account credentials.

#     Prefers GOOGLE_APPLICATION_CREDENTIALS_JSON (inline JSON). Falls back to
#     GOOGLE_APPLICATION_CREDENTIALS (file path). If neither is set, attempts
#     default ee.Initialize() which only works in some environments.

#     Returns True if initialization succeeded, False otherwise.
#     """
#     try:
#         import os
#         import json
#         import ee  # type: ignore

#         creds_json = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
#         creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")

#         if creds_json:
#             credentials_dict = json.loads(creds_json)
#             credentials = ee.ServiceAccountCredentials(
#                 credentials_dict["client_email"], key_data=creds_json
#             )
#             ee.Initialize(credentials)
#             return True

#         if creds_path:
#             with open(creds_path, "r") as f:
#                 credentials_dict = json.load(f)
#             credentials = ee.ServiceAccountCredentials(
#                 credentials_dict["client_email"], creds_path
#             )
#             ee.Initialize(credentials)
#             return True

#         # No explicit credentials provided – do NOT fallback in cloud
#         # Explicitly fail so callers can surface a clear error/log
#         return False
#     except Exception:
#         return False


def initialize_gee() -> bool:
    """
    Initialize Google Earth Engine using service account credentials
    for a cloud deployment.

    Tries credentials in this order:
    1. GOOGLE_APPLICATION_CREDENTIALS_JSON (inline JSON string)
    2. GOOGLE_APPLICATION_CREDENTIALS (file path to JSON)

    This function will NOT fall back to default credentials.
    It will explicitly fail if the required env vars are not set.

    Returns True if initialization succeeded, False otherwise.
    """
    try:
        import ee  # Import ee here since it's only needed for GEE initialization
        
        # 1. Try to get the inline JSON string
        creds_json_string = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
        
        # DEBUG: Check if env var is loaded
        logger.info(f"🔍 DEBUG: GOOGLE_APPLICATION_CREDENTIALS_JSON exists: {creds_json_string is not None}")
        if creds_json_string:
            logger.info(f"🔍 DEBUG: GOOGLE_APPLICATION_CREDENTIALS_JSON length: {len(creds_json_string)} chars")
        
        if creds_json_string:
            logger.info("🔑 Initializing GEE from GOOGLE_APPLICATION_CREDENTIALS_JSON env var...")
            credentials_dict = json.loads(creds_json_string)
            credentials = ee.ServiceAccountCredentials(
                credentials_dict["client_email"], key_data=creds_json_string
            )
            ee.Initialize(credentials)
            logger.info("✅ GEE initialized successfully (from JSON string).")
            return True

        # 2. If no JSON string, try to get the file path
        creds_file_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if creds_file_path:
            logger.info(f"🔑 Initializing GEE from GOOGLE_APPLICATION_CREDENTIALS file: {creds_file_path}")
            
            # We must read the file to get the client_email for the constructor
            with open(creds_file_path, 'r') as f:
                creds_dict = json.load(f)
            
            credentials = ee.ServiceAccountCredentials(
                creds_dict["client_email"],
                creds_file_path  # The method can take the file path directly
            )
            ee.Initialize(credentials)
            logger.info("✅ GEE initialized successfully (from file path).")
            return True

        # 3. No credentials found - explicit failure
        logger.error("❌ GEE initialization failed: No credentials found.")
        logger.error("❌ Set either GOOGLE_APPLICATION_CREDENTIALS_JSON or GOOGLE_APPLICATION_CREDENTIALS env var.")
        return False

    except Exception as e:
        # Catch any error during loading or initialization
        logger.error(f"❌ GEE initialization failed with an exception: {e}", exc_info=True)
        return False

__all__ = [
    "NDVIService",
    "LSTService",
    "LULCService",
    "WaterService",
    "ROIHandler",
    "initialize_gee",
]

