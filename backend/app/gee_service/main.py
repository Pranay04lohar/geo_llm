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
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Simplified GEE initialization - supports both file path and JSON string
def initialize_gee():
    """Initialize Google Earth Engine with service account authentication"""
    try:
        import ee
        import json
        import os
        
        # Try to get credentials from environment
        creds_json = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
        creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        
        if creds_json:
            # Use JSON string from environment variable
            logger.info("🔑 Using GEE credentials from GOOGLE_APPLICATION_CREDENTIALS_JSON")
            credentials_dict = json.loads(creds_json)
            credentials = ee.ServiceAccountCredentials(
                credentials_dict['client_email'],
                key_data=creds_json
            )
            ee.Initialize(credentials)
        elif creds_path:
            # Use file path from environment variable
            logger.info(f"🔑 Using GEE credentials from file: {creds_path}")
            with open(creds_path, 'r') as f:
                credentials_dict = json.load(f)
            credentials = ee.ServiceAccountCredentials(
                credentials_dict['client_email'],
                creds_path
            )
            ee.Initialize(credentials)
        else:
            # Fall back to default credentials (for local development)
            logger.info("🔑 Using default GEE credentials")
            ee.Initialize()
        
        logger.info("✅ GEE initialized successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to initialize GEE: {e}")
        return False

# Import Google Earth Engine
try:
    import ee
    GEE_AVAILABLE = True
    logger.info("✅ Google Earth Engine module imported successfully")
except ImportError as e:
    GEE_AVAILABLE = False
    ee = None
    logger.warning(f"⚠️ Google Earth Engine not available: {e}")
    logger.info("💡 Install with: pip install earthengine-api")

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
        logger.warning("⚠️ Google Earth Engine not available. Install earthengine-api package.")
        logger.info("💡 Service will run in fallback mode - endpoints will return service unavailable")
        return
    
    try:
        # Initialize GEE
        gee_initialized = initialize_gee()
        
        if gee_initialized:
            logger.info("✅ GEE Service initialized successfully")
        else:
            logger.warning("⚠️ Failed to initialize GEE client - service will run in fallback mode")
            logger.info("💡 Check GOOGLE_APPLICATION_CREDENTIALS_JSON environment variable")
    except Exception as e:
        logger.warning(f"⚠️ Startup error: {e}")
        logger.info("💡 Service will run in fallback mode - endpoints will return service unavailable")

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

class LSTSampleRequest(BaseModel):
    """Request model to sample LST at a coordinate."""
    lng: float
    lat: float
    startDate: str = "2023-06-01"
    endDate: str = "2023-08-31"
    scale: int = 1000

class LSTGridRequest(BaseModel):
    """Request model to generate LST vector grid over ROI."""
    roi: Dict[str, Any]  # GeoJSON geometry
    cellSizeKm: float = 1.0  # Grid cell size in km
    startDate: str = "2023-06-01"
    endDate: str = "2023-08-31"
    scale: int = 1000

class LSTBatchSampleRequest(BaseModel):
    """Request model to sample LST at multiple points."""
    points: List[Dict[str, float]]  # List of {lng, lat} dicts
    startDate: str = "2023-06-01"
    endDate: str = "2023-08-31"
    scale: int = 1000

class NDVISampleRequest(BaseModel):
    """Request model to sample NDVI at a coordinate."""
    lng: float
    lat: float
    startDate: str = "2023-06-01"
    endDate: str = "2023-08-31"
    scale: int = 30
    cloudThreshold: float = 20

class NDVIGridRequest(BaseModel):
    """Request model to generate NDVI vector grid over ROI."""
    roi: Dict[str, Any]  # GeoJSON geometry
    cellSizeKm: float = 1.0  # Grid cell size in km
    startDate: str = "2023-06-01"
    endDate: str = "2023-08-31"
    scale: int = 30
    cloudThreshold: float = 20

class NDVIBatchSampleRequest(BaseModel):
    """Request model to sample NDVI at multiple points."""
    points: List[Dict[str, float]]  # List of {lng, lat} dicts
    startDate: str = "2023-06-01"
    endDate: str = "2023-08-31"
    scale: int = 30
    cloudThreshold: float = 20

