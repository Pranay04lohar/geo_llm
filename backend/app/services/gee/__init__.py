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
        if evidence is None:
            evidence = []
            
        try:
            # Step 1: Initialize GEE client
            if not self.client.initialize():
                return {
                    "analysis": "Google Earth Engine authentication failed. Please check your credentials.",
                    "roi": None,
                    "evidence": evidence + ["gee_tool:auth_failed"]
                }
            
            # Step 2: Analyze query intent and parameters  
            analysis = self.query_analyzer.analyze_query(query)
            evidence.append("gee_tool:query_analyzed")
            
            # Step 3: Extract ROI from locations or query
            roi = None
            if locations:
                roi = self.roi_handler.extract_roi_from_locations(locations)
                
            if not roi:
                roi = self.roi_handler.extract_roi_from_query(query)
                
            if not roi:
                roi = self.roi_handler.get_default_roi()
                
            evidence.append(f"gee_tool:roi_extracted_{roi.get('source', 'unknown')}")
            
            # Step 4: Generate GEE script
            script_result = self.script_generator.generate_script(
                intent=analysis.get("primary_intent", "general_stats"),
                roi_geometry=roi.get("geometry", {}),
                parameters=analysis
            )
            evidence.append("gee_tool:script_generated")
            
            # Step 5: Execute GEE script with real data
            execution_result = self.client.execute_script(
                script_code=script_result.get("script_code", ""),
                timeout=60
            )
            
            if execution_result.get("success"):
                evidence.append("gee_tool:execution_success")
                gee_data = execution_result.get("data", {})
            else:
                evidence.append("gee_tool:execution_failed")
                # Return error analysis but continue with fallback
                return {
                    "analysis": f"GEE execution failed: {execution_result.get('error', 'Unknown error')}",
                    "roi": roi,
                    "evidence": evidence
                }
            
            # Step 6: Process and format results
            final_result = self.result_processor.process_gee_result(
                gee_result=gee_data,
                script_metadata=script_result.get("metadata", {}),
                roi_info=roi
            )
            evidence.extend(final_result.get("evidence", []))
            
            return {
                "analysis": final_result.get("analysis", "Analysis completed successfully."),
                "roi": final_result.get("roi"),
                "evidence": evidence
            }
            
        except Exception as e:
            evidence.append(f"gee_tool:error_{str(e)[:50]}")
            return {
                "analysis": f"GEE processing error: {str(e)}",
                "roi": None,
                "evidence": evidence
            }

__all__ = ["GEETool"]
