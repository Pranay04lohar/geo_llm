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
        
        # Template-based classification rules
        self.template_rules = {
            "water_analysis": {
                "keywords": ["water", "river", "lake", "reservoir", "ocean", "sea", "pond", "stream", 
                           "ndwi", "mndwi", "flooding", "flood", "wetland", "aquatic"],
                "patterns": [r"\bwater\s+bod(y|ies)\b", r"\bwater\s+detect", r"\bwater\s+map", 
                           r"\bhydro", r"\baquatic", r"\briver\s+system"],
                "confidence_boost": 0.2
            },
            "forest_cover": {
                "keywords": ["forest", "tree", "deforestation", "canopy", "woodland", "timber", 
                           "logging", "afforestation", "reforestation", "vegetation", "ndvi"],
                "patterns": [r"\bforest\s+cover", r"\btree\s+cover", r"\bdeforest", r"\bcanopy", 
                           r"\bwood(land|s)", r"\bvegetation\s+health"],
                "confidence_boost": 0.2
            },
            "lulc_analysis": {
                "keywords": ["land use", "land cover", "lulc", "urban", "built-up", "classification", 
                           "development", "sprawl", "settlement", "crop", "agriculture"],
                "patterns": [r"\bland\s+use", r"\bland\s+cover", r"\blulc", r"\burban\s+area", 
                           r"\bbuilt.?up", r"\bclassif", r"\bdevelopment"],
                "confidence_boost": 0.2
            },
            "population_density": {
                "keywords": ["population", "density", "demographic", "people", "inhabitants", 
                           "census", "settlement", "human", "residents"],
                "patterns": [r"\bpopulation\s+densit", r"\bdemographic", r"\bpeople\s+per", 
                           r"\binhabitants", r"\bresidents"],
                "confidence_boost": 0.2
            },
            "soil_analysis": {
                "keywords": ["soil", "fertility", "erosion", "ph", "organic", "clay", "sand", 
                           "nutrients", "agriculture", "farming", "cultivation"],
                "patterns": [r"\bsoil\s+proper", r"\bsoil\s+health", r"\bsoil\s+qualit", 
                           r"\bfertility", r"\berosion", r"\bsoil\s+ph"],
                "confidence_boost": 0.2
            },
            "transportation_network": {
                "keywords": ["road", "highway", "transport", "traffic", "infrastructure", "connectivity", 
                           "accessibility", "railway", "street", "network"],
                "patterns": [r"\broad\s+network", r"\btransport", r"\binfrastructure", 
                           r"\bconnectivity", r"\baccessibility", r"\bhighway"],
                "confidence_boost": 0.2
            },
            "climate_analysis": {
                "keywords": ["climate", "weather", "temperature", "precipitation", "humidity", "air quality", 
                           "pollution", "seasonal", "monsoon", "rainfall", "heat", "drought", "atmospheric",
                           "no2", "co", "so2", "era5", "gldas", "meteorological", "climatic"],
                "patterns": [r"\bclimate\s+pattern", r"\bweather\s+analy", r"\btemperature\s+trend", 
                           r"\bair\s+quality", r"\bseasonal\s+pattern", r"\bprecipitation", 
                           r"\bmonsoon", r"\batmospheric", r"\bmeteorological"],
                "confidence_boost": 0.3
            }
        }
        
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
        Analyze query using hybrid approach with template classification.
        
        Args:
            query: User query string
            use_llm_fallback: Whether to use LLM for low-confidence cases
            
        Returns:
            Dict with enhanced analysis results including template recommendation
        """
        start_time = time.time()
        
        # Step 1: Template-based classification (fastest)
        template_result = self._classify_query_to_template(query)
        template_confidence = template_result.get("confidence", 0.0)
        
        # Step 2: Fast regex-based analysis  
        regex_result = self.regex_analyzer.analyze_query(query)
        regex_confidence = regex_result.get("confidence", 0.0)
        
        # Step 3: Determine best approach
        if template_confidence >= self.HIGH_CONFIDENCE_THRESHOLD:
            # High-confidence template match - use directly
            final_result = self._merge_template_and_regex(template_result, regex_result)
            final_result["analysis_method"] = "template_direct"
        elif regex_confidence >= self.HIGH_CONFIDENCE_THRESHOLD:
            # High-confidence regex match
            final_result = regex_result
            final_result["template_recommendation"] = template_result.get("recommended_template")
            final_result["analysis_method"] = "regex_direct"
        elif self.llm_available and use_llm_fallback:
            # Low confidence - use LLM refinement
            llm_result = self._llm_analyze_query(query, regex_result)
            final_result = self._merge_all_results(template_result, regex_result, llm_result)
            final_result["analysis_method"] = "hybrid_llm"
        else:
            # Fallback to best available result
            if template_confidence > regex_confidence:
                final_result = self._merge_template_and_regex(template_result, regex_result)
                final_result["analysis_method"] = "template_fallback"
            else:
                final_result = regex_result
                final_result["template_recommendation"] = template_result.get("recommended_template")
                final_result["analysis_method"] = "regex_fallback"
            
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

    def _classify_query_to_template(self, query: str) -> Dict[str, Any]:
        """Classify query to specific GEE template using rule-based approach."""
        query_lower = query.lower()
        template_scores = {}
        
        # Score each template based on keyword and pattern matches
        for template_name, rules in self.template_rules.items():
            score = 0.0
            matches = []
            
            # Keyword matching
            for keyword in rules["keywords"]:
                if keyword in query_lower:
                    score += 0.1
                    matches.append(f"keyword:{keyword}")
                    
            # Pattern matching
            for pattern in rules["patterns"]:
                if re.search(pattern, query_lower, re.IGNORECASE):
                    score += 0.2
                    matches.append(f"pattern:{pattern}")
            
            if score > 0:
                # Apply confidence boost for this template
                score += rules.get("confidence_boost", 0)
                template_scores[template_name] = {
                    "score": min(score, 1.0),  # Cap at 1.0
                    "matches": matches
                }
        
        if not template_scores:
            return {
                "recommended_template": None,
                "confidence": 0.0,
                "classification_method": "template_rules"
            }
        
        # Find best matching template
        best_template = max(template_scores.items(), key=lambda x: x[1]["score"])
        template_name, template_data = best_template
        
        return {
            "recommended_template": template_name,
            "confidence": template_data["score"],
            "matches": template_data["matches"],
            "all_scores": {k: v["score"] for k, v in template_scores.items()},
            "classification_method": "template_rules"
        }
    
    def _merge_template_and_regex(self, template_result: Dict[str, Any], 
                                 regex_result: Dict[str, Any]) -> Dict[str, Any]:
        """Merge template classification with regex analysis."""
        merged = regex_result.copy()
        
        # Override intent if template has high confidence
        if template_result.get("confidence", 0) > 0.7:
            merged["primary_intent"] = template_result["recommended_template"]
            merged["confidence"] = template_result["confidence"]
        
        # Add template information
        merged["template_recommendation"] = template_result.get("recommended_template")
        merged["template_confidence"] = template_result.get("confidence", 0)
        merged["template_matches"] = template_result.get("matches", [])
        
        return merged
    
    def _merge_all_results(self, template_result: Dict[str, Any], 
                          regex_result: Dict[str, Any], 
                          llm_result: Dict[str, Any]) -> Dict[str, Any]:
        """Merge template, regex, and LLM results intelligently."""
        # Start with regex as base
        merged = regex_result.copy()
        
        # Get confidences
        template_conf = template_result.get("confidence", 0)
        regex_conf = regex_result.get("confidence", 0)
        llm_conf = llm_result.get("confidence", 0)
        
        # Choose primary intent based on highest confidence
        if template_conf >= max(regex_conf, llm_conf) and template_conf > 0.6:
            merged["primary_intent"] = template_result["recommended_template"]
            merged["confidence"] = template_conf
            merged["intent_source"] = "template"
        elif llm_conf >= regex_conf and "error" not in llm_result:
            merged["primary_intent"] = llm_result.get("primary_intent", merged["primary_intent"])
            merged["confidence"] = llm_conf
            merged["intent_source"] = "llm"
        else:
            merged["intent_source"] = "regex"
        
        # Add all analysis information
        merged["template_recommendation"] = template_result.get("recommended_template")
        merged["template_confidence"] = template_conf
        merged["llm_reasoning"] = llm_result.get("reasoning", "")
        merged["query_complexity"] = llm_result.get("complexity", "moderate")
        
        return merged

    def get_available_templates(self) -> List[str]:
        """Get list of available template names."""
        return list(self.template_rules.keys())
    
    def get_template_info(self, template_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific template."""
        return self.template_rules.get(template_name)

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
