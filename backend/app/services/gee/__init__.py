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

__all__ = [
    "NDVIService",
    "LSTService",
    "LULCService",
    "WaterService",
    "ROIHandler",
]