class WaterRequest(BaseModel):
    """Water analysis request parameters"""
    roi: Dict[str, Any]  # Region of interest (Polygon or Point)
    year: int = None  # Year for analysis (default: current year)
    threshold: int = 20  # Water occurrence threshold (default: 20%)
    include_seasonal: bool = True  # Include seasonal analysis

class WaterChangeRequest(BaseModel):
    """Water change analysis request parameters"""
    roi: Dict[str, Any]  # Region of interest
    start_year: int  # Start year for comparison
    end_year: int  # End year for comparison
    threshold: int = 20  # Water occurrence threshold

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
    status = "healthy" if GEE_AVAILABLE and gee_initialized else "degraded"
    return {
        "status": status,
        "gee_available": GEE_AVAILABLE,
        "gee_initialized": gee_initialized,
        "message": "Service running" if status == "healthy" else "Service running in fallback mode - GEE not available"
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
            "/lst/land-surface-temperature",
            "/lst/urban-heat-island",
            "/water/analyze",
            "/water/change",
            "/water/quality",
            "/docs"
        ]
    }

# Import services
try:
    from .services.lulc_service import LULCService
    logger.info("✅ Successfully imported LULCService")
    
    # Try to import NDVIService with detailed error logging
    try:
        from .services.ndvi_service import NDVIService
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
    
    # Try to import WaterService
    try:
        from .services.water_service import WaterService
        logger.info("✅ Successfully imported WaterService")
    except Exception as water_import_error:
        logger.error(f"❌ Failed to import WaterService: {water_import_error}")
        logger.error(f"❌ Error type: {type(water_import_error)}")
        import traceback
        logger.error(f"❌ Import traceback:")
        logger.error(traceback.format_exc())
        
        # Create a dummy service so the app can still start
        class WaterService:
            @staticmethod
            def analyze_water_presence(**kwargs):
                raise Exception(f"WaterService import failed: {water_import_error}")
        
except ImportError as general_import_error:
    logger.error(f"❌ General import error: {general_import_error}")
    # Fallback for direct execution
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), 'services'))
    from .services.lulc_service import LULCService
    
    try:
        from .services.ndvi_service import NDVIService
        logger.info("✅ Successfully imported NDVIService via fallback")
    except Exception as fallback_error:
        logger.error(f"❌ Fallback import also failed: {fallback_error}")
        
        class NDVIService:
            @staticmethod
            def analyze_ndvi(**kwargs):
                raise Exception(f"NDVIService fallback import failed: {fallback_error}")
    
    try:
        from .services.water_service import WaterService
        logger.info("✅ Successfully imported WaterService via fallback")
    except Exception as water_fallback_error:
        logger.error(f"❌ WaterService fallback import also failed: {water_fallback_error}")
        
        class WaterService:
            @staticmethod
            def analyze_water_presence(**kwargs):
                raise Exception(f"WaterService fallback import failed: {water_fallback_error}")

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

