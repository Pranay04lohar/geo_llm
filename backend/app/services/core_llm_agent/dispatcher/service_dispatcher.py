"""
Service Dispatcher - Routes requests to appropriate services.

This module dispatches requests to GEE, RAG, or Search services based on
intent classification results. It provides a unified interface for service calls.
"""

import logging
from typing import Dict, Any, List, Optional

try:
    from ..models.intent import IntentResult, ServiceType, GEESubIntent
    from ..models.location import LocationParseResult
except ImportError:
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent.parent.parent.parent))
    
    from app.services.core_llm_agent.models.intent import IntentResult, ServiceType, GEESubIntent
    from app.services.core_llm_agent.models.location import LocationParseResult

logger = logging.getLogger(__name__)


class ServiceDispatcher:
    """Dispatcher for routing requests to appropriate services."""
    
    def __init__(self, rag_store=None):
        """Initialize the ServiceDispatcher.
        
        Args:
            rag_store: RAGStore instance for document Q&A (optional)
        """
        self.rag_store = rag_store
        self.services_initialized = False
        self._init_services()
    
    def _init_services(self):
        """Initialize service connections and imports."""
        try:
            # ================================================================
            # GEE Services - Direct imports (no HTTP)
            # ================================================================
            try:
                from app.services.gee import (
                    NDVIService,
                    LSTService,
                    LULCService,
                    WaterService,
                    ROIHandler
                )
                self.ndvi_service = NDVIService
                self.lst_service = LSTService
                self.lulc_service = LULCService
                self.water_service = WaterService
                self.roi_handler = ROIHandler()
                self.gee_services_available = True
                logger.info("✅ GEE services loaded (direct imports)")
            except ImportError as e:
                logger.warning(f"⚠️ GEE services not available: {e}")
                self.gee_services_available = False
            
            # ================================================================
            # Search Services - Direct imports (no HTTP)
            # ================================================================
            try:
                from app.services.search import (
                    NominatimClient,
                    LocationResolver,
                    ResultProcessor
                )
                self.nominatim_client = NominatimClient()
                self.location_resolver = LocationResolver()
                self.result_processor = ResultProcessor()
                self.search_services_available = True
                logger.info("✅ Search services loaded (direct imports)")
            except ImportError as e:
                logger.warning(f"⚠️ Search services not available: {e}")
                self.search_services_available = False
            
            # ================================================================
            # RAG Service - Direct instance (no HTTP)
            # ================================================================
            if self.rag_store:
                self.rag_service_available = True
                logger.info("✅ RAG store available (direct instance)")
            else:
                self.rag_service_available = False
                logger.warning("⚠️ RAG store not provided")
            
            self.services_initialized = True
            logger.info("✅ Service dispatcher initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize services: {e}")
            self.services_initialized = False
    
    def dispatch(
        self, 
        query: str, 
        intent_result: IntentResult, 
        location_result: LocationParseResult,
        rag_session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Dispatch request to appropriate service based on intent.
        
        Args:
            query: Original user query
            intent_result: Intent classification result
            location_result: Location parsing result
            
        Returns:
            Service response dictionary with analysis, roi, and metadata
        """
        if not self.services_initialized:
            logger.error("Services not initialized, cannot dispatch")
            return self._error_response("Service dispatcher not initialized")
        
        service_type_str = intent_result.service_type.value if hasattr(intent_result.service_type, 'value') else str(intent_result.service_type)
        logger.info(f"Dispatching {service_type_str} request: {query[:100]}...")
        
        try:
            # Handle both enum and string service types
            service_type = intent_result.service_type
            if hasattr(service_type, 'value'):
                service_type_value = service_type.value
            else:
                service_type_value = str(service_type)
            
            # Check for RAG session first (dynamic RAG usage when files uploaded)
            if rag_session_id and self.rag_service_available:
                logger.info("RAG session detected; routing to RAG service")
                return self._dispatch_rag(query, intent_result, location_result, rag_session_id)
            
            # Route based on intent classification
            if service_type == ServiceType.GEE or service_type_value == "GEE":
                return self._dispatch_gee(query, intent_result, location_result)
            elif service_type == ServiceType.SEARCH or service_type_value == "SEARCH":
                return self._dispatch_search(query, intent_result, location_result)
            else:
                logger.error(f"Unknown service type: {intent_result.service_type}")
                return self._error_response(f"Unknown service type: {intent_result.service_type}")
                
        except Exception as e:
            logger.error(f"Error in service dispatch: {e}")
            return self._error_response(f"Service dispatch failed: {str(e)}")
    
    def _dispatch_gee(
        self, 
        query: str, 
        intent_result: IntentResult, 
        location_result: LocationParseResult
    ) -> Dict[str, Any]:
        """Dispatch to GEE service.
        
        Args:
            query: Original user query
            intent_result: Intent classification result
            location_result: Location parsing result
            
        Returns:
            GEE service response
        """
        logger.info(f"Dispatching to GEE service: {intent_result.analysis_type}")
        
        try:
            # Prepare location data in legacy format for backward compatibility
            locations_legacy = []
            if location_result.entities:
                locations_legacy = [
                    {
                        "matched_name": entity.matched_name,
                        "type": entity.type,
                        "confidence": entity.confidence
                    }
                    for entity in location_result.entities
                ]
            
            # Get ROI geometry using ROI handler
            roi_info = None
            if locations_legacy:
                roi_info = self.roi_handler.extract_roi_from_locations(locations_legacy)
            elif location_result.roi_geometry:
                # Use already resolved geometry
                roi_info = {
                    "geometry": location_result.roi_geometry,
                    "area_km2": location_result.primary_location.area_km2 if location_result.primary_location else 0,
                    "polygon_geometry": location_result.roi_geometry
                }
            
            if not roi_info:
                # Fallback to default ROI
                roi_info = self.roi_handler.get_default_roi()
            
            # Route to specific GEE service based on sub-intent
            analysis_type = intent_result.analysis_type
            
            # DEBUG: Log intent classification results
            logger.info(f"🎯 Intent Classification Results:")
            logger.info(f"   Service Type: {intent_result.service_type}")
            logger.info(f"   GEE Sub-Intent: {intent_result.gee_sub_intent}")
            logger.info(f"   Analysis Type: {analysis_type}")
            logger.info(f"   Confidence: {intent_result.confidence}")
            
            # Call GEE services directly (no HTTP)
            return self._call_gee_service_direct(analysis_type, roi_info, query)
                
        except Exception as e:
            logger.error(f"Error in GEE service dispatch: {e}")
            # Fallback to search service
            logger.info("Falling back to search service due to GEE error")
            return self._dispatch_search(query, intent_result, location_result)
    
    def _call_ndvi_service(self, roi_info: Dict[str, Any], query: str) -> Dict[str, Any]:
        """Call NDVI service directly.
        
        Args:
            roi_info: ROI information dictionary
            query: Original query for context
            
        Returns:
            NDVI service response
        """
        try:
            # Use polygon-based analysis if available
            if roi_info.get("polygon_geometry"):
                result = self.ndvi_service.analyze_ndvi_with_polygon(
                    roi_data=roi_info,
                    start_date="2023-06-01",
                    end_date="2023-08-31",
                    cloud_threshold=30,
                    scale=30,
                    max_pixels=5e8,
                    include_time_series=False,
                    exact_computation=False
                )
            else:
                result = self.ndvi_service.analyze_ndvi(
                    geometry=roi_info["geometry"],
                    start_date="2023-06-01",
                    end_date="2023-08-31",
                    cloud_threshold=30,
                    scale=30,
                    max_pixels=5e8,
                    include_time_series=False,
                    exact_computation=False
                )
            
            if result.get("success"):
                return self._format_gee_response(result, "ndvi", roi_info)
            else:
                logger.error(f"NDVI service failed: {result.get('error')}")
                return self._error_response(f"NDVI analysis failed: {result.get('error')}")
                
        except Exception as e:
            logger.error(f"Error calling NDVI service: {e}")
            return self._error_response(f"NDVI service error: {str(e)}")
    
    def _call_lst_service(self, roi_info: Dict[str, Any], query: str) -> Dict[str, Any]:
        """Call LST service directly.
        
        Args:
            roi_info: ROI information dictionary
            query: Original query for context
            
        Returns:
            LST service response
        """
        try:
            # Use polygon-based analysis if available
            if roi_info.get("polygon_geometry"):
                result = self.lst_service.analyze_lst_with_polygon(
                    roi_data=roi_info,
                    start_date="2023-06-01",
                    end_date="2023-08-31",
                    include_uhi=True,
                    include_time_series=False,
                    scale=1000,
                    max_pixels=1e8,
                    exact_computation=False
                )
            else:
                # Fallback to HTTP service
                return self._call_gee_http_service("lst", roi_info, query)
            
            if result.get("success"):
                return self._format_gee_response(result, "lst", roi_info)
            else:
                logger.error(f"LST service failed: {result.get('error')}")
                return self._error_response(f"LST analysis failed: {result.get('error')}")
                
        except Exception as e:
            logger.error(f"Error calling LST service: {e}")
            return self._error_response(f"LST service error: {str(e)}")
    
    def _call_gee_service_direct(
        self, 
        analysis_type: str, 
        roi_info: Dict[str, Any], 
        query: str
    ) -> Dict[str, Any]:
        """Call GEE service directly (no HTTP).
        
        Args:
            analysis_type: Type of analysis (ndvi, lulc, lst, etc.)
            roi_info: ROI information dictionary
            query: Original query for context
            
        Returns:
            GEE service response
        """
        try:
            # Get base service URL from config
            from app.config_urls import get_service_url
            base_url = get_service_url()
            
            # Determine service endpoint
            if analysis_type == "ndvi":
                url = f"{base_url}/ndvi/vegetation-analysis"
                payload = {
                    "geometry": roi_info["geometry"],
                    "startDate": "2023-06-01",
                    "endDate": "2023-08-31",
                    "cloudThreshold": 30,
                    "scale": 30,
                    "maxPixels": 2e8,
                    "includeTimeSeries": False,
                    "exactComputation": False
                }
            elif analysis_type == "lst":
                url = f"{base_url}/lst/land-surface-temperature"
                payload = {
                    "geometry": roi_info["geometry"],
                    "startDate": "2024-01-01",
                    "endDate": "2024-08-31",
                    "includeUHI": True,
                    "includeTimeSeries": False,
                    "scale": 1000,
                    "maxPixels": 5e7,
                    "exactComputation": False
                }
            elif analysis_type == "water":
                url = f"{base_url}/water/analyze"
                payload = {
                    "roi": roi_info["geometry"],
                    "year": 2023,
                    "threshold": 20,
                    "include_seasonal": True
                }
            elif analysis_type == "lulc":
                url = f"{base_url}/lulc/dynamic-world"
                payload = {
                    "geometry": roi_info["geometry"],
                    "startDate": "2023-01-01",
                    "endDate": "2023-12-31",
                    "confidenceThreshold": 0.3,
                    "scale": 20,
                    "maxPixels": 5e8,
                    "exactComputation": False,
                    "includeMedianVis": False
                }
            else:  # Default to LULC
                url = f"{base_url}/lulc/dynamic-world"
                payload = {
                    "geometry": roi_info["geometry"],
                    "startDate": "2023-01-01",
                    "endDate": "2023-12-31",
                    "confidenceThreshold": 0.5,
                    "scale": 30,
                    "maxPixels": 1e9,
                    "exactComputation": False,
                    "includeMedianVis": False
                }
            
            # Calculate timeout based on area size
            area_km2 = roi_info.get("area_km2", 0)
            if area_km2 > 35000:  # Areas larger than 35k km² are rejected
                logger.warning(f"🚫 AREA TOO LARGE: {area_km2:.0f} km² exceeds 35,000 km² limit")
                return self._create_area_too_large_response(area_km2, analysis_type, roi_info)
            
            # Log warnings for large area analysis
            timeout = self._calculate_timeout_for_area(area_km2, analysis_type)
            self._log_area_warnings(area_km2, analysis_type, timeout)
            
            # Call appropriate GEE service directly
            logger.info(f"📡 Calling {analysis_type.upper()} service directly (area={area_km2:.0f} km²)")
            
            if analysis_type == "ndvi":
                result = self.ndvi_service.analyze_ndvi(
                    geometry=roi_info["geometry"],
                    start_date="2023-06-01",
                    end_date="2023-08-31",
                    cloud_threshold=30,
                    scale=30,
                    max_pixels=int(2e8),
                    include_time_series=False,
                    exact_computation=False
                )
            elif analysis_type == "lst":
                result = self.lst_service.analyze_lst_with_polygon(
                    roi_data=roi_info,
                    start_date="2024-01-01",
                    end_date="2024-08-31",
                    include_uhi=True,
                    include_time_series=False,
                    scale=1000,
                    max_pixels=int(5e7),
                    exact_computation=False
                )
            elif analysis_type == "water":
                water_instance = self.water_service()
                result = water_instance.analyze_water_presence(
                    roi=roi_info["geometry"],
                    year=2023,
                    threshold=20,
                    include_seasonal=True
                )
            elif analysis_type == "lulc":
                result = self.lulc_service.analyze_dynamic_world(
                    geometry=roi_info["geometry"],
                    start_date="2023-01-01",
                    end_date="2023-12-31",
                    confidence_threshold=0.3,
                    scale=20,
                    max_pixels=int(5e8),
                    exact_computation=False,
                    include_median_vis=False
                )
            else:
                # Default to LULC
                result = self.lulc_service.analyze_dynamic_world(
                    geometry=roi_info["geometry"],
                    start_date="2023-01-01",
                    end_date="2023-12-31",
                    confidence_threshold=0.5,
                    scale=30,
                    max_pixels=int(1e9),
                    exact_computation=False,
                    include_median_vis=False
                )
            
            logger.info(f"✅ {analysis_type.upper()} service completed successfully")
            
            # Format and return response
            return self._format_gee_response(result, analysis_type, roi_info)
                
        except Exception as e:
            logger.error(f"❌ Error calling GEE service directly: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
            # Create error response with analysis_data for consistency
            error_response = self._error_response(f"GEE service error: {str(e)}")
            error_response["analysis_data"] = {
                "analysis_type": analysis_type,
                "error": str(e),
                "tile_url": None
            }
            return error_response
    
    def _calculate_timeout_for_area(self, area_km2: float, analysis_type: str) -> int:
        """Calculate appropriate timeout based on area size and analysis type.
        
        Args:
            area_km2: Area in square kilometers
            analysis_type: Type of analysis (water, ndvi, lulc, lst)
            
        Returns:
            Timeout in seconds
        """
        # Base timeouts by analysis type (water is generally fastest)
        base_timeouts = {
            "water": 120,    # Water analysis is typically faster
            "ndvi": 120,     # NDVI with time series takes longer
            "lulc": 150,    # LULC classification is complex
            "lst": 150      # LST with UHI calculation is most complex
        }
        
        base_timeout = base_timeouts.get(analysis_type, 90)
        
        # Scale timeout based on area (simplified since max is 20k km²)
        if area_km2 > 10000:       # Large regions (10-20k km²)
            multiplier = 2.0       # 2x timeout (e.g., 240s for water)
        elif area_km2 > 1000:      # Districts (1-10k km²)
            multiplier = 1.5       # 1.5x timeout (e.g., 180s for water)
        else:                      # Cities (<1k km²)
            multiplier = 1.0       # Base timeout
        
        timeout = int(base_timeout * multiplier)
        
        # Cap at reasonable maximum (20 minutes)
        return min(timeout, 1200)
    
    def _log_area_warnings(self, area_km2: float, analysis_type: str, timeout: int) -> None:
        """Log appropriate warnings and information for area analysis.
        
        Args:
            area_km2: Area in square kilometers
            analysis_type: Type of analysis
            timeout: Calculated timeout
        """
        # Since we now have a 20k km² limit, simplify the warnings
        if area_km2 > 10000:  # Large regions (10-20k km²)
            logger.info(f"📍 LARGE REGIONAL ANALYSIS: {area_km2:.0f} km² {analysis_type.upper()} analysis")
            logger.info(f"⏱️  Expected processing time: {timeout} seconds")
        elif area_km2 > 1000:  # Medium regions (1-10k km²)
            logger.info(f"📊 REGIONAL ANALYSIS: {area_km2:.0f} km² {analysis_type.upper()} analysis")
            logger.info(f"⏱️  Using {timeout}s timeout")
        else:  # Cities and smaller (<1k km²)
            logger.info(f"🏙️  CITY ANALYSIS: {area_km2:.0f} km² {analysis_type.upper()} analysis")
            logger.info(f"⏱️  Using standard {timeout}s timeout")
    
    def _create_area_too_large_response(
        self, 
        area_km2: float, 
        analysis_type: str, 
        roi_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create response for areas that are too large to analyze.
        
        Args:
            area_km2: Area in square kilometers
            analysis_type: Type of analysis requested
            roi_info: ROI information
            
        Returns:
            Error response with helpful suggestions
        """
        location_name = roi_info.get("display_name", "the selected area")
        
        # Create user-friendly error message with suggestions
        error_message = (
            f"🚫 **Area Too Large for Analysis**\n\n"
            f"The requested area ({location_name}) covers {area_km2:,.0f} km², "
            f"which exceeds our 35,000 km² processing limit.\n\n"
            f"**Why this limit exists:**\n"
            f"• Large areas require 15-30+ minutes to process\n"
            f"• High computational cost and resource usage\n"
            f"• Risk of timeouts and incomplete results\n\n"
            f"**🎯 Suggested alternatives:**\n"
            f"• Try a specific **city** or **district** instead\n"
            f"• Choose a **smaller region** within the area\n"
            f"• Focus on a **particular zone** of interest\n\n"
            f"**Examples of good alternatives:**\n"
            f"• Instead of 'Madhya Pradesh' → try 'Bhopal' or 'Indore'\n"
            f"• Instead of 'Rajasthan' → try 'Jaipur' or 'Jodhpur'\n"
            f"• Instead of 'Uttar Pradesh' → try 'Lucknow' or 'Kanpur'"
        )
        
        return {
            "success": False,
            "analysis": error_message,
            "roi": roi_info,
            "summary": f"Analysis not performed: {location_name} ({area_km2:,.0f} km²) exceeds size limit",
            "evidence": [f"area_too_large:{area_km2:.0f}km2"],
            "metadata": {
                "processing_time": 0.1,
                "service_used": "size_validator",
                "area_km2": area_km2,
                "limit_km2": 35000,
                "analysis_type": analysis_type
            },
            "sources": [],
            "confidence": 1.0,
            "analysis_data": {
                "analysis_type": analysis_type,
                "error": f"Area too large: {area_km2:,.0f} km² > 35,000 km² limit",
                "tile_url": None,
                "area_km2": area_km2,
                "limit_exceeded": True
            },
            "debug": {
                "area_check": f"REJECTED: {area_km2:.0f} km² > 35,000 km² limit",
                "location": location_name,
                "suggested_action": "Try a smaller, more specific location"
            }
        }
    
    def _dispatch_rag(
        self, 
        query: str, 
        intent_result: IntentResult, 
        location_result: LocationParseResult,
        rag_session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Dispatch to RAG service for document-based question answering.
        
        Args:
            query: Original user query
            intent_result: Intent classification result
            location_result: Location parsing result
            rag_session_id: RAG session ID for document context
            
        Returns:
            RAG service response with grounded answer and sources
        """
        logger.info("📚 Dispatching to RAG service for document-based analysis")
        
        if not self.rag_service_available or not self.rag_store:
            # Fallback response when RAG service is not available
            location_names = [entity.matched_name for entity in location_result.entities]
            location_text = f"related to {', '.join(location_names)} " if location_names else ""
            
            return {
                "analysis": (
                    f"📚 RAG Analysis {location_text}\n"
                    f"{'=' * 50}\n"
                    f"⚠️ RAG service is currently unavailable\n"
                    f"📝 Query: {query}\n"
                    f"📍 Locations: {', '.join(location_names) if location_names else 'None detected'}\n\n"
                    f"💡 The RAG service provides:\n"
                    f"   • Document-based knowledge retrieval\n"
                    f"   • Policy and regulation information\n"
                    f"   • Historical data and context\n"
                    f"   • Factual question answering\n\n"
                    f"🔧 Please ensure RAG store is initialized."
                ),
                "roi": None,
                "evidence": ["rag_service:unavailable"],
                "sources": [],
                "confidence": 0.0
            }
        
        try:
            # Call RAG store directly (no HTTP)
            import asyncio
            
            # Create an event loop if needed
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Query the RAG store
            response = loop.run_until_complete(
                self.rag_store.query(
                    query=query,
                    session_id=rag_session_id,
                    k=5
                )
            )
            
            logger.info(f"✅ RAG service response received with confidence: {response.get('confidence', 0.0)}")
            return response
            
        except Exception as e:
            logger.error(f"❌ Error calling RAG service: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
            # Fallback to search service on error
            logger.info("⚠️  Falling back to search service due to RAG error")
            return self._dispatch_search(query, intent_result, location_result)
    
    def _dispatch_search(
        self, 
        query: str, 
        intent_result: IntentResult, 
        location_result: LocationParseResult
    ) -> Dict[str, Any]:
        """Dispatch to Search service (direct imports, no HTTP).
        
        Args:
            query: Original user query
            intent_result: Intent classification result
            location_result: Location parsing result
            
        Returns:
            Search service response
        """
        logger.info("🔍 Dispatching to Search service (direct)")
        
        if not self.search_services_available:
            logger.warning("⚠️  Search services not available, returning fallback")
            return self._fallback_search_response(query, location_result)
        
        try:
            # Convert location entities to dict format
            locations_data = []
            if location_result.entities:
                locations_data = [
                    {
                        "matched_name": entity.matched_name,
                        "type": entity.type,
                        "confidence": entity.confidence
                    }
                    for entity in location_result.entities
                ]
            
            # Use Nominatim for location resolution
            location_info = None
            if locations_data:
                primary_location = locations_data[0]
                logger.info(f"🔍 Resolving location: {primary_location['matched_name']}")
                location_info = self.nominatim_client.search_location(
                    primary_location["matched_name"],
                    primary_location.get("type", "city")
                )
            
            # Use ResultProcessor to generate analysis
            logger.info(f"📝 Generating search-based analysis")
            
            # Create simple analysis from location data
            if location_info:
                analysis = f"📍 Location Analysis for {location_info.get('display_name', 'Unknown')}\n\n"
                analysis += f"Coordinates: {location_info.get('coordinates', {})}\n"
                if location_info.get("area_km2"):
                    analysis += f"Area: {location_info['area_km2']:.2f} km²\n"
                analysis += f"\n💡 For detailed geospatial analysis, try queries like:\n"
                analysis += f"- 'Analyze NDVI for {primary_location['matched_name']}'\n"
                analysis += f"- 'Show land surface temperature in {primary_location['matched_name']}'\n"
            else:
                analysis = f"🔍 Search analysis for: {query}\n\n"
                analysis += "No specific location data available. Try adding a location to your query."
            
            return {
                "analysis": analysis,
                "roi": location_info.get("polygon_geometry") if location_info else None,
                "evidence": ["search_service:direct_nominatim"],
                "sources": [],
                "confidence": 0.7 if location_info else 0.3
            }
            
        except Exception as e:
            logger.error(f"❌ Error calling search service: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return self._fallback_search_response(query, location_result)
    
    def _format_gee_response(
        self, 
        service_result: Dict[str, Any], 
        analysis_type: str, 
        roi_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Format GEE service response for consistent output.
        
        Args:
            service_result: Raw service result
            analysis_type: Type of analysis performed
            roi_info: ROI information used
            
        Returns:
            Formatted response dictionary
        """
        # Normalize analysis_data across services for downstream consumers/tests
        analysis_data: Dict[str, Any] = {"analysis_type": analysis_type}
        if analysis_type == "water":
            stats = service_result.get("mapStats", {})
            analysis_data.update({
                "water_percentage": stats.get("water_percentage"),
                "non_water_percentage": stats.get("non_water_percentage"),
                "tile_url": service_result.get("urlFormat")
            })
        elif analysis_type == "ndvi":
            stats = service_result.get("mapStats", {}).get("ndvi_statistics", {})
            analysis_data.update({
                "mean_ndvi": stats.get("mean"),
                "min_ndvi": stats.get("min"),
                "max_ndvi": stats.get("max"),
                "tile_url": service_result.get("urlFormat")
            })
        elif analysis_type == "lulc":
            stats = service_result.get("mapStats", {})
            analysis_data.update({
                "dominant_class": stats.get("dominant_class"),
                "class_percentages": stats.get("class_percentages"),
                "tile_url": service_result.get("urlFormat")
            })
        elif analysis_type == "lst":
            lst_stats = service_result.get("lst_stats", {})
            analysis_data.update({
                "mean_lst": lst_stats.get("LST_mean"),
                "uhi_intensity": service_result.get("uhi_intensity"),
                "tile_url": service_result.get("urlFormat")
            })
        else:
            analysis_data["tile_url"] = service_result.get("urlFormat")

        analysis_text = service_result.get("extraDescription", f"{analysis_type.upper()} analysis completed")
        
        # Create ROI feature
        roi_feature = None
        if roi_info.get("geometry"):
            roi_feature = {
                "type": "Feature",
                "properties": {
                    "name": f"{analysis_type.upper()} Analysis ROI",
                    "area_km2": roi_info.get("area_km2", 0),
                    "analysis_type": analysis_type,
                    "processing_time": service_result.get("processing_time_seconds", 0)
                },
                "geometry": roi_info["geometry"]
            }
        
        return {
            "analysis": analysis_text,
            "roi": roi_feature,
            "evidence": [f"{analysis_type}_service:success"],
            "service_result": service_result,
            "analysis_data": analysis_data,
            "processing_time": service_result.get("processing_time_seconds", 0)
        }
    
    def _fallback_search_response(
        self, 
        query: str, 
        location_result: LocationParseResult
    ) -> Dict[str, Any]:
        """Generate fallback response when search service fails.
        
        Args:
            query: Original query
            location_result: Location parsing result
            
        Returns:
            Fallback response dictionary
        """
        location_names = [entity.matched_name for entity in location_result.entities]
        location_text = f"for {', '.join(location_names)} " if location_names else ""
        
        return {
            "analysis": (
                f"🔍 Search Analysis {location_text}\n"
                f"{'=' * 50}\n"
                f"⚠️ Search service temporarily unavailable\n"
                f"📝 Query: {query}\n"
                f"📍 Locations: {', '.join(location_names) if location_names else 'None detected'}\n\n"
                f"🔧 Please ensure the search service is running."
            ),
            "roi": None,
            "evidence": ["search_service:fallback"],
            "sources": [],
            "confidence": 0.0
        }
    
    def _error_response(self, error_message: str) -> Dict[str, Any]:
        """Generate error response.
        
        Args:
            error_message: Error description
            
        Returns:
            Error response dictionary
        """
        return {
            "analysis": f"❌ Service Error: {error_message}",
            "roi": None,
            "evidence": ["service_dispatcher:error"],
            "sources": [],
            "confidence": 0.0,
            "error": error_message
        }
