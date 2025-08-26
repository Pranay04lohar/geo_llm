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

class TileResponse(BaseModel):
    """Response model for tile-based analysis"""
    urlFormat: str
    mapStats: Dict[str, Any]
    analysis_type: str
    datasets_used: List[str]
    processing_time_seconds: float
    roi_area_km2: float
    class_definitions: Dict[str, Any]
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
            "/docs"
        ]
    }

# Import LULC service
try:
    from services.lulc_service import LULCService
except ImportError:
    # Fallback for direct execution
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), 'services'))
    from services.lulc_service import LULCService

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
            max_pixels=request.maxPixels
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
