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
    
    def __init__(self):
        """Initialize the ServiceDispatcher."""
        self.services_initialized = False
        self._init_services()
    
    def _init_services(self):
        """Initialize service connections and imports."""
        try:
            # Import services - these should already exist
            from app.search_service.integration_client import call_search_service_for_analysis
            self.search_service = call_search_service_for_analysis
            
            # Check if GEE services are available
            try:
                from app.gee_service.services.ndvi_service import NDVIService
                from app.gee_service.services.lst_service import LSTService
                self.ndvi_service = NDVIService
                self.lst_service = LSTService
                self.gee_services_available = True
                logger.info("GEE services available for direct integration")
            except ImportError as e:
                logger.warning(f"GEE services not available: {e}")
                self.gee_services_available = False
            
            # RAG service (planned, not yet implemented)
            self.rag_service_available = False
            
            self.services_initialized = True
            logger.info("Service dispatcher initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize services: {e}")
            self.services_initialized = False
    
    def dispatch(
        self, 
        query: str, 
        intent_result: IntentResult, 
        location_result: LocationParseResult
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
            
            if service_type == ServiceType.GEE or service_type_value == "GEE":
                return self._dispatch_gee(query, intent_result, location_result)
            elif service_type == ServiceType.RAG or service_type_value == "RAG":
                return self._dispatch_rag(query, intent_result, location_result)
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
        
        # Import ROI handler for geometry resolution
        try:
            from app.services.gee.roi_handler import ROIHandler
            roi_handler = ROIHandler()
            
            # Get ROI geometry
            roi_info = None
            if locations_legacy:
                roi_info = roi_handler.extract_roi_from_locations(locations_legacy)
            elif location_result.roi_geometry:
                # Use already resolved geometry
                roi_info = {
                    "geometry": location_result.roi_geometry,
                    "area_km2": location_result.primary_location.area_km2 if location_result.primary_location else 0,
                    "polygon_geometry": location_result.roi_geometry
                }
            
            if not roi_info:
                # Fallback to default ROI
                roi_info = roi_handler.get_default_roi()
            
            # Route to specific GEE service based on sub-intent
            analysis_type = intent_result.analysis_type
            
            # Always use HTTP service calls for reliability
            return self._call_gee_http_service(analysis_type, roi_info, query)
                
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
    
    def _call_gee_http_service(
        self, 
        analysis_type: str, 
        roi_info: Dict[str, Any], 
        query: str
    ) -> Dict[str, Any]:
        """Call GEE service via HTTP.
        
        Args:
            analysis_type: Type of analysis (ndvi, lulc, lst, etc.)
            roi_info: ROI information dictionary
            query: Original query for context
            
        Returns:
            GEE HTTP service response
        """
        import requests
        
        try:
            # Determine service endpoint
            if analysis_type == "ndvi":
                url = "http://localhost:8000/ndvi/vegetation-analysis"
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
                url = "http://localhost:8000/lst/land-surface-temperature"
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
                url = "http://localhost:8000/water/analyze"
                payload = {
                    "roi": roi_info["geometry"],
                    "year": 2023,
                    "threshold": 20,
                    "include_seasonal": True
                }
            elif analysis_type == "lulc":
                url = "http://localhost:8000/lulc/dynamic-world"
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
                url = "http://localhost:8000/lulc/dynamic-world"
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
            
            response = requests.post(url, json=payload, timeout=120)
            response.raise_for_status()
            result = response.json()
            
            # GEE services return data directly, not wrapped in success/error
            return self._format_gee_response(result, analysis_type, roi_info)
                
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP error calling GEE service: {e}")
            # Create a basic error response with analysis_data for consistency
            error_response = self._error_response(f"GEE service connection failed: {str(e)}")
            error_response["analysis_data"] = {
                "analysis_type": analysis_type,
                "error": str(e),
                "tile_url": None
            }
            return error_response
        except Exception as e:
            logger.error(f"Error calling GEE HTTP service: {e}")
            # Create a basic error response with analysis_data for consistency
            error_response = self._error_response(f"GEE service error: {str(e)}")
            error_response["analysis_data"] = {
                "analysis_type": analysis_type,
                "error": str(e),
                "tile_url": None
            }
            return error_response
    
    def _dispatch_rag(
        self, 
        query: str, 
        intent_result: IntentResult, 
        location_result: LocationParseResult
    ) -> Dict[str, Any]:
        """Dispatch to RAG service (placeholder - not yet implemented).
        
        Args:
            query: Original user query
            intent_result: Intent classification result
            location_result: Location parsing result
            
        Returns:
            RAG service response (mocked for now)
        """
        logger.info("Dispatching to RAG service (not yet implemented)")
        
        # Extract location names for context
        location_names = [entity.matched_name for entity in location_result.entities]
        location_text = f"related to {', '.join(location_names)} " if location_names else ""
        
        return {
            "analysis": (
                f"📚 RAG Analysis {location_text}\n"
                f"{'=' * 50}\n"
                f"⚠️ RAG service not yet implemented\n"
                f"📝 Query: {query}\n"
                f"📍 Locations: {', '.join(location_names) if location_names else 'None detected'}\n\n"
                f"💡 This service will provide:\n"
                f"   • Document-based knowledge retrieval\n"
                f"   • Policy and regulation information\n"
                f"   • Historical data and context\n"
                f"   • Factual question answering\n\n"
                f"🔧 RAG service implementation is planned for future release."
            ),
            "roi": None,
            "evidence": ["rag_service:not_implemented"],
            "sources": [],
            "confidence": 0.0
        }
    
    def _dispatch_search(
        self, 
        query: str, 
        intent_result: IntentResult, 
        location_result: LocationParseResult
    ) -> Dict[str, Any]:
        """Dispatch to Search service.
        
        Args:
            query: Original user query
            intent_result: Intent classification result
            location_result: Location parsing result
            
        Returns:
            Search service response
        """
        logger.info("Dispatching to Search service")
        
        try:
            # Convert location entities to legacy format
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
            
            # Call search service
            result = self.search_service(query, locations_legacy, intent_result.analysis_type)
            
            return {
                "analysis": result.get("analysis", "Search analysis completed"),
                "roi": result.get("roi"),
                "evidence": result.get("evidence", []),
                "sources": result.get("sources", []),
                "confidence": result.get("confidence", 0.0)
            }
            
        except Exception as e:
            logger.error(f"Error calling search service: {e}")
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
