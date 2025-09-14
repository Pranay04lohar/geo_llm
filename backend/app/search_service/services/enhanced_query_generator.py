"""
Enhanced Query Generator - Generates data-specific search queries for geospatial analysis.

This module provides functionality to:
- Generate targeted queries for different analysis types
- Create multiple search strategies for comprehensive data collection
- Focus on data-rich sources and repositories
- Optimize queries for specific geospatial metrics
"""

import logging
from typing import List, Dict, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)

class AnalysisType(Enum):
    """Supported analysis types."""
    NDVI = "ndvi"
    LST = "lst"
    LULC = "lulc"
    WATER = "water"
    CLIMATE = "climate"
    URBAN = "urban"

class DataSourceType(Enum):
    """Types of data sources to target."""
    SATELLITE_DATA = "satellite_data"
    RESEARCH_PAPERS = "research_papers"
    GOVERNMENT_REPORTS = "government_reports"
    ACADEMIC_DATABASES = "academic_databases"
    ENVIRONMENTAL_AGENCIES = "environmental_agencies"
    NEWS_ARTICLES = "news_articles"

class EnhancedQueryGenerator:
    """Generates enhanced, data-specific search queries for geospatial analysis."""
    
    def __init__(self):
        # Data-specific keywords for different analysis types
        self.analysis_keywords = {
            AnalysisType.NDVI: [
                "vegetation index", "green cover", "forest cover", "vegetation health",
                "NDVI values", "satellite imagery", "remote sensing", "biomass",
                "vegetation density", "greenness index", "plant health"
            ],
            AnalysisType.LST: [
                "land surface temperature", "thermal data", "heat island", "temperature",
                "LST values", "thermal imagery", "surface heat", "urban heat",
                "temperature mapping", "thermal analysis", "heat distribution"
            ],
            AnalysisType.LULC: [
                "land use", "land cover", "urbanization", "built-up area",
                "agricultural land", "forest land", "water bodies", "land classification",
                "spatial analysis", "land change", "development patterns"
            ],
            AnalysisType.WATER: [
                "water bodies", "water resources", "water quality", "aquatic systems",
                "water monitoring", "hydrological data", "water management", "wetlands",
                "water availability", "water stress", "water security"
            ],
            AnalysisType.CLIMATE: [
                "climate data", "weather patterns", "precipitation", "temperature trends",
                "climate change", "meteorological data", "climate monitoring", "weather stations",
                "climate indicators", "environmental conditions"
            ],
            AnalysisType.URBAN: [
                "urban development", "city planning", "urban growth", "infrastructure",
                "population density", "urban sprawl", "city expansion", "urban planning",
                "municipal data", "urban indicators"
            ]
        }
        
        # Data source specific domains and keywords
        self.data_sources = {
            DataSourceType.SATELLITE_DATA: {
                "domains": ["nasa.gov", "usgs.gov", "esa.int", "copernicus.eu", "earthengine.google.com"],
                "keywords": ["satellite data", "remote sensing", "imagery", "Landsat", "MODIS", "Sentinel"]
            },
            DataSourceType.RESEARCH_PAPERS: {
                "domains": [".edu", "researchgate.net", "scholar.google.com", "academia.edu"],
                "keywords": ["research paper", "study", "academic", "peer-reviewed", "journal"]
            },
            DataSourceType.GOVERNMENT_REPORTS: {
                "domains": [".gov", "government", "ministry", "department", "agency"],
                "keywords": ["official report", "government data", "ministry", "department", "agency"]
            },
            DataSourceType.ACADEMIC_DATABASES: {
                "domains": ["jstor.org", "springer.com", "ieee.org", "sciencedirect.com"],
                "keywords": ["database", "academic", "scholarly", "peer-reviewed", "journal"]
            },
            DataSourceType.ENVIRONMENTAL_AGENCIES: {
                "domains": ["epa.gov", "unep.org", "who.int", "environment", "conservation"],
                "keywords": ["environmental", "conservation", "sustainability", "ecology", "biodiversity"]
            },
            DataSourceType.NEWS_ARTICLES: {
                "domains": ["news", "article", "media", "press"],
                "keywords": ["news", "article", "report", "update", "latest"]
            }
        }
        
        # Location-specific enhancements
        self.location_enhancements = {
            "india": ["India", "Indian", "subcontinent", "South Asia"],
            "delhi": ["Delhi", "New Delhi", "NCT", "National Capital Territory"],
            "mumbai": ["Mumbai", "Bombay", "Maharashtra", "financial capital"],
            "bangalore": ["Bangalore", "Bengaluru", "Karnataka", "IT capital"],
            "chennai": ["Chennai", "Madras", "Tamil Nadu", "southern India"]
        }
    
    def generate_enhanced_queries(
        self, 
        analysis_type: AnalysisType, 
        location: str, 
        max_queries: int = 5  # Reduced from 8 to 5 for faster processing
    ) -> List[Dict[str, Any]]:
        """
        Generate enhanced, data-specific search queries.
        
        Args:
            analysis_type: Type of analysis to perform
            location: Location to analyze
            max_queries: Maximum number of queries to generate
            
        Returns:
            List of query dictionaries with metadata
        """
        try:
            logger.info(f"Generating enhanced queries for {analysis_type.value} analysis in {location}")
            
            queries = []
            
            # 1. Data-specific queries (highest priority)
            data_queries = self._generate_data_specific_queries(analysis_type, location)
            queries.extend(data_queries[:2])  # Top 2 data-specific queries
            
            # 2. Source-specific queries
            source_queries = self._generate_source_specific_queries(analysis_type, location)
            queries.extend(source_queries[:2])  # Top 2 source-specific queries
            
            # 3. Metric-specific queries
            metric_queries = self._generate_metric_specific_queries(analysis_type, location)
            queries.extend(metric_queries[:1])  # Top 1 metric-specific query
            
            # Limit to max_queries
            return queries[:max_queries]
            
        except Exception as e:
            logger.error(f"Error generating enhanced queries: {e}")
            return self._generate_fallback_queries(analysis_type, location)
    
    def _generate_data_specific_queries(
        self, 
        analysis_type: AnalysisType, 
        location: str
    ) -> List[Dict[str, Any]]:
        """Generate queries focused on specific data types and metrics."""
        queries = []
        keywords = self.analysis_keywords.get(analysis_type, [])
        
        # Query 1: Specific metrics and values
        metric_query = f'"{location}" {" ".join(keywords[:3])} data values metrics statistics'
        queries.append({
            "query": metric_query,
            "type": "data_specific",
            "priority": "high",
            "description": f"Specific {analysis_type.value} metrics for {location}",
            "expected_data": ["numerical_values", "statistics", "measurements"]
        })
        
        # Query 2: Recent data and trends
        trend_query = f'"{location}" {" ".join(keywords[:2])} 2023 2024 recent data trends analysis'
        queries.append({
            "query": trend_query,
            "type": "data_specific",
            "priority": "high",
            "description": f"Recent {analysis_type.value} trends for {location}",
            "expected_data": ["temporal_data", "trends", "recent_values"]
        })
        
        # Query 3: Satellite and remote sensing data
        satellite_query = f'"{location}" {" ".join(keywords[:2])} satellite imagery remote sensing data download'
        queries.append({
            "query": satellite_query,
            "type": "data_specific",
            "priority": "high",
            "description": f"Satellite data for {analysis_type.value} in {location}",
            "expected_data": ["satellite_data", "imagery", "remote_sensing"]
        })
        
        return queries
    
    def _generate_source_specific_queries(
        self, 
        analysis_type: AnalysisType, 
        location: str
    ) -> List[Dict[str, Any]]:
        """Generate queries targeting specific data sources."""
        queries = []
        keywords = self.analysis_keywords.get(analysis_type, [])
        
        # Government and official sources
        gov_query = f'site:gov.in OR site:nic.in "{location}" {" ".join(keywords[:2])} official data report'
        queries.append({
            "query": gov_query,
            "type": "source_specific",
            "priority": "high",
            "description": f"Government data for {analysis_type.value} in {location}",
            "expected_data": ["official_reports", "government_data", "policy_documents"],
            "include_domains": [".gov.in", ".nic.in"]
        })
        
        # Academic and research sources
        academic_query = f'site:edu OR site:researchgate.net "{location}" {" ".join(keywords[:2])} research study paper'
        queries.append({
            "query": academic_query,
            "type": "source_specific",
            "priority": "medium",
            "description": f"Academic research for {analysis_type.value} in {location}",
            "expected_data": ["research_papers", "academic_studies", "scientific_data"],
            "include_domains": [".edu", "researchgate.net"]
        })
        
        # Environmental agencies
        env_query = f'site:epa.gov OR site:unep.org OR site:who.int "{location}" {" ".join(keywords[:2])} environmental data'
        queries.append({
            "query": env_query,
            "type": "source_specific",
            "priority": "medium",
            "description": f"Environmental agency data for {analysis_type.value} in {location}",
            "expected_data": ["environmental_reports", "agency_data", "monitoring_data"],
            "include_domains": ["epa.gov", "unep.org", "who.int"]
        })
        
        return queries
    
    def _generate_metric_specific_queries(
        self, 
        analysis_type: AnalysisType, 
        location: str
    ) -> List[Dict[str, Any]]:
        """Generate queries focused on specific metrics and measurements."""
        queries = []
        
        if analysis_type == AnalysisType.NDVI:
            queries.extend([
                {
                    "query": f'"{location}" NDVI values 0.1 0.2 0.3 0.4 0.5 0.6 0.7 0.8 0.9 vegetation index range',
                    "type": "metric_specific",
                    "priority": "high",
                    "description": f"NDVI value ranges for {location}",
                    "expected_data": ["ndvi_values", "vegetation_index", "greenness_metrics"]
                },
                {
                    "query": f'"{location}" forest cover percentage area km2 vegetation density biomass',
                    "type": "metric_specific",
                    "priority": "high",
                    "description": f"Vegetation area and density metrics for {location}",
                    "expected_data": ["area_measurements", "percentage_values", "density_metrics"]
                }
            ])
        elif analysis_type == AnalysisType.LST:
            queries.extend([
                {
                    "query": f'"{location}" land surface temperature degrees celsius °C thermal data heat island',
                    "type": "metric_specific",
                    "priority": "high",
                    "description": f"Temperature values for {location}",
                    "expected_data": ["temperature_values", "thermal_data", "heat_metrics"]
                },
                {
                    "query": f'"{location}" urban heat island temperature difference °C thermal analysis',
                    "type": "metric_specific",
                    "priority": "medium",
                    "description": f"Urban heat island analysis for {location}",
                    "expected_data": ["heat_island_data", "temperature_differences", "urban_thermal"]
                }
            ])
        elif analysis_type == AnalysisType.LULC:
            queries.extend([
                {
                    "query": f'"{location}" land use land cover percentage built-up area agricultural forest water',
                    "type": "metric_specific",
                    "priority": "high",
                    "description": f"Land use percentages for {location}",
                    "expected_data": ["land_use_percentages", "area_breakdown", "classification_data"]
                },
                {
                    "query": f'"{location}" urbanization rate built-up area growth percentage change',
                    "type": "metric_specific",
                    "priority": "medium",
                    "description": f"Urbanization metrics for {location}",
                    "expected_data": ["urbanization_rates", "growth_metrics", "change_analysis"]
                }
            ])
        
        return queries
    
    def _generate_fallback_queries(
        self, 
        analysis_type: AnalysisType, 
        location: str
    ) -> List[Dict[str, Any]]:
        """Generate basic fallback queries if enhanced generation fails."""
        return [
            {
                "query": f'"{location}" {analysis_type.value} data analysis',
                "type": "fallback",
                "priority": "low",
                "description": f"Basic {analysis_type.value} query for {location}",
                "expected_data": ["general_data"]
            }
        ]
    
    def get_analysis_type_from_string(self, analysis_type_str: str) -> AnalysisType:
        """Convert string to AnalysisType enum."""
        analysis_type_str = analysis_type_str.lower().strip()
        for analysis_type in AnalysisType:
            if analysis_type.value == analysis_type_str:
                return analysis_type
        return AnalysisType.NDVI  # Default fallback
    
    def enhance_location_name(self, location: str) -> str:
        """Enhance location name with additional context."""
        location_lower = location.lower().strip()
        
        # Add country context for Indian cities
        if location_lower in ["delhi", "mumbai", "bangalore", "chennai", "kolkata", "hyderabad"]:
            return f"{location}, India"
        
        # Add state context for major cities
        state_mapping = {
            "delhi": "Delhi, NCT, India",
            "mumbai": "Mumbai, Maharashtra, India",
            "bangalore": "Bangalore, Karnataka, India",
            "chennai": "Chennai, Tamil Nadu, India",
            "kolkata": "Kolkata, West Bengal, India",
            "hyderabad": "Hyderabad, Telangana, India"
        }
        
        return state_mapping.get(location_lower, location)
