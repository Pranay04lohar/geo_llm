"""
Result Formatter - Format service results into consistent output.

This module provides consistent formatting for all service responses,
ensuring a unified output format regardless of the underlying service used.
"""

import time
import logging
from typing import Dict, Any, List, Optional

try:
    from ..models.intent import IntentResult
    from ..models.location import LocationParseResult
except ImportError:
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent.parent.parent.parent))
    
    from app.services.core_llm_agent.models.intent import IntentResult
    from app.services.core_llm_agent.models.location import LocationParseResult

logger = logging.getLogger(__name__)


class ResultFormatter:
    """Formatter for consistent service result output."""
    
    def __init__(self):
        """Initialize the ResultFormatter."""
        pass
    
    def format_final_result(
        self,
        query: str,
        intent_result: IntentResult,
        location_result: LocationParseResult,
        service_response: Dict[str, Any],
        total_processing_time: float
    ) -> Dict[str, Any]:
        """Format the final result for the agent contract.
        
        Args:
            query: Original user query
            intent_result: Intent classification result
            location_result: Location parsing result
            service_response: Response from the dispatched service
            total_processing_time: Total processing time for the request
            
        Returns:
            Final formatted result matching the agent contract
        """
        try:
            # Extract core components
            analysis = service_response.get("analysis", "Analysis completed")
            roi = service_response.get("roi")
            
            # Enhance analysis with metadata if needed
            enhanced_analysis = self._enhance_analysis(
                analysis, query, intent_result, location_result, total_processing_time
            )
            
            # Format ROI if needed
            formatted_roi = self._format_roi(roi, location_result)
            
            # Build evidence trail
            evidence = self._build_evidence(
                intent_result, location_result, service_response
            )
            
            # Create final result
            # Build natural-language summary from normalized analysis_data if present
            nl_summary = self._build_natural_language_summary(intent_result, service_response)
            logger.info(f"Generated natural language summary: {nl_summary[:100]}...")  # Log first 100 chars

            result = {
                "analysis": enhanced_analysis,
                "roi": formatted_roi,
                "summary": nl_summary,
                "evidence": evidence,  # Add evidence at top level for tests
                "metadata": {
                    "query": query,
                    "service_type": intent_result.service_type.value if hasattr(intent_result.service_type, 'value') else str(intent_result.service_type),
                    "analysis_type": intent_result.analysis_type,
                    "locations_found": len(location_result.entities),
                    "processing_time": total_processing_time,
                    "intent_confidence": intent_result.confidence,
                    "success": True,
                    "evidence": evidence
                }
            }
            
            # Add optional fields if available
            if "sources" in service_response:
                result["sources"] = service_response["sources"]

            if "confidence" in service_response:
                result["confidence"] = service_response["confidence"]

            # Surface analysis_data for consumers/tests
            if "analysis_data" in service_response:
                result["analysis_data"] = service_response["analysis_data"]

            if "service_result" in service_response:
                result["service_result"] = service_response["service_result"]
            
            service_type_str = intent_result.service_type.value if hasattr(intent_result.service_type, 'value') else str(intent_result.service_type)
            logger.info(f"Formatted final result for {service_type_str} service")
            return result
            
        except Exception as e:
            logger.error(f"Error formatting final result: {e}")
            return self._error_result(query, str(e), total_processing_time)

    def _build_natural_language_summary(self, intent_result: IntentResult, service_response: Dict[str, Any]) -> str:
        """Create a concise natural language summary based on analysis_data, handling errors gracefully."""
        try:
            analysis_type = getattr(intent_result, 'analysis_type', None)
            if hasattr(analysis_type, 'value'):
                analysis_type = analysis_type.value
            analysis_type = (analysis_type or '').lower()

            data = service_response.get("analysis_data", {})

            # Check if there's an error in the data
            if data.get("error"):
                error_msg = data.get("error", "Unknown error")
                return f"Sorry, I encountered an issue while processing your request: {error_msg}. Please try again later."

            # Generate meaningful summaries based on analysis type
            if analysis_type == "water":
                wp = data.get("water_percentage")
                if wp is not None:
                    try:
                        wp_float = float(wp)
                        if wp_float > 50:
                            return f"The area shows extensive water coverage at {wp_float:.1f}%, indicating significant water bodies, lakes, or coastal regions."
                        elif wp_float > 20:
                            return f"Moderate water coverage of {wp_float:.1f}% was found, suggesting mixed land-water usage."
                        else:
                            return f"Low water coverage at {wp_float:.1f}% indicates mostly dry land with limited water features."
                    except (ValueError, TypeError):
                        return f"Water coverage analysis shows {wp}% in the selected area."
                else:
                    return "Water coverage analysis was performed. Check the detailed results for specific percentages."

            elif analysis_type == "ndvi":
                mean_ndvi = data.get("mean_ndvi")
                if mean_ndvi is not None:
                    try:
                        ndvi_float = float(mean_ndvi)
                        if ndvi_float > 0.6:
                            health = "excellent vegetation health"
                        elif ndvi_float > 0.4:
                            health = "good vegetation health"
                        elif ndvi_float > 0.2:
                            health = "moderate vegetation health"
                        else:
                            health = "sparse or stressed vegetation"
                        return f"Vegetation analysis shows {health} with an average NDVI of {ndvi_float:.3f}."
                    except (ValueError, TypeError):
                        return f"Vegetation health analysis completed with average NDVI of {mean_ndvi}."
                else:
                    return "Vegetation health analysis was completed. Review the detailed results for NDVI values."

            elif analysis_type == "lulc":
                dom = data.get("dominant_class")
                if dom:
                    return f"Land cover analysis reveals {dom} as the dominant land use type in the selected area."
                else:
                    return "Land cover classification analysis was completed. Check the detailed results for land use distribution."

            elif analysis_type == "lst":
                mean_lst = data.get("mean_lst")
                uhi = data.get("uhi_intensity")
                if mean_lst is not None:
                    try:
                        lst_float = float(mean_lst)
                        temp_desc = f"hot" if lst_float > 40 else f"warm" if lst_float > 30 else f"moderate" if lst_float > 20 else "cool"
                        summary = f"The area has a {temp_desc} surface temperature averaging {lst_float:.1f}°C."
                        if uhi is not None:
                            try:
                                uhi_float = float(uhi)
                                if uhi_float > 5:
                                    summary += f" A significant urban heat island effect of {uhi_float:.1f}°C was detected."
                                elif uhi_float > 2:
                                    summary += f" Moderate urban heat island effect of {uhi_float:.1f}°C observed."
                                else:
                                    summary += " Minimal urban heat island effect detected."
                            except (ValueError, TypeError):
                                summary += f" Urban heat island intensity measured at {uhi}°C."
                        return summary
                    except (ValueError, TypeError):
                        return f"Surface temperature analysis shows average LST of {mean_lst}°C."
                else:
                    return "Surface temperature analysis was completed. Check detailed results for temperature metrics."

            # Default summary for unknown analysis types
            return f"{analysis_type.title() if analysis_type else 'Geospatial'} analysis was completed successfully."

        except Exception as e:
            logger.warning(f"Error building natural language summary: {e}")
            return "Analysis completed. See details for metrics and map visualization."
    
    def _enhance_analysis(
        self,
        analysis: str,
        query: str,
        intent_result: IntentResult,
        location_result: LocationParseResult,
        processing_time: float
    ) -> str:
        """Enhance analysis text with metadata and context.
        
        Args:
            analysis: Original analysis text
            query: Original query
            intent_result: Intent classification result
            location_result: Location parsing result
            processing_time: Total processing time
            
        Returns:
            Enhanced analysis text
        """
        # If analysis is already comprehensive, return as-is
        if len(analysis) > 500 and "=" in analysis:
            return analysis
        
        # Add header if missing
        if not analysis.startswith("🌍") and not analysis.startswith("🌿") and not analysis.startswith("🌡️"):
            header = f"🔍 Analysis Results\n{'=' * 50}\n"
            
            # Add query context
            header += f"📝 Query: {query}\n"
            
            # Add location context
            if location_result.entities:
                location_names = [entity.matched_name for entity in location_result.entities]
                header += f"📍 Locations: {', '.join(location_names)}\n"
            
            # Add service context
            service_type_str = intent_result.service_type.value if hasattr(intent_result.service_type, 'value') else str(intent_result.service_type)
            header += f"🔧 Service: {service_type_str}"
            if intent_result.gee_sub_intent:
                gee_sub_str = intent_result.gee_sub_intent.value if hasattr(intent_result.gee_sub_intent, 'value') else str(intent_result.gee_sub_intent)
                header += f" → {gee_sub_str}"
            header += f" (confidence: {intent_result.confidence:.2f})\n"
            
            # Add timing
            header += f"⏱️ Processing time: {processing_time:.1f}s\n\n"
            
            return header + analysis
        
        return analysis
    
    def _format_roi(
        self, 
        roi: Optional[Dict[str, Any]], 
        location_result: LocationParseResult
    ) -> Optional[Dict[str, Any]]:
        """Format ROI for consistent output.
        
        Args:
            roi: ROI from service response
            location_result: Location parsing result
            
        Returns:
            Formatted ROI or None
        """
        if roi:
            # ROI already formatted by service
            return roi
        
        # Try to create ROI from location result
        if location_result.primary_location and location_result.roi_geometry:
            return {
                "type": "Feature",
                "properties": {
                    "name": f"Analysis ROI - {location_result.primary_location.display_name}",
                    "area_km2": location_result.primary_location.area_km2,
                    "source": location_result.roi_source,
                    "center": location_result.primary_location.center
                },
                "geometry": location_result.roi_geometry
            }
        
        return None
    
    def _build_evidence(
        self,
        intent_result: IntentResult,
        location_result: LocationParseResult,
        service_response: Dict[str, Any]
    ) -> List[str]:
        """Build evidence trail for debugging and transparency.
        
        Args:
            intent_result: Intent classification result
            location_result: Location parsing result
            service_response: Service response
            
        Returns:
            List of evidence strings
        """
        evidence = []
        
        # Location parsing evidence
        if location_result.success:
            if location_result.entities:
                evidence.append(f"location_parser:found_{len(location_result.entities)}_entities")
                if location_result.resolved_locations:
                    evidence.append(f"location_parser:resolved_{len(location_result.resolved_locations)}_locations")
            else:
                evidence.append("location_parser:no_entities_found")
        else:
            evidence.append("location_parser:failed")
        
        # Intent classification evidence
        if intent_result.success:
            service_type_str = intent_result.service_type.value if hasattr(intent_result.service_type, 'value') else str(intent_result.service_type)
            evidence.append(f"intent_classifier:{service_type_str.lower()}_selected")
            if intent_result.gee_sub_intent:
                gee_sub_str = intent_result.gee_sub_intent.value if hasattr(intent_result.gee_sub_intent, 'value') else str(intent_result.gee_sub_intent)
                evidence.append(f"intent_classifier:{gee_sub_str.lower()}_subintent")
        else:
            evidence.append("intent_classifier:failed")
        
        # Service evidence
        service_evidence = service_response.get("evidence", [])
        logger.info(f"DEBUG - Service evidence: {service_evidence}")
        evidence.extend(service_evidence)
        logger.info(f"DEBUG - Final evidence after adding service evidence: {evidence}")
        
        # Processing time evidence
        if intent_result.processing_time > 0:
            evidence.append(f"intent_processing_time_{intent_result.processing_time:.1f}s")
        if location_result.processing_time > 0:
            evidence.append(f"location_processing_time_{location_result.processing_time:.1f}s")
        
        return evidence
    
    def _error_result(
        self, 
        query: str, 
        error_message: str, 
        processing_time: float
    ) -> Dict[str, Any]:
        """Create error result in consistent format.
        
        Args:
            query: Original query
            error_message: Error description
            processing_time: Processing time before error
            
        Returns:
            Error result dictionary
        """
        return {
            "analysis": (
                f"❌ Processing Error\n"
                f"{'=' * 50}\n"
                f"📝 Query: {query}\n"
                f"⚠️ Error: {error_message}\n"
                f"⏱️ Processing time: {processing_time:.1f}s\n\n"
                f"🔧 Please try again or contact support if the issue persists."
            ),
            "roi": None,
            "metadata": {
                "query": query,
                "service_type": "error",
                "analysis_type": "error",
                "locations_found": 0,
                "processing_time": processing_time,
                "intent_confidence": 0.0,
                "success": False,
                "evidence": ["result_formatter:error"],
                "error": error_message
            }
        }
    
    def format_legacy_result(
        self,
        result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Format result for backward compatibility with legacy format.
        
        Args:
            result: Modern formatted result
            
        Returns:
            Legacy format result
        """
        # Extract only the required fields for the legacy contract
        return {
            "analysis": result.get("analysis", ""),
            "roi": result.get("roi")
        }
    
    def format_debug_result(
        self,
        query: str,
        intent_result: IntentResult,
        location_result: LocationParseResult,
        service_response: Dict[str, Any],
        total_processing_time: float
    ) -> Dict[str, Any]:
        """Format detailed debug result with all intermediate data.
        
        Args:
            query: Original user query
            intent_result: Intent classification result
            location_result: Location parsing result
            service_response: Response from the dispatched service
            total_processing_time: Total processing time
            
        Returns:
            Detailed debug result
        """
        regular_result = self.format_final_result(
            query, intent_result, location_result, service_response, total_processing_time
        )
        
        # Add debug information
        regular_result["debug"] = {
            "intent_classification": {
                "service_type": intent_result.service_type.value if hasattr(intent_result.service_type, 'value') else str(intent_result.service_type),
                "confidence": intent_result.confidence,
                "gee_sub_intent": intent_result.gee_sub_intent.value if intent_result.gee_sub_intent and hasattr(intent_result.gee_sub_intent, 'value') else str(intent_result.gee_sub_intent) if intent_result.gee_sub_intent else None,
                "gee_confidence": intent_result.gee_confidence,
                "reasoning": intent_result.reasoning,
                "model_used": intent_result.model_used,
                "processing_time": intent_result.processing_time,
                "raw_response": intent_result.raw_response
            },
            "location_parsing": {
                "entities_found": len(location_result.entities),
                "entities": [
                    {
                        "name": entity.matched_name,
                        "type": entity.type,
                        "confidence": entity.confidence
                    }
                    for entity in location_result.entities
                ],
                "resolved_count": len(location_result.resolved_locations),
                "roi_source": location_result.roi_source,
                "processing_time": location_result.processing_time,
                "success": location_result.success
            },
            "service_response": service_response,
            "timing": {
                "total_processing_time": total_processing_time,
                "intent_time": intent_result.processing_time,
                "location_time": location_result.processing_time,
                "service_time": service_response.get("processing_time", 0)
            }
        }
        
        return regular_result
