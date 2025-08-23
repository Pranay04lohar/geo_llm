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
        """Initialize GEE tool with template-based architecture."""
        # Import here to avoid circular imports
        from .gee_client import GEEClient
        from .roi_handler import ROIHandler
        from .template_loader import TemplateLoader
        from .result_processor import ResultProcessor
        
        # Always use hybrid analyzer as default (fallback to regex-only internally)
        try:
            from .hybrid_query_analyzer import HybridQueryAnalyzer
            self.query_analyzer = HybridQueryAnalyzer()  # Auto-detects OpenRouter key
        except ImportError:
            # Ultimate fallback if hybrid analyzer is not available
            from .query_analyzer import QueryAnalyzer
            self.query_analyzer = QueryAnalyzer()
        
        # Template-based system
        self.template_loader = TemplateLoader()
        
        # Legacy components (kept for fallback)
        from .script_generator import ScriptGenerator
        self.client = GEEClient()
        self.roi_handler = ROIHandler()
        self.script_generator = ScriptGenerator()
        self.result_processor = ResultProcessor()
        
    def process_query(self, query: str, locations: list = None, evidence: list = None):
        """
        Process a geospatial query using template-based Google Earth Engine analysis.
        
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
            
            # Step 2: Analyze query with template classification
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
            
            # Step 4: Try template-based execution first
            template_name = analysis.get("template_recommendation") or analysis.get("primary_intent")
            
            if template_name and template_name in self.template_loader.get_available_templates():
                evidence.append(f"gee_tool:using_template_{template_name}")
                
                # Execute using template (pass initialized GEE client)
                template_result = self.template_loader.execute_template(
                    template_name=template_name,
                    roi_geometry=roi.get("geometry", {}),
                    params=analysis.get("parameters", {}),
                    gee_client=self.client
                )
                
                if template_result.get("execution_success", False):
                    evidence.append("gee_tool:template_execution_success")
                    
                    # Build script_metadata from template result
                    script_metadata = {
                        "analysis_type": template_name, 
                        "template_used": template_name,
                        "datasets_used": template_result.get("datasets_used", []),
                        "expected_processing_time_seconds": 0  # Template execution time
                    }
                    
                    # Process template results
                    final_result = self.result_processor.process_gee_result(
                        gee_result=template_result,
                        script_metadata=script_metadata,
                        roi_info=roi
                    )
                    evidence.extend(final_result.get("evidence", []))
                    
                    return {
                        "analysis": final_result.get("analysis", f"Template-based {template_name} analysis completed."),
                        "roi": final_result.get("roi"),
                        "evidence": evidence
                    }
                else:
                    evidence.append("gee_tool:template_execution_failed")
                    # Fall back to legacy system
            else:
                evidence.append("gee_tool:no_template_match")
            
            # Step 5: Fallback to legacy script generation system
            evidence.append("gee_tool:fallback_to_legacy")
            
            script_result = self.script_generator.generate_script(
                intent=analysis.get("primary_intent", "general_stats"),
                roi_geometry=roi.get("geometry", {}),
                parameters=analysis
            )
            evidence.append("gee_tool:script_generated")
            
            # Execute GEE script with real data
            execution_result = self.client.execute_script(
                script_code=script_result.get("script_code", ""),
                timeout=60
            )
            
            if execution_result.get("success"):
                evidence.append("gee_tool:execution_success")
                gee_data = execution_result.get("data", {})
            else:
                evidence.append("gee_tool:execution_failed")
                return {
                    "analysis": f"GEE execution failed: {execution_result.get('error', 'Unknown error')}",
                    "roi": roi,
                    "evidence": evidence
                }
            
            # Process and format results
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
