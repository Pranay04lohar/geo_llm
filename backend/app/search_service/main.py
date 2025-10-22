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
from .services.nominatim_client import NominatimClient
from .services.tavily_client import TavilyClient
from .services.location_resolver import LocationResolver
from .services.result_processor import ResultProcessor

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Search API Service",
    description="Web search and location intelligence service for GeoLLM",
    version="1.0.0"
)

# CORS middleware is handled by main app when running as monolith
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # Configure appropriately for production
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # Initialize services
# tavily_client = TavilyClient()
# location_resolver = LocationResolver()
# result_processor = ResultProcessor()

# # Pydantic models
# class LocationRequest(BaseModel):
#     location_name: str
#     location_type: str = "city"

# class EnvironmentalContextRequest(BaseModel):
#     location: str
#     analysis_type: str = "ndvi"
#     query: str

# class CompleteAnalysisRequest(BaseModel):
#     query: str
#     locations: List[Dict[str, Any]]
#     analysis_type: str = "ndvi"

# class LocationResponse(BaseModel):
#     coordinates: Dict[str, float]
#     boundaries: Optional[Dict[str, Any]] = None
#     area_km2: Optional[float] = None
#     population: Optional[int] = None
#     administrative_info: Optional[Dict[str, Any]] = None
#     success: bool = True
#     error: Optional[str] = None

# class EnvironmentalContextResponse(BaseModel):
#     reports: List[Dict[str, Any]] = []
#     studies: List[Dict[str, Any]] = []
#     news: List[Dict[str, Any]] = []
#     statistics: Dict[str, Any] = {}
#     context_summary: str = ""
#     success: bool = True
#     error: Optional[str] = None

# class CompleteAnalysisResponse(BaseModel):
#     analysis: str
#     roi: Optional[Dict[str, Any]] = None
#     sources: List[Dict[str, Any]] = []
#     confidence: float = 0.0
#     success: bool = True
#     error: Optional[str] = None

# # Health check endpoint
# @app.get("/health")
# async def health_check():
#     """Health check endpoint."""
#     return {
#         "status": "healthy",
#         "service": "search_api_service",
#         "version": "1.0.0"
#     }

# # Location resolution endpoint
# @app.post("/search/location-data", response_model=LocationResponse)
# async def get_location_data(request: LocationRequest):
#     """
#     Get location data including coordinates, boundaries, area, and polygon geometry.
    
#     This endpoint resolves location names to geographical data using
#     Nominatim for accurate polygon geometry and Tavily for environmental context.
#     """
#     try:
#         logger.info(f"Resolving location: {request.location_name} ({request.location_type})")
        
#         # Use Nominatim client directly to get polygon geometry
#         from app.search_service.services.nominatim_client import NominatimClient
#         nominatim_client = NominatimClient()
        
#         logger.info(f"🔍 Calling Nominatim client for: {request.location_name}")
#         location_data = nominatim_client.search_location(
#             request.location_name, 
#             request.location_type
#         )
        
#         logger.info(f"📊 Nominatim client returned: {type(location_data)}")
#         if location_data:
#             logger.info(f"📋 Available fields in location_data:")
#             for key, value in location_data.items():
#                 if isinstance(value, (dict, list)) and value:
#                     logger.info(f"   {key}: {type(value).__name__} (length: {len(value) if hasattr(value, '__len__') else 'N/A'})")
#                 else:
#                     logger.info(f"   {key}: {value}")
        
#         if not location_data:
#             logger.error(f"❌ No location data returned for {request.location_name}")
#             return LocationResponse(
#                 coordinates={"lat": 0.0, "lng": 0.0},
#                 success=False,
#                 error=f"Location '{request.location_name}' not found"
#             )
        
#         # Map the data to the expected LocationResponse format
#         response_data = {
#             "coordinates": location_data.get("coordinates", {"lat": 0.0, "lng": 0.0}),
#             "boundaries": None,  # Not used in new format
#             "area_km2": location_data.get("area_km2"),
#             "population": location_data.get("population"),
#             "administrative_info": location_data.get("administrative_info"),
#             "sources": location_data.get("sources", []),
#             "polygon_geometry": location_data.get("polygon_geometry"),
#             "geometry_tiles": location_data.get("geometry_tiles", []),
#             "bounding_box": location_data.get("bounding_box"),
#             "is_tiled": location_data.get("is_tiled", False),
#             "is_fallback": location_data.get("is_fallback", False),
#             "success": True,
#             "error": None
#         }
        
