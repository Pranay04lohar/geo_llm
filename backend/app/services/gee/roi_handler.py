"""
Region of Interest (ROI) Handler

Extracts and validates ROI from various sources:
- Extracted location entities from LLM
- Direct coordinates from query text
- User prompts for clarification
- Default fallback locations
"""

import re
import os
import requests
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv

# Try to import geocoding libraries
try:
    from geopy.geocoders import GoogleV3
    from geopy.exc import GeocoderTimedOut, GeocoderQuotaExceeded
    GEOPY_AVAILABLE = True
except ImportError:
    GEOPY_AVAILABLE = False
    # Mock geocoder for development
    class MockGeocoder:
        def geocode(self, query, timeout=None):
            # Return mock coordinates for common Indian cities
            mock_coords = {
                "mumbai": (19.0760, 72.8777),
                "delhi": (28.7041, 77.1025),
                "bangalore": (12.9716, 77.5946),
                "kolkata": (22.5726, 88.3639),
                "chennai": (13.0827, 80.2707),
                "hyderabad": (17.3850, 78.4867),
                "punjab": (31.1471, 75.3412),
                "ludhiana": (30.9010, 75.8573),
                "udaipur": (24.5854, 73.7125),  # Add Udaipur coordinates
                "rajasthan": (26.9124, 75.7873)  # Add Rajasthan coordinates
            }
            
            query_lower = query.lower()
            for city, coords in mock_coords.items():
                if city in query_lower:
                    class MockLocation:
                        def __init__(self, lat, lng):
                            self.latitude = lat
                            self.longitude = lng
                    return MockLocation(coords[0], coords[1])
            return None
    
    # Mock exception classes
    class GeocoderTimedOut(Exception):
        pass
    
    class GeocoderQuotaExceeded(Exception):
        pass
    
    GoogleV3 = MockGeocoder


