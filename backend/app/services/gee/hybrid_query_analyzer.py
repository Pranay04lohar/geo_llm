"""
Hybrid Query Analyzer

Combines fast regex-based intent detection with LLM-based refinement
for optimal accuracy and performance in geospatial query analysis.
"""

import re
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

try:
    import requests
    import json
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    from dotenv import load_dotenv
    load_dotenv()
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False

from .query_analyzer import QueryAnalyzer  # Original regex-based analyzer


class HybridQueryAnalyzer:
    """
    Hybrid query analyzer that combines regex patterns with LLM capabilities.
    
    Strategy:
    1. Fast regex-based detection for explicit technical terms
    2. LLM fallback for ambiguous or complex queries
    3. LLM confidence scoring and intent refinement
    """
    
    def __init__(self, openrouter_api_key: Optional[str] = None):
        """Initialize hybrid analyzer with both regex and LLM capabilities."""
        self.regex_analyzer = QueryAnalyzer()
        
        # Try to get API key from parameter, environment, or .env file (same as core_llm_agent.py)
        if openrouter_api_key:
            self.openrouter_api_key = openrouter_api_key
        else:
            # Load .env from backend repo root (same approach as core_llm_agent.py)
            try:
                import os
                current_dir = os.path.dirname(os.path.abspath(__file__))
                backend_root = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))
                dotenv_path = os.path.join(backend_root, ".env")
                load_dotenv(dotenv_path, override=False)
            except Exception:
                pass
            
            import os
            self.openrouter_api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
            
        self.llm_available = REQUESTS_AVAILABLE and self.openrouter_api_key
        
        # Confidence thresholds
        self.HIGH_CONFIDENCE_THRESHOLD = 0.8  # Use regex result directly
        self.LOW_CONFIDENCE_THRESHOLD = 0.4   # Use LLM refinement
        
    def analyze_query(self, query: str, use_llm_fallback: bool = True) -> Dict[str, Any]:
        """
        Analyze query using hybrid approach.
        
        Args:
            query: User query string
            use_llm_fallback: Whether to use LLM for low-confidence cases
            
        Returns:
            Dict with enhanced analysis results
        """
        start_time = time.time()
        
        # Step 1: Fast regex-based analysis
        regex_result = self.regex_analyzer.analyze_query(query)
        regex_confidence = regex_result.get("confidence", 0.0)
        
        # Step 2: Determine if LLM refinement is needed
        needs_llm_refinement = (
            self.llm_available and 
            use_llm_fallback and 
            regex_confidence < self.HIGH_CONFIDENCE_THRESHOLD
        )
        
        if needs_llm_refinement:
            # Step 3: LLM-based refinement for ambiguous cases
            llm_result = self._llm_analyze_query(query, regex_result)
            final_result = self._merge_results(regex_result, llm_result)
            final_result["analysis_method"] = "hybrid"
        else:
            # Use regex result directly for high-confidence cases
            final_result = regex_result
            final_result["analysis_method"] = "regex_only"
            
        final_result["processing_time_ms"] = round((time.time() - start_time) * 1000, 2)
        return final_result
        
    def _llm_analyze_query(self, query: str, regex_baseline: Dict[str, Any]) -> Dict[str, Any]:
        """Use LLM to analyze query with regex baseline as context."""
        if not self.llm_available:
            return {}
            
        # Available analysis types for LLM
        analysis_types = [
            "ndvi - vegetation health and greenness analysis",
            "landcover - surface classification (urban, forest, water, etc.)",
            "change_detection - temporal analysis of landscape changes",
            "water_analysis - water body detection and mapping", 
            "climate_weather - meteorological data analysis",
            "urban_analysis - built-up area and development tracking",
            "forest_analysis - tree cover and deforestation monitoring",
            "agriculture - crop mapping and agricultural monitoring",
            "general_stats - basic geospatial measurements"
        ]
        
        prompt = f"""Analyze this geospatial query and determine the primary analysis intent:

Query: "{query}"

Available analysis types:
{chr(10).join(f"- {t}" for t in analysis_types)}

Current regex detection: {regex_baseline.get('primary_intent', 'unknown')} (confidence: {regex_baseline.get('confidence', 0)})

Respond with JSON only:
{{
    "primary_intent": "most_relevant_type",
    "confidence": 0.95,
    "reasoning": "why this classification makes sense",
    "secondary_intents": ["other_relevant_types"],
    "complexity": "simple|moderate|complex"
}}"""

        try:
            # Use OpenRouter API (same as your core_llm_agent.py approach)
            url = "https://openrouter.ai/api/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.openrouter_api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost",
                "X-Title": "GeoLLM Hybrid Query Analyzer",
            }
            
            payload = {
                "model": "deepseek/deepseek-r1:free",  # Same as your main model
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,  # Low temperature for consistent classification
                "max_tokens": 200,
                "response_format": {"type": "json_object"},
            }
            
            resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=20)
            resp.raise_for_status()
            data = resp.json()
            content = (
                data.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
                .strip()
            )
            
            if not content:
                return {"error": "Empty response from LLM"}
                
            llm_analysis = json.loads(content)
            return llm_analysis
            
        except Exception as e:
            # Fallback to regex on LLM failure
            return {"error": f"LLM analysis failed: {str(e)}"}
            
    def _merge_results(self, regex_result: Dict[str, Any], llm_result: Dict[str, Any]) -> Dict[str, Any]:
        """Intelligently merge regex and LLM analysis results."""
        if "error" in llm_result:
            # LLM failed, use regex
            return regex_result
            
        # Use LLM intent if confidence is higher, otherwise keep regex
        llm_confidence = llm_result.get("confidence", 0.0)
        regex_confidence = regex_result.get("confidence", 0.0)
        
        if llm_confidence > regex_confidence + 0.1:  # LLM needs significant confidence advantage
            primary_intent = llm_result.get("primary_intent", regex_result["primary_intent"])
            final_confidence = llm_confidence
            analysis_source = "llm_override"
        else:
            primary_intent = regex_result["primary_intent"] 
            final_confidence = max(regex_confidence, llm_confidence * 0.8)  # Boost regex confidence
            analysis_source = "regex_confirmed"
            
        # Merge datasets and parameters from regex (more reliable)
        merged = regex_result.copy()
        merged.update({
            "primary_intent": primary_intent,
            "confidence": final_confidence,
            "llm_reasoning": llm_result.get("reasoning", ""),
            "analysis_source": analysis_source,
            "query_complexity": llm_result.get("complexity", "moderate")
        })
        
        return merged

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics for the hybrid analyzer."""
        return {
            "regex_analyzer": "Always available, ~1-5ms",
            "llm_analyzer": f"Available: {self.llm_available}, ~200-2000ms",
            "strategy": "Fast regex first, LLM refinement for ambiguous cases",
            "confidence_thresholds": {
                "high_confidence": self.HIGH_CONFIDENCE_THRESHOLD,
                "low_confidence": self.LOW_CONFIDENCE_THRESHOLD
            }
        }
