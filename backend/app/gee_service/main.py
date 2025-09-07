"""
FastAPI GEE Service - High-Performance Geospatial Analysis
Tile-first, histogram-based approach for fast web mapping

This service replaces heavy reduceRegion operations with:
- Frequency histograms for fast statistics
- Tile URLs for immediate map rendering
- Single dataset per endpoint for optimal performance
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import logging
import os
import sys

# Simplified GEE initialization - no external dependencies
def initialize_gee():
    """Initialize Google Earth Engine with simple authentication"""
    try:
        import ee
        ee.Initialize()
        return True
    except Exception as e:
        logger.error(f"Failed to initialize GEE: {e}")
        return False

# Import Google Earth Engine
try:
    import ee
    GEE_AVAILABLE = True
except ImportError:
    GEE_AVAILABLE = False
    ee = None

# Initialize FastAPI app
app = FastAPI(
    title="GeoLLM GEE Service",
    description="High-performance geospatial analysis service with tile-first architecture",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global GEE status
gee_initialized = False

@app.on_event("startup")
async def startup_event():
    """Initialize GEE client on startup"""
    global gee_initialized
    
    if not GEE_AVAILABLE:
        logger.error("Google Earth Engine not available. Install earthengine-api package.")
        return
    
    try:
        # Initialize GEE
        gee_initialized = initialize_gee()
        
        if gee_initialized:
            logger.info("✅ GEE Service initialized successfully")
        else:
            logger.error("❌ Failed to initialize GEE client")
    except Exception as e:
        logger.error(f"❌ Startup error: {e}")

# Request/Response Models
class GEERequest(BaseModel):
    """Base request model for GEE analysis"""
    geometry: Dict[str, Any]  # GeoJSON geometry
    startDate: str = "2023-01-01"
    endDate: str = "2023-12-31"
    scale: int = 10
    maxPixels: int = 1e13

class LULCRequest(GEERequest):
    """LULC-specific request parameters"""
    confidenceThreshold: float = 0.5
    maxCloudCover: int = 20
    exactComputation: bool = False
    includeMedianVis: bool = False

class NDVIRequest(GEERequest):
    """NDVI-specific request parameters"""
    cloudThreshold: int = 20
    includeTimeSeries: bool = True
    exactComputation: bool = False

class LSTRequest(GEERequest):
    """LST-specific request parameters"""
    includeUHI: bool = True
    includeTimeSeries: bool = False
    exactComputation: bool = False

class TileResponse(BaseModel):
    """Response model for tile-based analysis"""
    urlFormat: str
    mapStats: Dict[str, Any]
    analysis_type: str
    datasets_used: List[str]
    processing_time_seconds: float
    roi_area_km2: float
    class_definitions: Dict[str, Any]
    visualization: Optional[Dict[str, Any]] = None
    success: bool = True

class ErrorResponse(BaseModel):
    """Error response model"""
    error: str
    error_type: str
    success: bool = False

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "gee_available": GEE_AVAILABLE,
        "gee_initialized": gee_initialized
    }

@app.get("/")
async def root():
    """Root endpoint with service info"""
    return {
        "service": "GeoLLM GEE Service",
        "version": "2.0.0",
        "description": "High-performance geospatial analysis with tile-first architecture",
        "endpoints": [
            "/health",
            "/lulc/dynamic-world",
            "/ndvi/vegetation-analysis",
            "/docs"
        ]
    }

# Import services
try:
    from services.lulc_service import LULCService
    logger.info("✅ Successfully imported LULCService")
    
    # Try to import NDVIService with detailed error logging
    try:
        from services.ndvi_service import NDVIService
        logger.info("✅ Successfully imported NDVIService")
    except Exception as ndvi_import_error:
        logger.error(f"❌ Failed to import NDVIService: {ndvi_import_error}")
        logger.error(f"❌ Error type: {type(ndvi_import_error)}")
        import traceback
        logger.error(f"❌ Import traceback:")
        logger.error(traceback.format_exc())
        
        # Create a dummy service so the app can still start
        class NDVIService:
            @staticmethod
            def analyze_ndvi(**kwargs):
                raise Exception(f"NDVIService import failed: {ndvi_import_error}")
        
except ImportError as general_import_error:
    logger.error(f"❌ General import error: {general_import_error}")
    # Fallback for direct execution
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), 'services'))
    from services.lulc_service import LULCService
    
    try:
        from services.ndvi_service import NDVIService
        logger.info("✅ Successfully imported NDVIService via fallback")
    except Exception as fallback_error:
        logger.error(f"❌ Fallback import also failed: {fallback_error}")
        
        class NDVIService:
            @staticmethod
            def analyze_ndvi(**kwargs):
                raise Exception(f"NDVIService fallback import failed: {fallback_error}")

@app.post("/lulc/dynamic-world", response_model=TileResponse)
async def analyze_lulc_dynamic_world(request: LULCRequest):
    """
    High-performance LULC analysis using Google Dynamic World
    
    Features:
    - Frequency histogram for fast statistics (vs. slow area calculations)
    - Tile URL for immediate map rendering
    - Confidence filtering for quality results
    - ~10s processing time vs. 100s+ with old approach
    
    Returns:
    - Tile URL for web mapping
    - Class percentages and areas
    - Processing metadata
    """
    if not GEE_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Google Earth Engine not available"
        )
    
    if not gee_initialized:
        raise HTTPException(
            status_code=503, 
            detail="GEE client not initialized"
        )
    
    logger.info(f"🚀 Starting LULC analysis for geometry: {request.geometry.get('type', 'Unknown')}")
    
    try:
        # Call the optimized LULC service
        result = LULCService.analyze_dynamic_world(
            geometry=request.geometry,
            start_date=request.startDate,
            end_date=request.endDate,
            confidence_threshold=request.confidenceThreshold,
            scale=request.scale,
            max_pixels=request.maxPixels,
            exact_computation=request.exactComputation,
            include_median_vis=request.includeMedianVis
        )
        
        if not result.get("success", False):
            # Handle service-level errors
            error_detail = result.get("error", "Unknown error")
            error_type = result.get("error_type", "unknown")
            
            if error_type == "quota_exceeded":
                raise HTTPException(status_code=429, detail=error_detail)
            elif error_type == "timeout":
                raise HTTPException(status_code=408, detail=error_detail)
            else:
                raise HTTPException(status_code=500, detail=error_detail)
        
        logger.info(f"✅ LULC analysis completed successfully in {result.get('processing_time_seconds', 0)}s")
        return result
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error in LULC endpoint: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@app.post("/ndvi/vegetation-analysis", response_model=TileResponse)
async def analyze_ndvi_vegetation(request: NDVIRequest):
    """
    High-performance NDVI vegetation analysis using Sentinel-2
    
    Features:
    - Time-series NDVI analysis (weekly/monthly/yearly aggregation)
    - Robust histogram extraction with multiple fallback methods
    - Cloud masking and quality filtering
    - Vegetation health assessment and distribution analysis
    - Tile URLs for immediate map visualization
    
    Returns:
    - Tile URL for NDVI visualization
    - NDVI statistics and vegetation distribution
    - Time-series data for trend analysis
    - Processing metadata and quality metrics
    """
    if not GEE_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Google Earth Engine not available"
        )
    
    if not gee_initialized:
        raise HTTPException(
            status_code=503, 
            detail="GEE client not initialized"
        )
    
    logger.info(f"🌱 Starting NDVI analysis for geometry: {request.geometry.get('type', 'Unknown')}")
    
    try:
        # Debug: Log all parameters
        logger.info(f"🔧 NDVI Parameters:")
        logger.info(f"   - start_date: {request.startDate}")
        logger.info(f"   - end_date: {request.endDate}")
        logger.info(f"   - cloud_threshold: {request.cloudThreshold}")
        logger.info(f"   - scale: {request.scale}")
        logger.info(f"   - max_pixels: {request.maxPixels}")
        logger.info(f"   - include_time_series: {request.includeTimeSeries}")
        logger.info(f"   - exact_computation: {request.exactComputation}")
        
        # Debug: Check if NDVIService is available
        logger.info(f"🔧 NDVIService class: {NDVIService}")
        logger.info(f"🔧 NDVIService.analyze_ndvi method: {NDVIService.analyze_ndvi}")
        
        # Call the NDVI service
        logger.info("🔧 Calling NDVIService.analyze_ndvi...")
        result = NDVIService.analyze_ndvi(
            geometry=request.geometry,
            start_date=request.startDate,
            end_date=request.endDate,
            cloud_threshold=request.cloudThreshold,
            scale=request.scale,
            max_pixels=request.maxPixels,
            include_time_series=request.includeTimeSeries,
            exact_computation=request.exactComputation
        )
        logger.info(f"🔧 NDVIService.analyze_ndvi returned: {type(result)}")
        
        if not result.get("success", False):
            # Handle service-level errors
            error_detail = result.get("error", "Unknown error")
            error_type = result.get("error_type", "unknown")
            
            if error_type == "quota_exceeded":
                raise HTTPException(status_code=429, detail=error_detail)
            elif error_type == "timeout":
                raise HTTPException(status_code=408, detail=error_detail)
            elif error_type == "no_data":
                raise HTTPException(status_code=404, detail=error_detail)
            else:
                raise HTTPException(status_code=500, detail=error_detail)
        
        logger.info(f"✅ NDVI analysis completed successfully in {result.get('processing_time_seconds', 0)}s")
        return result
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error in NDVI endpoint: {str(e)}")
        logger.error(f"❌ Error type: {type(e)}")
        
        # Import traceback for detailed error info
        import traceback
        logger.error(f"❌ Full traceback:")
        logger.error(traceback.format_exc())
        
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {type(e).__name__}: {str(e)}"
        )

@app.post("/lst/land-surface-temperature", response_model=TileResponse)
async def analyze_lst(request: LSTRequest):
    """
    Analyze Land Surface Temperature (LST) using MODIS MOD11A2 data.
    
    This endpoint provides:
    - LST statistics (mean, min, max, std dev)
    - Urban Heat Island intensity calculation
    - Time series analysis (optional)
    - Visualization tiles
    """
    if not gee_initialized:
        raise HTTPException(status_code=503, detail="GEE service not initialized")
    
    try:
        logger.info(f"🌡️ Starting LST analysis for geometry: {request.geometry.get('type', 'unknown')}")
        
        # Import LST service
        from services.lst_service import LSTService
        
        # Create ROI data structure (simplified for basic endpoint)
        roi_data = {
            "polygon_geometry": request.geometry,
            "geometry_tiles": [],
            "is_tiled": False,
            "is_fallback": False,
            "area_km2": 0  # Will be calculated by service
        }
        
        # Call LST service
        result = LSTService.analyze_lst_with_polygon(
            roi_data=roi_data,
            start_date=request.startDate,
            end_date=request.endDate,
            include_uhi=request.includeUHI,
            include_time_series=request.includeTimeSeries,
            scale=request.scale,
            max_pixels=request.maxPixels,
            exact_computation=request.exactComputation
        )
        
        if not result.get("success", False):
            # Handle service-level errors
            error_detail = result.get("error", "Unknown error")
            error_type = result.get("error_type", "unknown")
            
            if error_type == "quota_exceeded":
                raise HTTPException(status_code=429, detail=error_detail)
            elif error_type == "timeout":
                raise HTTPException(status_code=408, detail=error_detail)
            elif error_type == "no_data":
                raise HTTPException(status_code=404, detail=error_detail)
            else:
                raise HTTPException(status_code=500, detail=error_detail)
        
        logger.info(f"✅ LST analysis completed successfully")
        return result
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error in LST endpoint: {str(e)}")
        logger.error(f"❌ Error type: {type(e)}")
        
        # Import traceback for detailed error info
        import traceback
        logger.error(f"❌ Full traceback:")
        logger.error(traceback.format_exc())
        
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {type(e).__name__}: {str(e)}"
        )

@app.post("/lst/urban-heat-island", response_model=TileResponse)
async def analyze_uhi(request: LSTRequest):
    """
    Analyze Urban Heat Island (UHI) intensity using LST data.
    
    This endpoint provides:
    - UHI intensity calculation (urban vs rural temperature difference)
    - LST statistics for urban and rural areas
    - Visualization tiles showing UHI patterns
    """
    if not gee_initialized:
        raise HTTPException(status_code=503, detail="GEE service not initialized")
    
    try:
        logger.info(f"🏙️ Starting UHI analysis for geometry: {request.geometry.get('type', 'unknown')}")
        
        # Import LST service
        from services.lst_service import LSTService
        
        # Create ROI data structure
        roi_data = {
            "polygon_geometry": request.geometry,
            "geometry_tiles": [],
            "is_tiled": False,
            "is_fallback": False,
            "area_km2": 0
        }
        
        # Call LST service with UHI enabled
        result = LSTService.analyze_lst_with_polygon(
            roi_data=roi_data,
            start_date=request.startDate,
            end_date=request.endDate,
            include_uhi=True,  # Force UHI calculation
            include_time_series=request.includeTimeSeries,
            scale=request.scale,
            max_pixels=request.maxPixels,
            exact_computation=request.exactComputation
        )
        
        if not result.get("success", False):
            # Handle service-level errors
            error_detail = result.get("error", "Unknown error")
            error_type = result.get("error_type", "unknown")
            
            if error_type == "quota_exceeded":
                raise HTTPException(status_code=429, detail=error_detail)
            elif error_type == "timeout":
                raise HTTPException(status_code=408, detail=error_detail)
            elif error_type == "no_data":
                raise HTTPException(status_code=404, detail=error_detail)
            else:
                raise HTTPException(status_code=500, detail=error_detail)
        
        logger.info(f"✅ UHI analysis completed successfully")
        return result
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error in UHI endpoint: {str(e)}")
        logger.error(f"❌ Error type: {type(e)}")
        
        # Import traceback for detailed error info
        import traceback
        logger.error(f"❌ Full traceback:")
        logger.error(traceback.format_exc())
        
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {type(e).__name__}: {str(e)}"
        )
