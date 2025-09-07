"""
Nominatim client for geocoding location entities.

This module provides geocoding functionality using the OpenStreetMap Nominatim API
to resolve location names into geographic boundaries and coordinates.
"""

import time
import requests
import logging
from typing import List, Optional, Dict, Any
from urllib.parse import quote

try:
    from ..models.location import LocationEntity, BoundaryInfo
except ImportError:
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent.parent.parent.parent))
    
    from app.services.core_llm_agent.models.location import LocationEntity, BoundaryInfo

logger = logging.getLogger(__name__)


class NominatimClient:
    """Client for OpenStreetMap Nominatim geocoding API."""
    
    def __init__(self, base_url: str = "https://nominatim.openstreetmap.org"):
        """Initialize the Nominatim client.
        
        Args:
            base_url: Base URL for Nominatim API
        """
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'GeoLLM/1.0 (geospatial analysis application)'
        })
        self.rate_limit_delay = 1.0  # Nominatim rate limit: max 1 request per second
        self.last_request_time = 0
    
    def _rate_limit(self):
        """Enforce rate limiting for Nominatim API."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = time.time()
    
    def geocode_location(self, entity: LocationEntity, country_code: str = "in") -> Optional[BoundaryInfo]:
        """Geocode a single location entity.
        
        Args:
            entity: LocationEntity to geocode
            country_code: Country code to restrict search (default: "in" for India)
            
        Returns:
            BoundaryInfo with resolved geographic data, or None if geocoding fails
        """
        self._rate_limit()
        
        # Build search query
        query = entity.matched_name
        if entity.type == "city":
            query += f", {entity.type}"
        
        params = {
            'q': query,
            'format': 'json',
            'polygon_geojson': '1',
            'addressdetails': '1',
            'limit': '1',
            'countrycodes': country_code
        }
        
        try:
            url = f"{self.base_url}/search"
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            results = response.json()
            if not results:
                logger.warning(f"No geocoding results for: {entity.matched_name}")
                return None
            
            result = results[0]
            
            # Extract coordinates
            lat = float(result['lat'])
            lon = float(result['lon'])
            
            # Extract bounding box
            bbox = None
            if 'boundingbox' in result:
                bbox_str = result['boundingbox']
                bbox = [
                    float(bbox_str[2]),  # min_lng (west)
                    float(bbox_str[0]),  # min_lat (south)
                    float(bbox_str[3]),  # max_lng (east)
                    float(bbox_str[1])   # max_lat (north)
                ]
            
            # Extract geometry
            geometry = result.get('geojson')
            if not geometry:
                # Fallback: create point geometry
                geometry = {
                    "type": "Point",
                    "coordinates": [lon, lat]
                }
            
            # Calculate area for polygons
            area_km2 = None
            if geometry.get('type') in ['Polygon', 'MultiPolygon']:
                area_km2 = self._estimate_area_from_bbox(bbox) if bbox else None
            
            return BoundaryInfo(
                geometry=geometry,
                bbox=bbox or [lon, lat, lon, lat],  # Fallback to point bbox
                area_km2=area_km2,
                center=[lon, lat],
                display_name=result.get('display_name', entity.matched_name),
                place_id=result.get('place_id'),
                importance=float(result.get('importance', 0)) if result.get('importance') else None
            )
            
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP error in geocoding {entity.matched_name}: {e}")
            return None
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Data parsing error in geocoding {entity.matched_name}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in geocoding {entity.matched_name}: {e}")
            return None
    
    def geocode_locations(self, entities: List[LocationEntity], country_code: str = "in") -> List[BoundaryInfo]:
        """Geocode multiple location entities.
        
        Args:
            entities: List of LocationEntity objects to geocode
            country_code: Country code to restrict search (default: "in" for India)
            
        Returns:
            List of BoundaryInfo objects (excludes failed geocoding attempts)
        """
        resolved = []
        
        for entity in entities:
            boundary_info = self.geocode_location(entity, country_code)
            if boundary_info:
                resolved.append(boundary_info)
            else:
                logger.warning(f"Failed to geocode: {entity.matched_name}")
        
        logger.info(f"Successfully geocoded {len(resolved)}/{len(entities)} locations")
        return resolved
    
    def _estimate_area_from_bbox(self, bbox: List[float]) -> float:
        """Rough area estimation from bounding box.
        
        Args:
            bbox: Bounding box [min_lng, min_lat, max_lng, max_lat]
            
        Returns:
            Estimated area in square kilometers
        """
        if not bbox or len(bbox) != 4:
            return 0.0
        
        min_lng, min_lat, max_lng, max_lat = bbox
        
        # Rough calculation using degrees (not accurate but good enough for estimation)
        # 1 degree ≈ 111 km at equator
        width_km = abs(max_lng - min_lng) * 111 * abs(min_lat + max_lat) / 2 * 3.14159 / 180
        height_km = abs(max_lat - min_lat) * 111
        
        return width_km * height_km
    
    def search_by_query(self, query: str, country_code: str = "in", limit: int = 5) -> List[BoundaryInfo]:
        """Search locations by free-form query.
        
        Args:
            query: Free-form search query
            country_code: Country code to restrict search
            limit: Maximum number of results
            
        Returns:
            List of BoundaryInfo objects
        """
        self._rate_limit()
        
        params = {
            'q': query,
            'format': 'json',
            'polygon_geojson': '1',
            'addressdetails': '1',
            'limit': str(limit),
            'countrycodes': country_code
        }
        
        try:
            url = f"{self.base_url}/search"
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            results = response.json()
            boundary_infos = []
            
            for result in results:
                try:
                    lat = float(result['lat'])
                    lon = float(result['lon'])
                    
                    bbox = None
                    if 'boundingbox' in result:
                        bbox_str = result['boundingbox']
                        bbox = [
                            float(bbox_str[2]), float(bbox_str[0]),
                            float(bbox_str[3]), float(bbox_str[1])
                        ]
                    
                    geometry = result.get('geojson', {
                        "type": "Point",
                        "coordinates": [lon, lat]
                    })
                    
                    area_km2 = None
                    if geometry.get('type') in ['Polygon', 'MultiPolygon'] and bbox:
                        area_km2 = self._estimate_area_from_bbox(bbox)
                    
                    boundary_info = BoundaryInfo(
                        geometry=geometry,
                        bbox=bbox or [lon, lat, lon, lat],
                        area_km2=area_km2,
                        center=[lon, lat],
                        display_name=result.get('display_name', query),
                        place_id=result.get('place_id'),
                        importance=float(result.get('importance', 0)) if result.get('importance') else None
                    )
                    boundary_infos.append(boundary_info)
                    
                except (KeyError, ValueError, TypeError) as e:
                    logger.warning(f"Failed to parse result: {e}")
                    continue
            
            logger.info(f"Found {len(boundary_infos)} results for query: {query}")
            return boundary_infos
            
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP error in search query '{query}': {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error in search query '{query}': {e}")
            return []