@app.post("/ndvi/sample")
async def sample_ndvi_value(request: NDVISampleRequest):
    """Sample median NDVI at a given coordinate (lng, lat)."""
    if not gee_initialized:
        raise HTTPException(status_code=503, detail="GEE service not initialized")
    try:
        from .services.ndvi_service import NDVIService
        result = NDVIService.sample_ndvi_at_point(
            lng=request.lng,
            lat=request.lat,
            start_date=request.startDate,
            end_date=request.endDate,
            scale=request.scale,
            cloud_threshold=request.cloudThreshold
        )
        if not result.get("success", False):
            raise HTTPException(status_code=404, detail=result.get("error", "Sampling failed"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error in NDVI sample endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/ndvi/grid")
async def generate_ndvi_grid(request: NDVIGridRequest):
    """Generate a vector grid over ROI with NDVI statistics per cell.
    
    Returns GeoJSON FeatureCollection with mean/min/max/std NDVI per grid cell.
    Useful for fast hover interactions on large ROIs.
    """
    if not gee_initialized:
        raise HTTPException(status_code=503, detail="GEE service not initialized")
    try:
        from .services.ndvi_service import NDVIService
        
        # Run grid generation with 30 second timeout to prevent backend hanging
        loop = asyncio.get_event_loop()
        executor = ThreadPoolExecutor(max_workers=1)
        
        try:
            result = await asyncio.wait_for(
                loop.run_in_executor(
                    executor,
                    lambda: NDVIService.generate_ndvi_grid(
                        roi_geojson=request.roi,
                        cell_size_km=request.cellSizeKm,
                        start_date=request.startDate,
                        end_date=request.endDate,
                        scale=request.scale,
                        cloud_threshold=request.cloudThreshold
                    )
                ),
                timeout=30.0
            )
        except asyncio.TimeoutError:
            logger.warning("⏱️ NDVI grid generation timed out after 30 seconds")
            raise HTTPException(status_code=408, detail="Grid generation timeout - ROI too large or GEE overloaded")
        finally:
            executor.shutdown(wait=False)
        
        if not result.get("success", False):
            raise HTTPException(status_code=500, detail=result.get("error", "Grid generation failed"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error in NDVI grid endpoint: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/ndvi/sample-batch")
async def sample_ndvi_batch(request: NDVIBatchSampleRequest):
    """Sample NDVI at multiple points in batch.
    
    More efficient than calling /ndvi/sample multiple times.
    """
    if not gee_initialized:
        raise HTTPException(status_code=503, detail="GEE service not initialized")
    try:
        from .services.ndvi_service import NDVIService
        result = NDVIService.sample_ndvi_batch(
            points=request.points,
            start_date=request.startDate,
            end_date=request.endDate,
            scale=request.scale,
            cloud_threshold=request.cloudThreshold
        )
        if not result.get("success", False):
            raise HTTPException(status_code=500, detail=result.get("error", "Batch sampling failed"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error in NDVI batch sample endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/lst/sample")
async def sample_lst_value(request: LSTSampleRequest):
    """Sample median LST at a given coordinate (lng, lat)."""
    if not gee_initialized:
        raise HTTPException(status_code=503, detail="GEE service not initialized")
    try:
        from .services.lst_service import LSTService
        result = LSTService.sample_lst_at_point(
            lng=request.lng,
            lat=request.lat,
            start_date=request.startDate,
            end_date=request.endDate,
            scale=request.scale
        )
        if not result.get("success", False):
            raise HTTPException(status_code=404, detail=result.get("error", "Sampling failed"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error in LST sample endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/lst/grid")
async def generate_lst_grid(request: LSTGridRequest):
    """Generate a vector grid over ROI with LST statistics per cell.
    
    Returns GeoJSON FeatureCollection with mean/min/max/std LST per grid cell.
    Useful for fast hover interactions on large ROIs.
    """
    if not gee_initialized:
        raise HTTPException(status_code=503, detail="GEE service not initialized")
    try:
        from .services.lst_service import LSTService
        
        # Run grid generation with 30 second timeout to prevent backend hanging
        loop = asyncio.get_event_loop()
        executor = ThreadPoolExecutor(max_workers=1)
        
        try:
            result = await asyncio.wait_for(
                loop.run_in_executor(
                    executor,
                    lambda: LSTService.generate_lst_grid(
                        roi_geojson=request.roi,
                        cell_size_km=request.cellSizeKm,
                        start_date=request.startDate,
                        end_date=request.endDate,
                        scale=request.scale
                    )
                ),
                timeout=30.0
            )
        except asyncio.TimeoutError:
            logger.warning("⏱️ LST grid generation timed out after 30 seconds")
            raise HTTPException(status_code=408, detail="Grid generation timeout - ROI too large or GEE overloaded")
        finally:
            executor.shutdown(wait=False)
        
        if not result.get("success", False):
            raise HTTPException(status_code=500, detail=result.get("error", "Grid generation failed"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error in LST grid endpoint: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/lst/sample-batch")
async def sample_lst_batch(request: LSTBatchSampleRequest):
    """Sample LST at multiple points in batch.
    
    More efficient than calling /lst/sample multiple times.
    """
    if not gee_initialized:
        raise HTTPException(status_code=503, detail="GEE service not initialized")
    try:
        from .services.lst_service import LSTService
        result = LSTService.sample_lst_batch(
            points=request.points,
            start_date=request.startDate,
            end_date=request.endDate,
            scale=request.scale
        )
        if not result.get("success", False):
            raise HTTPException(status_code=500, detail=result.get("error", "Batch sampling failed"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error in LST batch sample endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

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
        from .services.lst_service import LSTService
        
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
        from .services.lst_service import LSTService
        
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

@app.post("/water/analyze")
async def analyze_water_presence(request: WaterRequest):
    """
    Analyze water presence using JRC Global Surface Water dataset
    
    Features:
    - JRC Global Surface Water occurrence analysis
    - Seasonal water analysis (monsoon vs dry season)
    - Fast frequency histogram processing
    - Tile URLs for immediate map rendering
    - ROI clipping for performance
    
    Returns:
    - Tile URL for water visualization
    - Water percentage statistics
    - Seasonal comparison data
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
    
    logger.info(f"🌊 Starting water analysis for ROI: {request.roi.get('type', 'Unknown')}")
    
    try:
        # Create water service instance and call the method
        water_service = WaterService()
        result = water_service.analyze_water_presence(
            roi=request.roi,
            year=request.year,
            threshold=request.threshold,
            include_seasonal=request.include_seasonal
        )
        
        if "error" in result:
            raise HTTPException(
                status_code=500,
                detail=result["error"]
            )
        
        logger.info(f"✅ Water analysis completed successfully")
        return result
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error in water analysis endpoint: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@app.post("/water/change")
async def analyze_water_change(request: WaterChangeRequest):
    """
    Analyze water change between two time periods
    
    Features:
    - Water change detection between years
    - JRC Global Surface Water dataset
    - Change percentage and direction analysis
    - Tile URLs for visualization
    
    Returns:
    - Tile URL for change visualization
    - Change analysis statistics
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
    
    logger.info(f"🌊 Starting water change analysis: {request.start_year} - {request.end_year}")
    
    try:
        # Create water service instance and call the method
        water_service = WaterService()
        result = water_service.analyze_water_change(
            roi=request.roi,
            start_year=request.start_year,
            end_year=request.end_year,
            threshold=request.threshold
        )
        
        if "error" in result:
            raise HTTPException(
                status_code=500,
                detail=result["error"]
            )
        
        logger.info(f"✅ Water change analysis completed successfully")
        return result
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error in water change endpoint: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@app.post("/water/sample")
async def sample_water_value(request: LSTSampleRequest):
    """
    Sample water classification at a specific point
    
    Features:
    - Point-based water/land classification
    - JRC Global Surface Water dataset
    - Confidence scoring based on occurrence percentage
    - 30m resolution sampling
    
    Returns:
    - Water classification (1=Water, 0=Land)
    - Confidence score
    - Occurrence value
    - Dataset metadata
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
    
    logger.info(f"🌊 Sampling water at point: {request.lng}, {request.lat}")
    
    try:
        # Create water service instance and call the method
        water_service = WaterService()
        result = water_service.sample_water_at_point(
            lng=request.lng,
            lat=request.lat,
            scale=request.scale
        )
        
        if not result.get("success", False):
            raise HTTPException(
                status_code=404,
                detail=result.get("error", "Water sampling failed")
            )
        
        logger.info(f"✅ Water sampling completed successfully")
        return result
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error in water sample endpoint: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@app.get("/water/quality")
async def get_water_quality_info():
    """
    Get information about water analysis quality and methodology
    
    Returns:
    - Dataset information
    - Methodology details
    - Quality thresholds
    - Limitations and recommendations
    """
    try:
        # Create water service instance and call the method
        water_service = WaterService()
        result = water_service.get_water_quality_info()
        return result
        
    except Exception as e:
        logger.error(f"❌ Unexpected error in water quality info endpoint: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
