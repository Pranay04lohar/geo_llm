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
        # Use dedicated NER model for faster, more efficient location extraction
        self.model_name = model_name or config["ner_model"]
        self.api_key = config["api_key"]
        self.referrer = config["referrer"]
        self.app_title = config["app_title"]
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        
        if not self.api_key:
            logger.warning("OPENROUTER_API_KEY not set. Location extraction will fail.")
        
        logger.info(f"LocationNER initialized with model: {self.model_name}")
    
    def _extract_json_from_content(self, content: str) -> str:
        """Extract JSON from LLM response content, handling extra text after JSON.
        
        Args:
            content: Raw content from LLM
            
        Returns:
            Extracted JSON string or empty string if not found
        """
        content = content.strip()
        
        # First, try to parse the entire content as JSON
        try:
            json.loads(content)
            return content
        except json.JSONDecodeError:
            pass
        
        # Look for JSON array pattern
        import re
        
        # Pattern to find JSON array starting with [
        array_pattern = r'\[.*?\]'
        array_matches = re.findall(array_pattern, content, re.DOTALL)
        
        for match in array_matches:
            try:
                # Validate that this is valid JSON
                json.loads(match)
                return match
            except json.JSONDecodeError:
                continue
        
        # Look for JSON object pattern with "locations" key
        object_pattern = r'\{[^{}]*"locations"\s*:\s*\[.*?\]\s*\}'
        object_matches = re.findall(object_pattern, content, re.DOTALL)
        
        for match in object_matches:
            try:
                # Validate that this is valid JSON
                json.loads(match)
                return match
            except json.JSONDecodeError:
                continue
        
        # If no patterns found, try to find the first complete JSON structure
        # Look for the first { or [ and try to find the matching closing bracket
        start_chars = ['{', '[']
        for start_char in start_chars:
            start_idx = content.find(start_char)
            if start_idx != -1:
                # Find the matching closing bracket
                bracket_count = 0
                end_idx = start_idx
                for i, char in enumerate(content[start_idx:], start_idx):
                    if char in ['{', '[']:
                        bracket_count += 1
                    elif char in ['}', ']']:
                        bracket_count -= 1
                        if bracket_count == 0:
                            end_idx = i + 1
                            break
                
                if bracket_count == 0:  # Found matching closing bracket
                    json_candidate = content[start_idx:end_idx]
                    try:
                        json.loads(json_candidate)
                        return json_candidate
                    except json.JSONDecodeError:
                        continue
        
        return ""
    
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
            resp = requests.post(self.base_url, headers=headers, data=json.dumps(payload), timeout=10)
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
            
            # Try to extract JSON from content (handle cases where LLM adds extra text)
            json_content = self._extract_json_from_content(content)
            if not json_content:
                logger.warning("Could not extract valid JSON from LLM response")
                logger.warning(f"Original content: {content[:200]}...")
                return []
            
            logger.info(f"Successfully extracted JSON from LLM response: {json_content[:100]}...")
                
            parsed = json.loads(json_content)
            
            # Handle formats: array, object with "locations", or single location object
            if isinstance(parsed, list):
                locations_data = parsed
            elif isinstance(parsed, dict):
                if "locations" in parsed and isinstance(parsed["locations"], list):
                    locations_data = parsed["locations"]
                elif all(k in parsed for k in ("matched_name", "type", "confidence")):
                    # Accept single location object
                    locations_data = [parsed]
                else:
                    logger.warning(f"Unexpected LLM response dict keys: {list(parsed.keys())}")
                    return []
            else:
                logger.warning(f"Unexpected LLM response type: {type(parsed)}")
                return []
                
            # Validate and convert to LocationEntity objects
            entities = []
            seen_names = set()  # Track unique location names to avoid duplicates
            
            for loc_data in locations_data:
                if (isinstance(loc_data, dict) and 
                    "matched_name" in loc_data and 
                    "type" in loc_data and 
                    "confidence" in loc_data):
                    try:
                        matched_name = loc_data["matched_name"].strip()
                        
                        # Skip duplicates (case-insensitive)
                        if matched_name.lower() in seen_names:
                            logger.info(f"Skipping duplicate location: {matched_name}")
                            continue
                        
                        seen_names.add(matched_name.lower())
                        
                        entity = LocationEntity(
                            matched_name=matched_name,
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
            # Fallback to simple regex extraction for common Indian cities
            return self._fallback_location_extraction(query)
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in location extraction: {e}")
            logger.error(f"Raw content that failed to parse: '{content[:200]}...' (truncated)")
            # Fallback to simple regex extraction for common Indian cities
            return self._fallback_location_extraction(query)
        except Exception as e:
            logger.error(f"Unexpected error in location extraction: {e}")
            # Fallback to simple regex extraction for common Indian cities
            return self._fallback_location_extraction(query)
    
    def _fallback_location_extraction(self, query: str) -> List[LocationEntity]:
        """Fallback location extraction using regex patterns for common Indian cities.
        
        Args:
            query: User query string
            
        Returns:
            List of LocationEntity objects found via regex
        """
        import re
        
        # Common Indian cities and states (case-insensitive)
        indian_locations = {
            # Major cities
            'mumbai': ('Mumbai', 'city', 95),
            'delhi': ('Delhi', 'city', 95),
            'bangalore': ('Bangalore', 'city', 95),
            'bengaluru': ('Bengaluru', 'city', 95),
            'chennai': ('Chennai', 'city', 95),
            'kolkata': ('Kolkata', 'city', 95),
            'hyderabad': ('Hyderabad', 'city', 95),
            'pune': ('Pune', 'city', 95),
            'ahmedabad': ('Ahmedabad', 'city', 95),
            'jaipur': ('Jaipur', 'city', 95),
            'surat': ('Surat', 'city', 95),
            'lucknow': ('Lucknow', 'city', 95),
            'kanpur': ('Kanpur', 'city', 95),
            'nagpur': ('Nagpur', 'city', 95),
            'indore': ('Indore', 'city', 95),
            'thane': ('Thane', 'city', 95),
            'bhopal': ('Bhopal', 'city', 95),
            'visakhapatnam': ('Visakhapatnam', 'city', 95),
            'pimpri': ('Pimpri-Chinchwad', 'city', 95),
            'patna': ('Patna', 'city', 95),
            'vadodara': ('Vadodara', 'city', 95),
            'ghaziabad': ('Ghaziabad', 'city', 95),
            'ludhiana': ('Ludhiana', 'city', 95),
            'agra': ('Agra', 'city', 95),
            'nashik': ('Nashik', 'city', 95),
            'faridabad': ('Faridabad', 'city', 95),
            'meerut': ('Meerut', 'city', 95),
            'rajkot': ('Rajkot', 'city', 95),
            'kalyan': ('Kalyan-Dombivli', 'city', 95),
            'vasai': ('Vasai-Virar', 'city', 95),
            'varanasi': ('Varanasi', 'city', 95),
            'srinagar': ('Srinagar', 'city', 95),
            'aurangabad': ('Aurangabad', 'city', 95),
            'dhanbad': ('Dhanbad', 'city', 95),
            'amritsar': ('Amritsar', 'city', 95),
            'navi mumbai': ('Navi Mumbai', 'city', 95),
            'allahabad': ('Allahabad', 'city', 95),
            'prayagraj': ('Prayagraj', 'city', 95),
            'howrah': ('Howrah', 'city', 95),
            'ranchi': ('Ranchi', 'city', 95),
            'gwalior': ('Gwalior', 'city', 95),
            'jabalpur': ('Jabalpur', 'city', 95),
            'coimbatore': ('Coimbatore', 'city', 95),
            'vijayawada': ('Vijayawada', 'city', 95),
            'jodhpur': ('Jodhpur', 'city', 95),
            'udaipur': ('Udaipur', 'city', 95),
            'leh': ('Leh', 'city', 95),
            'ladakh': ('Ladakh', 'state', 95),
            'kargil': ('Kargil', 'city', 95),
            'madurai': ('Madurai', 'city', 95),
            'raipur': ('Raipur', 'city', 95),
            'kota': ('Kota', 'city', 95),
            'chandigarh': ('Chandigarh', 'city', 95),
            'guwahati': ('Guwahati', 'city', 95),
            
            # States
            'maharashtra': ('Maharashtra', 'state', 95),
            'karnataka': ('Karnataka', 'state', 95),
            'tamil nadu': ('Tamil Nadu', 'state', 95),
            'gujarat': ('Gujarat', 'state', 95),
            'rajasthan': ('Rajasthan', 'state', 95),
            'uttar pradesh': ('Uttar Pradesh', 'state', 95),
            'west bengal': ('West Bengal', 'state', 95),
            'madhya pradesh': ('Madhya Pradesh', 'state', 95),
            'bihar': ('Bihar', 'state', 95),
            'odisha': ('Odisha', 'state', 95),
            'telangana': ('Telangana', 'state', 95),
            'andhra pradesh': ('Andhra Pradesh', 'state', 95),
            'kerala': ('Kerala', 'state', 95),
            'punjab': ('Punjab', 'state', 95),
            'haryana': ('Haryana', 'state', 95),
            'jharkhand': ('Jharkhand', 'state', 95),
            'assam': ('Assam', 'state', 95),
            'himachal pradesh': ('Himachal Pradesh', 'state', 95),
            'chhattisgarh': ('Chhattisgarh', 'state', 95),
            'uttarakhand': ('Uttarakhand', 'state', 95),
            'goa': ('Goa', 'state', 95),
            'tripura': ('Tripura', 'state', 95),
            'manipur': ('Manipur', 'state', 95),
            'meghalaya': ('Meghalaya', 'state', 95),
            'nagaland': ('Nagaland', 'state', 95),
            'mizoram': ('Mizoram', 'state', 95),
            'arunachal pradesh': ('Arunachal Pradesh', 'state', 95),
            'sikkim': ('Sikkim', 'state', 95),
        }
        
        entities = []
        query_lower = query.lower()
        
        # Find matches (prioritize longer matches first)
        for location_key in sorted(indian_locations.keys(), key=len, reverse=True):
            if location_key in query_lower:
                # Avoid partial matches by checking word boundaries
                pattern = r'\b' + re.escape(location_key) + r'\b'
                if re.search(pattern, query_lower):
                    proper_name, loc_type, confidence = indian_locations[location_key]
                    
                    # Check if we already found this location (avoid duplicates)
                    if not any(e.matched_name.lower() == proper_name.lower() for e in entities):
                        entity = LocationEntity(
                            matched_name=proper_name,
                            type=loc_type,
                            confidence=float(confidence)
                        )
                        entities.append(entity)
        
        if entities:
            logger.info(f"Fallback extraction found {len(entities)} locations: {[e.matched_name for e in entities]}")
        else:
            logger.warning("Fallback extraction found no locations")
            
        return entities
    
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
