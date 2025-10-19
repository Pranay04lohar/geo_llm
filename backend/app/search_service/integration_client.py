"""
Integration client for connecting Search API Service to core LLM agent.

This module provides functions to call the Search API Service from the
core LLM agent, replacing the mocked websearch_tool_node.
"""

import requests
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class SearchServiceClient:
    """Client for calling Search API Service from core LLM agent."""
    
    def __init__(self, base_url: str = None):
        import os
        self.base_url = base_url or os.getenv("SERVICE_BASE_URL", "http://localhost:8000")
        self.timeout = 60  # Increased timeout for enhanced analysis
    
    def get_location_data(
        self, 
        location_name: str, 
        location_type: str = "city"
    ) -> Optional[Dict[str, Any]]:
        """
        Get location data from Search API Service.
        
        Args:
            location_name: Name of the location
            location_type: Type of location (city, state, country)
            
        Returns:
            Location data dictionary or None if failed
        """
        try:
            response = requests.post(
                f"{self.base_url}/search/location-data",
                json={
                    "location_name": location_name,
                    "location_type": location_type
                },
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success", False):
                    return data
                else:
                    logger.warning(f"Location resolution failed: {data.get('error', 'Unknown error')}")
                    return None
            else:
                logger.error(f"Location resolution HTTP error: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error calling location resolution: {e}")
            return None
    
    def get_environmental_context(
        self, 
        location: str, 
        analysis_type: str, 
        query: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get environmental context from Search API Service.
        
        Args:
            location: Location name
            analysis_type: Type of analysis (ndvi, lulc, etc.)
            query: Base query
            
        Returns:
            Environmental context data or None if failed
        """
        try:
            response = requests.post(
                f"{self.base_url}/search/environmental-context",
                json={
                    "location": location,
                    "analysis_type": analysis_type,
                    "query": query
                },
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success", False):
                    return data
                else:
                    logger.warning(f"Environmental context failed: {data.get('error', 'Unknown error')}")
                    return None
            else:
                logger.error(f"Environmental context HTTP error: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error calling environmental context: {e}")
            return None
    
    def get_complete_analysis(
        self, 
        query: str, 
        locations: List[Dict[str, Any]], 
        analysis_type: str = "ndvi"
    ) -> Optional[Dict[str, Any]]:
        """
        Get complete analysis from Search API Service.
        
        Args:
            query: User query
            locations: List of detected locations
            analysis_type: Type of analysis
            
        Returns:
            Complete analysis data or None if failed
        """
        try:
            response = requests.post(
                f"{self.base_url}/search/complete-analysis",
                json={
                    "query": query,
                    "locations": locations,
                    "analysis_type": analysis_type
                },
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success", False):
                    return data
                else:
                    logger.warning(f"Complete analysis failed: {data.get('error', 'Unknown error')}")
                    return None
            else:
                logger.error(f"Complete analysis HTTP error: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error calling complete analysis: {e}")
            return None
    
    def get_enhanced_analysis(
        self, 
        query: str, 
        locations: List[Dict[str, Any]], 
        analysis_type: str = "ndvi"
    ) -> Optional[Dict[str, Any]]:
        """
        Get enhanced analysis with data extraction and validation.
        
        Args:
            query: User query string
            locations: List of location dictionaries
            analysis_type: Type of analysis to perform
            
        Returns:
            Enhanced analysis data or None if failed
        """
        try:
            response = requests.post(
                f"{self.base_url}/search/enhanced-analysis",
                json={
                    "query": query,
                    "locations": locations,
                    "analysis_type": analysis_type
                },
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Enhanced analysis failed with status {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error calling enhanced analysis: {e}")
            return None

    def health_check(self) -> bool:
        """Check if Search API Service is healthy."""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False

# Global client instance
search_client = SearchServiceClient()

def call_search_service_for_analysis(
    query: str, 
    locations: List[Dict[str, Any]], 
    analysis_type: str = "ndvi"
) -> Dict[str, Any]:
    """
    Call Search API Service for complete analysis.
    
    This function is designed to be used in the core LLM agent's
    websearch_tool_node to replace the mock implementation.
    
    Args:
        query: User query
        locations: List of detected locations
        analysis_type: Type of analysis
        
    Returns:
        Dictionary with analysis, roi, and evidence
    """
    try:
        # Check if service is available
        if not search_client.health_check():
            logger.warning("Search API Service not available, using fallback")
            return _fallback_analysis(query, locations, analysis_type)
        
        # Try enhanced analysis first
        logger.info(f"DEBUG - Calling enhanced analysis with query: '{query}', analysis_type: '{analysis_type}'")
        analysis_data = search_client.get_enhanced_analysis(query, locations, analysis_type)
        
        if analysis_data and analysis_data.get("success", False):
            return {
                "analysis": analysis_data.get("analysis", "Analysis generation failed"),
                "roi": analysis_data.get("roi"),
                "evidence": ["search_service:enhanced_analysis_success"],
                "sources": analysis_data.get("sources", []),
                "confidence": analysis_data.get("confidence", 0.0),
                "structured_data": analysis_data.get("structured_data", {}),
                "data_quality": analysis_data.get("data_quality", {}),
                "extracted_metrics_count": analysis_data.get("extracted_metrics_count", 0)
            }
        else:
            # Fallback to basic analysis if enhanced fails
            logger.warning("Enhanced analysis failed, falling back to basic analysis")
            analysis_data = search_client.get_complete_analysis(query, locations, analysis_type)
            
            if analysis_data:
                return {
                    "analysis": analysis_data.get("analysis", "Analysis generation failed"),
                    "roi": analysis_data.get("roi"),
                    "evidence": ["search_service:complete_analysis_success"],
                    "sources": analysis_data.get("sources", []),
                    "confidence": analysis_data.get("confidence", 0.0)
                }
            else:
                logger.warning("Search API Service returned no data, using fallback")
                return _fallback_analysis(query, locations, analysis_type)
            
    except Exception as e:
        logger.error(f"Error calling Search API Service: {e}")
        return _fallback_analysis(query, locations, analysis_type)

def _fallback_analysis(
    query: str, 
    locations: List[Dict[str, Any]], 
    analysis_type: str
) -> Dict[str, Any]:
    """Fallback analysis when Search API Service is unavailable."""
    
    location_names = [loc.get("matched_name", "Unknown") for loc in locations] if locations else ["Unknown"]
    location_text = f"for {', '.join(location_names)}" if location_names else ""
    
    analysis = (
        f"🔍 Search Analysis {location_text}\n"
        f"{'=' * 50}\n"
        f"⚠️ Search API Service temporarily unavailable\n"
        f"📝 Query: {query}\n"
        f"🎯 Analysis Type: {analysis_type}\n"
        f"📍 Locations: {', '.join(location_names)}\n\n"
        f"💡 This is a fallback response. The Search API Service provides:\n"
        f"   • Location resolution and boundaries\n"
        f"   • Environmental context from web sources\n"
        f"   • Complete analysis based on web data\n"
        f"   • Integration with Tavily search API\n\n"
        f"🔧 To enable full functionality, ensure the Search API Service is running:\n"
        f"   cd backend/app/search_service && python start.py"
    )
    
    return {
        "analysis": analysis,
        "roi": None,
        "evidence": ["search_service:fallback_used"],
        "sources": [],
        "confidence": 0.0
    }
