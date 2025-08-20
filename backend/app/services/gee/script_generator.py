"""
GEE Script Generator

Generates Google Earth Engine scripts dynamically based on analysis intent and parameters.
Uses template-based approach for different types of geospatial analysis.
"""

import os
from typing import Dict, Any, List, Optional
from .parameter_normalizer import normalize_llm_parameters


class ScriptGenerator:
    """Generates Google Earth Engine scripts based on analysis requirements."""
    
    def __init__(self):
        """Initialize script generator with template loading."""
        self.templates_dir = os.path.join(os.path.dirname(__file__), "templates")
        self.base_templates = self._load_base_templates()
        
    def _load_base_templates(self) -> Dict[str, str]:
        """Load base script templates for different analysis types."""
        return {
            "ndvi": self._get_ndvi_template(),
            "landcover": self._get_landcover_template(), 
            "change_detection": self._get_change_detection_template(),
            "water_analysis": self._get_water_analysis_template(),
            "climate_weather": self._get_climate_template(),
            "urban_analysis": self._get_urban_template(),
            "forest_analysis": self._get_forest_template(),
            "agriculture": self._get_agriculture_template(),
            "general_stats": self._get_general_stats_template()
        }
        
    def generate_script(
        self, 
        intent: str, 
        roi_geometry: Dict[str, Any],
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate a GEE script based on analysis intent and parameters.
        
        Args:
            intent: Analysis intent (ndvi, landcover, etc.)
            roi_geometry: GeoJSON geometry for the region of interest
            parameters: Analysis parameters (date_range, datasets, etc.)
            
        Returns:
            Dict containing the generated script and metadata
        """
        # Normalize parameters for LLM compatibility
        normalized_params = normalize_llm_parameters(parameters)
        
        # Use normalized intent if provided, otherwise use the passed intent
        final_intent = normalized_params.get("primary_intent", intent)
        
        # Get base template for the intent
        template = self.base_templates.get(final_intent, self.base_templates["general_stats"])
        
        # Extract normalized parameters
        datasets = normalized_params.get("recommended_datasets", ["COPERNICUS/S2_SR"])
        date_range = normalized_params.get("date_range", {})
        analysis_params = normalized_params.get("parameters", {})
        
        # Generate script by filling template
        script_code = self._fill_template(
            template=template,
            intent=final_intent,
            roi_geometry=roi_geometry,
            datasets=datasets,
            date_range=date_range,
            analysis_params=analysis_params
        )
        
        # Generate metadata
        metadata = self._generate_metadata(final_intent, normalized_params, roi_geometry)
        
        return {
            "script_code": script_code,
            "metadata": metadata,
            "intent": final_intent,
            "datasets_used": datasets,
            "roi_geometry": roi_geometry,
            "original_parameters": parameters,  # Keep track of original
            "normalized_parameters": normalized_params  # Show normalization
        }
        
    def _fill_template(
        self,
        template: str,
        intent: str,
        roi_geometry: Dict[str, Any],
        datasets: List[str],
        date_range: Dict[str, Any],
        analysis_params: Dict[str, Any]
    ) -> str:
        """Fill template with actual parameters."""
        
        # Convert GeoJSON geometry to GEE geometry
        gee_geometry = self._geojson_to_gee_geometry(roi_geometry)
        
        # Format date range
        start_date = date_range.get("start_date", "2023-01-01")
        end_date = date_range.get("end_date", "2023-12-31")
        
        # Get primary dataset
        primary_dataset = datasets[0] if datasets else "COPERNICUS/S2_SR"
        
        # Format cloud cover
        max_cloud_cover = analysis_params.get("max_cloud_cover", 20)
        
        # Prepare template parameters (avoid conflicts)
        template_params = {
            "roi_geometry": gee_geometry,
            "primary_dataset": primary_dataset,
            "start_date": start_date,
            "end_date": end_date,
            "max_cloud_cover": max_cloud_cover
        }
        
        # Add other analysis parameters (excluding conflicts)
        for key, value in analysis_params.items():
            if key not in template_params:
                template_params[key] = value
        
        # Fill template placeholders
        script_code = template.format(**template_params)
        
        return script_code
        
    def _geojson_to_gee_geometry(self, geojson_geometry: Dict[str, Any]) -> str:
        """Convert GeoJSON geometry to GEE geometry code."""
        geom_type = geojson_geometry.get("type", "")
        coordinates = geojson_geometry.get("coordinates", [])
        
        if geom_type == "Polygon" and coordinates and len(coordinates) > 0:
            # Convert polygon coordinates to GEE format
            coords_list = coordinates[0]  # First ring (exterior)
            if coords_list and len(coords_list) >= 3:  # Need at least 3 points
                coord_pairs = ", ".join([f"[{lng}, {lat}]" for lng, lat in coords_list])
                return f"ee.Geometry.Polygon([[{coord_pairs}]])"
        
        elif geom_type == "Point" and coordinates and len(coordinates) >= 2:
            # Convert point to small buffer around point
            lng, lat = coordinates[0], coordinates[1]
            buffer_size = 0.01  # ~1km buffer
            return f"ee.Geometry.Rectangle([{lng-buffer_size}, {lat-buffer_size}, {lng+buffer_size}, {lat+buffer_size}])"
        
        elif geom_type == "LineString" and coordinates and len(coordinates) >= 2:
            # Convert line to polygon by buffering
            coord_pairs = ", ".join([f"[{lng}, {lat}]" for lng, lat in coordinates])
            return f"ee.Geometry.LineString([{coord_pairs}]).buffer(1000)"  # 1km buffer
        
        # Enhanced fallback - try to extract any coordinate pair from the geometry
        if isinstance(geojson_geometry, dict):
            all_coords = self._extract_any_coordinates(geojson_geometry)
            if all_coords:
                lng, lat = all_coords[0], all_coords[1]
                # Create a reasonable rectangle around the coordinate
                buffer_size = 0.05  # ~5km buffer for better analysis area
                return f"ee.Geometry.Rectangle([{lng-buffer_size}, {lat-buffer_size}, {lng+buffer_size}, {lat+buffer_size}])"
        
        # Ultimate fallback - global extent (avoid hardcoded Mumbai)
        return "ee.Geometry.Rectangle([-180, -60, 180, 60])"  # Global extent excluding polar regions
    
    def _extract_any_coordinates(self, geom: Dict[str, Any]) -> List[float]:
        """Extract any valid coordinate pair from a geometry object."""
        def extract_coords_recursive(obj):
            if isinstance(obj, list):
                # Check if this is a coordinate pair [lng, lat]
                if len(obj) == 2 and all(isinstance(x, (int, float)) for x in obj):
                    return obj
                # Recursively check nested lists
                for item in obj:
                    result = extract_coords_recursive(item)
                    if result:
                        return result
            elif isinstance(obj, dict):
                for value in obj.values():
                    result = extract_coords_recursive(value)
                    if result:
                        return result
            return None
        
        return extract_coords_recursive(geom)
        
    def _generate_metadata(
        self, 
        intent: str, 
        parameters: Dict[str, Any], 
        roi_geometry: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate metadata for the script execution."""
        return {
            "analysis_type": intent,
            "script_version": "1.0",
            "generated_timestamp": "2024-01-01T00:00:00Z",  # Would use actual timestamp
            "parameters_used": parameters,
            "roi_area_km2": self._estimate_area(roi_geometry),
            "expected_processing_time_seconds": self._estimate_processing_time(intent, roi_geometry),
            "output_description": self._get_output_description(intent)
        }
        
    def _estimate_area(self, roi_geometry: Dict[str, Any]) -> float:
        """Estimate area of ROI in square kilometers (rough calculation)."""
        # Simple bounding box area estimation
        if roi_geometry.get("type") == "Polygon":
            coordinates = roi_geometry.get("coordinates", [])
            if coordinates and len(coordinates) > 0 and len(coordinates[0]) >= 4:
                coords = coordinates[0]
                lngs = [coord[0] for coord in coords]
                lats = [coord[1] for coord in coords]
                
                lng_diff = max(lngs) - min(lngs)
                lat_diff = max(lats) - min(lats)
                
                # Rough conversion to km (1 degree ≈ 111 km)
                area_km2 = lng_diff * lat_diff * 111 * 111
                return round(area_km2, 2)
        
        return 100.0  # Default estimate
        
    def _estimate_processing_time(self, intent: str, roi_geometry: Dict[str, Any]) -> int:
        """Estimate processing time in seconds."""
        base_times = {
            "ndvi": 10,
            "landcover": 30,
            "change_detection": 60,
            "water_analysis": 15,
            "climate_weather": 20,
            "urban_analysis": 25,
            "forest_analysis": 20,
            "agriculture": 15,
            "general_stats": 10
        }
        
        base_time = base_times.get(intent, 15)
        area_factor = max(1.0, self._estimate_area(roi_geometry) / 100.0)
        
        return int(base_time * area_factor)
        
    def _get_output_description(self, intent: str) -> str:
        """Get description of expected output for the analysis type."""
        descriptions = {
            "ndvi": "NDVI map showing vegetation health (green = healthy, red = stressed)",
            "landcover": "Land cover classification map with different colors for each land type",
            "change_detection": "Change detection map highlighting areas of temporal variation",
            "water_analysis": "Water body map highlighting rivers, lakes, and water features",
            "climate_weather": "Climate statistics and trends for the region",
            "urban_analysis": "Urban development map showing built-up areas and growth",
            "forest_analysis": "Forest cover map showing tree density and forest health",
            "agriculture": "Agricultural area map showing crop distribution and health",
            "general_stats": "General statistics and summary information for the region"
        }
        
        return descriptions.get(intent, "Geospatial analysis results for the specified region")
        
    # Template definitions
    def _get_ndvi_template(self) -> str:
        """Template for NDVI analysis."""
        return '''
// NDVI Analysis Script
var roi = {roi_geometry};
var startDate = '{start_date}';
var endDate = '{end_date}';
var maxCloudCover = {max_cloud_cover};

// Load image collection
var collection = ee.ImageCollection('{primary_dataset}')
  .filterBounds(roi)
  .filterDate(startDate, endDate)
  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', maxCloudCover));

// Calculate median composite
var composite = collection.median().clip(roi);

// Calculate NDVI
var ndvi = composite.normalizedDifference(['B8', 'B4']).rename('NDVI');

// Calculate statistics
var stats = ndvi.reduceRegion({{
  reducer: ee.Reducer.mean().combine({{
    reducer2: ee.Reducer.min(),
    sharedInputs: true
  }}).combine({{
    reducer2: ee.Reducer.max(),
    sharedInputs: true
  }}),
  geometry: roi,
  scale: 30,
  maxPixels: 1e9
}});

// Export results
var result = {{
  'ndvi_stats': stats,
  'pixel_count': ndvi.select('NDVI').reduceRegion({{
    reducer: ee.Reducer.count(),
    geometry: roi,
    scale: 30,
    maxPixels: 1e9
  }}),
  'analysis_type': 'ndvi'
}};

result;
'''

    def _get_landcover_template(self) -> str:
        """Template for land cover analysis."""
        return '''
// Land Cover Analysis Script
var roi = {roi_geometry};
var startDate = '{start_date}';
var endDate = '{end_date}';

// Load land cover dataset
var landcover = ee.Image('ESA/WorldCover/v100/2020').clip(roi);

// Calculate area statistics for each land cover class
var areaImage = ee.Image.pixelArea().divide(1000000); // Convert to km²
var areaStats = areaImage.addBands(landcover).reduceRegion({{
  reducer: ee.Reducer.sum().group({{
    groupField: 1,
    groupName: 'landcover_class'
  }}),
  geometry: roi,
  scale: 100,
  maxPixels: 1e9
}});

var result = {{
  'landcover_stats': areaStats,
  'analysis_type': 'landcover',
  'total_area_km2': areaImage.reduceRegion({{
    reducer: ee.Reducer.sum(),
    geometry: roi,
    scale: 100,
    maxPixels: 1e9
  }})
}};

result;
'''

    def _get_general_stats_template(self) -> str:
        """Template for general statistics."""
        return '''
// General Statistics Script
var roi = {roi_geometry};
var startDate = '{start_date}';
var endDate = '{end_date}';
var maxCloudCover = {max_cloud_cover};

// Load image collection
var collection = ee.ImageCollection('{primary_dataset}')
  .filterBounds(roi)
  .filterDate(startDate, endDate)
  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', maxCloudCover));

// Get collection info
var collectionSize = collection.size();
var composite = collection.median().clip(roi);

// Calculate basic statistics
var stats = composite.select(['B4', 'B3', 'B2']).reduceRegion({{
  reducer: ee.Reducer.mean().combine({{
    reducer2: ee.Reducer.min(),
    sharedInputs: true
  }}).combine({{
    reducer2: ee.Reducer.max(),
    sharedInputs: true
  }}),
  geometry: roi,
  scale: 30,
  maxPixels: 1e9
}});

// Calculate area
var area = ee.Image.pixelArea().reduceRegion({{
  reducer: ee.Reducer.sum(),
  geometry: roi,
  scale: 30,
  maxPixels: 1e9
}});

var result = {{
  'basic_stats': stats,
  'area_m2': area,
  'image_count': collectionSize,
  'analysis_type': 'general_stats'
}};

result;
'''

    def _get_water_analysis_template(self) -> str:
        """Template for water analysis."""
        return '''
// Water Analysis Script
var roi = {roi_geometry};
var startDate = '{start_date}';
var endDate = '{end_date}';
var maxCloudCover = {max_cloud_cover};

// Load image collection
var collection = ee.ImageCollection('{primary_dataset}')
  .filterBounds(roi)
  .filterDate(startDate, endDate)
  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', maxCloudCover));

var composite = collection.median().clip(roi);

// Calculate NDWI for water detection
var ndwi = composite.normalizedDifference(['B3', 'B8']).rename('NDWI');
var waterMask = ndwi.gt(0.3);

// Calculate water area
var waterArea = ee.Image.pixelArea().multiply(waterMask).reduceRegion({{
  reducer: ee.Reducer.sum(),
  geometry: roi,
  scale: 30,
  maxPixels: 1e9
}});

var result = {{
  'water_area_m2': waterArea,
  'ndwi_stats': ndwi.reduceRegion({{
    reducer: ee.Reducer.mean().combine({{
      reducer2: ee.Reducer.min(),
      sharedInputs: true
    }}).combine({{
      reducer2: ee.Reducer.max(),
      sharedInputs: true
    }}),
    geometry: roi,
    scale: 30,
    maxPixels: 1e9
  }}),
  'analysis_type': 'water_analysis'
}};

result;
'''

    def _get_change_detection_template(self) -> str:
        """Template for change detection analysis."""
        return '''
// Change Detection Script
var roi = {roi_geometry};
var startDate = '{start_date}';
var endDate = '{end_date}';
var maxCloudCover = {max_cloud_cover};

// Split date range into two periods
var midDate = ee.Date(startDate).advance(
  ee.Date(endDate).difference(ee.Date(startDate), 'day').divide(2), 'day'
);

// Load images for both periods
var collection1 = ee.ImageCollection('{primary_dataset}')
  .filterBounds(roi)
  .filterDate(startDate, midDate)
  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', maxCloudCover));

var collection2 = ee.ImageCollection('{primary_dataset}')
  .filterBounds(roi)
  .filterDate(midDate, endDate)
  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', maxCloudCover));

var composite1 = collection1.median().clip(roi);
var composite2 = collection2.median().clip(roi);

// Calculate NDVI for both periods
var ndvi1 = composite1.normalizedDifference(['B8', 'B4']);
var ndvi2 = composite2.normalizedDifference(['B8', 'B4']);

// Calculate change
var change = ndvi2.subtract(ndvi1);
var significantChange = change.abs().gt(0.1);

// Calculate change statistics
var changeStats = change.reduceRegion({{
  reducer: ee.Reducer.mean().combine({{
    reducer2: ee.Reducer.min(),
    sharedInputs: true
  }}).combine({{
    reducer2: ee.Reducer.max(),
    sharedInputs: true
  }}),
  geometry: roi,
  scale: 30,
  maxPixels: 1e9
}});

var result = {{
  'change_stats': changeStats,
  'change_area_m2': ee.Image.pixelArea().multiply(significantChange).reduceRegion({{
    reducer: ee.Reducer.sum(),
    geometry: roi,
    scale: 30,
    maxPixels: 1e9
  }}),
  'analysis_type': 'change_detection'
}};

result;
'''

    # Placeholder templates for other analysis types
    def _get_climate_template(self) -> str:
        return self._get_general_stats_template().replace('general_stats', 'climate_weather')
        
    def _get_urban_template(self) -> str:
        return self._get_landcover_template().replace('landcover', 'urban_analysis')
        
    def _get_forest_template(self) -> str:
        return self._get_ndvi_template().replace('ndvi', 'forest_analysis')
        
    def _get_agriculture_template(self) -> str:
        return self._get_ndvi_template().replace('ndvi', 'agriculture')
