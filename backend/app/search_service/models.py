# """
# Pydantic models for the Search API Service.

# This module defines the data models used for request/response validation
# and serialization in the Search API Service.
# """

# from pydantic import BaseModel, Field
# from typing import Dict, List, Optional, Any
# from datetime import datetime

# # Request Models
# class LocationRequest(BaseModel):
#     """Request model for location data resolution."""
#     location_name: str = Field(..., description="Name of the location to resolve")
#     location_type: str = Field(default="city", description="Type of location (city, state, country)")

# class EnvironmentalContextRequest(BaseModel):
#     """Request model for environmental context search."""
#     location: str = Field(..., description="Location name for context search")
#     analysis_type: str = Field(default="ndvi", description="Type of analysis (ndvi, lulc, etc.)")
#     query: str = Field(..., description="Base query for context search")

# class CompleteAnalysisRequest(BaseModel):
#     """Request model for complete analysis generation."""
#     query: str = Field(..., description="User query for analysis")
#     locations: List[Dict[str, Any]] = Field(..., description="List of detected locations")
#     analysis_type: str = Field(default="ndvi", description="Type of analysis")

# # Response Models
# class Coordinates(BaseModel):
#     """Geographical coordinates."""
#     lat: float = Field(..., description="Latitude")
#     lng: float = Field(..., description="Longitude")

# class AdministrativeInfo(BaseModel):
#     """Administrative information for a location."""
#     name: str = Field(..., description="Location name")
#     type: str = Field(default="unknown", description="Location type")
#     country: Optional[str] = Field(None, description="Country name")
#     state: Optional[str] = Field(None, description="State/province name")
#     city: Optional[str] = Field(None, description="City name")

# class SourceInfo(BaseModel):
#     """Information about a data source."""
#     title: str = Field(..., description="Source title")
#     url: str = Field(..., description="Source URL")
#     score: float = Field(..., description="Relevance score")

# class LocationResponse(BaseModel):
#     """Response model for location data."""
#     coordinates: Coordinates = Field(..., description="Geographical coordinates")
#     boundaries: Optional[Dict[str, Any]] = Field(None, description="Geographical boundaries")
#     area_km2: Optional[float] = Field(None, description="Area in square kilometers")
#     population: Optional[int] = Field(None, description="Population count")
#     administrative_info: Optional[AdministrativeInfo] = Field(None, description="Administrative details")
#     sources: List[SourceInfo] = Field(default=[], description="Data sources")
#     # New polygon geometry fields
#     polygon_geometry: Optional[Dict[str, Any]] = Field(None, description="GeoJSON polygon geometry")
#     geometry_tiles: List[Dict[str, Any]] = Field(default=[], description="Tiled geometry for large areas")
#     bounding_box: Optional[Dict[str, Any]] = Field(None, description="Bounding box coordinates")
#     is_tiled: bool = Field(default=False, description="Whether geometry was tiled")
#     is_fallback: bool = Field(default=False, description="Whether using fallback geometry")
#     success: bool = Field(default=True, description="Success status")
#     error: Optional[str] = Field(None, description="Error message if failed")

# class EnvironmentalContextResponse(BaseModel):
#     """Response model for environmental context."""
#     reports: List[Dict[str, Any]] = Field(default=[], description="Official reports and documents")
#     studies: List[Dict[str, Any]] = Field(default=[], description="Research studies and papers")
#     news: List[Dict[str, Any]] = Field(default=[], description="News articles and updates")
#     statistics: Dict[str, Any] = Field(default={}, description="Extracted statistical data")
#     context_summary: str = Field(default="", description="Generated context summary")
#     success: bool = Field(default=True, description="Success status")
#     error: Optional[str] = Field(None, description="Error message if failed")

# class CompleteAnalysisResponse(BaseModel):
#     """Response model for complete analysis."""
#     analysis: str = Field(..., description="Generated analysis text")
#     roi: Optional[Dict[str, Any]] = Field(None, description="Region of Interest data")
#     sources: List[SourceInfo] = Field(default=[], description="Data sources used")
#     confidence: float = Field(default=0.0, description="Analysis confidence score")
#     success: bool = Field(default=True, description="Success status")
#     error: Optional[str] = Field(None, description="Error message if failed")

