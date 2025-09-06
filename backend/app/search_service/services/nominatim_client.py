"""
Nominatim Client for OpenStreetMap geocoding and location data.

This client provides accurate location data including coordinates, area, and boundaries
using the free OpenStreetMap Nominatim service.
"""

import requests
import logging
import math
import time
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

# Try to import geospatial libraries, but work without them
try:
    from shapely.geometry import shape
    from shapely.ops import transform
    import pyproj
    GEOSPATIAL_AVAILABLE = True
    logger.info("Geospatial libraries loaded successfully")
except ImportError as e:
    GEOSPATIAL_AVAILABLE = False
    logger.info(f"Working without geospatial libraries: {e}")

class NominatimClient:
    """Fixed Nominatim client with working area calculation."""
    
    def __init__(self):
        self.base_url = "https://nominatim.openstreetmap.org"
        self.headers = {
            'User-Agent': 'GeoLLM-SearchService/1.0 (geospatial analysis tool)'
        }
        self.last_request_time = 0
        self.min_request_interval = 1.0
    
    def _rate_limit(self):
        """Ensure we don't exceed Nominatim's rate limit."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def search_location(self, location_name: str, location_type: str = "city") -> Optional[Dict[str, Any]]:
        """
        Search for location data using Nominatim with focus on polygon geometry.
        """
        try:
            self._rate_limit()
            
            # Try multiple search strategies with different approaches
            search_queries = [
                f"{location_name}, India",
                f"{location_name}, city, India", 
                location_name,
                f"{location_name} city"
            ]
            
            for search_query in search_queries:
                params = {
                    'q': search_query,
                    'format': 'json',
                    'polygon_geojson': 1,  # Critical: Get polygon geometry
                    'addressdetails': 1,
                    'limit': 10,  # Get more results to find polygon data
                    'extratags': 1,
                    'class': 'boundary',  # Prefer boundary data for geometry
                    'type': 'administrative'  # Administrative boundaries have better geometry
                }
                
                logger.info(f"Searching Nominatim for: {search_query}")
                
                response = requests.get(
                    f"{self.base_url}/search",
                    params=params,
                    headers=self.headers,
                    timeout=15
                )
                
                if response.status_code == 200:
                    results = response.json()
                    logger.info(f"Found {len(results)} results for query: {search_query}")
                    
                    if results:
                        # Log all results for debugging
                        for i, result in enumerate(results):
                            logger.info(f"Result {i}: {result.get('display_name', 'No name')} - {result.get('class')}/{result.get('type')}")
                        
                        # Try to find best result
                        best_result = self._find_best_result(results, location_name)
                        
                        # If no best result, use first result
                        if not best_result:
                            logger.info("No best result found, using first result")
                            best_result = results[0]
                        
                        logger.info(f"Processing result: {best_result.get('display_name', 'No name')}")
                        
                        # Process the result - be more lenient
                        location_data = self._process_result(best_result, location_name)
                        if location_data:
                            logger.info(f"Successfully processed {location_name}")
                            return location_data
                        else:
                            logger.warning(f"Failed to process result for {location_name}")
                    else:
                        logger.warning(f"No results found for query: {search_query}")
                else:
                    logger.error(f"HTTP error {response.status_code} for query: {search_query}")
                
                # Small delay between different queries
                time.sleep(0.5)
            
            logger.error(f"All search strategies failed for {location_name}")
            return None
            
        except Exception as e:
            logger.error(f"Error searching for {location_name}: {e}")
            return None
    
    def _find_best_result(self, results: List[Dict], location_name: str) -> Optional[Dict]:
        """Find the best result prioritizing polygon geometry."""
        best_result = None
        best_score = 0
        
        for result in results:
            score = 0
            
            # PRIORITY 1: Results with polygon geometry (most important)
            if 'geojson' in result and result['geojson'].get('type') in ['Polygon', 'MultiPolygon']:
                score += 50  # Highest priority
                logger.info(f"Found polygon geometry for: {result.get('display_name')}")
            
            # PRIORITY 2: Administrative boundaries (better geometry than places)
            if result.get('class') == 'boundary':
                if result.get('type') == 'administrative':
                    score += 30
                else:
                    score += 20
            
            # PRIORITY 3: Places (fallback if no boundary data)
            elif result.get('class') == 'place':
                if result.get('type') in ['city', 'town']:
                    score += 25
                elif result.get('type') in ['village', 'hamlet']:
                    score += 15
                else:
                    score += 10
            
            # Prefer exact name matches
            display_name = result.get('display_name', '').lower()
            location_lower = location_name.lower()
            if location_lower in display_name:
                score += 10
                # Bonus for exact match at start
                if display_name.startswith(location_lower):
                    score += 5
            
            # Prefer results with geojson
            if 'geojson' in result:
                score += 8
            
            # Prefer results with OSM data
            if result.get('osm_type') and result.get('osm_id'):
                score += 5
            
            # Check if bounding box size is reasonable
            if 'boundingbox' in result:
                try:
                    bbox = result['boundingbox']
                    area = self._estimate_bbox_area(bbox)
                    if 1 <= area <= 10000:  # Reasonable city size
                        score += 3
                    elif area > 50000:  # Too large (probably district)
                        score -= 5  # Reduced penalty - don't completely reject
                except:
                    pass
            
            if score > best_score:
                best_score = score
                best_result = result
        
        logger.info(f"Best result score: {best_score} for {best_result.get('display_name') if best_result else 'None'}")
        return best_result
    
    def _process_result(self, result: Dict, location_name: str) -> Optional[Dict[str, Any]]:
        """Process Nominatim result focusing on polygon geometry."""
        try:
            # Extract coordinates - be more defensive
            lat = result.get('lat')
            lng = result.get('lon')
            
            if not lat or not lng:
                logger.error("Missing lat/lon in result")
                return None
                
            try:
                lat = float(lat)
                lng = float(lng)
            except (ValueError, TypeError):
                logger.error("Invalid lat/lon format")
                return None
            
            if lat == 0 and lng == 0:
                logger.error("Coordinates are 0,0 - likely invalid")
                return None
            
            logger.info(f"Coordinates: {lat}, {lng}")
            
            # PRIORITY: Extract polygon geometry
            polygon_geometry = self._extract_polygon_geometry(result)
            is_fallback = polygon_geometry is None
            
            if is_fallback:
                logger.warning(f"No polygon geometry found for {location_name}, using bounding box fallback")
                polygon_geometry = self._create_bbox_polygon(result.get('boundingbox', []))
            
            # Check if geometry needs tiling
            geometry_tiles = []
            if polygon_geometry and self._should_tile_geometry(polygon_geometry):
                logger.info(f"Large geometry detected, creating tiles for {location_name}")
                geometry_tiles = self._create_geometry_tiles(polygon_geometry)
            else:
                geometry_tiles = [polygon_geometry] if polygon_geometry else []
            
            # Calculate area from geometry (most accurate)
            area_km2 = self._calculate_area_from_geometry(polygon_geometry)
            
            # Fallback area calculation if geometry fails
            if not area_km2:
                area_km2 = self._get_location_area(result, location_name)
            
            # Extract address info
            address = result.get('address', {})
            
            # Calculate bounding box for GEE filtering
            bbox = self._calculate_bounding_box(polygon_geometry) if polygon_geometry else self._extract_bbox(result)
            
            location_data = {
                'coordinates': {'lat': lat, 'lng': lng},
                'polygon_geometry': polygon_geometry,  # Main geometry for GEE
                'geometry_tiles': geometry_tiles,  # Tiled geometry for large areas
                'bounding_box': bbox,  # For GEE filtering
                'area_km2': area_km2,
                'population': None,
                'is_fallback': is_fallback,  # Mark if using fallback geometry
                'is_tiled': len(geometry_tiles) > 1,  # Mark if geometry was tiled
                'administrative_info': {
                    'name': result.get('display_name', location_name),
                    'type': result.get('type', 'unknown'),
                    'country': address.get('country', 'India'),
                    'state': address.get('state', ''),
                    'city': address.get('city', location_name)
                },
                'sources': [{
                    'title': 'OpenStreetMap Nominatim',
                    'url': 'https://nominatim.openstreetmap.org',
                    'score': 1.0
                }],
                'location_name': location_name
            }
            
            geometry_type = polygon_geometry.get('type', 'Unknown') if polygon_geometry else 'BoundingBox'
            logger.info(f"Successfully processed {location_name}: area={area_km2} km², geometry={geometry_type}, fallback={is_fallback}")
            return location_data
            
        except Exception as e:
            logger.error(f"Error processing result: {e}")
            return None
    
    def _calculate_simple_bbox_area(self, bbox: List[str]) -> Optional[float]:
        """Simple bounding box area calculation as last resort."""
        try:
            if len(bbox) != 4:
                return None
            
            min_lat, max_lat, min_lng, max_lng = map(float, bbox)
            
            # Simple area calculation
            lat_diff = abs(max_lat - min_lat)
            lng_diff = abs(max_lng - min_lng)
            
            if lat_diff == 0 or lng_diff == 0:
                return None
            
            # Convert to kilometers (rough approximation)
            lat_km = lat_diff * 111.32
            lng_km = lng_diff * 111.32 * math.cos(math.radians((min_lat + max_lat) / 2))
            
            area_km2 = lat_km * lng_km * 0.6  # Apply correction factor
            
            return round(area_km2, 2) if area_km2 > 0.01 else None
            
        except Exception as e:
            logger.warning(f"Simple bbox area calculation failed: {e}")
            return None
    
    def _get_location_area(self, result: Dict, location_name: str) -> Optional[float]:
        """Get area using multiple methods in order of accuracy."""
        
        # Debug: Log what data we have
        logger.info(f"Calculating area for {location_name}")
        logger.info(f"OSM type: {result.get('osm_type')}, OSM ID: {result.get('osm_id')}")
        logger.info(f"Has geojson: {'geojson' in result}")
        logger.info(f"Has boundingbox: {'boundingbox' in result}")
        if 'boundingbox' in result:
            bbox = result['boundingbox']
            logger.info(f"Bounding box: {bbox}")
        
        # Method 1: Calculate from bounding box first (more reliable than hardcoded)
        if 'boundingbox' in result:
            area = self._calculate_improved_bbox_area(result['boundingbox'])
            if area and 0.01 <= area <= 500000:  # Reasonable range
                logger.info(f"Calculated area from bounding box: {area} km²")
                return area
        
        # Method 2: Use known accurate areas as fallback
        accurate_area = self._get_known_area(location_name)
        if accurate_area:
            logger.info(f"Using known area for {location_name}: {accurate_area} km²")
            return accurate_area
        
        # Method 2: Calculate from GeoJSON geometry (most accurate)
        if GEOSPATIAL_AVAILABLE and 'geojson' in result:
            area = self._calculate_geojson_area(result['geojson'])
            if area and 0.01 <= area <= 500000:  # Much more lenient range
                logger.info(f"Calculated area from GeoJSON: {area} km²")
                return area
        
        # Method 3: Overpass API for more detailed geometry
        if result.get('osm_type') and result.get('osm_id'):
            area = self._get_overpass_area(result['osm_type'], result['osm_id'])
            if area and 0.01 <= area <= 500000:  # More lenient
                logger.info(f"Calculated area from Overpass: {area} km²")
                return area
        
        # Method 4: Improved bounding box calculation
        if 'boundingbox' in result:
            area = self._calculate_improved_bbox_area(result['boundingbox'])
            if area and 0.01 <= area <= 500000:  # More lenient
                logger.info(f"Calculated area from bounding box: {area} km²")
                return area
        
        logger.warning(f"All area calculation methods failed for {location_name}")
        return None
    
    def _get_known_area(self, location_name: str) -> Optional[float]:
        """Get known accurate areas for major Indian cities."""
        known_areas = {
            "mumbai": 603.4,
            "delhi": 1483.0,
            "bangalore": 741.0,
            "bengaluru": 741.0,
            "kolkata": 206.1,
            "chennai": 426.0,
            "hyderabad": 650.0,
            "pune": 331.3,
            "ahmedabad": 505.0,
            "jaipur": 467.0,
            "jodhpur": 233.0,
            "bikaner": 270.0,  # Added Bikaner
            "surat": 326.0,
            "lucknow": 349.0,
            "kanpur": 267.0,
            "nagpur": 227.0,
            "indore": 530.0,
            "thane": 147.0,
            "bhopal": 285.9,
            "visakhapatnam": 681.96,
            "pimpri chinchwad": 181.0,
            "patna": 135.0,
            "vadodara": 235.0,
            "ghaziabad": 190.0,
            "ludhiana": 159.0,
            "agra": 188.4
        }
        
        location_lower = location_name.lower().strip()
        for city, area in known_areas.items():
            if city in location_lower or location_lower in city:
                return area
        
        return None
    
    def _calculate_geojson_area(self, geojson: Dict) -> Optional[float]:
        """Calculate area from GeoJSON using Shapely if available."""
        if not GEOSPATIAL_AVAILABLE:
            return None
        
        try:
            geom = shape(geojson)
            if geom.is_empty:
                return None
            
            # Project to Web Mercator for area calculation
            transformer = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
            geom_projected = transform(transformer.transform, geom)
            
            area_sq_m = geom_projected.area
            area_sq_km = area_sq_m / 1_000_000
            
            return round(area_sq_km, 2)
            
        except Exception as e:
            logger.warning(f"GeoJSON area calculation failed: {e}")
            return None
    
    def _get_overpass_area(self, osm_type: str, osm_id: int) -> Optional[float]:
        """Get area using Overpass API for detailed geometry."""
        try:
            overpass_url = "https://overpass-api.de/api/interpreter"
            
            # Build query based on OSM type
            if osm_type == "relation":
                query = f"[out:json][timeout:25];relation({osm_id});out geom;"
            elif osm_type == "way":
                query = f"[out:json][timeout:25];way({osm_id});out geom;"
            else:
                return None
            
            response = requests.get(overpass_url, params={"data": query}, timeout=30)
            if response.status_code != 200:
                return None
            
            data = response.json()
            elements = data.get('elements', [])
            
            if not elements:
                return None
            
            # Extract coordinates and calculate area
            element = elements[0]
            if element.get('type') == 'relation':
                # Handle relation (complex geometry)
                return self._process_relation_geometry(element)
            elif element.get('type') == 'way':
                # Handle way (simple polygon)
                return self._process_way_geometry(element)
            
        except Exception as e:
            logger.warning(f"Overpass area calculation failed: {e}")
        
        return None
    
    def _process_way_geometry(self, way: Dict) -> Optional[float]:
        """Process way geometry for area calculation."""
        try:
            nodes = way.get('nodes', [])
            if len(nodes) < 3:
                return None
            
            coords = []
            for node in nodes:
                if 'lat' in node and 'lon' in node:
                    coords.append((node['lon'], node['lat']))
            
            if len(coords) < 3:
                return None
            
            # Use simple polygon area calculation
            return self._calculate_polygon_area(coords)
            
        except Exception as e:
            logger.warning(f"Way geometry processing failed: {e}")
            return None
    
    def _process_relation_geometry(self, relation: Dict) -> Optional[float]:
        """Process relation geometry (simplified)."""
        # For now, fall back to bounding box
        # Proper relation processing would require much more complex code
        return None

    def _calculate_polygon_area(self, coords: List[tuple]) -> Optional[float]:
        """Calculate polygon area using shoelace formula."""
        try:
            if len(coords) < 3:
                return None
            
            # Ensure polygon is closed
            if coords[0] != coords[-1]:
                coords.append(coords[0])
            
            # Shoelace formula
            area = 0.0
            n = len(coords) - 1  # Don't count the closing point twice
            
            for i in range(n):
                j = (i + 1) % n
                area += coords[i][0] * coords[j][1]
                area -= coords[j][0] * coords[i][1]
            
            area = abs(area) / 2.0
            
            # Convert from degrees to km² (rough approximation)
            area_km2 = area * 111.32 * 111.32
            
            return round(area_km2, 2) if area_km2 > 0.01 else None
            
        except Exception as e:
            logger.warning(f"Polygon area calculation failed: {e}")
            return None
    
    def _calculate_improved_bbox_area(self, bbox: List[str]) -> Optional[float]:
        """Calculate improved area from bounding box."""
        try:
            if len(bbox) != 4:
                return None
            
            min_lat, max_lat, min_lng, max_lng = map(float, bbox)
            
            # Calculate area using proper spherical geometry
            lat_diff = max_lat - min_lat
            lng_diff = max_lng - min_lng
            
            if lat_diff <= 0 or lng_diff <= 0:
                return None
            
            # Average latitude for longitude correction
            avg_lat_rad = math.radians((min_lat + max_lat) / 2)
            
            # Convert to kilometers
            lat_km = lat_diff * 111.32  # 1 degree lat ≈ 111.32 km
            lng_km = lng_diff * 111.32 * math.cos(avg_lat_rad)  # Corrected longitude
            
            area_km2 = lat_km * lng_km
            
            # Apply correction factor for administrative boundaries
            # Bounding boxes are often larger than actual administrative areas
            correction_factor = 0.7  # Assume 70% of bounding box
            area_km2 *= correction_factor
            
            return round(area_km2, 2) if area_km2 > 0.01 else None
            
        except Exception as e:
            logger.error(f"Bounding box area calculation failed: {e}")
            return None
    
    def _estimate_bbox_area(self, bbox: List[str]) -> float:
        """Quick estimate of bounding box area for filtering."""
        try:
            if len(bbox) != 4:
                return 0
            
            min_lat, max_lat, min_lng, max_lng = map(float, bbox)
            lat_diff = abs(max_lat - min_lat)
            lng_diff = abs(max_lng - min_lng)
            
            return lat_diff * lng_diff * 111.32 * 111.32  # Very rough km²
        except:
            return 0
    
    def _extract_polygon_geometry(self, result: Dict) -> Optional[Dict]:
        """Extract and simplify polygon geometry from Nominatim result."""
        if 'geojson' in result:
            geojson = result['geojson']
            if geojson.get('type') in ['Polygon', 'MultiPolygon']:
                logger.info(f"Found {geojson.get('type')} geometry")
                
                # Simplify geometry to reduce coordinate points
                simplified_geojson = self._simplify_geometry(geojson)
                if simplified_geojson:
                    logger.info(f"Simplified geometry: {self._count_coordinates(geojson)} → {self._count_coordinates(simplified_geojson)} points")
                    return simplified_geojson
                else:
                    return geojson
            else:
                logger.warning(f"GeoJSON type {geojson.get('type')} not suitable for polygon analysis")
        
        return None
    
    def _create_bbox_polygon(self, bbox: List[str]) -> Optional[Dict]:
        """Create polygon from bounding box as fallback."""
        if len(bbox) != 4:
            return None
        
        try:
            min_lat, max_lat, min_lng, max_lng = map(float, bbox)
            return {
                "type": "Polygon",
                "coordinates": [[
                    [min_lng, min_lat],
                    [max_lng, min_lat],
                    [max_lng, max_lat],
                    [min_lng, max_lat],
                    [min_lng, min_lat]
                ]]
            }
        except:
            return None
    
    def _calculate_area_from_geometry(self, geometry: Dict) -> Optional[float]:
        """Calculate area from GeoJSON geometry."""
        if not geometry:
            return None
        
        try:
            if GEOSPATIAL_AVAILABLE:
                # Use Shapely for accurate calculation
                geom = shape(geometry)
                if geom.is_empty:
                    return None
                
                # Project to Web Mercator for area calculation
                transformer = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
                geom_projected = transform(transformer.transform, geom)
                
                area_sq_m = geom_projected.area
                area_sq_km = area_sq_m / 1_000_000
                
                return round(area_sq_km, 2)
            else:
                # Fallback: rough calculation for simple polygons
                return self._calculate_simple_polygon_area(geometry)
                
        except Exception as e:
            logger.warning(f"Geometry area calculation failed: {e}")
            return None
    
    def _calculate_simple_polygon_area(self, geometry: Dict) -> Optional[float]:
        """Simple polygon area calculation without Shapely."""
        try:
            if geometry.get('type') == 'Polygon':
                coords = geometry['coordinates'][0]  # Exterior ring
                if len(coords) < 3:
                    return None
                
                # Shoelace formula
                area = 0.0
                n = len(coords) - 1
                for i in range(n):
                    j = (i + 1) % n
                    area += coords[i][0] * coords[j][1]
                    area -= coords[j][0] * coords[i][1]
                
                area = abs(area) / 2.0
                # Convert from degrees to km² (rough approximation)
                area_km2 = area * 111.32 * 111.32
                
                return round(area_km2, 2) if area_km2 > 0.01 else None
                
        except Exception as e:
            logger.warning(f"Simple polygon area calculation failed: {e}")
            return None
    
    def _calculate_bounding_box(self, geometry: Dict) -> Optional[Dict]:
        """Calculate bounding box from polygon geometry."""
        if not geometry:
            return None
        
        try:
            if geometry.get('type') == 'Polygon':
                coords = geometry['coordinates'][0]  # Exterior ring
            elif geometry.get('type') == 'MultiPolygon':
                # Get all coordinates from all polygons
                coords = []
                for polygon in geometry['coordinates']:
                    coords.extend(polygon[0])
            else:
                return None
            
            if not coords:
                return None
            
            # Find min/max coordinates
            lngs = [coord[0] for coord in coords]
            lats = [coord[1] for coord in coords]
            
            return {
                'west': min(lngs),
                'east': max(lngs),
                'south': min(lats),
                'north': max(lats)
            }
            
        except Exception as e:
            logger.warning(f"Bounding box calculation failed: {e}")
            return None
    
    def _extract_bbox(self, result: Dict) -> Optional[Dict]:
        """Extract bounding box from Nominatim result."""
        if 'boundingbox' in result:
            bbox = result['boundingbox']
            if len(bbox) == 4:
                try:
                    min_lat, max_lat, min_lng, max_lng = map(float, bbox)
                    return {
                        'west': min_lng,
                        'east': max_lng,
                        'south': min_lat,
                        'north': max_lat
                    }
                except:
                    pass
        return None
    
    def _simplify_geometry(self, geojson: Dict) -> Optional[Dict]:
        """Simplify geometry to reduce coordinate points while preserving topology."""
        if not GEOSPATIAL_AVAILABLE:
            logger.warning("Shapely not available, cannot simplify geometry")
            return geojson
        
        try:
            geom = shape(geojson)
            if geom.is_empty:
                return geojson
            
            # Calculate original area for comparison
            original_area = self._calculate_area_from_geometry(geojson)
            
            # Determine tolerance based on geometry size
            if original_area and original_area > 10000:  # Large area (state/country level)
                tolerance = 0.001  # ~100m tolerance
            elif original_area and original_area > 1000:  # Medium area (district level)
                tolerance = 0.0005  # ~50m tolerance
            else:  # Small area (city level)
                tolerance = 0.0001  # ~10m tolerance
            
            # Simplify geometry
            simplified_geom = geom.simplify(tolerance, preserve_topology=True)
            
            if simplified_geom.is_empty:
                logger.warning("Simplified geometry is empty, returning original")
                return geojson
            
            # Convert back to GeoJSON
            simplified_geojson = {
                "type": simplified_geom.geom_type,
                "coordinates": self._geom_to_coordinates(simplified_geom)
            }
            
            # Validate simplification - check area preservation
            simplified_area = self._calculate_area_from_geometry(simplified_geojson)
            if original_area and simplified_area:
                area_error = abs(original_area - simplified_area) / original_area
                if area_error > 0.02:  # More than 2% error
                    logger.warning(f"Simplification error too high: {area_error:.2%}, returning original")
                    return geojson
                else:
                    logger.info(f"Simplification successful: {area_error:.2%} area error")
            
            return simplified_geojson
            
        except Exception as e:
            logger.warning(f"Geometry simplification failed: {e}")
            return geojson
    
    def _count_coordinates(self, geojson: Dict) -> int:
        """Count total number of coordinate points in geometry."""
        try:
            if geojson.get('type') == 'Polygon':
                coords = geojson['coordinates'][0]  # Exterior ring
                return len(coords)
            elif geojson.get('type') == 'MultiPolygon':
                total = 0
                for polygon in geojson['coordinates']:
                    total += len(polygon[0])  # Exterior ring of each polygon
                return total
            return 0
        except:
            return 0
    
    def _geom_to_coordinates(self, geom) -> List:
        """Convert Shapely geometry to coordinate list."""
        try:
            if geom.geom_type == 'Polygon':
                return [list(geom.exterior.coords)]
            elif geom.geom_type == 'MultiPolygon':
                return [[list(polygon.exterior.coords)] for polygon in geom.geoms]
            else:
                return []
        except:
            return []
    
    def _should_tile_geometry(self, geojson: Dict) -> bool:
        """Check if geometry should be tiled due to large size."""
        area = self._calculate_area_from_geometry(geojson)
        return area and area > 10000  # 10,000 km² threshold (more aggressive)
    
    def _create_geometry_tiles(self, geojson: Dict) -> List[Dict]:
        """Break large polygons into smaller tiles for processing."""
        if not GEOSPATIAL_AVAILABLE:
            logger.warning("Shapely not available, cannot create tiles")
            return [geojson]
        
        try:
            geom = shape(geojson)
            if geom.is_empty:
                return [geojson]
            
            # Get bounding box
            bbox = geom.bounds  # (minx, miny, maxx, maxy)
            minx, miny, maxx, maxy = bbox
            
            # Calculate tile size (roughly 100km x 100km)
            tile_size = 1.0  # degrees (roughly 100km)
            
            tiles = []
            x = minx
            while x < maxx:
                y = miny
                while y < maxy:
                    # Create tile bounding box
                    tile_bbox = (x, y, min(x + tile_size, maxx), min(y + tile_size, maxy))
                    
                    # Create tile polygon
                    from shapely.geometry import box
                    tile_geom = box(*tile_bbox)
                    
                    # Intersect with original geometry
                    intersection = geom.intersection(tile_geom)
                    
                    if not intersection.is_empty and intersection.area > 0:
                        # Convert to GeoJSON
                        tile_geojson = {
                            "type": intersection.geom_type,
                            "coordinates": self._geom_to_coordinates(intersection)
                        }
                        tiles.append(tile_geojson)
                    
                    y += tile_size
                x += tile_size
            
            logger.info(f"Created {len(tiles)} tiles from large geometry")
            return tiles if tiles else [geojson]
            
        except Exception as e:
            logger.warning(f"Tiling failed: {e}")
            return [geojson]
    
    def _extract_boundaries(self, result: Dict) -> Optional[Dict]:
        """Legacy method - kept for compatibility."""
        return self._extract_polygon_geometry(result)


# Test function
def test_nominatim_client():
    """Test the fixed Nominatim client."""
    client = NominatimClient()
    
    test_cities = ["Mumbai", "Jodhpur", "Ahmedabad", "Bikaner"]
    
    for city in test_cities:
        print(f"\nTesting {city}:")
        result = client.search_location(city)
        
        if result:
            print(f"  ✓ Found: {result['location_name']}")
            print(f"  ✓ Coordinates: {result['coordinates']}")
            print(f"  ✓ Area: {result['area_km2']} km²")
            print(f"  ✓ Type: {result['administrative_info']['type']}")
        else:
            print(f"  ✗ Failed to find {city}")


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    test_nominatim_client()