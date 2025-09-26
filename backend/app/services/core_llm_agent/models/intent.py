"""
Intent classification models.

These models define the structure for intent classification results
at both the top level (service selection) and sub-level (GEE service selection).
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from enum import Enum


class ServiceType(str, Enum):
    """Available service types for routing."""
    GEE = "GEE"
    SEARCH = "SEARCH"


class GEESubIntent(str, Enum):
    """Sub-intents for GEE service routing."""
    NDVI = "NDVI"
    LULC = "LULC"
    LST = "LST"  # Land Surface Temperature / Urban Heat Island
    CLIMATE = "CLIMATE"
    WATER = "WATER"
    SOIL = "SOIL"
    POPULATION = "POPULATION"
    TRANSPORTATION = "TRANSPORTATION"


class IntentResult(BaseModel):
    """Complete result of intent classification."""
    
    # Primary intent
    service_type: ServiceType = Field(..., description="Primary service to route to")
    confidence: float = Field(..., ge=0, le=1, description="Confidence score (0-1)")
    
    # Sub-intent for GEE service
    gee_sub_intent: Optional[GEESubIntent] = Field(None, description="Sub-intent for GEE service")
    gee_confidence: Optional[float] = Field(None, ge=0, le=1, description="GEE sub-intent confidence")
    
    # Analysis parameters
    analysis_type: str = Field("general", description="Analysis type for service")
    time_range: Optional[Dict[str, str]] = Field(None, description="Time range if specified")
    metrics: List[str] = Field(default_factory=list, description="Specific metrics requested")
    
    # Processing metadata
    reasoning: str = Field("", description="Reasoning for the classification")
    processing_time: float = Field(0.0, description="Processing time in seconds")
    model_used: str = Field("", description="Model used for classification")
    success: bool = Field(True, description="Whether classification was successful")
    error: Optional[str] = Field(None, description="Error message if classification failed")
    
    # Raw LLM outputs for debugging
    raw_response: Optional[Dict[str, Any]] = Field(None, description="Raw LLM response")
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        protected_namespaces = ()  # Disable protected namespace warnings