# # Health Check Models
# class HealthResponse(BaseModel):
#     """Response model for health check."""
#     status: str = Field(..., description="Service status")
#     service: str = Field(..., description="Service name")
#     version: str = Field(..., description="Service version")
#     timestamp: Optional[datetime] = Field(default_factory=datetime.now, description="Response timestamp")

# # Error Models
# class ErrorResponse(BaseModel):
#     """Error response model."""
#     error: str = Field(..., description="Error message")
#     detail: Optional[str] = Field(None, description="Detailed error information")
#     status_code: int = Field(..., description="HTTP status code")
#     timestamp: datetime = Field(default_factory=datetime.now, description="Error timestamp")



"""
Pydantic models for the Search API Service.

This module defines the data models used for request/response validation
and serialization in the Search API Service.
"""

from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional, Any, Union
from datetime import datetime

# Request Models
class LocationRequest(BaseModel):
    """Request model for location data resolution."""
    location_name: str = Field(..., description="Name of the location to resolve")
    location_type: str = Field(default="city", description="Type of location (city, state, country)")

class EnvironmentalContextRequest(BaseModel):
    """Request model for environmental context search."""
    location: str = Field(..., description="Location name for context search")
    analysis_type: str = Field(default="ndvi", description="Type of analysis (ndvi, lulc, etc.)")
    query: str = Field(..., description="Base query for context search")

class CompleteAnalysisRequest(BaseModel):
    """Request model for complete analysis generation."""
    query: str = Field(..., description="User query for analysis")
    locations: List[Dict[str, Any]] = Field(..., description="List of detected locations")
    analysis_type: str = Field(default="ndvi", description="Type of analysis")

# Response Models
class Coordinates(BaseModel):
    """Geographical coordinates."""
    lat: float = Field(..., description="Latitude")
    lng: float = Field(..., description="Longitude")
    
    @validator('lat')
    def validate_latitude(cls, v):
        if not -90 <= v <= 90:
            raise ValueError('Latitude must be between -90 and 90')
        return v
    
    @validator('lng')
    def validate_longitude(cls, v):
        if not -180 <= v <= 180:
            raise ValueError('Longitude must be between -180 and 180')
        return v

class AdministrativeInfo(BaseModel):
    """Administrative information for a location."""
    name: str = Field(..., description="Location name")
    type: str = Field(default="unknown", description="Location type")
    country: Optional[str] = Field(None, description="Country name")
    state: Optional[str] = Field(None, description="State/province name")
    city: Optional[str] = Field(None, description="City name")

class SourceInfo(BaseModel):
    """Information about a data source."""
    title: str = Field(..., description="Source title")
    url: str = Field(..., description="Source URL")
    score: float = Field(..., description="Relevance score")
    
    @validator('score')
    def validate_score(cls, v):
        if not 0 <= v <= 1:
            raise ValueError('Score must be between 0 and 1')
        return v
    
    @validator('url')
    def validate_url(cls, v):
        if not v.startswith(('http://', 'https://')):
            raise ValueError('URL must start with http:// or https://')
        return v

class LocationResponse(BaseModel):
    """Response model for location data."""
    coordinates: Coordinates = Field(..., description="Geographical coordinates")
    boundaries: Optional[Dict[str, Any]] = Field(None, description="Geographical boundaries")
    area_km2: Optional[float] = Field(None, description="Area in square kilometers")
    population: Optional[int] = Field(None, description="Population count")
    administrative_info: Optional[AdministrativeInfo] = Field(None, description="Administrative details")
    sources: List[SourceInfo] = Field(default_factory=list, description="Data sources")
    
    # New polygon geometry fields - These are the critical ones for GEE service
    polygon_geometry: Optional[Dict[str, Any]] = Field(None, description="GeoJSON polygon geometry")
    geometry_tiles: List[Dict[str, Any]] = Field(default_factory=list, description="Tiled geometry for large areas")
    bounding_box: Optional[Dict[str, Any]] = Field(None, description="Bounding box coordinates")
    is_tiled: bool = Field(default=False, description="Whether geometry was tiled")
    is_fallback: bool = Field(default=False, description="Whether using fallback geometry")
    
    # Status fields
    success: bool = Field(default=True, description="Success status")
    error: Optional[str] = Field(None, description="Error message if failed")
    
    @validator('area_km2')
    def validate_area(cls, v):
        if v is not None and v < 0:
            raise ValueError('Area cannot be negative')
        return v
    
    @validator('population')
    def validate_population(cls, v):
        if v is not None and v < 0:
            raise ValueError('Population cannot be negative')
        return v
    
    @validator('polygon_geometry')
    def validate_polygon_geometry(cls, v):
        """Validate that polygon_geometry has proper GeoJSON structure."""
        if v is not None:
            if not isinstance(v, dict):
                raise ValueError('polygon_geometry must be a dictionary')
            
            # Check for basic GeoJSON structure
            if 'type' in v and 'coordinates' in v:
                if v['type'] not in ['Polygon', 'MultiPolygon']:
                    raise ValueError('polygon_geometry type must be Polygon or MultiPolygon')
                
                if not isinstance(v['coordinates'], list):
                    raise ValueError('polygon_geometry coordinates must be a list')
        
        return v
    
    @validator('bounding_box')
    def validate_bounding_box(cls, v):
        """Validate bounding box structure."""
        if v is not None:
            if not isinstance(v, dict):
                raise ValueError('bounding_box must be a dictionary')
            
            # Check for required fields
            required_fields = ['min_lat', 'max_lat', 'min_lng', 'max_lng']
            for field in required_fields:
                if field not in v:
                    raise ValueError(f'bounding_box missing required field: {field}')
                if not isinstance(v[field], (int, float)):
                    raise ValueError(f'bounding_box {field} must be a number')
        
        return v
    
    class Config:
        """Pydantic configuration."""
        # Allow extra fields in case we need to add more data
        extra = "forbid"  # Changed to forbid to catch field mismatches
        # Validate assignments to catch issues early
        validate_assignment = True

