"""
Search Router - Handles location search requests

This router provides dedicated location search functionality
separate from the main query pipeline.
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================

class LocationSearchRequest(BaseModel):
    """Request model for location search"""
    location_name: str = Field(..., min_length=1, max_length=200)
    location_type: Optional[str] = Field("city", description="Type of location (city, region, country, etc.)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "location_name": "Mumbai",
                "location_type": "city"
            }
        }


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/location-data")
async def search_location(request_data: LocationSearchRequest):
    """
    Search for location coordinates and geometry.
    
    This endpoint provides location data without running full GEE analysis.
    Used by the frontend to get ROI before submitting analysis queries.
    
    Returns:
        - success: bool
        - coordinates: {lat, lng}
        - polygon_geometry: GeoJSON polygon
        - administrative_info: location metadata
        - area_km2: area in square kilometers
        - is_fallback: whether using fallback bbox
    """
    try:
        logger.info(f"🔍 Searching for location: {request_data.location_name}")
        
        # Import NominatimClient for location search
        from app.services.search import NominatimClient
        
        # Initialize client
        nominatim_client = NominatimClient()
        
        # Search for location
        result = nominatim_client.search_location(
            location_name=request_data.location_name,
            location_type=request_data.location_type
        )
        
        # Check if search failed (returns None on failure)
        if not result:
            logger.warning(f"Location not found: {request_data.location_name}")
            return {
                "success": False,
                "error": f"Location not found: {request_data.location_name}",
                "coordinates": None,
                "polygon_geometry": None
            }
        
        logger.info(f"✅ Found location: {result.get('administrative_info', {}).get('name', request_data.location_name)}")
        
        # Extract coordinates from result structure
        coords = result.get("coordinates", {})
        lat = coords.get("lat")
        lng = coords.get("lng")
        
        if not lat or not lng:
            raise ValueError("Missing coordinates in search result")
        
        # Get polygon geometry
        polygon_geometry = result.get("polygon_geometry")
        
        # Build response matching old search service format
        admin_info = result.get("administrative_info", {})
        
        response = {
            "success": True,
            "coordinates": {
                "lat": float(lat),
                "lng": float(lng)
            },
            "polygon_geometry": polygon_geometry,
            "administrative_info": admin_info,
            "area_km2": result.get("area_km2", 0),
            "is_fallback": result.get("is_fallback", False),
            "bounding_box": result.get("bounding_box"),
            "geometry_tiles": result.get("geometry_tiles", []),
            "is_tiled": result.get("is_tiled", False)
        }
        
        logger.info(f"📍 Coordinates: {lat}, {lng} | Area: {response['area_km2']:.2f} km²")
        
        return response
        
    except Exception as e:
        logger.error(f"❌ Error searching for location: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        return {
            "success": False,
            "error": str(e),
            "coordinates": None,
            "polygon_geometry": None
        }


@router.get("/health")
async def search_health():
    """Health check for search service"""
    return {
        "status": "healthy",
        "service": "search"
    }

