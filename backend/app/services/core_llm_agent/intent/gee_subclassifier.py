"""
GEE sub-intent classifier for geospatial analysis type routing.

This module determines which specific GEE analysis should be performed
(NDVI, LULC, LST, etc.) based on query content.
"""

import json
import time
import requests
import logging
from typing import Dict, Any, Optional

try:
    from ..models.intent import GEESubIntent
    from ..config import get_openrouter_config
except ImportError:
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent.parent.parent.parent))
    
    from app.services.core_llm_agent.models.intent import GEESubIntent
    from app.services.core_llm_agent.config import get_openrouter_config

logger = logging.getLogger(__name__)


class GEESubClassifier:
    """Classifier for GEE sub-intent routing."""
    
    def __init__(self, model_name: str = None):
        """Initialize the GEESubClassifier.
        
        Args:
            model_name: Model name for classification (uses env default if None)
        """
        config = get_openrouter_config()
        self.model_name = model_name or config["intent_model"]
        self.api_key = config["api_key"]
        self.referrer = config["referrer"]
        self.app_title = config["app_title"]
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        
        if not self.api_key:
            logger.warning("OPENROUTER_API_KEY not set. GEE sub-classification will use fallback.")
    
    def classify_gee_intent(self, query: str) -> Dict[str, Any]:
        """Classify GEE sub-intent for specific analysis type.
        
        Args:
            query: User query string
            
        Returns:
            Dictionary with gee_sub_intent, confidence, reasoning, and metadata
        """
        if not query.strip():
            return {
                "gee_sub_intent": GEESubIntent.LULC,
                "confidence": 0.0,
                "reasoning": "Empty query, defaulting to LULC",
                "success": False,
                "error": "Empty query"
            }
        
        # Try LLM classification first, fallback to keyword matching
        if self.api_key:
            try:
                return self._llm_classify_gee_intent(query)
            except Exception as e:
                logger.warning(f"LLM GEE classification failed: {e}, using keyword fallback")
        
        # Fallback to keyword-based classification
        return self._keyword_classify_gee_intent(query)
    
    def _llm_classify_gee_intent(self, query: str) -> Dict[str, Any]:
        """LLM-based GEE sub-intent classification.
        
        Args:
            query: User query string
            
        Returns:
            Dictionary with classification results
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": self.referrer,
            "X-Title": self.app_title,
        }
        
        system_prompt = (
            "You are a geospatial analysis classifier. Given a query for geospatial analysis, "
            "determine the most appropriate analysis type and respond with JSON only:\n"
            "{\"analysis_type\": \"NDVI|LULC|LST|CLIMATE|WATER|SOIL|POPULATION|TRANSPORTATION\", \"confidence\": 0.95, \"reasoning\": \"brief explanation\"}\n\n"
            "Analysis Types:\n"
            "- NDVI: vegetation analysis, greenness, plant health, forest cover, biomass\n"
            "- LULC: land use/land cover, urban development, built areas, agriculture, classification\n"
            "- LST: temperature analysis, heat islands, thermal analysis, surface temperature, UHI\n"
            "- CLIMATE: weather patterns, precipitation, climate data\n"
            "- WATER: hydrology, water bodies, rivers, lakes, water quality\n"
            "- SOIL: soil analysis, erosion, soil health\n"
            "- POPULATION: demographics, population density\n"
            "- TRANSPORTATION: roads, infrastructure, transportation networks\n\n"
            "Choose the MOST SPECIFIC type that matches the query. If multiple apply, pick the primary focus."
        )
        
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }
        
        start_time = time.time()
        
        resp = requests.post(self.base_url, headers=headers, data=json.dumps(payload), timeout=15)
        resp.raise_for_status()
        processing_time = time.time() - start_time
        
        data = resp.json()
        content = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )
        
        if not content:
            raise RuntimeError("LLM returned empty content")
        
        parsed = json.loads(content)
        analysis_type_str = parsed.get("analysis_type", "").upper()
        confidence = float(parsed.get("confidence", 0.0))
        reasoning = parsed.get("reasoning", "No reasoning provided")
        
        # Convert to GEESubIntent enum
        gee_sub_intent = None
        try:
            gee_sub_intent = GEESubIntent(analysis_type_str)
        except ValueError:
            # Fallback if invalid analysis type returned
            logger.warning(f"Invalid analysis type from LLM: {analysis_type_str}")
            gee_sub_intent = self._keyword_classify_gee_intent(query)["gee_sub_intent"]
            reasoning = f"LLM returned invalid type '{analysis_type_str}', used keyword fallback"
            confidence = 0.5
        
        gee_sub_str = gee_sub_intent.value if hasattr(gee_sub_intent, 'value') else str(gee_sub_intent)
        logger.info(f"GEE sub-intent: {gee_sub_str} (confidence: {confidence:.2f}) in {processing_time:.2f}s")
        
        return {
            "gee_sub_intent": gee_sub_intent,
            "confidence": confidence,
            "reasoning": reasoning,
            "processing_time": processing_time,
            "model_used": self.model_name,
            "success": True,
            "raw_response": parsed
        }
    
    def _keyword_classify_gee_intent(self, query: str) -> Dict[str, Any]:
        """Keyword-based GEE sub-intent classification fallback.
        
        Args:
            query: User query string
            
        Returns:
            Dictionary with classification results
        """
        start_time = time.time()
        query_lower = query.lower()
        
        # Define keyword patterns for each analysis type
        patterns = {
            GEESubIntent.LST: [
                "temperature", "heat", "thermal", "lst", "land surface temperature",
                "urban heat island", "uhi", "hot", "cool", "warming", "climate",
                "surface temp", "thermal analysis", "heat island", "temperature analysis"
            ],
            GEESubIntent.NDVI: [
                "ndvi", "vegetation", "greenness", "plant", "tree", "forest health",
                "vegetation index", "canopy", "biomass", "chlorophyll", "photosynthesis",
                "vegetation analysis", "vegetation health", "green cover", "leaf"
            ],
            GEESubIntent.LULC: [
                "land use", "land cover", "lulc", "urban", "built", "classification",
                "developed", "settlement", "infrastructure", "city", "agricultural",
                "cropland", "farming", "development", "construction"
            ],
            GEESubIntent.CLIMATE: [
                "weather", "precipitation", "rainfall", "climate", "meteorology",
                "atmospheric", "wind", "humidity", "pressure"
            ],
            GEESubIntent.WATER: [
                "water", "river", "lake", "hydrology", "watershed", "stream",
                "water body", "aquatic", "marine", "coastal", "flood"
            ],
            GEESubIntent.SOIL: [
                "soil", "erosion", "sediment", "agriculture", "farming",
                "soil health", "soil quality", "degradation"
            ],
            GEESubIntent.POPULATION: [
                "population", "demographics", "density", "people", "inhabitants",
                "census", "urban population", "settlement patterns"
            ],
            GEESubIntent.TRANSPORTATION: [
                "road", "highway", "transportation", "infrastructure", "network",
                "connectivity", "accessibility", "traffic", "mobility"
            ]
        }
        
        # Score each analysis type
        scores = {}
        for analysis_type, keywords in patterns.items():
            score = sum(1 for keyword in keywords if keyword in query_lower)
            if score > 0:
                scores[analysis_type] = score
        
        # Determine best match
        if not scores:
            # Default to LULC for general geospatial queries
            gee_sub_intent = GEESubIntent.LULC
            confidence = 0.3
            reasoning = "No specific keywords found, defaulting to LULC analysis"
        else:
            # Get the analysis type with highest score
            gee_sub_intent = max(scores.keys(), key=lambda k: scores[k])
            max_score = scores[gee_sub_intent]
            total_keywords = len(patterns[gee_sub_intent])
            confidence = min(0.9, max_score / total_keywords + 0.1)  # Scale confidence
            gee_sub_str = gee_sub_intent.value if hasattr(gee_sub_intent, 'value') else str(gee_sub_intent)
            reasoning = f"Keyword match: {max_score} keywords found for {gee_sub_str}"
        
        processing_time = time.time() - start_time
        
        gee_sub_str = gee_sub_intent.value if hasattr(gee_sub_intent, 'value') else str(gee_sub_intent)
        logger.info(f"GEE sub-intent (keyword): {gee_sub_str} (confidence: {confidence:.2f})")
        
        return {
            "gee_sub_intent": gee_sub_intent,
            "confidence": confidence,
            "reasoning": reasoning,
            "processing_time": processing_time,
            "model_used": "keyword_fallback",
            "success": True,
            "keyword_scores": scores
        }
    
    def get_analysis_type_string(self, gee_sub_intent: GEESubIntent) -> str:
        """Convert GEESubIntent to analysis type string for service calls.
        
        Args:
            gee_sub_intent: GEE sub-intent enum value
            
        Returns:
            Analysis type string for service routing
        """
        mapping = {
            GEESubIntent.NDVI: "ndvi",
            GEESubIntent.LULC: "lulc", 
            GEESubIntent.LST: "lst",
            GEESubIntent.CLIMATE: "climate",
            GEESubIntent.WATER: "water",
            GEESubIntent.SOIL: "soil",
            GEESubIntent.POPULATION: "population",
            GEESubIntent.TRANSPORTATION: "transportation"
        }
        return mapping.get(gee_sub_intent, "lulc")
