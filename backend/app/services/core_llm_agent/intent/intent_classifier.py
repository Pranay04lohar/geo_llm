"""
Intent Classifier - Orchestrates hierarchical intent classification.

This module combines top-level service routing with GEE sub-classification
to provide complete intent analysis for query routing.
"""

import time
import logging
from typing import Dict, Any, Optional

try:
    from .top_level_classifier import TopLevelClassifier
    from .gee_subclassifier import GEESubClassifier
    from ..models.intent import IntentResult, ServiceType, GEESubIntent
except ImportError:
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent.parent.parent.parent))
    
    from app.services.core_llm_agent.intent.top_level_classifier import TopLevelClassifier
    from app.services.core_llm_agent.intent.gee_subclassifier import GEESubClassifier
    from app.services.core_llm_agent.models.intent import IntentResult, ServiceType, GEESubIntent

logger = logging.getLogger(__name__)


class IntentClassifier:
    """Main orchestrator for hierarchical intent classification."""
    
    def __init__(self, model_name: str = None):
        """Initialize the IntentClassifier.
        
        Args:
            model_name: Model name for classification (uses env default if None)
        """
        self.top_level_classifier = TopLevelClassifier(model_name)
        self.gee_subclassifier = GEESubClassifier(model_name)
    
    def classify_intent(self, query: str) -> IntentResult:
        """Perform complete hierarchical intent classification.
        
        Args:
            query: User query string
            
        Returns:
            IntentResult with complete classification results
        """
        start_time = time.time()
        
        try:
            # Step 1: Top-level classification (GEE vs RAG vs Search)
            logger.info(f"Classifying top-level intent for: {query[:100]}...")
            top_level_result = self.top_level_classifier.classify_intent(query)
            
            if not top_level_result.get("success", False):
                logger.warning(f"Top-level classification failed: {top_level_result.get('error')}")
            
            service_type = top_level_result["service_type"]
            confidence = top_level_result["confidence"]
            reasoning = top_level_result["reasoning"]
            
            # Step 2: GEE sub-classification (if needed)
            gee_sub_intent = None
            gee_confidence = None
            analysis_type = "general"
            
            if service_type == ServiceType.GEE:
                logger.info("Performing GEE sub-classification...")
                gee_result = self.gee_subclassifier.classify_gee_intent(query)
                
                if gee_result.get("success", True):  # Keyword fallback always succeeds
                    gee_sub_intent = gee_result["gee_sub_intent"]
                    gee_confidence = gee_result["confidence"]
                    analysis_type = self.gee_subclassifier.get_analysis_type_string(gee_sub_intent)
                    
                    # Combine reasoning
                    reasoning += f" → {gee_result['reasoning']}"
                else:
                    logger.warning(f"GEE sub-classification failed: {gee_result.get('error')}")
                    # Use defaults
                    gee_sub_intent = GEESubIntent.LULC
                    gee_confidence = 0.3
                    analysis_type = "lulc"
            
            # Step 3: Extract additional parameters
            time_range = self._extract_time_range(query)
            metrics = self._extract_metrics(query)
            
            processing_time = time.time() - start_time
            
            # Build final result
            result = IntentResult(
                service_type=service_type,
                confidence=confidence,
                gee_sub_intent=gee_sub_intent,
                gee_confidence=gee_confidence,
                analysis_type=analysis_type,
                time_range=time_range,
                metrics=metrics,
                reasoning=reasoning,
                processing_time=processing_time,
                model_used=top_level_result.get("model_used", "unknown"),
                success=True,
                raw_response={
                    "top_level": top_level_result.get("raw_response"),
                    "gee_sub": gee_result.get("raw_response") if service_type == ServiceType.GEE else None
                }
            )
            
            service_type_str = service_type.value if hasattr(service_type, 'value') else str(service_type)
            gee_sub_str = gee_sub_intent.value if gee_sub_intent and hasattr(gee_sub_intent, 'value') else str(gee_sub_intent) if gee_sub_intent else ""
            logger.info(f"Intent classification complete: {service_type_str}" + 
                       (f" → {gee_sub_str}" if gee_sub_intent else "") + 
                       f" (confidence: {confidence:.2f}) in {processing_time:.2f}s")
            
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Error in intent classification: {e}")
            
            # Return fallback result
            return IntentResult(
                service_type=ServiceType.SEARCH,  # Safe fallback
                confidence=0.1,
                analysis_type="general",
                reasoning=f"Classification failed: {str(e)}",
                processing_time=processing_time,
                model_used="fallback",
                success=False,
                error=str(e)
            )
    
    def _extract_time_range(self, query: str) -> Optional[Dict[str, str]]:
        """Extract time range from query if specified.
        
        Args:
            query: User query string
            
        Returns:
            Dictionary with start and end dates, or None
        """
        # Simple keyword-based time range extraction
        # This could be enhanced with more sophisticated NLP
        query_lower = query.lower()
        
        # Look for common time patterns
        if "last year" in query_lower or "2023" in query:
            return {"start": "2023-01-01", "end": "2023-12-31"}
        elif "this year" in query_lower or "2024" in query:
            return {"start": "2024-01-01", "end": "2024-12-31"}
        elif "last month" in query_lower:
            # Would need more sophisticated date handling
            return None
        elif "summer" in query_lower:
            return {"start": "2023-06-01", "end": "2023-08-31"}
        elif "winter" in query_lower:
            return {"start": "2023-12-01", "end": "2024-02-28"}
        
        return None
    
    def _extract_metrics(self, query: str) -> list[str]:
        """Extract specific metrics mentioned in the query.
        
        Args:
            query: User query string
            
        Returns:
            List of metric names found in the query
        """
        query_lower = query.lower()
        metrics = []
        
        # Common geospatial metrics
        metric_patterns = {
            "ndvi": ["ndvi", "vegetation index", "greenness"],
            "temperature": ["temperature", "temp", "thermal", "heat"],
            "area": ["area", "coverage", "extent"],
            "percentage": ["percentage", "percent", "%", "distribution"],
            "mean": ["mean", "average", "avg"],
            "max": ["maximum", "max", "highest"],
            "min": ["minimum", "min", "lowest"],
            "change": ["change", "difference", "trend", "variation"]
        }
        
        for metric, patterns in metric_patterns.items():
            if any(pattern in query_lower for pattern in patterns):
                metrics.append(metric)
        
        return metrics
    
    def classify_legacy_format(self, query: str) -> str:
        """Classify intent and return in legacy format for backward compatibility.
        
        Args:
            query: User query string
            
        Returns:
            Legacy intent string ("GEE_Tool", "RAG_Tool", "WebSearch_Tool")
        """
        result = self.classify_intent(query)
        
        # Convert to legacy format
        if result.service_type == ServiceType.GEE:
            return "GEE_Tool"
        else:
            return "WebSearch_Tool"
