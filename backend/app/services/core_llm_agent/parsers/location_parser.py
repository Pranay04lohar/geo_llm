"""
Location Parser - Orchestrates location extraction and resolution.

This module combines LLM-based NER with geocoding to extract locations from queries
and resolve them into geographic boundaries and coordinates.
"""

import time
import logging
from typing import List, Optional, Dict, Any

try:
    from .location_ner import LocationNER
    from .nominatim_client import NominatimClient
    from ..models.location import LocationParseResult, LocationEntity, BoundaryInfo
except ImportError:
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent.parent.parent.parent))
    
    from app.services.core_llm_agent.parsers.location_ner import LocationNER
    from app.services.core_llm_agent.parsers.nominatim_client import NominatimClient
    from app.services.core_llm_agent.models.location import LocationParseResult, LocationEntity, BoundaryInfo

logger = logging.getLogger(__name__)


class LocationParser:
    """Main orchestrator for location parsing and resolution."""
    
    def __init__(self, ner_model: str = None, nominatim_url: str = None):
        """Initialize the LocationParser.
        
        Args:
            ner_model: Model name for NER (uses env default if None)
            nominatim_url: Nominatim API URL (uses default if None)
        """
        self.ner = LocationNER(ner_model)
        self.geocoder = NominatimClient(nominatim_url) if nominatim_url else NominatimClient()
        
    def parse_query(self, query: str, resolve_locations: bool = True) -> LocationParseResult:
        """Parse a query to extract and resolve locations.
        
        Args:
            query: User query string
            resolve_locations: Whether to geocode extracted locations
            
        Returns:
            LocationParseResult with extracted entities and resolved boundaries
        """
        start_time = time.time()
        
        try:
            # Step 1: Extract location entities using NER
            logger.info(f"Extracting locations from query: {query[:100]}...")
            entities = self.ner.extract_locations(query)
            
            if not entities:
                logger.info("No location entities found in query")
                return LocationParseResult(
                    entities=[],
                    resolved_locations=[],
                    primary_location=None,
                    roi_geometry=None,
                    roi_source="none",
                    processing_time=time.time() - start_time,
                    success=True
                )
            
            logger.info(f"Found {len(entities)} location entities: {[e.matched_name for e in entities]}")
            
            # Step 2: Resolve locations to geographic boundaries (if requested)
            resolved_locations = []
            if resolve_locations:
                logger.info("Resolving locations to geographic boundaries...")
                resolved_locations = self.geocoder.geocode_locations(entities)
                
                if not resolved_locations:
                    logger.warning("Failed to resolve any locations to boundaries")
                else:
                    logger.info(f"Successfully resolved {len(resolved_locations)} locations")
            
            # Step 3: Determine primary location and ROI
            primary_location = None
            roi_geometry = None
            roi_source = "none"
            
            if resolved_locations:
                # Use the first resolved location as primary
                primary_location = resolved_locations[0]
                roi_geometry = primary_location.geometry
                roi_source = f"ner_{primary_location.display_name.split(',')[0]}"
                logger.info(f"Primary location: {primary_location.display_name}")
            
            processing_time = time.time() - start_time
            
            return LocationParseResult(
                entities=entities,
                resolved_locations=resolved_locations,
                primary_location=primary_location,
                roi_geometry=roi_geometry,
                roi_source=roi_source,
                processing_time=processing_time,
                success=True
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Error in location parsing: {e}")
            
            return LocationParseResult(
                entities=[],
                resolved_locations=[],
                primary_location=None,
                roi_geometry=None,
                roi_source="error",
                processing_time=processing_time,
                success=False,
                error=str(e)
            )
    
    def extract_roi_from_query(self, query: str) -> Optional[Dict[str, Any]]:
        """Extract ROI information from query for backward compatibility.
        
        This method provides compatibility with the existing ROI extraction workflow
        used in the original core_llm_agent.py.
        
        Args:
            query: User query string
            
        Returns:
            ROI information dictionary or None
        """
        result = self.parse_query(query, resolve_locations=True)
        
        if not result.success or not result.primary_location:
            return None
        
        # Convert to the expected format for backward compatibility
        return {
            "geometry": result.roi_geometry,
            "buffer_km": self._estimate_buffer_from_area(result.primary_location.area_km2),
            "area_km2": result.primary_location.area_km2 or 0,
            "center": result.primary_location.center,
            "display_name": result.primary_location.display_name,
            "source": result.roi_source,
            "polygon_geometry": result.roi_geometry,
            "geometry_tiles": [],  # Not implemented in this version
            "is_tiled": False,
            "is_fallback": False
        }
    
    def extract_roi_from_locations(self, locations: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Extract ROI from location dictionaries for backward compatibility.
        
        Args:
            locations: List of location dictionaries (legacy format)
            
        Returns:
            ROI information dictionary or None
        """
        if not locations:
            return None
        
        # Convert legacy format to LocationEntity objects
        entities = []
        for loc in locations:
            try:
                entity = LocationEntity(
                    matched_name=loc.get("matched_name", ""),
                    type=loc.get("type", "city"),
                    confidence=float(loc.get("confidence", 0))
                )
                entities.append(entity)
            except Exception as e:
                logger.warning(f"Failed to convert location dict to entity: {e}")
                continue
        
        if not entities:
            return None
        
        # Resolve first entity
        resolved = self.geocoder.geocode_locations([entities[0]])
        if not resolved:
            return None
        
        primary = resolved[0]
        
        return {
            "geometry": primary.geometry,
            "buffer_km": self._estimate_buffer_from_area(primary.area_km2),
            "area_km2": primary.area_km2 or 0,
            "center": primary.center,
            "display_name": primary.display_name,
            "source": f"legacy_{primary.display_name.split(',')[0]}",
            "polygon_geometry": primary.geometry,
            "geometry_tiles": [],
            "is_tiled": False,
            "is_fallback": False
        }
    
    def get_default_roi(self) -> Dict[str, Any]:
        """Get default ROI (Mumbai area) for backward compatibility.
        
        Returns:
            Default ROI information dictionary
        """
        # Default Mumbai area
        center_lng, center_lat = 72.8777, 19.0760
        d = 0.01  # Small buffer
        
        ring = [
            [center_lng - d, center_lat - d],
            [center_lng + d, center_lat - d],
            [center_lng + d, center_lat + d],
            [center_lng - d, center_lat + d],
            [center_lng - d, center_lat - d],
        ]
        
        geometry = {
            "type": "Polygon",
            "coordinates": [ring]
        }
        
        return {
            "geometry": geometry,
            "buffer_km": 2.0,
            "area_km2": 4.0,  # Rough estimate
            "center": [center_lng, center_lat],
            "display_name": "Mumbai, Maharashtra, India (Default)",
            "source": "default_mumbai",
            "polygon_geometry": geometry,
            "geometry_tiles": [],
            "is_tiled": False,
            "is_fallback": True
        }
    
    def _estimate_buffer_from_area(self, area_km2: Optional[float]) -> float:
        """Estimate buffer distance from area.
        
        Args:
            area_km2: Area in square kilometers
            
        Returns:
            Estimated buffer in kilometers
        """
        if not area_km2:
            return 10.0  # Default buffer
        
        # Rough estimation: buffer = sqrt(area) / 2
        import math
        return max(1.0, min(50.0, math.sqrt(area_km2) / 2))
    
    def extract_locations_legacy(self, query: str) -> List[Dict[str, Any]]:
        """Extract locations in legacy dictionary format.
        
        Args:
            query: User query string
            
        Returns:
            List of location dictionaries (legacy format)
        """
        return self.ner.extract_locations_dict(query)
