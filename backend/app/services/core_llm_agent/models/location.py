"""
Location parsing and resolution models.

These models define the structure for location entities extracted from queries
and their resolved geographic information.
"""

from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field


class LocationEntity(BaseModel):
    """A single location entity extracted from a query."""
    
    matched_name: str = Field(..., description="The location name as extracted from the query")
    type: str = Field(..., description="Type of location (city, state, country, etc.)")
    confidence: float = Field(..., ge=0, le=100, description="Confidence score (0-100)")


class BoundaryInfo(BaseModel):
    """Geographic boundary information for a resolved location."""
    
    geometry: Dict[str, Any] = Field(..., description="GeoJSON geometry for the location")
    bbox: List[float] = Field(..., description="Bounding box [min_lng, min_lat, max_lng, max_lat]")
    area_km2: Optional[float] = Field(None, description="Area in square kilometers")
    center: List[float] = Field(..., description="Center coordinates [lng, lat]")
    display_name: str = Field(..., description="Full display name from geocoding service")
    place_id: Optional[Union[str, int]] = Field(None, description="Unique place identifier")
    importance: Optional[float] = Field(None, description="Importance score from geocoding service")


class LocationParseResult(BaseModel):
    """Complete result of location parsing and resolution."""
    
    entities: List[LocationEntity] = Field(default_factory=list, description="Extracted location entities")
    resolved_locations: List[BoundaryInfo] = Field(default_factory=list, description="Resolved geographic boundaries")
    primary_location: Optional[BoundaryInfo] = Field(None, description="Primary location for analysis")
    roi_geometry: Optional[Dict[str, Any]] = Field(None, description="Region of interest geometry")
    roi_source: str = Field("unknown", description="Source of ROI (ner, query_parsing, default)")
    processing_time: float = Field(0.0, description="Processing time in seconds")
    success: bool = Field(True, description="Whether parsing was successful")
    error: Optional[str] = Field(None, description="Error message if parsing failed")
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            # Custom encoders if needed
        }
