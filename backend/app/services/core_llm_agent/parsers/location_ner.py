"""
Location Named Entity Recognition using LLM.

This module extracts location entities from user queries using OpenRouter LLM.
Extracted from the original llm_extract_locations_openrouter function.
"""

import json
import sys
import time
import requests
import logging
from typing import List, Dict, Any

try:
    from ..models.location import LocationEntity
    from ..config import get_openrouter_config
except ImportError:
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent.parent.parent.parent))
    
    from app.services.core_llm_agent.models.location import LocationEntity
    from app.services.core_llm_agent.config import get_openrouter_config

logger = logging.getLogger(__name__)


class LocationNER:
    """LLM-based Named Entity Recognition for location extraction."""
    
    def __init__(self, model_name: str = None):
        """Initialize the LocationNER with model configuration."""
        config = get_openrouter_config()
        self.model_name = model_name or config["intent_model"]
        self.api_key = config["api_key"]
        self.referrer = config["referrer"]
        self.app_title = config["app_title"]
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        
        if not self.api_key:
            logger.warning("OPENROUTER_API_KEY not set. Location extraction will fail.")
    
    def extract_locations(self, query: str) -> List[LocationEntity]:
        """Extract location entities from a query string.
        
        Args:
            query: User query string
            
        Returns:
            List of LocationEntity objects with extracted locations
        """
        if not self.api_key:
            logger.error("OPENROUTER_API_KEY is not set. Location extraction will fail.")
            return []
        
        if not query.strip():
            return []
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": self.referrer,
            "X-Title": self.app_title,
        }

        system_prompt = (
            "You are a location entity extractor for Indian geography.\n"
            "Extract city names, state names, and geographic locations from the user query.\n"
            "Return a JSON array of location objects with keys: 'matched_name' (extracted location), 'type' ('city' or 'state'), 'confidence' (0-100).\n"
            "Rules:\n"
            "- Only extract Indian cities, states, and geographic regions\n"
            "- Use proper capitalization (e.g. 'Mumbai', 'Delhi', 'Karnataka')\n"
            "- confidence should be 90-100 for exact matches, 70-89 for fuzzy matches\n"
            "- Return empty array [] if no locations found\n"
            "- JSON only, no markdown or extra text"
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

        try:
            start_time = time.time()
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
                logger.warning("LLM returned empty content for location extraction")
                return []
            
            if not content.strip():
                logger.warning("LLM returned whitespace-only content for location extraction")
                return []
                
            parsed = json.loads(content)
            
            # Handle both array format and object with "locations" key
            if isinstance(parsed, list):
                locations_data = parsed
            elif isinstance(parsed, dict) and "locations" in parsed:
                locations_data = parsed["locations"]
            else:
                logger.warning(f"Unexpected LLM response format: {type(parsed)}")
                return []
                
            # Validate and convert to LocationEntity objects
            entities = []
            for loc_data in locations_data:
                if (isinstance(loc_data, dict) and 
                    "matched_name" in loc_data and 
                    "type" in loc_data and 
                    "confidence" in loc_data):
                    try:
                        entity = LocationEntity(
                            matched_name=loc_data["matched_name"],
                            type=loc_data["type"],
                            confidence=float(loc_data["confidence"])
                        )
                        entities.append(entity)
                    except Exception as e:
                        logger.warning(f"Failed to create LocationEntity: {e}")
                        continue
            
            logger.info(f"Extracted {len(entities)} location entities in {processing_time:.2f}s")
            return entities
            
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP error in location extraction: {e}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in location extraction: {e}")
            logger.error(f"Raw content that failed to parse: '{content[:200]}...' (truncated)")
            return []
        except Exception as e:
            logger.error(f"Unexpected error in location extraction: {e}")
            return []
    
    def extract_locations_dict(self, query: str) -> List[Dict[str, Any]]:
        """Extract locations and return as dict format for backward compatibility.
        
        Args:
            query: User query string
            
        Returns:
            List of location dictionaries (legacy format)
        """
        entities = self.extract_locations(query)
        return [
            {
                "matched_name": entity.matched_name,
                "type": entity.type,
                "confidence": entity.confidence
            }
            for entity in entities
        ]
