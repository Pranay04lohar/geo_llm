"""
Search API Service - FastAPI application for web search and location intelligence.

This service provides:
1. Location resolution (coordinates, boundaries, area)
2. Environmental context (reports, studies, news)
3. Complete analysis fallback when GEE/RAG services fail

Uses Tavily API for LLM-optimized web search.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
# Look for .env in the backend directory (parent of search_service)
backend_dir = Path(__file__).parent.parent.parent
env_path = backend_dir / ".env"
load_dotenv(env_path)

# Import our services
from services.tavily_client import TavilyClient
from services.location_resolver import LocationResolver
from services.result_processor import ResultProcessor

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Search API Service",
    description="Web search and location intelligence service for GeoLLM",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
tavily_client = TavilyClient()
location_resolver = LocationResolver()
result_processor = ResultProcessor()

# Pydantic models
class LocationRequest(BaseModel):
    location_name: str
    location_type: str = "city"

class EnvironmentalContextRequest(BaseModel):
    location: str
    analysis_type: str = "ndvi"
    query: str

class CompleteAnalysisRequest(BaseModel):
    query: str
    locations: List[Dict[str, Any]]
    analysis_type: str = "ndvi"

class LocationResponse(BaseModel):
    coordinates: Dict[str, float]
    boundaries: Optional[Dict[str, Any]] = None
    area_km2: Optional[float] = None
    population: Optional[int] = None
    administrative_info: Optional[Dict[str, Any]] = None
    success: bool = True
    error: Optional[str] = None

class EnvironmentalContextResponse(BaseModel):
    reports: List[Dict[str, Any]] = []
    studies: List[Dict[str, Any]] = []
    news: List[Dict[str, Any]] = []
    statistics: Dict[str, Any] = {}
    context_summary: str = ""
    success: bool = True
    error: Optional[str] = None

class CompleteAnalysisResponse(BaseModel):
    analysis: str
    roi: Optional[Dict[str, Any]] = None
    sources: List[Dict[str, Any]] = []
    confidence: float = 0.0
    success: bool = True
    error: Optional[str] = None

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "search_api_service",
        "version": "1.0.0"
    }

# Location resolution endpoint
@app.post("/search/location-data", response_model=LocationResponse)
async def get_location_data(request: LocationRequest):
    """
    Get location data including coordinates, boundaries, and area.
    
    This endpoint resolves location names to geographical data using
    web search and geocoding services.
    """
    try:
        logger.info(f"Resolving location: {request.location_name} ({request.location_type})")
        
        # Use location resolver to get coordinates and basic info
        location_data = await location_resolver.resolve_location(
            request.location_name, 
            request.location_type
        )
        
        if not location_data:
            return LocationResponse(
                coordinates={"lat": 0.0, "lng": 0.0},
                success=False,
                error=f"Location '{request.location_name}' not found"
            )
        
        return LocationResponse(**location_data)
        
    except Exception as e:
        logger.error(f"Error resolving location {request.location_name}: {e}")
        return LocationResponse(
            coordinates={"lat": 0.0, "lng": 0.0},
            success=False,
            error=str(e)
        )

# Environmental context endpoint
@app.post("/search/environmental-context", response_model=EnvironmentalContextResponse)
async def get_environmental_context(request: EnvironmentalContextRequest):
    """
    Get environmental context including reports, studies, and news.
    
    This endpoint searches for environmental information related to the location
    and analysis type using Tavily API.
    """
    try:
        logger.info(f"Getting environmental context for {request.location} ({request.analysis_type})")
        
        # Use the new environmental context method
        environmental_data = await location_resolver.get_environmental_context(
            request.location,
            request.analysis_type,
            request.query
        )
        
        if environmental_data:
            return EnvironmentalContextResponse(
                reports=environmental_data.get("reports", []),
                studies=environmental_data.get("studies", []),
                news=environmental_data.get("news", []),
                statistics={"total_sources": environmental_data.get("total_sources", 0)},
                context_summary=f"Found {environmental_data.get('total_sources', 0)} sources for {request.analysis_type} analysis",
                success=True
            )
        else:
            return EnvironmentalContextResponse(
                success=False,
                error="No environmental context found"
            )
        
    except Exception as e:
        logger.error(f"Error getting environmental context: {e}")
        return EnvironmentalContextResponse(
            success=False,
            error=str(e)
        )

# Complete analysis endpoint (fallback)
@app.post("/search/complete-analysis", response_model=CompleteAnalysisResponse)
async def get_complete_analysis(request: CompleteAnalysisRequest):
    """
    Generate complete analysis based on web search data.
    
    This endpoint is used as a fallback when GEE/RAG services fail.
    It provides a comprehensive analysis based on web search results.
    """
    try:
        logger.info(f"Generating complete analysis for: {request.query}")
        
        # Get location data first
        location_data = None
        if request.locations:
            primary_location = request.locations[0]
            location_data = await location_resolver.resolve_location(
                primary_location.get("matched_name", ""),
                primary_location.get("type", "city")
            )
        
        # Generate comprehensive search queries
        search_queries = _generate_comprehensive_queries(
            request.query, 
            request.locations, 
            request.analysis_type
        )
        
        # Search using Tavily
        all_results = []
        for query in search_queries:
            results = await tavily_client.search(query)
            all_results.extend(results)
        
        # Process results and generate analysis
        analysis_data = result_processor.generate_complete_analysis(
            all_results, 
            request.analysis_type,
            location_data
        )
        
        return CompleteAnalysisResponse(**analysis_data)
        
    except Exception as e:
        logger.error(f"Error generating complete analysis: {e}")
        return CompleteAnalysisResponse(
            success=False,
            error=str(e),
            analysis="Analysis generation failed"
        )

# Helper functions
def _generate_search_queries(location: str, analysis_type: str, base_query: str) -> List[str]:
    """Generate targeted search queries for environmental context."""
    queries = []
    
    # Base location-specific queries
    queries.append(f"{location} {analysis_type} analysis 2023")
    queries.append(f"{location} environmental report")
    queries.append(f"{location} vegetation health study")
    
    # Analysis type specific queries
    if analysis_type == "ndvi":
        queries.extend([
            f"{location} NDVI satellite data",
            f"{location} vegetation index study",
            f"{location} green cover analysis"
        ])
    elif analysis_type == "lulc":
        queries.extend([
            f"{location} land use land cover",
            f"{location} urban development analysis",
            f"{location} land classification study"
        ])
    
    # General environmental queries
    queries.extend([
        f"{location} environmental policy",
        f"{location} conservation initiatives",
        f"{location} climate data"
    ])
    
    return queries

def _generate_comprehensive_queries(
    base_query: str, 
    locations: List[Dict[str, Any]], 
    analysis_type: str
) -> List[str]:
    """Generate comprehensive search queries for complete analysis."""
    queries = []
    
    # Use the base query
    queries.append(base_query)
    
    # Add location-specific variations
    if locations:
        for location in locations:
            location_name = location.get("matched_name", "")
            if location_name:
                queries.append(f"{location_name} {analysis_type} analysis")
                queries.append(f"{location_name} environmental data")
                queries.append(f"{location_name} satellite imagery study")
    
    # Add analysis type specific queries
    if analysis_type == "ndvi":
        queries.extend([
            "vegetation health analysis",
            "NDVI satellite data interpretation",
            "green cover assessment"
        ])
    elif analysis_type == "lulc":
        queries.extend([
            "land use land cover analysis",
            "urban development assessment",
            "land classification study"
        ])
    
    return queries

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
