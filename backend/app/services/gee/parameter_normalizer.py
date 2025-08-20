"""
Parameter Normalizer

Normalizes LLM-generated parameters into the format expected by Script Generator.
Handles camelCase, different key names, flat structures, and missing parameters.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta


class ParameterNormalizer:
    """Normalizes parameters from various LLM formats into standard Script Generator format."""
    
    def __init__(self):
        """Initialize parameter normalizer with key mappings."""
        self._setup_key_mappings()
        self._setup_defaults()
    
    def _setup_key_mappings(self):
        """Setup mappings for different parameter key variations."""
        
        # Intent key variations
        self.intent_keys = [
            "primary_intent", "intent", "analysis_type", "primaryIntent", 
            "analysisType", "task", "action", "operation"
        ]
        
        # Dataset key variations  
        self.dataset_keys = [
            "recommended_datasets", "datasets", "recommendedDatasets", 
            "dataset", "data_source", "dataSource", "satellite", "imagery"
        ]
        
        # Date range key variations
        self.date_range_keys = [
            "date_range", "dateRange", "dates", "time_period", "timePeriod", 
            "temporal_range", "temporalRange"
        ]
        
        # Start date sub-key variations
        self.start_date_keys = [
            "start_date", "startDate", "start", "from", "begin", "since"
        ]
        
        # End date sub-key variations
        self.end_date_keys = [
            "end_date", "endDate", "end", "to", "until", "finish"
        ]
        
        # Parameters key variations
        self.parameters_keys = [
            "parameters", "params", "options", "settings", "config", "configuration"
        ]
        
        # Cloud cover variations
        self.cloud_cover_keys = [
            "max_cloud_cover", "maxCloudCover", "cloud_cover", "cloudCover",
            "cloud_threshold", "cloudThreshold", "max_cloud", "maxCloud"
        ]
        
        # Natural language to technical mappings
        self.intent_mappings = {
            "vegetation_health": "ndvi",
            "vegetation": "ndvi", 
            "greenness": "ndvi",
            "plant_health": "ndvi",
            "green_cover": "ndvi",
            "land_classification": "landcover",
            "surface_types": "landcover",
            "land_types": "landcover",
            "water_detection": "water_analysis",
            "water_mapping": "water_analysis",
            "water_bodies": "water_analysis",
            "temporal_analysis": "change_detection",
            "time_series": "change_detection",
            "before_after": "change_detection",
            "weather_data": "climate_weather",
            "precipitation": "climate_weather",
            "rainfall": "climate_weather",
            "temperature": "climate_weather",
            "city_growth": "urban_analysis",
            "urban_sprawl": "urban_analysis",
            "built_up": "urban_analysis",
            "forest_cover": "forest_analysis",
            "deforestation": "forest_analysis",
            "tree_loss": "forest_analysis",
            "crop_monitoring": "agriculture",
            "farming": "agriculture",
            "agricultural": "agriculture"
        }
        
        # Dataset name mappings (human-readable to GEE asset IDs)
        self.dataset_mappings = {
            "sentinel-2": "COPERNICUS/S2_SR",
            "sentinel2": "COPERNICUS/S2_SR", 
            "s2": "COPERNICUS/S2_SR",
            "landsat-8": "LANDSAT/LC08/C02/T1_L2",
            "landsat8": "LANDSAT/LC08/C02/T1_L2",
            "l8": "LANDSAT/LC08/C02/T1_L2",
            "modis": "MODIS/006/MOD13Q1",
            "worldcover": "ESA/WorldCover/v100",
            "esa_worldcover": "ESA/WorldCover/v100",
            "global_surface_water": "JRC/GSW1_3/GlobalSurfaceWater",
            "era5": "ECMWF/ERA5_LAND/HOURLY",
            "chirps": "CHIRPS/DAILY"
        }
    
    def _setup_defaults(self):
        """Setup default values for missing parameters."""
        self.defaults = {
            "primary_intent": "general_stats",
            "recommended_datasets": ["COPERNICUS/S2_SR"],
            "date_range": {
                "start_date": "2023-01-01",
                "end_date": "2023-12-31"
            },
            "parameters": {
                "max_cloud_cover": 20
            }
        }
    
    def normalize_parameters(self, raw_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize parameters from various LLM formats into standard format.
        
        Args:
            raw_params: Raw parameters from LLM or other sources
            
        Returns:
            Dict in standard Script Generator format
        """
        normalized = {}
        
        # 1. Normalize intent
        normalized["primary_intent"] = self._normalize_intent(raw_params)
        
        # 2. Normalize datasets
        normalized["recommended_datasets"] = self._normalize_datasets(raw_params)
        
        # 3. Normalize date range
        normalized["date_range"] = self._normalize_date_range(raw_params)
        
        # 4. Normalize analysis parameters
        normalized["parameters"] = self._normalize_analysis_parameters(raw_params)
        
        # 5. Preserve other fields that don't need normalization
        for key in ["confidence", "all_detected_intents", "output_type", "processing_notes"]:
            if key in raw_params:
                normalized[key] = raw_params[key]
        
        return normalized
    
    def _normalize_intent(self, params: Dict[str, Any]) -> str:
        """Normalize intent from various key names and values."""
        
        # Try to find intent using various key names
        intent_value = None
        for key in self.intent_keys:
            if key in params:
                intent_value = params[key]
                break
        
        if not intent_value:
            return self.defaults["primary_intent"]
        
        # Convert to string and normalize
        intent_str = str(intent_value).lower().strip()
        
        # Check if it's already a valid intent
        valid_intents = [
            "ndvi", "landcover", "water_analysis", "change_detection",
            "climate_weather", "urban_analysis", "forest_analysis", 
            "agriculture", "general_stats"
        ]
        
        if intent_str in valid_intents:
            return intent_str
        
        # Try natural language mappings
        for natural, technical in self.intent_mappings.items():
            if natural in intent_str or intent_str in natural:
                return technical
        
        # Fuzzy matching for common patterns
        if any(term in intent_str for term in ["green", "vegetation", "plant", "ndvi"]):
            return "ndvi"
        elif any(term in intent_str for term in ["water", "lake", "river", "ndwi"]):
            return "water_analysis"
        elif any(term in intent_str for term in ["change", "temporal", "time", "before", "after"]):
            return "change_detection"
        elif any(term in intent_str for term in ["land", "cover", "classification", "surface"]):
            return "landcover"
        elif any(term in intent_str for term in ["urban", "city", "built"]):
            return "urban_analysis"
        elif any(term in intent_str for term in ["forest", "tree", "deforestation"]):
            return "forest_analysis"
        elif any(term in intent_str for term in ["crop", "agriculture", "farm"]):
            return "agriculture"
        elif any(term in intent_str for term in ["climate", "weather", "precipitation", "temperature"]):
            return "climate_weather"
        
        return self.defaults["primary_intent"]
    
    def _normalize_datasets(self, params: Dict[str, Any]) -> List[str]:
        """Normalize datasets from various formats."""
        
        # Try to find datasets using various key names
        datasets_value = None
        for key in self.dataset_keys:
            if key in params:
                datasets_value = params[key]
                break
        
        if not datasets_value:
            return self.defaults["recommended_datasets"]
        
        # Convert to list if string
        if isinstance(datasets_value, str):
            datasets_value = [datasets_value]
        elif not isinstance(datasets_value, list):
            return self.defaults["recommended_datasets"]
        
        # Normalize each dataset name
        normalized_datasets = []
        for dataset in datasets_value:
            dataset_str = str(dataset).lower().strip()
            
            # Check if it's already a valid GEE asset ID
            if "/" in dataset_str and dataset_str.count("/") >= 2:
                normalized_datasets.append(dataset)
                continue
            
            # Try mappings
            mapped_dataset = self.dataset_mappings.get(dataset_str)
            if mapped_dataset:
                normalized_datasets.append(mapped_dataset)
                continue
            
            # Fuzzy matching
            if "sentinel" in dataset_str or "s2" in dataset_str:
                normalized_datasets.append("COPERNICUS/S2_SR")
            elif "landsat" in dataset_str or "l8" in dataset_str:
                normalized_datasets.append("LANDSAT/LC08/C02/T1_L2")
            elif "modis" in dataset_str:
                normalized_datasets.append("MODIS/006/MOD13Q1")
            elif "worldcover" in dataset_str or "esa" in dataset_str:
                normalized_datasets.append("ESA/WorldCover/v100")
            else:
                # Use default as fallback
                normalized_datasets.append(self.defaults["recommended_datasets"][0])
        
        return normalized_datasets if normalized_datasets else self.defaults["recommended_datasets"]
    
    def _normalize_date_range(self, params: Dict[str, Any]) -> Dict[str, str]:
        """Normalize date range from various formats."""
        
        # Try to find date range as nested object
        date_range = None
        for key in self.date_range_keys:
            if key in params and isinstance(params[key], dict):
                date_range = params[key]
                break
        
        # Try to find dates at top level (flat structure)
        if not date_range:
            date_range = {}
            
            # Look for start date
            for key in self.start_date_keys:
                if key in params:
                    date_range["start_date"] = params[key]
                    break
            
            # Look for end date
            for key in self.end_date_keys:
                if key in params:
                    date_range["end_date"] = params[key]
                    break
        
        # Normalize date format
        normalized_range = {}
        
        # Normalize start date
        start_date = None
        for key in self.start_date_keys:
            if key in date_range:
                start_date = date_range[key]
                break
        
        normalized_range["start_date"] = self._normalize_date_string(start_date) or self.defaults["date_range"]["start_date"]
        
        # Normalize end date
        end_date = None
        for key in self.end_date_keys:
            if key in date_range:
                end_date = date_range[key]
                break
        
        normalized_range["end_date"] = self._normalize_date_string(end_date) or self.defaults["date_range"]["end_date"]
        
        return normalized_range
    
    def _normalize_date_string(self, date_value: Any) -> Optional[str]:
        """Normalize a date value to YYYY-MM-DD format."""
        if not date_value:
            return None
        
        date_str = str(date_value).strip()
        
        # If already in YYYY-MM-DD format, validate it
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return date_str
        except ValueError:
            pass
        
        # Try other common formats
        date_formats = [
            "%Y/%m/%d", "%m/%d/%Y", "%d/%m/%Y",
            "%Y-%m-%d", "%m-%d-%Y", "%d-%m-%Y",
            "%Y.%m.%d", "%m.%d.%Y", "%d.%m.%Y"
        ]
        
        for fmt in date_formats:
            try:
                parsed_date = datetime.strptime(date_str, fmt)
                return parsed_date.strftime("%Y-%m-%d")
            except ValueError:
                continue
        
        # Try parsing relative dates like "2023" -> "2023-01-01"
        if date_str.isdigit() and len(date_str) == 4:
            year = int(date_str)
            if 2000 <= year <= 2030:
                return f"{year}-01-01"
        
        return None
    
    def _normalize_analysis_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize analysis parameters."""
        
        # Try to find parameters object
        analysis_params = {}
        for key in self.parameters_keys:
            if key in params and isinstance(params[key], dict):
                analysis_params.update(params[key])
                break
        
        # Look for cloud cover at top level or in various formats
        cloud_cover = self.defaults["parameters"]["max_cloud_cover"]
        for key in self.cloud_cover_keys:
            if key in params:
                try:
                    cloud_cover = float(params[key])
                    break
                except (ValueError, TypeError):
                    pass
            elif key in analysis_params:
                try:
                    cloud_cover = float(analysis_params[key])
                    break
                except (ValueError, TypeError):
                    pass
        
        # Ensure cloud cover is in valid range
        if not (0 <= cloud_cover <= 100):
            cloud_cover = self.defaults["parameters"]["max_cloud_cover"]
        
        normalized_params = {"max_cloud_cover": cloud_cover}
        
        # Copy other valid analysis parameters
        valid_param_keys = [
            "vegetation_threshold", "water_threshold", "change_threshold",
            "scale", "max_pixels", "buffer_size"
        ]
        
        for key in valid_param_keys:
            if key in analysis_params:
                normalized_params[key] = analysis_params[key]
            elif key in params:
                normalized_params[key] = params[key]
        
        return normalized_params


# Convenience function for easy usage
def normalize_llm_parameters(raw_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize parameters from LLM format to Script Generator format.
    
    Args:
        raw_params: Raw parameters from LLM
        
    Returns:
        Normalized parameters ready for Script Generator
    """
    normalizer = ParameterNormalizer()
    return normalizer.normalize_parameters(raw_params)