#         logger.info(f"🎯 Mapped response_data polygon_geometry: {bool(response_data.get('polygon_geometry'))}")
#         logger.info(f"🎯 Mapped response_data is_tiled: {response_data.get('is_tiled')}")
#         logger.info(f"🎯 Mapped response_data geometry_tiles count: {len(response_data.get('geometry_tiles', []))}")
        
#         try:
#             logger.info(f"🔍 Attempting to create LocationResponse with data:")
#             logger.info(f"   polygon_geometry: {bool(response_data.get('polygon_geometry'))}")
#             logger.info(f"   geometry_tiles: {len(response_data.get('geometry_tiles', []))}")
#             logger.info(f"   bounding_box: {bool(response_data.get('bounding_box'))}")
#             logger.info(f"   is_tiled: {response_data.get('is_tiled')}")
#             logger.info(f"   is_fallback: {response_data.get('is_fallback')}")
            
#             # Debug the sources field specifically
#             sources = response_data.get('sources', [])
#             logger.info(f"   sources: {sources}")
#             if sources:
#                 logger.info(f"   sources[0]: {sources[0]}")
            
#             # Try to create LocationResponse step by step to catch validation errors
#             try:
#                 response = LocationResponse(**response_data)
#                 logger.info(f"✅ Successfully created LocationResponse")
#             except Exception as validation_error:
#                 logger.error(f"❌ LocationResponse validation failed: {validation_error}")
#                 logger.error(f"❌ Validation error details: {validation_error}")
                
#                 # Try to fix common validation issues
#                 logger.info(f"🔍 Attempting to fix validation issues...")
                
#                 # Fix sources field if it's causing issues
#                 if 'sources' in response_data and response_data['sources']:
#                     try:
#                         # Validate each source
#                         fixed_sources = []
#                         for source in response_data['sources']:
#                             if isinstance(source, dict) and all(key in source for key in ['title', 'url', 'score']):
#                                 fixed_sources.append(source)
#                         response_data['sources'] = fixed_sources
#                         logger.info(f"🔧 Fixed sources field: {len(fixed_sources)} valid sources")
#                     except Exception as e:
#                         logger.warning(f"⚠️ Could not fix sources field: {e}")
#                         response_data['sources'] = []
                
#                 # Try again with fixed data
#                 try:
#                     response = LocationResponse(**response_data)
#                     logger.info(f"✅ Successfully created LocationResponse after fixes")
#                 except Exception as second_error:
#                     logger.error(f"❌ Still failed after fixes: {second_error}")
                    
#                     # Fall back to minimal data
#                     minimal_data = {
#                         "coordinates": response_data.get("coordinates", {"lat": 0.0, "lng": 0.0}),
#                         "success": True,
#                         "error": None
#                     }
#                     logger.info(f"🔍 Falling back to minimal LocationResponse")
#                     response = LocationResponse(**minimal_data)
#                     logger.info(f"✅ Minimal LocationResponse created successfully")
            
#             # Log the actual response fields
#             response_dict = response.model_dump()  # Use model_dump instead of dict()
#             logger.info(f"🔍 LocationResponse contains:")
#             logger.info(f"   polygon_geometry: {bool(response_dict.get('polygon_geometry'))}")
#             logger.info(f"   geometry_tiles: {len(response_dict.get('geometry_tiles', []))}")
#             logger.info(f"   bounding_box: {bool(response_dict.get('bounding_box'))}")
#             logger.info(f"   is_tiled: {response_dict.get('is_tiled')}")
#             logger.info(f"   is_fallback: {response_dict.get('is_fallback')}")
            
#             return response
#         except Exception as e:
#             logger.error(f"❌ Failed to create LocationResponse: {e}")
#             import traceback
#             logger.error(f"❌ Traceback: {traceback.format_exc()}")
#             # Fallback response
#             return LocationResponse(
#                 coordinates=response_data.get("coordinates", {"lat": 0.0, "lng": 0.0}),
#                 success=False,
#                 error=f"Failed to create response: {str(e)}"
#             )
        
#     except Exception as e:
#         logger.error(f"Error resolving location {request.location_name}: {e}")
#         return LocationResponse(
#             coordinates={"lat": 0.0, "lng": 0.0},
#             success=False,
#             error=str(e)
#         )

