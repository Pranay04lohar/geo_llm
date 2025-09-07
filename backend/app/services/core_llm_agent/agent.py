"""
Core LLM Agent - Main orchestrator for the modular geospatial query pipeline.

This is the main entry point that replaces the monolithic core_llm_agent.py.
It orchestrates the entire pipeline: location parsing, intent classification,
service dispatch, and result formatting.
"""

import time
import logging
from typing import Dict, Any, Optional

try:
    # Try relative imports first (when used as module)
    from .parsers.location_parser import LocationParser
    from .intent.intent_classifier import IntentClassifier
    from .dispatcher.service_dispatcher import ServiceDispatcher
    from .output.result_formatter import ResultFormatter
    from .models.intent import IntentResult
    from .models.location import LocationParseResult
except ImportError:
    # Fall back to absolute imports (when run directly)
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent.parent.parent))
    
    from app.services.core_llm_agent.parsers.location_parser import LocationParser
    from app.services.core_llm_agent.intent.intent_classifier import IntentClassifier
    from app.services.core_llm_agent.dispatcher.service_dispatcher import ServiceDispatcher
    from app.services.core_llm_agent.output.result_formatter import ResultFormatter
    from app.services.core_llm_agent.models.intent import IntentResult
    from app.services.core_llm_agent.models.location import LocationParseResult

logger = logging.getLogger(__name__)


