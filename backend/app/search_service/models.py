"""
Pydantic models for the Search API Service.

This module defines the data models used for request/response validation
and serialization in the Search API Service.
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
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

class AdministrativeInfo(BaseModel):
    """Administrative information for a location."""
    name: str = Field(..., description="Location name")
    type: str = Field(default="unknown", description="Location type")
    country: Optional[str] = Field(None, description="Country name")
    state: Optional[str] = Field(None, description="State/province name")
    region: Optional[str] = Field(None, description="Region name")

class SourceInfo(BaseModel):
    """Information about a data source."""
    title: str = Field(..., description="Source title")
    url: str = Field(..., description="Source URL")
    score: float = Field(..., description="Relevance score")

class LocationResponse(BaseModel):
    """Response model for location data."""
    coordinates: Coordinates = Field(..., description="Geographical coordinates")
    boundaries: Optional[Dict[str, Any]] = Field(None, description="Geographical boundaries")
    area_km2: Optional[float] = Field(None, description="Area in square kilometers")
    population: Optional[int] = Field(None, description="Population count")
    administrative_info: Optional[AdministrativeInfo] = Field(None, description="Administrative details")
    sources: List[SourceInfo] = Field(default=[], description="Data sources")
    success: bool = Field(default=True, description="Success status")
    error: Optional[str] = Field(None, description="Error message if failed")

class EnvironmentalContextResponse(BaseModel):
    """Response model for environmental context."""
    reports: List[Dict[str, Any]] = Field(default=[], description="Official reports and documents")
    studies: List[Dict[str, Any]] = Field(default=[], description="Research studies and papers")
    news: List[Dict[str, Any]] = Field(default=[], description="News articles and updates")
    statistics: Dict[str, Any] = Field(default={}, description="Extracted statistical data")
    context_summary: str = Field(default="", description="Generated context summary")
    success: bool = Field(default=True, description="Success status")
    error: Optional[str] = Field(None, description="Error message if failed")

class CompleteAnalysisResponse(BaseModel):
    """Response model for complete analysis."""
    analysis: str = Field(..., description="Generated analysis text")
    roi: Optional[Dict[str, Any]] = Field(None, description="Region of Interest data")
    sources: List[SourceInfo] = Field(default=[], description="Data sources used")
    confidence: float = Field(default=0.0, description="Analysis confidence score")
    success: bool = Field(default=True, description="Success status")
    error: Optional[str] = Field(None, description="Error message if failed")

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