class ROIHandler:
    """Handles Region of Interest extraction and validation."""
    
    def __init__(self):
        """Initialize ROI handler with geocoding setup."""
        self.geocoder = None
        self.search_api_url = "http://localhost:8001"  # Search API Service URL
        self._setup_geocoder()
        
        # Default location (Mumbai) as fallback
        self.default_location = {
            "name": "Mumbai, India",
            "lat": 19.0760,
            "lng": 72.8777,
            "buffer_km": 10
        }
        
    def _setup_geocoder(self):
        """Setup geocoding client with API key."""
        try:
            # Load .env from backend root
            current_dir = os.path.dirname(os.path.abspath(__file__))
            backend_root = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))
            dotenv_path = os.path.join(backend_root, ".env")
            load_dotenv(dotenv_path, override=False)
        except Exception:
            pass
            
        # Get Google Maps API key for geocoding
        api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
        
        if GEOPY_AVAILABLE and api_key:
            self.geocoder = GoogleV3(api_key=api_key)
        else:
            # Use mock geocoder for development
            self.geocoder = MockGeocoder()
            
    def extract_roi_from_locations(self, locations: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Extract ROI from LLM-extracted location entities.
        
        Args:
            locations: List of location dicts with 'matched_name', 'type', 'confidence'
            
        Returns:
            ROI dict with geometry and metadata, or None if extraction fails
        """
        if not locations:
            return None
            
        # Sort by confidence and take the highest confidence location
        sorted_locations = sorted(locations, key=lambda x: x.get("confidence", 0), reverse=True)
        primary_location = sorted_locations[0]
        
        location_name = primary_location.get("matched_name", "")
        if not location_name:
            return None
            
        # Get location type first
        location_type = primary_location.get("type", "city").lower()
        
        # Try to get location data from Search API Service first
        search_data = self._get_location_from_search_api(location_name, location_type)
        
        if search_data:
            # Use Search API Service data with polygon geometry
            lat, lng = search_data["lat"], search_data["lng"]
            area_km2 = search_data.get("area_km2")
            polygon_geometry = search_data.get("polygon_geometry")
            geometry_tiles = search_data.get("geometry_tiles", [])
            bounding_box = search_data.get("bounding_box")
            is_tiled = search_data.get("is_tiled", False)
            is_fallback = search_data.get("is_fallback", False)
            
            print(f"✅ Using Search API data for {location_name}: {lat:.4f}°N, {lng:.4f}°E, {area_km2} km²")
            if polygon_geometry:
                print(f"🎯 Using polygon geometry (tiled: {is_tiled}, fallback: {is_fallback})")
                print(f"   📦 Polygon type: {polygon_geometry.get('type', 'unknown')}")
                print(f"   📍 Coordinates count: {len(polygon_geometry.get('coordinates', [[]])[0]) if polygon_geometry else 0}")
            else:
                print(f"⚠️ No polygon geometry available, using fallback approach")
        else:
            # Fallback to geocoding
            coords = self._geocode_location(location_name)
            if not coords:
                return None
            lat, lng = coords
            area_km2 = None
            polygon_geometry = None
            geometry_tiles = []
            bounding_box = None
            is_tiled = False
            is_fallback = True
            print(f"⚠️ Using fallback geocoding for {location_name}: {lat:.4f}°N, {lng:.4f}°E")
        
        # Get dynamic ROI dimensions based on city characteristics
        
        # Use polygon geometry if available, otherwise create from dimensions
        if search_data and polygon_geometry and not is_fallback:
            # Use actual polygon geometry from Search API
            roi_geometry = polygon_geometry
            print(f"🎯 Using actual polygon geometry from Search API")
        else:
            # Fallback to calculated dimensions
            if search_data and area_km2:
                # Calculate dimensions from Search API area data
                side_length = (area_km2 ** 0.5) * 1.2  # Add 20% buffer
                dimensions = {"width": side_length, "height": side_length}
                print(f"📊 Using Search API area data: {area_km2} km² → {side_length:.1f}km x {side_length:.1f}km")
            else:
                # Fallback to hardcoded dimensions
                dimensions = self._get_dynamic_roi_size(location_type, location_name)
                print(f"📐 Using hardcoded dimensions: {dimensions['width']}km x {dimensions['height']}km")
            
            # Create ROI geometry with dynamic dimensions
            roi_geometry = self._create_dynamic_geometry(lat, lng, dimensions)
        
        return {
            "source": "llm_locations",
            "primary_location": {
                "name": location_name,
                "type": location_type,
                "lat": lat,
                "lng": lng,
                "confidence": primary_location.get("confidence", 0)
            },
            "all_locations": locations,
            "buffer_km": max(dimensions.get("width", 30), dimensions.get("height", 25)) / 2 if 'dimensions' in locals() else 15,  # Equivalent radius for compatibility
            "dimensions": dimensions if 'dimensions' in locals() else {"width": 30, "height": 25},  # Add actual dimensions used
            "geometry": roi_geometry,
            "polygon_geometry": polygon_geometry,  # Main polygon geometry
            "geometry_tiles": geometry_tiles,  # Tiled geometry for large areas
            "bounding_box": bounding_box,  # Bounding box for GEE filtering
            "is_tiled": is_tiled,  # Whether geometry was tiled
            "is_fallback": is_fallback,  # Whether using fallback geometry
            "search_api_data": search_data,  # Include Search API data for reference
            "area_km2": area_km2  # Include area data
        }
        
    def extract_roi_from_query(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Extract ROI from direct coordinates or place names in query text.
        
        Args:
            query: User query string
            
        Returns:
            ROI dict with geometry and metadata, or None if extraction fails
        """
        # Try to extract coordinates first
        coords = self._extract_coordinates_from_text(query)
        if coords:
            lat, lng = coords
            return {
                "source": "query_coordinates",
                "primary_location": {
                    "name": f"Coordinates ({lat:.4f}, {lng:.4f})",
                    "type": "coordinates",
                    "lat": lat,
                    "lng": lng,
                    "confidence": 100
                },
                "buffer_km": 5,  # Default buffer for coordinates
                "geometry": self._create_buffer_geometry(lat, lng, 5)
            }
            
        # Try to extract place names not caught by LLM
        place_names = self._extract_place_names_from_text(query)
        if place_names:
            # Use the first found place name
            place_name = place_names[0]
            coords = self._geocode_location(place_name)
            if coords:
                lat, lng = coords
                return {
                    "source": "query_places",
                    "primary_location": {
                        "name": place_name,
                        "type": "place",
                        "lat": lat,
                        "lng": lng,
                        "confidence": 80
                    },
                    "buffer_km": 10,
                    "geometry": self._create_buffer_geometry(lat, lng, 10)
                }
                
        return None
        
    def get_default_roi(self) -> Dict[str, Any]:
        """
        Get default ROI (Mumbai) as fallback.
        
        Returns:
            Default ROI dict with geometry and metadata
        """
        default = self.default_location
        return {
            "source": "default_fallback",
            "primary_location": {
                "name": default["name"],
                "type": "city",
                "lat": default["lat"],
                "lng": default["lng"],
                "confidence": 0
            },
            "buffer_km": default["buffer_km"],
            "geometry": self._create_buffer_geometry(
                default["lat"], 
                default["lng"], 
                default["buffer_km"]
            )
        }
        
    def _geocode_location(self, location_name: str) -> Optional[Tuple[float, float]]:
        """Geocode a location name to lat/lng coordinates."""
        if not self.geocoder:
            return None
            
        try:
            # Add "India" to improve geocoding accuracy for Indian locations
            search_query = f"{location_name}, India"
            location = self.geocoder.geocode(search_query, timeout=10)
            
            if location:
                return (location.latitude, location.longitude)
                
        except (GeocoderTimedOut, GeocoderQuotaExceeded):
            pass
        except Exception:
            pass
            
        return None
        
    def _get_location_from_search_api(self, location_name: str, location_type: str = "city") -> Optional[Dict[str, Any]]:
        """
        Get accurate location data from Search API Service with polygon geometry.
        
        Args:
            location_name: Name of the location
            location_type: Type of location (city, state, etc.)
            
        Returns:
            Dict with coordinates, area, polygon geometry, and other location data, or None if failed
        """
        try:
            print(f"🔍 ROI Handler: Calling Search API for {location_name}")
            response = requests.post(
                f"{self.search_api_url}/search/location-data",
                json={
                    "location_name": location_name,
                    "location_type": location_type
                },
                timeout=15
            )
            
            print(f"🔍 ROI Handler: Search API response status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"🔍 ROI Handler: Search API success: {data.get('success', False)}")
                print(f"🔍 ROI Handler: Search API error: {data.get('error', 'None')}")
                if data.get("success", False):
                    coords = data.get("coordinates", {})
                    area = data.get("area_km2")
                    polygon_geometry = data.get("polygon_geometry")
                    geometry_tiles = data.get("geometry_tiles", [])
                    bounding_box = data.get("bounding_box")
                    is_tiled = data.get("is_tiled", False)
                    is_fallback = data.get("is_fallback", False)
                    
                    print(f"🔍 ROI Handler: Coordinates: {coords}")
                    if coords.get("lat") and coords.get("lng"):
                        print(f"🔍 ROI Handler: Valid coordinates found, returning data")
                        return {
                            "lat": coords["lat"],
                            "lng": coords["lng"],
                            "area_km2": area,
                            "polygon_geometry": polygon_geometry,
                            "geometry_tiles": geometry_tiles,
                            "bounding_box": bounding_box,
                            "is_tiled": is_tiled,
                            "is_fallback": is_fallback,
                            "source": "search_api"
                        }
                    else:
                        print(f"🔍 ROI Handler: Invalid coordinates, returning None")
                        
        except Exception as e:
            print(f"⚠️ Search API request failed for {location_name}: {e}")
            
        return None
        
    def _get_dynamic_roi_size(self, location_type: str, location_name: str = "") -> Dict[str, float]:
        """Get dynamic ROI dimensions based on actual city characteristics."""
        
        # Real city dimensions (approximate width x height in km) for major Indian cities
        city_dimensions = {
            "delhi": {"width": 51, "height": 48},      # ~1484 km² (actual NCT Delhi)
            "mumbai": {"width": 35, "height": 20},     # ~603 km² (Greater Mumbai)
            "bangalore": {"width": 40, "height": 35},  # ~741 km² (BBMP area)
            "hyderabad": {"width": 45, "height": 40},  # ~650 km² (GHMC area)
            "chennai": {"width": 30, "height": 25},    # ~426 km² (Chennai Corporation)
            "kolkata": {"width": 35, "height": 30},    # ~206 km² (KMC area)
            "pune": {"width": 35, "height": 30},       # ~331 km² (PMC area)
            "ahmedabad": {"width": 40, "height": 35},  # ~505 km² (AMC area)
            "jaipur": {"width": 35, "height": 30},     # ~467 km² (JMC area)
            "surat": {"width": 30, "height": 25},      # ~326 km² (SMC area)
            "lucknow": {"width": 35, "height": 30},    # ~349 km² (LMC area)
            "kanpur": {"width": 30, "height": 25},     # ~267 km² (KNN area)
        }
        
        # Check for city-specific dimensions first
        location_lower = location_name.lower()
        for city, dims in city_dimensions.items():
            if city in location_lower:
                return dims
        
        # Default dimensions based on location type
        default_dimensions = {
            "city": {"width": 30, "height": 25},      # ~400 km² for average city
            "state": {"width": 200, "height": 150},   # Large state coverage
            "district": {"width": 80, "height": 60},  # District coverage
            "town": {"width": 15, "height": 12},      # Small town
            "village": {"width": 8, "height": 6},     # Village area
            "coordinates": {"width": 20, "height": 15} # Default coordinate area
        }
        
        return default_dimensions.get(location_type.lower(), {"width": 30, "height": 25})
        
    def _extract_coordinates_from_text(self, text: str) -> Optional[Tuple[float, float]]:
        """Extract lat/lng coordinates from text using regex patterns."""
        # Pattern for decimal degrees: lat, lng or (lat, lng)
        decimal_pattern = r'(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)'
        
        # Pattern for degrees/minutes/seconds (if needed later)
        # dms_pattern = r'(\d+)°(\d+)\'(\d+\.?\d*)"([NS])\s*(\d+)°(\d+)\'(\d+\.?\d*)"([EW])'
        
        matches = re.findall(decimal_pattern, text)
        for match in matches:
            try:
                lat, lng = float(match[0]), float(match[1])
                
                # Basic validation for Indian coordinates
                # Lat: ~8 to 37, Lng: ~68 to 97
                if 8 <= lat <= 37 and 68 <= lng <= 97:
                    return (lat, lng)
                    
            except ValueError:
                continue
                
        return None
        
    def _extract_place_names_from_text(self, text: str) -> List[str]:
        """Extract potential place names from text (basic implementation)."""
        # This is a simple implementation - could be enhanced with NER
        place_indicators = [
            r'in\s+(\w+)',
            r'near\s+(\w+)', 
            r'around\s+(\w+)',
            r'at\s+(\w+)',
            r'from\s+(\w+)',
            r'to\s+(\w+)'
        ]
        
        places = []
        for pattern in place_indicators:
            matches = re.findall(pattern, text, re.IGNORECASE)
            places.extend(matches)
            
        # Filter out common words that aren't places
        common_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        places = [p for p in places if p.lower() not in common_words and len(p) > 2]
        
        return places[:3]  # Return max 3 potential places
        
    def _create_roi_from_location(self, location_name: str, location_type: str) -> Optional[Dict[str, Any]]:
        """
        Create ROI from a location name and type.
        
        Args:
            location_name: Name of the location
            location_type: Type of location (city, state, etc.)
            
        Returns:
            ROI dict with geometry and metadata, or None if location not found
        """
        # Try to find coordinates for the location
        coords = self._geocode_location(location_name)
        if not coords:
            return None
            
        lat, lng = coords
        
        # Get dynamic ROI dimensions
        dimensions = self._get_dynamic_roi_size(location_type, location_name)
        
        # Create ROI geometry with dynamic dimensions
        roi_geometry = self._create_dynamic_geometry(lat, lng, dimensions)
        
        return {
            "source": "llm_locations",
            "primary_location": {
                "name": location_name,
                "type": location_type,
                "lat": lat,
                "lng": lng,
                "confidence": 90
            },
            "buffer_km": max(dimensions["width"], dimensions["height"]) / 2,  # Equivalent radius for compatibility
            "dimensions": dimensions,  # Add actual dimensions used
            "geometry": roi_geometry
        }

    def _create_buffer_geometry(self, lat: float, lng: float, buffer_km: float) -> Dict[str, Any]:
        """
        Create a simple rectangular buffer around a point.
        
        Args:
            lat: Latitude of center point
            lng: Longitude of center point  
            buffer_km: Buffer distance in kilometers
            
        Returns:
            GeoJSON Polygon geometry
        """
        # Simple rectangular approximation (not geodetically accurate)
        # For more accuracy, use proper geodetic libraries like Shapely with projection
        
        # Rough conversion: 1 degree ≈ 111 km
        lat_offset = buffer_km / 111.0
        lng_offset = buffer_km / (111.0 * abs(lat / 90.0) + 0.1)  # Adjust for latitude
        
        # Create rectangle coordinates [lng, lat] (GeoJSON format)
        coordinates = [[
            [lng - lng_offset, lat - lat_offset],  # Bottom-left
            [lng + lng_offset, lat - lat_offset],  # Bottom-right
            [lng + lng_offset, lat + lat_offset],  # Top-right
            [lng - lng_offset, lat + lat_offset],  # Top-left
            [lng - lng_offset, lat - lat_offset]   # Close polygon
        ]]
        
        return {
            "type": "Polygon",
            "coordinates": coordinates
        }
    
    def _create_dynamic_geometry(self, lat: float, lng: float, dimensions: Dict[str, float]) -> Dict[str, Any]:
        """
        Create a rectangular ROI based on dynamic city dimensions.
        
        Args:
            lat: Latitude of center point
            lng: Longitude of center point  
            dimensions: Dict with 'width' and 'height' in kilometers
            
        Returns:
            GeoJSON Polygon geometry with proper city coverage
        """
        width_km = dimensions["width"]
        height_km = dimensions["height"]
        
        # Convert km to approximate degrees
        # More accurate conversion considering latitude
        lat_offset = height_km / 2 / 111.0  # Half height north/south
        lng_offset = width_km / 2 / (111.0 * abs(lat / 90.0) + 0.1)  # Half width east/west, adjusted for latitude
        
        # Create rectangle coordinates [lng, lat] (GeoJSON format)
        # This creates a proper rectangular coverage of the city
        coordinates = [[
            [lng - lng_offset, lat - lat_offset],  # Southwest corner
            [lng + lng_offset, lat - lat_offset],  # Southeast corner
            [lng + lng_offset, lat + lat_offset],  # Northeast corner
            [lng - lng_offset, lat + lat_offset],  # Northwest corner
            [lng - lng_offset, lat - lat_offset]   # Close polygon
        ]]
        
        return {
            "type": "Polygon",
            "coordinates": coordinates
        }