class CoreLLMAgent:
    """Main orchestrator for the modular geospatial query pipeline."""
    
    def __init__(
        self, 
        model_name: str = None,
        nominatim_url: str = None,
        enable_debug: bool = False
    ):
        """Initialize the CoreLLMAgent with all pipeline components.
        
        Args:
            model_name: Model name for LLM operations (uses env default if None)
            nominatim_url: Nominatim API URL (uses default if None)
            enable_debug: Whether to enable detailed debug output
        """
        self.enable_debug = enable_debug
        
        # Initialize pipeline components
        self.location_parser = LocationParser(model_name, nominatim_url)
        self.intent_classifier = IntentClassifier(model_name)
        self.service_dispatcher = ServiceDispatcher()
        self.result_formatter = ResultFormatter()
        
        logger.info("CoreLLMAgent initialized with modular pipeline")
    
    def process_query(self, query: str) -> Dict[str, Any]:
        """Process a user query through the complete pipeline.
        
        This is the main entry point that replaces the LangGraph workflow
        from the original core_llm_agent.py.
        
        Args:
            query: User query string
            
        Returns:
            Final result dictionary with analysis and roi
        """
        start_time = time.time()
        
        try:
            logger.info(f"Processing query: {query[:100]}...")
            
            # Validate input
            if not query or not query.strip():
                return self._empty_query_result(time.time() - start_time)
            
            # Step 1: Location Parsing (NER + Geocoding)
            logger.info("Step 1: Parsing locations...")
            location_result = self.location_parser.parse_query(query, resolve_locations=True)
            
            if not location_result.success:
                logger.warning(f"Location parsing failed: {location_result.error}")
            else:
                logger.info(f"Found {len(location_result.entities)} location entities")
            
            # Step 2: Intent Classification (Top-level + GEE sub-classification)
            logger.info("Step 2: Classifying intent...")
            intent_result = self.intent_classifier.classify_intent(query)
            
            if not intent_result.success:
                logger.warning(f"Intent classification failed: {intent_result.error}")
            else:
                logger.info(f"Classified as: {intent_result.service_type.value}" +
                           (f" → {intent_result.gee_sub_intent.value}" if intent_result.gee_sub_intent else ""))
            
            # Step 3: Service Dispatch
            logger.info(f"Step 3: Dispatching to {intent_result.service_type.value} service...")
            service_response = self.service_dispatcher.dispatch(query, intent_result, location_result)
            
            # Step 4: Result Formatting
            logger.info("Step 4: Formatting final result...")
            total_processing_time = time.time() - start_time
            
            if self.enable_debug:
                final_result = self.result_formatter.format_debug_result(
                    query, intent_result, location_result, service_response, total_processing_time
                )
            else:
                final_result = self.result_formatter.format_final_result(
                    query, intent_result, location_result, service_response, total_processing_time
                )
            
            logger.info(f"Query processing complete in {total_processing_time:.2f}s")
            return final_result
            
        except Exception as e:
            total_processing_time = time.time() - start_time
            logger.error(f"Error in query processing: {e}")
            return self.result_formatter._error_result(query, str(e), total_processing_time)
    
    def process_query_legacy(self, query: str) -> Dict[str, Any]:
        """Process query and return in legacy format for backward compatibility.
        
        This method provides the exact same interface as the original
        core_llm_agent.py for seamless replacement.
        
        Args:
            query: User query string
            
        Returns:
            Legacy format result with only analysis and roi fields
        """
        result = self.process_query(query)
        return self.result_formatter.format_legacy_result(result)
    
    def _empty_query_result(self, processing_time: float) -> Dict[str, Any]:
        """Handle empty query case.
        
        Args:
            processing_time: Processing time before validation
            
        Returns:
            Empty query result
        """
        return {
            "analysis": "Empty query provided. Please provide a geospatial query to analyze.",
            "roi": None,
            "metadata": {
                "query": "",
                "service_type": "validation_error",
                "analysis_type": "none",
                "locations_found": 0,
                "processing_time": processing_time,
                "intent_confidence": 0.0,
                "success": False,
                "evidence": ["validation:empty_query"]
            }
        }
    
    # Backward compatibility methods for the original LangGraph interface
    
    def invoke(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """LangGraph-compatible invoke method for backward compatibility.
        
        Args:
            state: State dictionary with query field
            
        Returns:
            Result dictionary with analysis and roi
        """
        query = state.get("query", "")
        return self.process_query_legacy(query)
    
    # Individual component access methods for testing and debugging
    
    def parse_locations_only(self, query: str) -> LocationParseResult:
        """Parse locations without full pipeline execution.
        
        Args:
            query: User query string
            
        Returns:
            LocationParseResult
        """
        return self.location_parser.parse_query(query, resolve_locations=True)
    
    def classify_intent_only(self, query: str) -> IntentResult:
        """Classify intent without full pipeline execution.
        
        Args:
            query: User query string
            
        Returns:
            IntentResult
        """
        return self.intent_classifier.classify_intent(query)
    
    def get_component_status(self) -> Dict[str, Any]:
        """Get status of all pipeline components.
        
        Returns:
            Status dictionary for all components
        """
        return {
            "location_parser": {
                "ner_model": self.location_parser.ner.model_name,
                "geocoder_url": self.location_parser.geocoder.base_url,
                "api_key_configured": bool(self.location_parser.ner.api_key)
            },
            "intent_classifier": {
                "top_level_model": self.intent_classifier.top_level_classifier.model_name,
                "gee_sub_model": self.intent_classifier.gee_subclassifier.model_name,
                "api_key_configured": bool(self.intent_classifier.top_level_classifier.api_key)
            },
            "service_dispatcher": {
                "services_initialized": self.service_dispatcher.services_initialized,
                "gee_services_available": getattr(self.service_dispatcher, 'gee_services_available', False),
                "rag_service_available": getattr(self.service_dispatcher, 'rag_service_available', False)
            },
            "result_formatter": {
                "debug_enabled": self.enable_debug
            }
        }


# Factory function for easy instantiation
def create_agent(
    model_name: str = None,
    nominatim_url: str = None,
    enable_debug: bool = False
) -> CoreLLMAgent:
    """Create a CoreLLMAgent instance with specified configuration.
    
    Args:
        model_name: Model name for LLM operations
        nominatim_url: Nominatim API URL
        enable_debug: Enable debug output
        
    Returns:
        Configured CoreLLMAgent instance
    """
    return CoreLLMAgent(
        model_name=model_name,
        nominatim_url=nominatim_url,
        enable_debug=enable_debug
    )


# Backward compatibility function that mimics the original build_graph()
def build_graph() -> CoreLLMAgent:
    """Build and return a CoreLLMAgent for backward compatibility.
    
    This function replaces the original build_graph() function that returned
    a compiled LangGraph. The CoreLLMAgent provides the same invoke() interface.
    
    Returns:
        CoreLLMAgent configured for production use
    """
    return create_agent(enable_debug=False)


# Sample query runner for testing (replaces run_sample_queries)
def run_sample_queries() -> None:
    """Run sample queries through the modular pipeline."""
    
    agent = create_agent(enable_debug=True)
    
    samples = [
        # Geospatial
        "Analyze NDVI vegetation health around Mumbai with a small buffer",
        "Show land surface temperature and heat island effects for Delhi",
        "What is the land use classification for Bangalore urban areas?",
        # RAG
        "Explain the forest conservation policy in simple terms",
        # WebSearch  
        "What is the latest weather update for Chennai today?",
    ]
    
    for i, query in enumerate(samples, start=1):
        print(f"\n=== SAMPLE {i} ===")
        print(f"Query: {query}")
        result = agent.process_query_legacy(query)
        print(f"Analysis: {result['analysis'][:200]}...")
        print(f"ROI: {'✅ Available' if result['roi'] else '❌ None'}")


if __name__ == "__main__":
    import sys
    
    # CLI mode for testing
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        run_sample_queries()
    elif len(sys.argv) > 1 and sys.argv[1] == "--status":
        agent = create_agent()
        status = agent.get_component_status()
        import json
        print(json.dumps(status, indent=2))
    elif len(sys.argv) > 1 and sys.argv[1] == "--query":
        query = " ".join(sys.argv[2:]) or input("Enter query: ")
        agent = create_agent(enable_debug=True)
        result = agent.process_query(query)
        print(json.dumps(result, indent=2))
    else:
        print("CoreLLMAgent - Modular Geospatial Query Pipeline")
        print("Usage:")
        print("  --test     Run sample queries")
        print("  --status   Show component status")
        print("  --query    Process a single query")
        print("  (no args) Show this help")
