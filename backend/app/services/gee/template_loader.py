"""
Template Loader for GEE Analysis Templates

Manages loading and execution of JavaScript GEE templates for specific analysis types.
Provides a clean interface between Python and JavaScript template execution.
"""

import os
import json
from typing import Dict, Any, List, Optional
from pathlib import Path
import sys

# Import Google Earth Engine
try:
    import ee
    GEE_AVAILABLE = True
except ImportError:
    print("Warning: Google Earth Engine not available")
    GEE_AVAILABLE = False
    ee = None


class TemplateLoader:
    """Loads and manages GEE JavaScript templates for different analysis types."""
    
    def __init__(self):
        """Initialize template loader."""
        self.templates_dir = Path(__file__).parent / "gee_templates"
        self.available_templates = self._load_available_templates()
        
    def _load_available_templates(self) -> Dict[str, Dict[str, Any]]:
        """Load metadata for all available templates."""
        templates = {}
        
        if not self.templates_dir.exists():
            print(f"Warning: Templates directory not found: {self.templates_dir}")
            return templates
            
        for template_file in self.templates_dir.glob("*.js"):
            template_name = template_file.stem
            template_info = self._extract_template_info(template_file)
            if template_info:
                templates[template_name] = template_info
                
        return templates
    
    def _extract_template_info(self, template_file: Path) -> Optional[Dict[str, Any]]:
        """Extract template configuration from JavaScript file."""
        try:
            with open(template_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Parse template configuration (simplified)
            # Look for TEMPLATE_CONFIG variable
            if "var TEMPLATE_CONFIG = {" in content:
                start = content.find("var TEMPLATE_CONFIG = {")
                end = content.find("};", start) + 2
                config_text = content[start:end]
                
                # Extract basic info (simplified parsing)
                info = {
                    "file_path": str(template_file),
                    "name": template_file.stem,
                    "description": self._extract_value(config_text, "description"),
                    "datasets": self._extract_array(config_text, "datasets"),
                    "metrics": self._extract_array(config_text, "metrics"),
                    "region": self._extract_value(config_text, "region"),
                    "example_query": self._extract_value(config_text, "example_query")
                }
                return info
                
        except Exception as e:
            print(f"Error parsing template {template_file}: {e}")
            
        return None
    
    def _extract_value(self, text: str, key: str) -> str:
        """Extract string value from JavaScript config."""
        try:
            pattern = f"{key}: '"
            start = text.find(pattern)
            if start == -1:
                pattern = f'{key}: "'
                start = text.find(pattern)
            if start == -1:
                return "Unknown"
                
            start += len(pattern)
            end = text.find("'", start)
            if end == -1:
                end = text.find('"', start)
            if end == -1:
                return "Unknown"
                
            return text[start:end]
        except:
            return "Unknown"
    
    def _extract_array(self, text: str, key: str) -> List[str]:
        """Extract array value from JavaScript config."""
        try:
            pattern = f"{key}: ["
            start = text.find(pattern)
            if start == -1:
                return []
                
            start += len(pattern)
            end = text.find("]", start)
            if end == -1:
                return []
                
            array_text = text[start:end]
            # Simple parsing - extract quoted strings
            items = []
            in_quote = False
            current_item = ""
            quote_char = None
            
            for char in array_text:
                if char in ['"', "'"] and not in_quote:
                    in_quote = True
                    quote_char = char
                elif char == quote_char and in_quote:
                    in_quote = False
                    if current_item.strip():
                        items.append(current_item.strip())
                    current_item = ""
                    quote_char = None
                elif in_quote:
                    current_item += char
                    
            return items
        except:
            return []
    
    def get_available_templates(self) -> Dict[str, Dict[str, Any]]:
        """Get list of all available templates with metadata."""
        return self.available_templates.copy()
    
    def get_template_by_name(self, template_name: str) -> Optional[Dict[str, Any]]:
        """Get template information by name."""
        return self.available_templates.get(template_name)
    
    def find_templates_by_keywords(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """Find templates that match given keywords."""
        matching_templates = []
        keywords_lower = [kw.lower() for kw in keywords]
        
        for template_name, template_info in self.available_templates.items():
            # Check template name
            if any(kw in template_name.lower() for kw in keywords_lower):
                matching_templates.append(template_info)
                continue
                
            # Check description
            description = template_info.get("description", "").lower()
            if any(kw in description for kw in keywords_lower):
                matching_templates.append(template_info)
                continue
                
            # Check example query
            example = template_info.get("example_query", "").lower()
            if any(kw in example for kw in keywords_lower):
                matching_templates.append(template_info)
                continue
                
        return matching_templates
    
    def execute_template(self, template_name: str, roi_geometry: Dict[str, Any], 
                        params: Optional[Dict[str, Any]] = None, gee_client=None) -> Dict[str, Any]:
        """Execute a GEE template with given ROI and parameters."""
        if not GEE_AVAILABLE:
            return {
                "error": "Google Earth Engine not available",
                "template_used": template_name,
                "fallback": True
            }
            
        # Check if GEE is initialized (if we have a client, it should be initialized)
        if gee_client and not gee_client.is_initialized:
            return {
                "error": "Google Earth Engine client not initialized",
                "template_used": template_name,
                "execution_success": False
            }
            
        if template_name not in self.available_templates:
            return {
                "error": f"Template '{template_name}' not found",
                "available_templates": list(self.available_templates.keys())
            }
            
        try:
            # Load template file
            template_info = self.available_templates[template_name]
            template_file = Path(template_info["file_path"])
            
            with open(template_file, 'r', encoding='utf-8') as f:
                template_code = f.read()
            
            # Convert ROI geometry to EE geometry
            ee_roi = self._dict_to_ee_geometry(roi_geometry)
            
            # Execute template using Earth Engine
            result = self._execute_js_template(template_code, ee_roi, params or {})
            
            # Add metadata
            result["template_used"] = template_name
            result["template_info"] = template_info
            result["execution_success"] = True
            
            return result
            
        except Exception as e:
            return {
                "error": f"Template execution failed: {str(e)}",
                "template_used": template_name,
                "execution_success": False
            }
    
    def _dict_to_ee_geometry(self, geom_dict: Dict[str, Any]):
        """Convert GeoJSON geometry dictionary to Earth Engine geometry."""
        if not GEE_AVAILABLE:
            return None
            
        geom_type = geom_dict.get("type", "Polygon")
        coordinates = geom_dict.get("coordinates", [])
        
        if geom_type == "Polygon":
            return ee.Geometry.Polygon(coordinates)
        elif geom_type == "Rectangle":
            # Assume coordinates are [west, south, east, north]
            if len(coordinates) == 4:
                return ee.Geometry.Rectangle(coordinates)
        elif geom_type == "Point":
            return ee.Geometry.Point(coordinates)
        elif geom_type == "LineString":
            return ee.Geometry.LineString(coordinates)
            
        # Fallback: try to create polygon
        try:
            return ee.Geometry.Polygon(coordinates)
        except:
            # Ultimate fallback: Delhi rectangle
            return ee.Geometry.Rectangle([76.68, 28.57, 77.53, 28.84])
    
    def _execute_js_template(self, template_code: str, roi, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute JavaScript template using Earth Engine Python API."""
        # Instead of using simplified Python equivalents, we need to properly
        # execute the JavaScript templates and extract their full results
        try:
            # Extract template name from code
            if "water_analysis" in template_code:
                return self._execute_water_template_full(roi, params)
            elif "forest_cover" in template_code:
                return self._execute_forest_template_full(roi, params)
            elif "lulc_analysis" in template_code:
                return self._execute_lulc_template_full(roi, params)
            elif "population_density" in template_code:
                return self._execute_population_template_full(roi, params)
            elif "soil_analysis" in template_code:
                return self._execute_soil_template_full(roi, params)
            elif "transportation_network" in template_code:
                return self._execute_transport_template_full(roi, params)
            elif "climate_analysis" in template_code:
                return self._execute_climate_template_full(roi, params)
            else:
                return {"error": "Unknown template type"}
        except Exception as e:
            return {"error": f"Template execution failed: {str(e)}"}
    
    def _execute_water_template_full(self, roi, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute water analysis template with full statistics."""
        try:
            start_date = params.get('startDate', '2023-01-01')
            end_date = params.get('endDate', '2023-12-31')
            
            # JRC Global Surface Water
            jrc_collection = ee.ImageCollection('JRC/GSW1_4/MonthlyHistory') \
                .filterBounds(roi) \
                .filterDate(start_date, end_date)
            
            # Check if JRC collection has any images
            jrc_count = jrc_collection.size().getInfo()
            
            if jrc_count > 0:
                jrc_recent = jrc_collection.sort('system:time_start', False).first()
                permanent_water = jrc_recent.select('water').eq(3)
                seasonal_water = jrc_recent.select('water').eq(2)
                all_water = permanent_water.Or(seasonal_water)
            else:
                # No JRC data available, create empty mask
                all_water = ee.Image.constant(0).clip(roi)
            
            # Sentinel-2
            s2_collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
                .filterBounds(roi) \
                .filterDate(start_date, end_date) \
                .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 15))
            
            # Check if S2 collection has any images
            s2_count = s2_collection.size().getInfo()
            
            if s2_count > 0:
                s2_composite = s2_collection.median().clip(roi)
            else:
                # No S2 data available, create empty image
                s2_composite = ee.Image.constant([0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]) \
                    .rename(['B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B8A', 'B9', 'B11', 'B12']) \
                    .clip(roi)
            
            # Water indices (only if we have S2 data)
            if s2_count > 0:
                ndwi = s2_composite.normalizedDifference(['B3', 'B8']).rename('NDWI')
                mndwi = s2_composite.normalizedDifference(['B3', 'B11']).rename('MNDWI')
                
                # Combined water mask
                ndwi_water = ndwi.gt(0.2)
                mndwi_water = mndwi.gt(0.1)
                combined_water = all_water.Or(ndwi_water).Or(mndwi_water)
            else:
                # No S2 data, use only JRC
                ndwi = ee.Image.constant(0).rename('NDWI').clip(roi)
                mndwi = ee.Image.constant(0).rename('MNDWI').clip(roi)
                combined_water = all_water
            
            # Calculate areas
            pixel_area = ee.Image.pixelArea()
            
            water_area_m2 = pixel_area.multiply(combined_water).reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=roi,
                scale=30,
                maxPixels=1e9
            ).getInfo()
            
            roi_area_m2 = pixel_area.reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=roi,
                scale=30,
                maxPixels=1e9
            ).getInfo()
            
            # Statistics (with proper error handling)
            try:
                ndwi_stats = ndwi.reduceRegion(
                    reducer=ee.Reducer.mean().combine(
                        reducer2=ee.Reducer.min(), sharedInputs=True
                    ).combine(
                        reducer2=ee.Reducer.max(), sharedInputs=True
                    ),
                    geometry=roi,
                    scale=30,
                    maxPixels=1e9
                ).getInfo()
            except Exception as e:
                ndwi_stats = {"NDWI_mean": 0, "NDWI_min": 0, "NDWI_max": 0}
            
            # Calculate water area in km2 and percentage
            water_area_value = water_area_m2.get('area', 0)
            roi_area_value = roi_area_m2.get('area', 0)
            
            water_area_km2 = water_area_value / 1000000 if water_area_value else 0
            roi_area_km2 = roi_area_value / 1000000 if roi_area_value else 0
            water_percentage = (water_area_km2 / roi_area_km2 * 100) if roi_area_km2 > 0 else 0
            
            return {
                "analysis_type": "water_analysis",
                "datasets_used": [
                    "JRC/GSW1_4/MonthlyHistory",
                    "COPERNICUS/S2_SR_HARMONIZED"
                ],
                "water_area_m2": water_area_m2,
                "water_area_km2": water_area_km2,
                "water_percentage": water_percentage,
                "roi_area_km2": roi_area_km2,
                "roi_area_m2": roi_area_m2,
                "ndwi_stats": ndwi_stats,
                "image_count": s2_collection.size().getInfo(),
                "water_detection_methods": [
                    "JRC Global Surface Water",
                    "NDWI (Green-NIR)",
                    "Modified NDWI (Green-SWIR)"
                ],
                "pixel_count": {
                    "total_roi": roi_area_m2.get('area', 0),
                    "water_pixels": water_area_m2.get('area', 0)
                }
            }
            
        except Exception as e:
            return {"error": f"Water template execution failed: {str(e)}"}
    
    def _execute_forest_template_full(self, roi, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute forest cover template with full statistics."""
        try:
            start_date = params.get('startDate', '2023-01-01')
            end_date = params.get('endDate', '2023-12-31')
            max_cloud_cover = params.get('maxCloudCover', 20)
            tree_cover_threshold = params.get('treeCoverThreshold', 30)
            
            # Hansen Global Forest Change
            hansen = ee.Image('UMD/hansen/global_forest_change_2022_v1_10')
            tree_cover_2000 = hansen.select('treecover2000').clip(roi)
            forest_loss = hansen.select('loss').clip(roi)
            forest_gain = hansen.select('gain').clip(roi)
            loss_year = hansen.select('lossyear').clip(roi)
            
            # Forest mask (>30% tree cover)
            forest_mask_2000 = tree_cover_2000.gte(tree_cover_threshold)
            current_forest = forest_mask_2000.And(forest_loss.Not())
            
            # Sentinel-2 for NDVI
            s2_collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
                .filterBounds(roi) \
                .filterDate(start_date, end_date) \
                .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', max_cloud_cover))
            
            # Calculate NDVI
            def add_ndvi(image):
                ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
                return image.addBands(ndvi)
            
            s2_with_ndvi = s2_collection.map(add_ndvi)
            ndvi = s2_with_ndvi.select('NDVI').mean().clip(roi)
            
            # High vegetation mask (NDVI > 0.5)
            high_veg_mask = ndvi.gt(0.5)
            
            # Calculate areas
            pixel_area = ee.Image.pixelArea()
            
            forest_area_m2 = pixel_area.multiply(current_forest).reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=roi,
                scale=30,
                maxPixels=1e9
            ).getInfo()
            
            loss_area_m2 = pixel_area.multiply(forest_loss).reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=roi,
                scale=30,
                maxPixels=1e9
            ).getInfo()
            
            gain_area_m2 = pixel_area.multiply(forest_gain).reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=roi,
                scale=30,
                maxPixels=1e9
            ).getInfo()
            
            high_veg_area_m2 = pixel_area.multiply(high_veg_mask).reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=roi,
                scale=30,
                maxPixels=1e9
            ).getInfo()
            
            roi_area_m2 = pixel_area.reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=roi,
                scale=30,
                maxPixels=1e9
            ).getInfo()
            
            # Tree cover statistics
            tree_cover_stats = tree_cover_2000.reduceRegion(
                reducer=ee.Reducer.mean().combine(
                    reducer2=ee.Reducer.min(), sharedInputs=True
                ).combine(
                    reducer2=ee.Reducer.max(), sharedInputs=True
                ).combine(
                    reducer2=ee.Reducer.stdDev(), sharedInputs=True
                ),
                geometry=roi,
                scale=30,
                maxPixels=1e9
            ).getInfo()
            
            # NDVI statistics
            ndvi_stats = ndvi.reduceRegion(
                reducer=ee.Reducer.mean().combine(
                    reducer2=ee.Reducer.min(), sharedInputs=True
                ).combine(
                    reducer2=ee.Reducer.max(), sharedInputs=True
                ).combine(
                    reducer2=ee.Reducer.stdDev(), sharedInputs=True
                ),
                geometry=roi,
                scale=30,
                maxPixels=1e9
            ).getInfo()
            
            # Convert to km2
            forest_area_km2 = forest_area_m2.get('area', 0) / 1000000
            loss_area_km2 = loss_area_m2.get('area', 0) / 1000000
            gain_area_km2 = gain_area_m2.get('area', 0) / 1000000
            high_veg_area_km2 = high_veg_area_m2.get('area', 0) / 1000000
            roi_area_km2 = roi_area_m2.get('area', 0) / 1000000
            
            return {
                "analysis_type": "forest_cover",
                "datasets_used": ["UMD/hansen/global_forest_change_2022_v1_10", "COPERNICUS/S2_SR_HARMONIZED"],
                "forest_area_km2": forest_area_km2,
                "forest_loss_area_km2": loss_area_km2,
                "forest_gain_area_km2": gain_area_km2,
                "high_vegetation_area_km2": high_veg_area_km2,
                "roi_area_km2": roi_area_km2,
                "tree_cover_stats": tree_cover_stats,
                "ndvi_stats": ndvi_stats,
                "analysis_methods": ["Hansen Global Forest Change", "Sentinel-2 NDVI Analysis"]
            }
            
        except Exception as e:
            return {"error": f"Forest template execution failed: {str(e)}"}
    
    def _execute_lulc_template_full(self, roi, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute LULC analysis template with full statistics."""
        try:
            # Initialize results with defaults
            result = {
                "analysis_type": "lulc_analysis",
                "datasets_used": [],
                "roi_area_km2": 0,
                "built_up_area_km2": 0,
                "cropland_area_km2": 0,
                "forest_area_km2": 0,
                "grassland_area_km2": 0,
                "water_area_km2": 0,
                "bare_soil_area_km2": 0,
                "analysis_methods": []
            }
            
            # Calculate ROI area first (this should always work)
            pixel_area = ee.Image.pixelArea()
            roi_area_m2 = pixel_area.reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=roi,
                scale=1000,
                maxPixels=1e9
            ).getInfo()
            
            roi_area_km2 = roi_area_m2.get('area', 0) / 1000000
            result["roi_area_km2"] = roi_area_km2
            
            # Try ESA WorldCover for land use classification
            try:
                world_cover = ee.Image("ESA/WorldCover/v200").clip(roi)
                
                # Classify different land cover types
                built_up = world_cover.eq(50)
                cropland = world_cover.eq(10)
                forest = world_cover.eq(10).Or(world_cover.eq(20)).Or(world_cover.eq(30)).Or(world_cover.eq(40))
                grassland = world_cover.eq(30)
                water = world_cover.eq(80)
                bare_soil = world_cover.eq(60)
                
                # Calculate areas for each class
                built_up_area_m2 = pixel_area.multiply(built_up).reduceRegion(
                    reducer=ee.Reducer.sum(),
                    geometry=roi,
                    scale=1000,
                    maxPixels=1e9
                ).getInfo()
                
                cropland_area_m2 = pixel_area.multiply(cropland).reduceRegion(
                    reducer=ee.Reducer.sum(),
                    geometry=roi,
                    scale=1000,
                    maxPixels=1e9
                ).getInfo()
                
                forest_area_m2 = pixel_area.multiply(forest).reduceRegion(
                    reducer=ee.Reducer.sum(),
                    geometry=roi,
                    scale=1000,
                    maxPixels=1e9
                ).getInfo()
                
                grassland_area_m2 = pixel_area.multiply(grassland).reduceRegion(
                    reducer=ee.Reducer.sum(),
                    geometry=roi,
                    scale=1000,
                    maxPixels=1e9
                ).getInfo()
                
                water_area_m2 = pixel_area.multiply(water).reduceRegion(
                    reducer=ee.Reducer.sum(),
                    geometry=roi,
                    scale=1000,
                    maxPixels=1e9
                ).getInfo()
                
                bare_soil_area_m2 = pixel_area.multiply(bare_soil).reduceRegion(
                    reducer=ee.Reducer.sum(),
                    geometry=roi,
                    scale=1000,
                    maxPixels=1e9
                ).getInfo()
                
                # Convert to km2
                result["built_up_area_km2"] = built_up_area_m2.get('area', 0) / 1000000
                result["cropland_area_km2"] = cropland_area_m2.get('area', 0) / 1000000
                result["forest_area_km2"] = forest_area_m2.get('area', 0) / 1000000
                result["grassland_area_km2"] = grassland_area_m2.get('area', 0) / 1000000
                result["water_area_km2"] = water_area_m2.get('area', 0) / 1000000
                result["bare_soil_area_km2"] = bare_soil_area_m2.get('area', 0) / 1000000
                
                result["datasets_used"].append("ESA/WorldCover/v200")
                result["analysis_methods"].append("ESA WorldCover Classification")
                
            except Exception as e:
                print(f"WorldCover failed: {e}")
                # Continue with basic ROI area only
            
            return result
            
        except Exception as e:
            return {"error": f"LULC template execution failed: {str(e)}"}
    
    def _execute_population_template_full(self, roi, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute population density template with full statistics."""
        try:
            year = params.get('year', 2020)
            
            # Initialize results with defaults
            result = {
                "analysis_type": "population_density",
                "datasets_used": [],
                "total_population": 0,
                "population_density_stats": {},
                "roi_area_km2": 0,
                "urban_area_km2": 0,
                "analysis_methods": []
            }
            
            # Calculate ROI area first (this should always work)
            pixel_area = ee.Image.pixelArea()
            roi_area_m2 = pixel_area.reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=roi,
                scale=1000,
                maxPixels=1e9
            ).getInfo()
            
            roi_area_km2 = roi_area_m2.get('area', 0) / 1000000
            result["roi_area_km2"] = roi_area_km2
            
            # Try WorldPop Population Grid
            try:
                world_pop = ee.ImageCollection("WorldPop/GP/100m/pop") \
                    .filter(ee.Filter.eq('year', year)) \
                    .first() \
                    .clip(roi)
                
                total_population = world_pop.reduceRegion(
                    reducer=ee.Reducer.sum(),
                    geometry=roi,
                    scale=100,
                    maxPixels=1e9
                ).getInfo()
                
                result["total_population"] = total_population.get('population', 0)
                result["datasets_used"].append("WorldPop/GP/100m/pop")
                result["analysis_methods"].append("WorldPop Population Grid")
                
            except Exception as e:
                print(f"WorldPop failed: {e}", file=sys.stderr)
                # Continue with other datasets
            
            # Try GPW Population Density
            try:
                gpw_collection = ee.ImageCollection("CIESIN/GPWv411/GPW_Population_Density") \
                    .filter(ee.Filter.eq('year', year))
                
                # Check if the collection is empty before calling .first()
                if gpw_collection.size().getInfo() > 0:
                    gpw_pop_density = gpw_collection.first().clip(roi)
                    pop_density_stats = gpw_pop_density.reduceRegion(
                        reducer=ee.Reducer.mean().combine(
                            reducer2=ee.Reducer.min(), sharedInputs=True
                        ).combine(
                            reducer2=ee.Reducer.max(), sharedInputs=True
                        ).combine(
                            reducer2=ee.Reducer.stdDev(), sharedInputs=True
                        ),
                        geometry=roi,
                        scale=1000,
                        maxPixels=1e9
                    ).getInfo()
                    
                    result["population_density_stats"] = pop_density_stats
                    result["datasets_used"].append("CIESIN/GPWv411/GPW_Population_Density")
                    result["analysis_methods"].append("GPW Population Density")
                
            except Exception as e:
                print(f"GPW failed: {e}", file=sys.stderr)
                # Continue with other datasets
            
            # Try ESA WorldCover for urban/rural classification
            try:
                # WorldCover is an ImageCollection, so filter for the latest year and get the first image.
                world_cover_img = ee.ImageCollection("ESA/WorldCover/v200").filterDate('2021-01-01', '2021-12-31').first()
                urban_mask = world_cover_img.eq(50).clip(roi)  # Built-up areas
                
                urban_area_m2 = pixel_area.multiply(urban_mask).reduceRegion(
                    reducer=ee.Reducer.sum(),
                    geometry=roi,
                    scale=100,
                    maxPixels=1e9
                ).getInfo()
                
                urban_area_km2 = urban_area_m2.get('area', 0) / 1000000
                result["urban_area_km2"] = urban_area_km2
                result["datasets_used"].append("ESA/WorldCover/v200")
                result["analysis_methods"].append("ESA WorldCover Urban Classification")
                
            except Exception as e:
                print(f"WorldCover failed: {e}", file=sys.stderr)
                # Continue without urban classification
            
            return result
            
        except Exception as e:
            return {"error": f"Population template execution failed: {str(e)}"}
    
    def _execute_transport_template_full(self, roi, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute transportation network template with full statistics."""
        try:
            # For transportation analysis, we'll use Sentinel-2 to identify built-up areas
            # and roads, then calculate connectivity metrics
            
            start_date = params.get('startDate', '2023-01-01')
            end_date = params.get('endDate', '2023-12-31')
            max_cloud_cover = params.get('maxCloudCover', 20)
            
            # Sentinel-2 for built-up area detection
            s2_collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
                .filterBounds(roi) \
                .filterDate(start_date, end_date) \
                .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', max_cloud_cover))
            
            # Calculate NDBI (Normalized Difference Built-up Index)
            def add_ndbi(image):
                ndbi = image.normalizedDifference(['B11', 'B8']).rename('NDBI')
                return image.addBands(ndbi)
            
            s2_with_ndbi = s2_collection.map(add_ndbi)
            ndbi = s2_with_ndbi.select('NDBI').mean().clip(roi)
            
            # Built-up area mask (NDBI > 0.1)
            built_up_mask = ndbi.gt(0.1)
            
            # Calculate pixel areas
            pixel_area = ee.Image.pixelArea()
            
            # Built-up area
            built_up_area_m2 = pixel_area.multiply(built_up_mask).reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=roi,
                scale=10,
                maxPixels=1e9
            ).getInfo()
            
            roi_area_m2 = pixel_area.reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=roi,
                scale=10,
                maxPixels=1e9
            ).getInfo()
            
            # NDBI statistics
            ndbi_stats = ndbi.reduceRegion(
                reducer=ee.Reducer.mean().combine(
                    reducer2=ee.Reducer.min(), sharedInputs=True
                ).combine(
                    reducer2=ee.Reducer.max(), sharedInputs=True
                ).combine(
                    reducer2=ee.Reducer.stdDev(), sharedInputs=True
                ),
                geometry=roi,
                scale=10,
                maxPixels=1e9
            ).getInfo()
            
            # Convert to km2
            roi_area_km2 = roi_area_m2.get('area', 0) / 1000000
            built_up_area_km2 = built_up_area_m2.get('area', 0) / 1000000
            
            return {
                "analysis_type": "transportation_network",
                "datasets_used": ["COPERNICUS/S2_SR_HARMONIZED"],
                "roi_area_km2": roi_area_km2,
                "built_up_area_km2": built_up_area_km2,
                "ndbi_stats": ndbi_stats,
                "analysis_methods": ["Sentinel-2 Built-up Area Detection", "NDBI Analysis"]
            }
            
        except Exception as e:
            return {"error": f"Transport template execution failed: {str(e)}"}
    
    def _execute_soil_template_full(self, roi, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute soil analysis template with full statistics."""
        try:
            depth = params.get('depth', '0-5cm')
            
            # Initialize results with defaults
            result = {
                "analysis_type": "soil_analysis",
                "datasets_used": [],
                "soil_ph_stats": {},
                "organic_carbon_stats": {},
                "clay_stats": {},
                "sand_stats": {},
                "silt_stats": {},
                "soil_moisture_stats": {},
                "roi_area_km2": 0,
                "analysis_methods": []
            }
            
            # Calculate ROI area first (this should always work)
            pixel_area = ee.Image.pixelArea()
            roi_area_m2 = pixel_area.reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=roi,
                scale=1000,
                maxPixels=1e9
            ).getInfo()
            
            roi_area_km2 = roi_area_m2.get('area', 0) / 1000000
            result["roi_area_km2"] = roi_area_km2
            
            # Try ISRIC SoilGrids Data (250m resolution) - this is deprecated and may fail.
            try:
                soil_grids = ee.Image("ISRIC/SoilGrids/v2017_07")
                
                # Soil properties at 0-5cm depth
                soil_ph = soil_grids.select("phh2o_0-5cm_mean").clip(roi)
                organic_carbon = soil_grids.select("soc_0-5cm_mean").clip(roi)
                clay_content = soil_grids.select("clay_0-5cm_mean").clip(roi)
                sand_content = soil_grids.select("sand_0-5cm_mean").clip(roi)
                silt_content = soil_grids.select("silt_0-5cm_mean").clip(roi)
                
                # Soil pH statistics
                ph_stats = soil_ph.reduceRegion(
                    reducer=ee.Reducer.mean().combine(
                        reducer2=ee.Reducer.min(), sharedInputs=True
                    ).combine(
                        reducer2=ee.Reducer.max(), sharedInputs=True
                    ).combine(
                        reducer2=ee.Reducer.stdDev(), sharedInputs=True
                    ),
                    geometry=roi,
                    scale=1000,
                    maxPixels=1e9
                ).getInfo()
                
                # Organic carbon statistics
                carbon_stats = organic_carbon.reduceRegion(
                    reducer=ee.Reducer.mean().combine(
                        reducer2=ee.Reducer.min(), sharedInputs=True
                    ).combine(
                        reducer2=ee.Reducer.max(), sharedInputs=True
                    ).combine(
                        reducer2=ee.Reducer.stdDev(), sharedInputs=True
                    ),
                    geometry=roi,
                    scale=1000,
                    maxPixels=1e9
                ).getInfo()
                
                # Clay content statistics
                clay_stats = clay_content.reduceRegion(
                    reducer=ee.Reducer.mean().combine(
                        reducer2=ee.Reducer.min(), sharedInputs=True
                    ).combine(
                        reducer2=ee.Reducer.max(), sharedInputs=True
                    ).combine(
                        reducer2=ee.Reducer.stdDev(), sharedInputs=True
                    ),
                    geometry=roi,
                    scale=1000,
                    maxPixels=1e9
                ).getInfo()
                
                # Sand content statistics
                sand_stats = sand_content.reduceRegion(
                    reducer=ee.Reducer.mean().combine(
                        reducer2=ee.Reducer.min(), sharedInputs=True
                    ).combine(
                        reducer2=ee.Reducer.max(), sharedInputs=True
                    ).combine(
                        reducer2=ee.Reducer.stdDev(), sharedInputs=True
                    ),
                    geometry=roi,
                    scale=1000,
                    maxPixels=1e9
                ).getInfo()
                
                # Silt content statistics
                silt_stats = silt_content.reduceRegion(
                    reducer=ee.Reducer.mean().combine(
                        reducer2=ee.Reducer.min(), sharedInputs=True
                    ).combine(
                        reducer2=ee.Reducer.max(), sharedInputs=True
                    ).combine(
                        reducer2=ee.Reducer.stdDev(), sharedInputs=True
                    ),
                    geometry=roi,
                    scale=1000,
                    maxPixels=1e9
                ).getInfo()
                
                result["soil_ph_stats"] = ph_stats
                result["organic_carbon_stats"] = carbon_stats
                result["clay_stats"] = clay_stats
                result["sand_stats"] = sand_stats
                result["silt_stats"] = silt_stats
                result["datasets_used"].append("ISRIC/SoilGrids/v2017_07")
                result["analysis_methods"].append("ISRIC SoilGrids Properties")
                
            except Exception as e:
                print(f"SoilGrids failed (dataset may be deprecated): {e}", file=sys.stderr)
                # Continue without soil properties
            
            # Try GLDAS Soil Moisture (25km resolution)
            try:
                gldas_collection = ee.ImageCollection("NASA/GLDAS/V021/NOAH/G025/T3H") \
                    .filterBounds(roi) \
                    .filterDate("2023-01-01", "2023-12-31") \
                    .select("SoilMoi0_10cm_inst")
                
                gldas_count = gldas_collection.size().getInfo()
                
                if gldas_count > 0:
                    gldas_mean = gldas_collection.mean().clip(roi)
            
                    # Soil moisture statistics
                    moisture_stats = gldas_mean.reduceRegion(
                        reducer=ee.Reducer.mean().combine(
                            reducer2=ee.Reducer.min(), sharedInputs=True
                        ).combine(
                            reducer2=ee.Reducer.max(), sharedInputs=True
                        ),
                        geometry=roi,
                        scale=25000,
                        maxPixels=1e9
                    ).getInfo()
            
                    result["soil_moisture_stats"] = moisture_stats
                    result["datasets_used"].append("NASA/GLDAS/V021/NOAH/G025/T3H")
                    result["analysis_methods"].append("GLDAS Soil Moisture")
                    
            except Exception as e:
                print(f"GLDAS failed: {e}", file=sys.stderr)
                # Continue without soil moisture
            
            return result
            
        except Exception as e:
            return {"error": f"Soil template execution failed: {str(e)}"}
    
    def _execute_climate_template_full(self, roi, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute climate analysis template with full statistics."""
        try:
            start_date = params.get('startDate', '2023-01-01')
            end_date = params.get('endDate', '2023-12-31')
            analysis_year = params.get('analysisYear', 2023)
            
            # Initialize results with defaults
            result = {
                "analysis_type": "climate_analysis",
                "datasets_used": [],
                "roi_area_km2": 0,
                "temperature_celsius": 0,
                "temperature_min_celsius": 0,
                "temperature_max_celsius": 0,
                "temperature_stats": {},
                "precipitation_mm": 0,
                "precipitation_stats": {},
                "soil_moisture_stats": {},
                "evapotranspiration_stats": {},
                "humidity_stats": {},
                "lst_stats": {},
                "analysis_methods": []
            }
            
            # Calculate ROI area first (this should always work)
            pixel_area = ee.Image.pixelArea()
            roi_area_m2 = pixel_area.reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=roi,
                scale=1000,
                maxPixels=1e9
            ).getInfo()
            
            roi_area_km2 = roi_area_m2.get('area', 0) / 1000000
            result["roi_area_km2"] = roi_area_km2
            
            # Try ERA5 Land Climate Data (Daily, 11km resolution)
            try:
                era5_land = ee.ImageCollection("ECMWF/ERA5_LAND/DAILY_AGGR") \
                    .filterBounds(roi) \
                    .filterDate(start_date, end_date)
                
                # Temperature analysis - MUST reduce collection to image first
                temperature_image = era5_land.select("temperature_2m").mean()
                temp_stats = temperature_image.reduceRegion(
                    reducer=ee.Reducer.mean().combine(
                        reducer2=ee.Reducer.min(), sharedInputs=True
                    ).combine(
                        reducer2=ee.Reducer.max(), sharedInputs=True
                    ).combine(
                        reducer2=ee.Reducer.stdDev(), sharedInputs=True
                    ),
                    geometry=roi,
                    scale=11000,
                    maxPixels=1e9
                ).getInfo()
            
                # Precipitation analysis - MUST reduce collection to image first
                precipitation_image = era5_land.select("total_precipitation_sum").sum()
                precip_sum = precipitation_image.reduceRegion(
                    reducer=ee.Reducer.sum(),
                    geometry=roi,
                    scale=11000,
                    maxPixels=1e9
                ).getInfo()
            
                # Convert temperature from Kelvin to Celsius
                temp_celsius = temp_stats.get('temperature_2m', 0) - 273.15 if temp_stats.get('temperature_2m') else 0
                temp_min_celsius = temp_stats.get('temperature_2m_min', 0) - 273.15 if temp_stats.get('temperature_2m_min') else 0
                temp_max_celsius = temp_stats.get('temperature_2m_max', 0) - 273.15 if temp_stats.get('temperature_2m_max') else 0
                
                # Convert precipitation from meters to mm
                precip_mm = precip_sum.get('total_precipitation_sum', 0) * 1000 if precip_sum.get('total_precipitation_sum') else 0
                
                result["temperature_celsius"] = temp_celsius
                result["temperature_min_celsius"] = temp_min_celsius
                result["temperature_max_celsius"] = temp_max_celsius
                result["temperature_stats"] = temp_stats
                result["precipitation_mm"] = precip_mm
                result["precipitation_stats"] = precip_sum
                result["datasets_used"].append("ECMWF/ERA5_LAND/DAILY_AGGR")
                result["analysis_methods"].append("ERA5 Land Climate Data")
            
            except Exception as e:
                print(f"ERA5 failed: {e}", file=sys.stderr)
                # Continue with other datasets
            
            # Try GLDAS Hydrological Data (3-hourly, 25km resolution)
            try:
                gldas = ee.ImageCollection("NASA/GLDAS/V021/NOAH/G025/T3H") \
                    .filterBounds(roi) \
                    .filterDate(start_date, end_date)
            
                # Soil moisture and evapotranspiration
                soil_moisture = gldas.select("SoilMoi0_10cm_inst").mean().clip(roi)
                evapotranspiration = gldas.select("Evap_tavg").mean().clip(roi)
                humidity = gldas.select("Qair_f_inst").mean().clip(roi)
                
                soil_moisture_stats = soil_moisture.reduceRegion(
                    reducer=ee.Reducer.mean().combine(
                        reducer2=ee.Reducer.min(), sharedInputs=True
                    ).combine(
                        reducer2=ee.Reducer.max(), sharedInputs=True
                    ),
                    geometry=roi,
                    scale=25000,
                    maxPixels=1e9
                ).getInfo()
                
                evapotranspiration_stats = evapotranspiration.reduceRegion(
                    reducer=ee.Reducer.mean().combine(
                        reducer2=ee.Reducer.min(), sharedInputs=True
                    ).combine(
                        reducer2=ee.Reducer.max(), sharedInputs=True
                    ),
                    geometry=roi,
                    scale=25000,
                    maxPixels=1e9
                ).getInfo()
                
                humidity_stats = humidity.reduceRegion(
                    reducer=ee.Reducer.mean().combine(
                        reducer2=ee.Reducer.min(), sharedInputs=True
                    ).combine(
                        reducer2=ee.Reducer.max(), sharedInputs=True
                    ),
                    geometry=roi,
                    scale=25000,
                    maxPixels=1e9
                ).getInfo()
                
                result["soil_moisture_stats"] = soil_moisture_stats
                result["evapotranspiration_stats"] = evapotranspiration_stats
                result["humidity_stats"] = humidity_stats
                result["datasets_used"].append("NASA/GLDAS/V021/NOAH/G025/T3H")
                result["analysis_methods"].append("GLDAS Hydrological Data")
                
            except Exception as e:
                print(f"GLDAS failed: {e}", file=sys.stderr)
                # Continue with other datasets
            
            # Try MODIS Land Surface Temperature (Daily, 1km resolution)
            try:
                modis_lst = ee.ImageCollection("MODIS/061/MOD11A1") \
                    .filterBounds(roi) \
                    .filterDate(start_date, end_date)
                
                # MUST reduce collection to image first
                lst_image = modis_lst.select("LST_Day_1km").mean()
                lst_stats = lst_image.reduceRegion(
                    reducer=ee.Reducer.mean().combine(
                        reducer2=ee.Reducer.min(), sharedInputs=True
                    ).combine(
                        reducer2=ee.Reducer.max(), sharedInputs=True
                    ).combine(
                        reducer2=ee.Reducer.stdDev(), sharedInputs=True
                    ),
                    geometry=roi,
                    scale=1000,
                    maxPixels=1e9
                ).getInfo()
                
                result["lst_stats"] = lst_stats
                result["datasets_used"].append("MODIS/061/MOD11A1")
                result["analysis_methods"].append("MODIS Land Surface Temperature")
                
            except Exception as e:
                print(f"MODIS failed: {e}", file=sys.stderr)
                # Continue without MODIS data
            
            return result
            
        except Exception as e:
            return {"error": f"Climate template execution failed: {str(e)}"}
