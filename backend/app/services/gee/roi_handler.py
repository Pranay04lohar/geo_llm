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
            
        # Geocode the location name to coordinates
        coords = self._geocode_location(location_name)
        if not coords:
            return None
            
        lat, lng = coords
        
        # Determine buffer size based on location type
        location_type = primary_location.get("type", "city").lower()
        buffer_km = self._get_buffer_size(location_type)
        
        # Create ROI geometry
        roi_geometry = self._create_buffer_geometry(lat, lng, buffer_km)
        
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
            "buffer_km": buffer_km,
            "geometry": roi_geometry
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
        
    def _get_buffer_size(self, location_type: str) -> float:
        """Get appropriate buffer size based on location type."""
        buffer_sizes = {
            "city": 2,       # 5km for cities (more reasonable for urban analysis)
            "state": 20,     # 50km for states  
            "district": 10,  # 25km for districts
            "town": 4,       # 4km for towns
            "village": 2,    # 2km for villages
            "coordinates": 3 # 3km for raw coordinates
        }
        
        return buffer_sizes.get(location_type.lower(), 10)  # Default 10km
        
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
        
        # Determine buffer size based on location type
        buffer_km = self._get_buffer_size(location_type)
        
        # Create ROI geometry
        roi_geometry = self._create_buffer_geometry(lat, lng, buffer_km)
        
        return {
            "source": "llm_locations",
            "primary_location": {
                "name": location_name,
                "type": location_type,
                "lat": lat,
                "lng": lng,
                "confidence": 90
            },
            "buffer_km": buffer_km,
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
