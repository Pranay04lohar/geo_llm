"""
Google Earth Engine (GEE) Tool Package

This package provides Google Earth Engine integration for geospatial analysis
within the GeoLLM agent pipeline.

Modules:
- gee_client: GEE authentication and client setup
- roi_handler: Region of Interest extraction and validation
- query_analyzer: Intent detection and parameter extraction
- script_generator: Dynamic GEE script generation
- result_processor: Output formatting and statistics

Usage:
    from backend.app.services.gee import GEETool
    
    # Initialize with authentication
    gee_tool = GEETool()
    
    # Process a geospatial query
    result = gee_tool.process_query(query, locations, evidence)
"""

__version__ = "1.0.0"
__author__ = "GeoLLM Team"

# Main tool class that orchestrates all components
class GEETool:
    """Main Google Earth Engine tool class for the LLM agent."""
    
    def __init__(self):
        """Initialize GEE tool with all required components."""
        # Import here to avoid circular imports
        from .gee_client import GEEClient
        from .roi_handler import ROIHandler
        from .query_analyzer import QueryAnalyzer
        from .script_generator import ScriptGenerator
        from .result_processor import ResultProcessor
        
        self.client = GEEClient()
        self.roi_handler = ROIHandler()
        self.query_analyzer = QueryAnalyzer()
        self.script_generator = ScriptGenerator()
        self.result_processor = ResultProcessor()
        
    def process_query(self, query: str, locations: list = None, evidence: list = None):
        """
        Process a geospatial query using Google Earth Engine.
        
        Args:
            query: User query string
            locations: List of extracted location entities
            evidence: List for tracking execution steps
            
        Returns:
            Dict with 'analysis', 'roi', and 'evidence' keys
        """
        # This will be implemented after individual components are ready
        pass

__all__ = ["GEETool"]