# # Environmental context endpoint
# @app.post("/search/environmental-context", response_model=EnvironmentalContextResponse)
# async def get_environmental_context(request: EnvironmentalContextRequest):
#     """
#     Get environmental context including reports, studies, and news.
    
#     This endpoint searches for environmental information related to the location
#     and analysis type using Tavily API.
#     """
#     try:
#         logger.info(f"Getting environmental context for {request.location} ({request.analysis_type})")
        
#         # Use the new environmental context method
#         environmental_data = await location_resolver.get_environmental_context(
#             request.location,
#             request.analysis_type,
#             request.query
#         )
        
#         if environmental_data:
#             return EnvironmentalContextResponse(
#                 reports=environmental_data.get("reports", []),
#                 studies=environmental_data.get("studies", []),
#                 news=environmental_data.get("news", []),
#                 statistics={"total_sources": environmental_data.get("total_sources", 0)},
#                 context_summary=f"Found {environmental_data.get('total_sources', 0)} sources for {request.analysis_type} analysis",
#                 success=True
#             )
#         else:
#             return EnvironmentalContextResponse(
#                 success=False,
#                 error="No environmental context found"
#             )
        
#     except Exception as e:
#         logger.error(f"Error getting environmental context: {e}")
#         return EnvironmentalContextResponse(
#             success=False,
#             error=str(e)
#         )

# # Complete analysis endpoint (fallback)
# @app.post("/search/complete-analysis", response_model=CompleteAnalysisResponse)
# async def get_complete_analysis(request: CompleteAnalysisRequest):
#     """
#     Generate complete analysis based on web search data.
    
#     This endpoint is used as a fallback when GEE/RAG services fail.
#     It provides a comprehensive analysis based on web search results.
#     """
#     try:
#         logger.info(f"Generating complete analysis for: {request.query}")
        
#         # Get location data first
#         location_data = None
#         if request.locations:
#             primary_location = request.locations[0]
#             location_data = await location_resolver.resolve_location(
#                 primary_location.get("matched_name", ""),
#                 primary_location.get("type", "city")
#             )
        
#         # Generate comprehensive search queries
#         search_queries = _generate_comprehensive_queries(
#             request.query, 
#             request.locations, 
#             request.analysis_type
#         )
        
#         # Search using Tavily
#         all_results = []
#         for query in search_queries:
#             results = await tavily_client.search(query)
#             all_results.extend(results)
        
#         # Process results and generate analysis
#         analysis_data = result_processor.generate_complete_analysis(
#             all_results, 
#             request.analysis_type,
#             location_data
#         )
        
#         return CompleteAnalysisResponse(**analysis_data)
        
#     except Exception as e:
#         logger.error(f"Error generating complete analysis: {e}")
#         return CompleteAnalysisResponse(
#             success=False,
#             error=str(e),
#             analysis="Analysis generation failed"
#         )

# # Helper functions
# def _generate_search_queries(location: str, analysis_type: str, base_query: str) -> List[str]:
#     """Generate targeted search queries for environmental context."""
#     queries = []
    
#     # Base location-specific queries
#     queries.append(f"{location} {analysis_type} analysis 2023")
#     queries.append(f"{location} environmental report")
#     queries.append(f"{location} vegetation health study")
    
#     # Analysis type specific queries
#     if analysis_type == "ndvi":
#         queries.extend([
#             f"{location} NDVI satellite data",
#             f"{location} vegetation index study",
#             f"{location} green cover analysis"
#         ])
#     elif analysis_type == "lulc":
#         queries.extend([
#             f"{location} land use land cover",
#             f"{location} urban development analysis",
#             f"{location} land classification study"
#         ])
    
#     # General environmental queries
#     queries.extend([
#         f"{location} environmental policy",
#         f"{location} conservation initiatives",
#         f"{location} climate data"
#     ])
    
#     return queries

# def _generate_comprehensive_queries(
#     base_query: str, 
#     locations: List[Dict[str, Any]], 
#     analysis_type: str
# ) -> List[str]:
#     """Generate comprehensive search queries for complete analysis."""
#     queries = []
    
#     # Use the base query
#     queries.append(base_query)
    
#     # Add location-specific variations
#     if locations:
#         for location in locations:
#             location_name = location.get("matched_name", "")
#             if location_name:
#                 queries.append(f"{location_name} {analysis_type} analysis")
#                 queries.append(f"{location_name} environmental data")
#                 queries.append(f"{location_name} satellite imagery study")
    
