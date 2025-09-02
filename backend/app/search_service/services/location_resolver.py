"""
Location Resolver - Resolves location names to geographical data.

This module provides functionality to resolve location names to:
- Coordinates (latitude, longitude)
- Administrative boundaries
- Area information
- Population data
- Administrative details

Uses web search and geocoding services for comprehensive location data.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
import re
import json
from .tavily_client import TavilyClient

logger = logging.getLogger(__name__)

class LocationResolver:
    """Resolves location names to geographical data using web search."""
    
    def __init__(self):
        self.tavily_client = TavilyClient()
        
        # Common location patterns for extraction
        self.coordinate_patterns = [
            r'(\d+\.?\d*)\s*[°]?\s*[NS]\s*,?\s*(\d+\.?\d*)\s*[°]?\s*[EW]',
            r'lat[itude]?\s*:?\s*(\d+\.?\d*)\s*,?\s*lng?[itude]?\s*:?\s*(\d+\.?\d*)',
            r'(\d+\.?\d*)\s*,?\s*(\d+\.?\d*)',  # Simple lat,lng format
        ]
        
        self.area_patterns = [
            r'(\d+(?:,\d+)*\.?\d*)\s*(?:km²|km2|square kilometers?|sq km)',
            r'area[:\s]*(\d+(?:,\d+)*\.?\d*)\s*(?:km²|km2)',
            r'(\d+(?:,\d+)*\.?\d*)\s*(?:sq\.?\s*km|km\s*squared)',
        ]
        
        self.population_patterns = [
            r'population[:\s]*(\d+(?:,\d+)*\.?\d*)\s*(?:people|inhabitants?|residents?)',
            r'(\d+(?:,\d+)*\.?\d*)\s*(?:people|inhabitants?|residents?)',
            r'(\d+(?:,\d+)*\.?\d*)\s*(?:million|billion|thousand)\s*(?:people|inhabitants?)',
        ]
    
    async def resolve_location(
        self, 
        location_name: str, 
        location_type: str = "city"
    ) -> Optional[Dict[str, Any]]:
        """
        Resolve location name to geographical data.
        
        Args:
            location_name: Name of the location to resolve
            location_type: Type of location (city, state, country, etc.)
            
        Returns:
            Dictionary with location data or None if not found
        """
        try:
            logger.info(f"Resolving location: {location_name} ({location_type})")
            
            # Generate search queries for location data
            search_queries = self._generate_location_queries(location_name, location_type)
            
            # Search for location information
            all_results = []
            for query in search_queries:
                results = await self.tavily_client.search(query, max_results=3)
                all_results.extend(results)
            
            if not all_results:
                logger.warning(f"No search results found for location: {location_name}")
                return None
            
            # Extract location data from search results
            location_data = self._extract_location_data(location_name, all_results)
            
            if location_data:
                logger.info(f"Successfully resolved location: {location_name}")
                return location_data
            else:
                logger.warning(f"Could not extract location data for: {location_name}")
                return None
                
        except Exception as e:
            logger.error(f"Error resolving location {location_name}: {e}")
            return None
    
    def _generate_location_queries(self, location_name: str, location_type: str) -> List[str]:
        """Generate search queries for location data."""
        queries = []
        
        # Basic location queries
        queries.extend([
            f"{location_name} coordinates latitude longitude",
            f"{location_name} geographical location",
            f"{location_name} area population statistics",
            f"{location_name} administrative boundaries",
        ])
        
        # Type-specific queries
        if location_type == "city":
            queries.extend([
                f"{location_name} city area km2",
                f"{location_name} urban area boundaries",
                f"{location_name} metropolitan area",
            ])
        elif location_type == "state":
            queries.extend([
                f"{location_name} state area km2",
                f"{location_name} state boundaries",
                f"{location_name} state population",
            ])
        elif location_type == "country":
            queries.extend([
                f"{location_name} country area km2",
                f"{location_name} national boundaries",
                f"{location_name} country population",
            ])
        
        # Wikipedia and official sources
        queries.extend([
            f"{location_name} wikipedia geographical data",
            f"{location_name} official statistics area",
            f"{location_name} government geographical information",
        ])
        
        return queries
    
    def _extract_location_data(
        self, 
        location_name: str, 
        search_results: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Extract location data from search results."""
        try:
            # Combine all content for analysis
            combined_content = ""
            sources = []
            
            for result in search_results:
                content = result.get("content", "")
                combined_content += f"\n{content}"
                sources.append({
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "score": result.get("score", 0.0)
                })
            
            # Extract coordinates
            coordinates = self._extract_coordinates(combined_content)
            if not coordinates:
                logger.warning(f"Could not extract coordinates for {location_name}")
                return None
            
            # Extract area
            area_km2 = self._extract_area(combined_content)
            
            # Extract population
            population = self._extract_population(combined_content)
            
            # Extract administrative info
            admin_info = self._extract_administrative_info(combined_content, location_name)
            
            # Create boundaries (simple rectangular approximation)
            boundaries = self._create_simple_boundaries(coordinates, area_km2)
            
            location_data = {
                "coordinates": coordinates,
                "boundaries": boundaries,
                "area_km2": area_km2,
                "population": population,
                "administrative_info": admin_info,
                "sources": sources,
                "location_name": location_name
            }
            
            return location_data
            
        except Exception as e:
            logger.error(f"Error extracting location data: {e}")
            return None
    
    def _extract_coordinates(self, content: str) -> Optional[Dict[str, float]]:
        """Extract latitude and longitude from content."""
        content_lower = content.lower()
        
        # Try different coordinate patterns
        for pattern in self.coordinate_patterns:
            matches = re.findall(pattern, content_lower, re.IGNORECASE)
            if matches:
                try:
                    lat, lng = matches[0]
                    lat, lng = float(lat), float(lng)
                    
                    # Validate coordinate ranges
                    if -90 <= lat <= 90 and -180 <= lng <= 180:
                        return {"lat": lat, "lng": lng}
                except (ValueError, IndexError):
                    continue
        
        # Fallback: look for common coordinate formats
        coord_patterns = [
            r'(\d+\.?\d*)\s*[°]?\s*[NS]\s*,?\s*(\d+\.?\d*)\s*[°]?\s*[EW]',
            r'(\d+\.?\d*)\s*,?\s*(\d+\.?\d*)',
        ]
        
        for pattern in coord_patterns:
            matches = re.findall(pattern, content)
            if matches:
                try:
                    lat, lng = matches[0]
                    lat, lng = float(lat), float(lng)
                    
                    # Basic validation
                    if -90 <= lat <= 90 and -180 <= lng <= 180:
                        return {"lat": lat, "lng": lng}
                except (ValueError, IndexError):
                    continue
        
        return None
    
    def _extract_area(self, content: str) -> Optional[float]:
        """Extract area in km² from content."""
        content_lower = content.lower()
        
        for pattern in self.area_patterns:
            matches = re.findall(pattern, content_lower)
            if matches:
                try:
                    area_str = matches[0].replace(',', '')
                    area = float(area_str)
                    
                    # Validate reasonable area range (1 km² to 50M km²)
                    if 1 <= area <= 50000000:
                        return area
                except ValueError:
                    continue
        
        return None
    
    def _extract_population(self, content: str) -> Optional[int]:
        """Extract population from content."""
        content_lower = content.lower()
        
        for pattern in self.population_patterns:
            matches = re.findall(pattern, content_lower)
            if matches:
                try:
                    pop_str = matches[0].replace(',', '')
                    
                    # Handle millions, billions, thousands
                    if 'million' in content_lower:
                        pop = float(pop_str) * 1_000_000
                    elif 'billion' in content_lower:
                        pop = float(pop_str) * 1_000_000_000
                    elif 'thousand' in content_lower:
                        pop = float(pop_str) * 1_000
                    else:
                        pop = float(pop_str)
                    
                    # Validate reasonable population range
                    if 1000 <= pop <= 10_000_000_000:
                        return int(pop)
                except ValueError:
                    continue
        
        return None
    
    def _extract_administrative_info(self, content: str, location_name: str) -> Dict[str, Any]:
        """Extract administrative information from content."""
        admin_info = {
            "name": location_name,
            "type": "unknown",
            "country": None,
            "state": None,
            "region": None
        }
        
        content_lower = content.lower()
        
        # Extract country information
        country_patterns = [
            r'country[:\s]*([^,\n]+)',
            r'in\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'located\s+in\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        ]
        
        for pattern in country_patterns:
            matches = re.findall(pattern, content_lower)
            if matches:
                admin_info["country"] = matches[0].strip()
                break
        
        # Extract state/region information
        state_patterns = [
            r'state[:\s]*([^,\n]+)',
            r'province[:\s]*([^,\n]+)',
            r'region[:\s]*([^,\n]+)',
        ]
        
        for pattern in state_patterns:
            matches = re.findall(pattern, content_lower)
            if matches:
                admin_info["state"] = matches[0].strip()
                break
        
        return admin_info
    
    def _create_simple_boundaries(
        self, 
        coordinates: Dict[str, float], 
        area_km2: Optional[float]
    ) -> Dict[str, Any]:
        """Create simple rectangular boundaries around coordinates."""
        lat = coordinates["lat"]
        lng = coordinates["lng"]
        
        # Default buffer size if area not available
        if area_km2:
            # Calculate approximate buffer based on area
            # Assuming roughly square area
            buffer_km = (area_km2 ** 0.5) / 2
        else:
            # Default buffer for cities
            buffer_km = 15
        
        # Convert km to degrees (approximate)
        lat_offset = buffer_km / 111.0  # 1 degree ≈ 111 km
        lng_offset = buffer_km / (111.0 * abs(lat / 90.0) + 0.1)  # Adjust for latitude
        
        # Create rectangular polygon
        coordinates_list = [
            [lng - lng_offset, lat - lat_offset],  # SW
            [lng + lng_offset, lat - lat_offset],  # SE
            [lng + lng_offset, lat + lat_offset],  # NE
            [lng - lng_offset, lat + lat_offset],  # NW
            [lng - lng_offset, lat - lat_offset]   # Close polygon
        ]
        
        return {
            "type": "Polygon",
            "coordinates": [coordinates_list]
        }
