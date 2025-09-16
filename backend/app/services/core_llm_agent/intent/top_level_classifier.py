"""
Top-level intent classifier for service routing.

This module determines whether a query should be routed to GEE, RAG, or Search services.
Extracted from the original llm_parse_intent_openrouter function.
"""

import json
import time
import requests
import logging
from typing import Dict, Any, Optional

try:
    from ..models.intent import ServiceType
    from ..config import get_openrouter_config
except ImportError:
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent.parent.parent.parent))
    
    from app.services.core_llm_agent.models.intent import ServiceType
    from app.services.core_llm_agent.config import get_openrouter_config

logger = logging.getLogger(__name__)


class TopLevelClassifier:
    """LLM-based classifier for top-level service routing."""
    
    def __init__(self, model_name: str = None):
        """Initialize the TopLevelClassifier.
        
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
            logger.warning("OPENROUTER_API_KEY not set. Intent classification will fail.")
    
    def classify_intent(self, query: str) -> Dict[str, Any]:
        """Classify query intent for service routing.
        
        Args:
            query: User query string
            
        Returns:
            Dictionary with service_type, confidence, reasoning, and metadata
        """
        if not self.api_key:
            raise RuntimeError("OPENROUTER_API_KEY is missing – intent classification requires OpenRouter.")
        
        if not query.strip():
            return {
                "service_type": ServiceType.SEARCH,
                "confidence": 0.0,
                "reasoning": "Empty query provided",
                "success": False,
                "error": "Empty query"
            }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": self.referrer,
            "X-Title": self.app_title,
        }
        
        system_prompt = (
            "You are an intent classifier for a geospatial assistant. "
            "Given a user query, respond ONLY with a compact JSON object of the form\n"
            "{\"intent\": \"GEE|RAG|SEARCH\", \"confidence\": 0.95, \"reasoning\": \"brief explanation\"}.\n"
            "Decision Policy (strict):\n"
            "- GEE: Choose for geospatial analysis tasks (ROI/polygon/coordinates, lat/lng, map analysis, NDVI, LULC, LST/temperature, satellite/imagery).\n"
            "- SEARCH: Choose for any timely, live, or update-oriented info (latest, current, today, now, news, weather, recent, real-time, updates).\n"
            "- RAG: Choose ONLY if the user explicitly asks to use RAG (e.g., 'use rag', 'use rag data', 'use rag service'). If not explicitly requested, DO NOT choose RAG.\n"
            "- Never choose RAG for generic questions; prefer SEARCH for time-sensitive info and GEE for geospatial analyses.\n"
            "- confidence: 0.0-1.0 score for classification certainty.\n"
            "- reasoning: 1 short sentence.\n"
            "Output JSON only."
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
        
        try:
            resp = requests.post(self.base_url, headers=headers, data=json.dumps(payload), timeout=20)
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
            
            # Parse the JSON response
            parsed = json.loads(content)
            intent_str = parsed.get("intent", "").upper()
            confidence = float(parsed.get("confidence", 0.0))
            reasoning = parsed.get("reasoning", "No reasoning provided")
            
            # Validate and convert intent
            service_type = None
            if intent_str == "GEE":
                service_type = ServiceType.GEE
            elif intent_str == "RAG":
                service_type = ServiceType.RAG
            elif intent_str == "SEARCH":
                service_type = ServiceType.SEARCH
            else:
                # Fallback logic based on keywords
                service_type = self._fallback_classification(query)
                reasoning = f"LLM returned invalid intent '{intent_str}', used fallback classification"
                confidence = 0.5
            
            service_type_str = service_type.value if hasattr(service_type, 'value') else str(service_type)
            logger.info(f"Classified intent: {service_type_str} (confidence: {confidence:.2f}) in {processing_time:.2f}s")
            
            return {
                "service_type": service_type,
                "confidence": confidence,
                "reasoning": reasoning,
                "processing_time": processing_time,
                "model_used": self.model_name,
                "success": True,
                "raw_response": parsed
            }
            
        except requests.exceptions.RequestException as e:
            processing_time = time.time() - start_time
            logger.error(f"HTTP error in intent classification: {e}")
            
            # Fallback to keyword-based classification
            service_type = self._fallback_classification(query)
            return {
                "service_type": service_type,
                "confidence": 0.3,
                "reasoning": f"LLM request failed, used keyword fallback: {str(e)}",
                "processing_time": processing_time,
                "model_used": self.model_name,
                "success": False,
                "error": str(e)
            }
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            processing_time = time.time() - start_time
            logger.error(f"Parsing error in intent classification: {e}")
            
            # Fallback to keyword-based classification
            service_type = self._fallback_classification(query)
            return {
                "service_type": service_type,
                "confidence": 0.3,
                "reasoning": f"LLM response parsing failed, used keyword fallback: {str(e)}",
                "processing_time": processing_time,
                "model_used": self.model_name,
                "success": False,
                "error": str(e)
            }
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Unexpected error in intent classification: {e}")
            
            # Fallback to keyword-based classification
            service_type = self._fallback_classification(query)
            return {
                "service_type": service_type,
                "confidence": 0.2,
                "reasoning": f"Unexpected error, used keyword fallback: {str(e)}",
                "processing_time": processing_time,
                "model_used": self.model_name,
                "success": False,
                "error": str(e)
            }
    
    def _fallback_classification(self, query: str) -> ServiceType:
        """Fallback keyword-based classification when LLM fails.
        
        Args:
            query: User query string
            
        Returns:
            ServiceType based on keyword matching
        """
        query_lower = query.lower()
        
        # GEE keywords
        gee_keywords = [
            "ndvi", "vegetation", "land use", "lulc", "satellite", "temperature", "lst",
            "heat island", "uhi", "roi", "polygon", "coordinates", "lat", "lng",
            "geospatial", "map", "imagery", "analysis", "greenness", "thermal"
        ]
        
        # RAG keywords - only when user explicitly requests RAG usage
        rag_keywords = [
            "use rag", "userag", "rag service", "use rag data", "use the rag",
            "please use rag", "with rag", "via rag"
        ]
        
        # Search keywords
        search_keywords = [
            "latest", "current", "today", "now", "weather", "news", "update",
            "recent", "live", "real-time", "current events"
        ]
        
        # Count keyword matches
        gee_score = sum(1 for keyword in gee_keywords if keyword in query_lower)
        rag_score = sum(1 for keyword in rag_keywords if keyword in query_lower)
        search_score = sum(1 for keyword in search_keywords if keyword in query_lower)
        
        # Hard preference: timely/update keywords -> SEARCH
        if search_score > 0 and search_score >= max(gee_score, rag_score):
            return ServiceType.SEARCH
        # Geospatial content -> GEE
        if gee_score > 0 and gee_score >= max(search_score, rag_score):
            return ServiceType.GEE
        # Explicit RAG invocation cues -> RAG
        if rag_score > 0:
            return ServiceType.RAG
        # Default to SEARCH for ambiguity
        return ServiceType.SEARCH