#     # Add analysis type specific queries
#     if analysis_type == "ndvi":
#         queries.extend([
#             "vegetation health analysis",
#             "NDVI satellite data interpretation",
#             "green cover assessment"
#         ])
#     elif analysis_type == "lulc":
#         queries.extend([
#             "land use land cover analysis",
#             "urban development assessment",
#             "land classification study"
#         ])
    
#     return queries

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8001)



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
from .services.tavily_client import TavilyClient
from .services.location_resolver import LocationResolver
from .services.result_processor import ResultProcessor
from .services.enhanced_result_processor import EnhancedResultProcessor

# Import the models
from .models import (
    LocationRequest, EnvironmentalContextRequest, CompleteAnalysisRequest,
    LocationResponse, EnvironmentalContextResponse, CompleteAnalysisResponse,
    Coordinates, AdministrativeInfo, SourceInfo
)

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
enhanced_result_processor = EnhancedResultProcessor()

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
    Get location data including coordinates, boundaries, area, and polygon geometry.
    
    This endpoint resolves location names to geographical data using
    Nominatim for accurate polygon geometry and Tavily for environmental context.
    """
    try:
        logger.info(f"Resolving location: {request.location_name} ({request.location_type})")
        
        # Use Nominatim client directly to get polygon geometry
        nominatim_client = NominatimClient()
        
        logger.info(f"🔍 SEARCH SERVICE: Calling Nominatim client for: {request.location_name} ({request.location_type})")
        logger.info(f"🔍 SEARCH SERVICE: Request details - name: {request.location_name}, type: {request.location_type}")
        location_data = nominatim_client.search_location(
            request.location_name,
            request.location_type
        )
        logger.info(f"🔍 SEARCH SERVICE: Nominatim client returned location data: {bool(location_data)}")
        
        logger.info(f"📊 Nominatim client returned: {type(location_data)}")
        if location_data:
            logger.info(f"📋 Available fields in location_data:")
            for key, value in location_data.items():
                if isinstance(value, (dict, list)) and value:
                    logger.info(f"   {key}: {type(value).__name__} (length: {len(value) if hasattr(value, '__len__') else 'N/A'})")
                else:
                    logger.info(f"   {key}: {value}")
        
        if not location_data:
            logger.error(f"❌ No location data returned for {request.location_name}")
            return LocationResponse(
                coordinates=Coordinates(lat=0.0, lng=0.0),
                success=False,
                error=f"Location '{request.location_name}' not found"
            )
        
        # Properly map coordinates to Coordinates model
        coords_data = location_data.get("coordinates", {"lat": 0.0, "lng": 0.0})
        coordinates = Coordinates(
            lat=coords_data.get("lat", 0.0),
            lng=coords_data.get("lng", 0.0)
        )
        
        # Properly map administrative info
        admin_info = None
        admin_data = location_data.get("administrative_info")
        if admin_data and isinstance(admin_data, dict):
            try:
                admin_info = AdministrativeInfo(
                    name=admin_data.get("name", request.location_name),
                    type=admin_data.get("type", request.location_type),
                    country=admin_data.get("country"),
                    state=admin_data.get("state"),
                    city=admin_data.get("city")
                )
            except Exception as e:
                logger.warning(f"⚠️ Could not create AdministrativeInfo: {e}")
                admin_info = None
        
        # Properly map sources
        sources = []
        sources_data = location_data.get("sources", [])
        if isinstance(sources_data, list):
            for source in sources_data:
                if isinstance(source, dict) and all(key in source for key in ['title', 'url', 'score']):
                    try:
                        sources.append(SourceInfo(
                            title=source['title'],
                            url=source['url'],
                            score=float(source['score'])
                        ))
                    except Exception as e:
                        logger.warning(f"⚠️ Could not create SourceInfo: {e}")
        
        # Map bounding box to expected format
        bounding_box = None
        bbox_data = location_data.get("bounding_box")
        if bbox_data and isinstance(bbox_data, dict):
            # Convert from Nominatim format (west, east, north, south) to our format (min_lat, max_lat, min_lng, max_lng)
            if all(key in bbox_data for key in ['west', 'east', 'north', 'south']):
                bounding_box = {
                    'min_lat': bbox_data['south'],
                    'max_lat': bbox_data['north'],
                    'min_lng': bbox_data['west'],
                    'max_lng': bbox_data['east']
                }
            # If already in our format, use as-is
            elif all(key in bbox_data for key in ['min_lat', 'max_lat', 'min_lng', 'max_lng']):
                bounding_box = bbox_data

        # Create the response with proper field mapping
        try:
            response = LocationResponse(
                coordinates=coordinates,
                # boundaries=location_data.get("boundaries"),  # Keep as optional dict
                boundaries=location_data.get("boundaries") if location_data.get("boundaries") else None,
                area_km2=location_data.get("area_km2"),
                population=location_data.get("population"),
                administrative_info=admin_info,
                sources=sources,
                # New polygon geometry fields - these are the critical ones
                polygon_geometry=location_data.get("polygon_geometry"),
                geometry_tiles=location_data.get("geometry_tiles", []),
                bounding_box=bounding_box,
                is_tiled=location_data.get("is_tiled", False),
                is_fallback=location_data.get("is_fallback", False),
                success=True,
                error=None
            )
            
            logger.info(f"✅ Successfully created LocationResponse with polygon data")
            logger.info(f"   🔍 polygon_geometry: {bool(response.polygon_geometry)}")
            logger.info(f"   🔍 geometry_tiles: {len(response.geometry_tiles)}")
            logger.info(f"   🔍 is_tiled: {response.is_tiled}")
            logger.info(f"   🔍 is_fallback: {response.is_fallback}")
            
            return response
            
        except Exception as validation_error:
            logger.error(f"❌ LocationResponse validation failed: {validation_error}")
            logger.error(f"❌ Validation error type: {type(validation_error)}")
            
            # Log detailed validation error information
            import traceback
            logger.error(f"❌ Full traceback: {traceback.format_exc()}")
            
            # Try to identify which field is causing the issue
            logger.info(f"🔍 Debugging field validation:")
            logger.info(f"   coordinates type: {type(coordinates)}")
            logger.info(f"   administrative_info type: {type(admin_info)}")
            logger.info(f"   sources type: {type(sources)} (length: {len(sources)})")
            logger.info(f"   polygon_geometry type: {type(location_data.get('polygon_geometry'))}")
            logger.info(f"   geometry_tiles type: {type(location_data.get('geometry_tiles', []))}")
            
            # Create minimal response that should work
            minimal_response = LocationResponse(
                coordinates=coordinates,
                success=False,
                error=f"Validation failed: {str(validation_error)}"
            )
            logger.info(f"🔧 Created minimal response fallback")
            return minimal_response
        
    except Exception as e:
        logger.error(f"❌ Error resolving location {request.location_name}: {e}")
        import traceback
        logger.error(f"❌ Full traceback: {traceback.format_exc()}")
        
        return LocationResponse(
            coordinates=Coordinates(lat=0.0, lng=0.0),
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

# Enhanced analysis endpoint with data extraction and validation
@app.post("/search/enhanced-analysis")
async def get_enhanced_analysis(request: CompleteAnalysisRequest):
    """
    Generate enhanced analysis with data extraction and validation.
    
    This endpoint provides:
    - Multiple search strategies for comprehensive data collection
    - Structured data extraction and validation
    - Quality assessment and confidence scoring
    - Data-rich analysis with specific metrics
    """
    try:
        logger.info(f"Generating enhanced analysis for: {request.query}")
        
        # Get location data first
        location_data = None
        if request.locations:
            primary_location = request.locations[0]
            location_data = await location_resolver.resolve_location(
                primary_location.get("matched_name", ""),
                primary_location.get("type", "city")
            )
        
        # Use enhanced result processor
        enhanced_analysis = await enhanced_result_processor.generate_enhanced_analysis(
            analysis_type=request.analysis_type,
            location=request.locations[0].get("matched_name", "Unknown") if request.locations else "Unknown",
            location_data=location_data
        )
        
        return enhanced_analysis
        
    except Exception as e:
        logger.error(f"Error generating enhanced analysis: {e}")
        return {
            "analysis": f"Enhanced analysis generation failed: {str(e)}",
            "roi": None,
            "sources": [],
            "confidence": 0.0,
            "structured_data": {},
            "data_quality": {"overall": 0.0},
            "search_metadata": {},
            "extracted_metrics_count": 0,
            "success": False,
            "error": str(e)
        }

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