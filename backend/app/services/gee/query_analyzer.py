"""
Query Analyzer

Analyzes user queries to detect intent and extract parameters for GEE processing.
Determines what type of geospatial analysis is needed and what datasets to use.
"""

import re
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta


class QueryAnalyzer:
    """Analyzes user queries to determine GEE processing intent and parameters."""
    
    def __init__(self):
        """Initialize query analyzer with intent patterns and parameters."""
        self._setup_intent_patterns()
        self._setup_dataset_mapping()
        
    def _setup_intent_patterns(self):
        """Setup regex patterns for detecting different analysis intents."""
        self.intent_patterns = {
            "ndvi": [
                r'\bndvi\b', r'\bvegetation\s+index\b', r'\bvegetation\s+health\b',
                r'\bgreen\s+cover\b', r'\bplant\s+health\b', r'\bvegetation\s+analysis\b',
                r'\bhow\s+green\b', r'\bgreen\w*\b.*\bvegetation\b', r'\bvegetation.*green\b'
            ],
            "landcover": [
                r'\bland\s+cover\b', r'\bland\s+use\b', r'\bclassification\b',
                r'\burban\s+area\b', r'\bforest\s+cover\b', r'\bwater\s+bodies\b',
                r'\bcrop\s+mapping\b', r'\bhabitat\s+mapping\b',
                r'\btypes?\s+of\s+surfaces?\b', r'\bwhat.*surfaces?\b', r'\bsurface\s+types?\b'
            ],
            "change_detection": [
                r'\bchange\s+detection\b', r'\btemporal\s+analysis\b', r'\bover\s+time\b',
                r'\bdeforestation\b', r'\burban\s+growth\b', r'\bchanges?\s+between\b',
                r'\bbefore\s+and\s+after\b', r'\bcompare.*years?\b',
                r'\bchanges?\s+in\b.*\byears?\b', r'\bchanges?\s+over\b', r'\bover.*\byears?\b'
            ],
            "water_analysis": [
                r'\bwater\s+bodies\b', r'\bwater\s+quality\b', r'\bwater\s+index\b',
                r'\bndwi\b', r'\bmndwi\b', r'\briver\b', r'\blake\b', r'\breservoir\b'
            ],
            "climate_weather": [
                r'\bprecipitation\b', r'\brainfall\b', r'\btemperature\b',
                r'\bweather\b', r'\bclimate\b', r'\bdrought\b', r'\bmoisture\b'
            ],
            "urban_analysis": [
                r'\burban\s+sprawl\b', r'\bcity\s+growth\b', r'\bbuilt\s+up\b',
                r'\bdevelopment\b', r'\binfrastructure\b', r'\bbuildings?\b'
            ],
            "forest_analysis": [
                r'\bforest\b', r'\btrees?\b', r'\bcanopy\b', r'\bdeforestation\b',
                r'\breforestation\b', r'\bforest\s+cover\b', r'\btimber\b'
            ],
            "agriculture": [
                r'\bcrop\b', r'\bagricultur\w*\b', r'\bfarm\w*\b', r'\birrigation\b',
                r'\bharvest\b', r'\bfield\b', r'\bcultivation\b'
            ],
            "general_stats": [
                r'\barea\b', r'\bstatistics\b', r'\banalyze\b', r'\bcalculate\b',
                r'\bmeasure\b', r'\bcount\b', r'\bsummary\b'
            ]
        }
        
    def _setup_dataset_mapping(self):
        """Setup mapping of intents to appropriate GEE datasets."""
        self.dataset_mapping = {
            "ndvi": [
                "LANDSAT/LC08/C02/T1_L2",  # Landsat 8 Surface Reflectance
                "COPERNICUS/S2_SR",        # Sentinel-2 Surface Reflectance
                "MODIS/006/MOD13Q1"        # MODIS NDVI
            ],
            "landcover": [
                "ESA/WorldCover/v100",     # ESA WorldCover
                "COPERNICUS/Landcover/100m/Proba-V-C3/Global",
                "MODIS/006/MCD12Q1"       # MODIS Land Cover
            ],
            "change_detection": [
                "LANDSAT/LC08/C02/T1_L2",  # Landsat time series
                "COPERNICUS/S2_SR",        # Sentinel-2 time series
            ],
            "water_analysis": [
                "COPERNICUS/S2_SR",        # Sentinel-2 for water indices
                "LANDSAT/LC08/C02/T1_L2",  # Landsat for water mapping
                "JRC/GSW1_3/GlobalSurfaceWater"  # Global Surface Water
            ],
            "climate_weather": [
                "ECMWF/ERA5_LAND/HOURLY",  # ERA5 climate data
                "CHIRPS/DAILY",            # Precipitation data
                "MODIS/006/MOD11A1"        # Land Surface Temperature
            ],
            "urban_analysis": [
                "COPERNICUS/S2_SR",        # High resolution for urban areas
                "LANDSAT/LC08/C02/T1_L2",
                "ESA/WorldCover/v100"      # For built-up areas
            ],
            "forest_analysis": [
                "LANDSAT/LC08/C02/T1_L2",
                "COPERNICUS/S2_SR",
                "UMD/hansen/global_forest_change_2021_v1_9"  # Global Forest Change
            ],
            "agriculture": [
                "COPERNICUS/S2_SR",        # High resolution for crops
                "LANDSAT/LC08/C02/T1_L2",
                "MODIS/006/MOD13Q1"        # MODIS NDVI for crop monitoring
            ],
            "general_stats": [
                "COPERNICUS/S2_SR",        # Default to Sentinel-2
                "LANDSAT/LC08/C02/T1_L2"
            ]
        }
        
    def analyze_query(self, query: str) -> Dict[str, Any]:
        """
        Analyze user query to determine intent and extract parameters.
        
        Args:
            query: User query string
            
        Returns:
            Dict containing analysis results with intent, datasets, parameters, etc.
        """
        query_lower = query.lower()
        
        # Detect primary intent
        detected_intents = self._detect_intents(query_lower)
        primary_intent = self._select_primary_intent(detected_intents, query_lower)
        
        # Extract date ranges
        date_range = self._extract_date_range(query_lower)
        
        # Extract analysis parameters
        parameters = self._extract_parameters(query_lower, primary_intent)
        
        # Get recommended datasets
        datasets = self.dataset_mapping.get(primary_intent, self.dataset_mapping["general_stats"])
        
        # Determine output type
        output_type = self._determine_output_type(query_lower, primary_intent)
        
        return {
            "primary_intent": primary_intent,
            "all_detected_intents": detected_intents,
            "confidence": self._calculate_confidence(detected_intents, query_lower),
            "recommended_datasets": datasets[:2],  # Top 2 datasets
            "date_range": date_range,
            "parameters": parameters,
            "output_type": output_type,
            "processing_notes": self._generate_processing_notes(primary_intent, parameters)
        }
        
    def _detect_intents(self, query_lower: str) -> List[str]:
        """Detect all matching intents in the query."""
        detected = []
        
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    detected.append(intent)
                    break  # Found this intent, move to next
                    
        return detected
        
    def _select_primary_intent(self, detected_intents: List[str], query_lower: str) -> str:
        """Select the most appropriate primary intent from detected intents."""
        if not detected_intents:
            return "general_stats"
            
        if len(detected_intents) == 1:
            return detected_intents[0]
            
        # Priority rules for multiple detected intents
        intent_priority = {
            # Technical indices have high priority
            "ndvi": 10,
            "water_analysis": 9,  # Higher than landcover for water-specific queries
            "change_detection": 8,
            
            # Specific analysis types
            "forest_analysis": 7,
            "agriculture": 7,
            "urban_analysis": 7,
            "climate_weather": 7,
            
            # Broad categories have lower priority
            "landcover": 5,  # Often matched but may not be primary intent
            "general_stats": 1
        }
        
        # Additional context-based scoring
        context_scores = {}
        for intent in detected_intents:
            base_score = intent_priority.get(intent, 5)
            context_score = 0
            
            # Boost specific intents based on context
            if intent == "water_analysis" and any(term in query_lower for term in ["ndwi", "mndwi", "water"]):
                context_score += 3
            elif intent == "ndvi" and any(term in query_lower for term in ["vegetation", "green", "plant"]):
                context_score += 3
            elif intent == "change_detection" and any(term in query_lower for term in ["change", "over time", "years", "temporal"]):
                context_score += 3
            elif intent == "forest_analysis" and any(term in query_lower for term in ["forest", "trees", "deforestation"]):
                context_score += 2
                
            context_scores[intent] = base_score + context_score
            
        # Select intent with highest score
        primary_intent = max(context_scores.keys(), key=lambda x: context_scores[x])
        return primary_intent
        
    def _extract_date_range(self, query_lower: str) -> Dict[str, Any]:
        """Extract date range from query text."""
        # Default to last year if no dates specified
        default_end = datetime.now()
        default_start = default_end - timedelta(days=365)
        
        date_range = {
            "start_date": default_start.strftime("%Y-%m-%d"),
            "end_date": default_end.strftime("%Y-%m-%d"),
            "source": "default"
        }
        
        # Look for specific years
        year_pattern = r'\b(20\d{2})\b'
        years = re.findall(year_pattern, query_lower)
        
        if years:
            if len(years) == 1:
                # Single year mentioned
                year = years[0]
                date_range.update({
                    "start_date": f"{year}-01-01",
                    "end_date": f"{year}-12-31",
                    "source": "single_year"
                })
            elif len(years) >= 2:
                # Multiple years - use range
                start_year = min(years)
                end_year = max(years)
                date_range.update({
                    "start_date": f"{start_year}-01-01", 
                    "end_date": f"{end_year}-12-31",
                    "source": "year_range"
                })
                
        # Look for relative time expressions
        if re.search(r'\blast\s+year\b', query_lower):
            date_range.update({
                "start_date": (default_end - timedelta(days=365)).strftime("%Y-%m-%d"),
                "end_date": default_end.strftime("%Y-%m-%d"),
                "source": "last_year"
            })
        elif re.search(r'\blast\s+month\b', query_lower):
            date_range.update({
                "start_date": (default_end - timedelta(days=30)).strftime("%Y-%m-%d"),
                "end_date": default_end.strftime("%Y-%m-%d"),
                "source": "last_month"
            })
            
        return date_range
        
    def _extract_parameters(self, query_lower: str, intent: str) -> Dict[str, Any]:
        """Extract analysis-specific parameters from query."""
        parameters = {}
        
        # Common parameters
        if re.search(r'\bcloud\s+cover\b', query_lower):
            # Extract cloud cover threshold if mentioned
            cloud_match = re.search(r'(\d+)%?\s*cloud', query_lower)
            if cloud_match:
                parameters["max_cloud_cover"] = int(cloud_match.group(1))
            else:
                parameters["max_cloud_cover"] = 20  # Default
        else:
            parameters["max_cloud_cover"] = 20
            
        # Resolution preferences
        if re.search(r'\bhigh\s+resolution\b', query_lower):
            parameters["prefer_high_resolution"] = True
        elif re.search(r'\blow\s+resolution\b', query_lower):
            parameters["prefer_high_resolution"] = False
            
        # Intent-specific parameters
        if intent == "ndvi":
            parameters["bands_needed"] = ["B4", "B8"]  # Red, NIR for Sentinel-2
            parameters["index_type"] = "ndvi"
            
        elif intent == "water_analysis":
            if re.search(r'\bndwi\b', query_lower):
                parameters["index_type"] = "ndwi"
                parameters["bands_needed"] = ["B3", "B8"]  # Green, NIR
            elif re.search(r'\bmndwi\b', query_lower):
                parameters["index_type"] = "mndwi"
                parameters["bands_needed"] = ["B3", "B11"]  # Green, SWIR1
            else:
                parameters["index_type"] = "water_mask"
                
        elif intent == "change_detection":
            parameters["comparison_type"] = "temporal"
            parameters["change_threshold"] = 0.1  # Default change threshold
            
        return parameters
        
    def _determine_output_type(self, query_lower: str, intent: str) -> str:
        """Determine what type of output is requested."""
        if re.search(r'\bmap\b|\bvisuali[sz]e\b|\bimage\b', query_lower):
            return "visualization"
        elif re.search(r'\bstatistics\b|\bstats\b|\bnumbers\b|\bcount\b', query_lower):
            return "statistics"
        elif re.search(r'\bdownload\b|\bexport\b|\bdata\b', query_lower):
            return "export"
        else:
            # Default based on intent
            if intent in ["general_stats", "climate_weather"]:
                return "statistics"
            else:
                return "visualization"
                
    def _calculate_confidence(self, detected_intents: List[str], query_lower: str) -> float:
        """Calculate confidence score for the analysis."""
        if not detected_intents:
            return 0.3  # Low confidence for general queries
            
        # Base confidence on number of matching patterns
        confidence = min(0.7 + (len(detected_intents) * 0.1), 0.95)
        
        # Boost confidence for specific technical terms
        technical_terms = ['ndvi', 'landsat', 'sentinel', 'modis', 'gee', 'remote sensing']
        for term in technical_terms:
            if term in query_lower:
                confidence = min(confidence + 0.1, 0.98)
                
        return round(confidence, 2)
        
    def _generate_processing_notes(self, intent: str, parameters: Dict[str, Any]) -> List[str]:
        """Generate helpful processing notes for the analysis."""
        notes = []
        
        intent_notes = {
            "ndvi": "NDVI analysis will show vegetation health (values 0-1, higher = healthier)",
            "landcover": "Land cover classification will identify different surface types",
            "change_detection": "Change analysis will identify areas of temporal variation",
            "water_analysis": "Water analysis will identify and map water bodies",
            "climate_weather": "Climate analysis will provide meteorological statistics",
            "urban_analysis": "Urban analysis will focus on built-up areas and development",
            "forest_analysis": "Forest analysis will examine tree cover and forest health",
            "agriculture": "Agricultural analysis will focus on crop areas and health"
        }
        
        if intent in intent_notes:
            notes.append(intent_notes[intent])
            
        # Add parameter-specific notes
        if parameters.get("max_cloud_cover"):
            notes.append(f"Filtering for <{parameters['max_cloud_cover']}% cloud cover")
            
        if parameters.get("prefer_high_resolution"):
            notes.append("Using high-resolution imagery for detailed analysis")
            
        return notes
