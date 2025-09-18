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
# Reuse the Core LLM Agent's Nominatim client to avoid drift and ensure
# consistent ROI extraction. This client provides search_by_query.
try:
    from app.services.core_llm_agent.parsers.nominatim_client import NominatimClient
except ImportError:
    # When running the search service standalone, ensure backend root is on sys.path
    import sys
    from pathlib import Path
    backend_root = Path(__file__).resolve().parents[3]
    if str(backend_root) not in sys.path:
        sys.path.insert(0, str(backend_root))
    from app.services.core_llm_agent.parsers.nominatim_client import NominatimClient

logger = logging.getLogger(__name__)

class LocationResolver:
    """Resolves location names to geographical data using web search."""
    
    def __init__(self):
        self.tavily_client = TavilyClient()
        self.nominatim_client = NominatimClient()
        
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
        Resolve location name to geographical data using Nominatim.
        
        Args:
            location_name: Name of the location to resolve
            location_type: Type of location (city, state, country, etc.)
            
        Returns:
            Dictionary with location data or None if not found
        """
        try:
            logger.info(f"Resolving location: {location_name} ({location_type})")
            
            # Use Nominatim for accurate location data
            logger.info(f"Calling nominatim_client.search_by_query for {location_name}")
            boundary_infos = self.nominatim_client.search_by_query(location_name, country_code="in", limit=1)
            logger.info(f"Nominatim client returned: {len(boundary_infos)} results")
            
            if boundary_infos:
                boundary_info = boundary_infos[0]
                location_data = {
                    "coordinates": {"lat": boundary_info.center[1], "lng": boundary_info.center[0]},
                    "boundaries": boundary_info.geometry,
                    "area_km2": boundary_info.area_km2,
                    "display_name": boundary_info.display_name,
                    "place_id": boundary_info.place_id,
                    "importance": boundary_info.importance,
                    "location_name": location_name
                }
            else:
                location_data = None
            
            if location_data:
                logger.info(f"Successfully resolved location via Nominatim: {location_name}")
                return location_data
            else:
                logger.warning(f"Could not resolve location via Nominatim: {location_name}")
                return None
                
        except Exception as e:
            logger.error(f"Error resolving location {location_name}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None
    
    async def get_environmental_context(
        self, 
        location_name: str, 
        analysis_type: str, 
        query: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get environmental context using Tavily search.
        
        Args:
            location_name: Name of the location
            analysis_type: Type of analysis (ndvi, climate, etc.)
            query: Original user query
            
        Returns:
            Dictionary with environmental context or None
        """
        try:
            logger.info(f"Getting environmental context for {location_name} ({analysis_type})")
            
            # Generate environmental search queries
            search_queries = self._generate_environmental_queries(location_name, analysis_type)
            
            # Search for environmental information
            all_results = []
            for search_query in search_queries:
                results = await self.tavily_client.search(search_query, max_results=5)
                all_results.extend(results)
            
            if not all_results:
                logger.warning(f"No environmental results found for {location_name}")
                return None
            
            # Process environmental results
            environmental_data = self._process_environmental_results(all_results, analysis_type)
            
            if environmental_data:
                logger.info(f"Successfully retrieved environmental context for {location_name}")
                return environmental_data
            else:
                logger.warning(f"Could not process environmental results for {location_name}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting environmental context for {location_name}: {e}")
            return None
    
    def _generate_environmental_queries(self, location_name: str, analysis_type: str) -> List[str]:
        """Generate environmental search queries for Tavily."""
        queries = []
        
        if analysis_type == "ndvi":
            queries.extend([
                f"{location_name} ndvi analysis 2023",
                f"{location_name} environmental report",
                f"{location_name} vegetation health study",
                f"{location_name} NDVI satellite data",
                f"{location_name} vegetation index study",
                f"{location_name} green cover analysis",
                f"{location_name} environmental policy",
                f"{location_name} conservation initiatives",
                f"{location_name} climate data"
            ])
        elif analysis_type == "climate":
            queries.extend([
                f"{location_name} climate data 2023",
                f"{location_name} weather patterns",
                f"{location_name} temperature rainfall",
                f"{location_name} climate change impact"
            ])
        else:
            queries.extend([
                f"{location_name} environmental conditions",
                f"{location_name} environmental report",
                f"{location_name} environmental data"
            ])
        
        return queries
    
    def _process_environmental_results(self, results: List[Dict[str, Any]], analysis_type: str) -> Optional[Dict[str, Any]]:
        """Process environmental search results."""
        try:
            reports = []
            studies = []
            news = []
            
            for result in results:
                content = result.get("content", "")
                title = result.get("title", "")
                url = result.get("url", "")
                
                # Categorize results
                if any(keyword in content.lower() for keyword in ["report", "study", "research", "analysis"]):
                    studies.append({
                        "title": title,
                        "url": url,
                        "content": content[:500] + "..." if len(content) > 500 else content
                    })
                elif any(keyword in content.lower() for keyword in ["news", "update", "recent", "latest"]):
                    news.append({
                        "title": title,
                        "url": url,
                        "content": content[:300] + "..." if len(content) > 300 else content
                    })
                else:
                    reports.append({
                        "title": title,
                        "url": url,
                        "content": content[:400] + "..." if len(content) > 400 else content
                    })
            
            return {
                "reports": reports,
                "studies": studies,
                "news": news,
                "analysis_type": analysis_type,
                "total_sources": len(results)
            }
            
        except Exception as e:
            logger.error(f"Error processing environmental results: {e}")
            return None
    
    def _generate_location_queries(self, location_name: str, location_type: str) -> List[str]:
        """Generate search queries for location data."""
        queries = []
        
        # Simplified queries - just what we need
        queries.extend([
            f"{location_name} coordinates latitude longitude India",
            f"{location_name} area km2 India",
            f"{location_name} geographical location India"
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
                # Try fallback coordinates for major cities
                coordinates = self._get_fallback_coordinates(location_name)
                if not coordinates:
                    logger.warning(f"Could not extract coordinates for {location_name}")
                    return None
            
            # Extract area
            area_km2 = self._extract_area(combined_content)
            if not area_km2:
                # Try fallback area data for major cities
                area_km2 = self._get_fallback_area(location_name)
            
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
                    
                    # Validate coordinate ranges and Indian region
                    if -90 <= lat <= 90 and -180 <= lng <= 180:
                        # Additional validation for Indian coordinates
                        if 8 <= lat <= 37 and 68 <= lng <= 97:
                            return {"lat": lat, "lng": lng}
                        # Allow other valid coordinates but log warning
                        elif -90 <= lat <= 90 and -180 <= lng <= 180:
                            logger.warning(f"Found non-Indian coordinates: {lat}, {lng}")
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
                        # Additional validation for Indian coordinates
                        if 8 <= lat <= 37 and 68 <= lng <= 97:
                            return {"lat": lat, "lng": lng}
                        # Allow other valid coordinates but log warning
                        elif -90 <= lat <= 90 and -180 <= lng <= 180:
                            logger.warning(f"Found non-Indian coordinates: {lat}, {lng}")
                            return {"lat": lat, "lng": lng}
                except (ValueError, IndexError):
                    continue
        
        return None
    
    def _get_fallback_coordinates(self, location_name: str) -> Optional[Dict[str, float]]:
        """Get fallback coordinates for major Indian cities with accurate data."""
        fallback_coords = {
            "mumbai": {"lat": 19.0760, "lng": 72.8777},
            "delhi": {"lat": 28.7041, "lng": 77.1025},
            "bangalore": {"lat": 12.9716, "lng": 77.5946},
            "kolkata": {"lat": 22.5726, "lng": 88.3639},
            "chennai": {"lat": 13.0827, "lng": 80.2707},
            "hyderabad": {"lat": 17.3850, "lng": 78.4867},
            "pune": {"lat": 18.5204, "lng": 73.8567},
            "ahmedabad": {"lat": 23.0225, "lng": 72.5714},  # Correct coordinates
            "jaipur": {"lat": 26.9124, "lng": 75.7873},
            "surat": {"lat": 21.1702, "lng": 72.8311},
            "lucknow": {"lat": 26.8467, "lng": 80.9462},
            "kanpur": {"lat": 26.4499, "lng": 80.3319},
        }
        
        location_lower = location_name.lower()
        for city, coords in fallback_coords.items():
            if city in location_lower:
                logger.info(f"Using fallback coordinates for {location_name}: {coords}")
                return coords
        
        return None
    
    def _get_fallback_area(self, location_name: str) -> Optional[float]:
        """Get fallback area data for major Indian cities with accurate data."""
        fallback_areas = {
            "mumbai": 603.4,      # Greater Mumbai
            "delhi": 1483.0,      # NCT Delhi
            "bangalore": 741.0,   # BBMP area
            "kolkata": 206.1,     # KMC area
            "chennai": 426.0,     # Chennai Corporation
            "hyderabad": 650.0,   # GHMC area
            "pune": 331.3,        # PMC area
            "ahmedabad": 505.0,   # AMC area - Correct area
            "jaipur": 467.0,      # JMC area
            "surat": 326.0,       # SMC area
            "lucknow": 349.0,     # LMC area
            "kanpur": 267.0,      # KNN area
        }
        
        location_lower = location_name.lower()
        for city, area in fallback_areas.items():
            if city in location_lower:
                logger.info(f"Using fallback area for {location_name}: {area} km²")
                return area
        
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