class EnvironmentalContextResponse(BaseModel):
    """Response model for environmental context."""
    reports: List[Dict[str, Any]] = Field(default_factory=list, description="Official reports and documents")
    studies: List[Dict[str, Any]] = Field(default_factory=list, description="Research studies and papers")
    news: List[Dict[str, Any]] = Field(default_factory=list, description="News articles and updates")
    statistics: Dict[str, Any] = Field(default_factory=dict, description="Extracted statistical data")
    context_summary: str = Field(default="", description="Generated context summary")
    success: bool = Field(default=True, description="Success status")
    error: Optional[str] = Field(None, description="Error message if failed")

class CompleteAnalysisResponse(BaseModel):
    """Response model for complete analysis."""
    analysis: str = Field(..., description="Generated analysis text")
    roi: Optional[Dict[str, Any]] = Field(None, description="Region of Interest data")
    sources: List[SourceInfo] = Field(default_factory=list, description="Data sources used")
    confidence: float = Field(default=0.0, description="Analysis confidence score")
    success: bool = Field(default=True, description="Success status")
    error: Optional[str] = Field(None, description="Error message if failed")
    
    @validator('confidence')
    def validate_confidence(cls, v):
        if not 0 <= v <= 1:
            raise ValueError('Confidence must be between 0 and 1')
        return v

# Health Check Models
class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str = Field(..., description="Service status")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    timestamp: Optional[datetime] = Field(default_factory=datetime.now, description="Response timestamp")

# Error Models
class ErrorResponse(BaseModel):
    """Error response model."""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    status_code: int = Field(..., description="HTTP status code")
    timestamp: datetime = Field(default_factory=datetime.now, description="Error timestamp")

# Utility Models for Better Type Safety
class GeoJSONPolygon(BaseModel):
    """Specific model for GeoJSON Polygon validation."""
    type: str = Field(..., description="GeoJSON type (Polygon or MultiPolygon)")
    coordinates: List[List[List[float]]] = Field(..., description="Polygon coordinates")
    
    @validator('type')
    def validate_type(cls, v):
        if v not in ['Polygon', 'MultiPolygon']:
            raise ValueError('Type must be Polygon or MultiPolygon')
        return v

class BoundingBox(BaseModel):
    """Specific model for bounding box validation."""
    min_lat: float = Field(..., description="Minimum latitude")
    max_lat: float = Field(..., description="Maximum latitude")
    min_lng: float = Field(..., description="Minimum longitude")
    max_lng: float = Field(..., description="Maximum longitude")
    
    @validator('min_lat', 'max_lat')
    def validate_latitude_range(cls, v):
        if not -90 <= v <= 90:
            raise ValueError('Latitude must be between -90 and 90')
        return v
    
    @validator('min_lng', 'max_lng')
    def validate_longitude_range(cls, v):
        if not -180 <= v <= 180:
            raise ValueError('Longitude must be between -180 and 180')
        return v