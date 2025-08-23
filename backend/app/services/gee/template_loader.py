"""
Template Loader for GEE Analysis Templates

Manages loading and execution of JavaScript GEE templates for specific analysis types.
Provides a clean interface between Python and JavaScript template execution.
"""

import os
import json
from typing import Dict, Any, List, Optional
from pathlib import Path

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
        # This is a simplified approach - in production, you might want to:
        # 1. Use ee.data.evaluateExpression() for full JS execution
        # 2. Or translate the JS template to Python equivalent
        # 3. Or use Earth Engine Apps API
        
        # For now, we'll execute the generateScript function logic
        # by translating key parts to Python
        
        # Extract template name from code
        if "water_analysis" in template_code:
            return self._execute_water_template(roi, params)
        elif "forest_cover" in template_code:
            return self._execute_forest_template(roi, params)
        elif "lulc_analysis" in template_code:
            return self._execute_lulc_template(roi, params)
        elif "population_density" in template_code:
            return self._execute_population_template(roi, params)
        elif "soil_analysis" in template_code:
            return self._execute_soil_template(roi, params)
        elif "transportation_network" in template_code:
            return self._execute_transport_template(roi, params)
        elif "climate_analysis" in template_code:
            return self._execute_climate_template(roi, params)
        else:
            return {"error": "Unknown template type"}
    
    def _execute_water_template(self, roi, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute water analysis template (Python equivalent)."""
        try:
            # This mirrors the water_analysis.js logic
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
    
    def _execute_forest_template(self, roi, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute forest cover template (Python equivalent)."""
        try:
            # Hansen Global Forest Change
            hansen = ee.Image('UMD/hansen/global_forest_change_2022_v1_10')
            tree_cover_2000 = hansen.select('treecover2000').clip(roi)
            forest_loss = hansen.select('loss').clip(roi)
            
            # Forest mask (>30% tree cover)
            forest_mask_2000 = tree_cover_2000.gte(30)
            current_forest = forest_mask_2000.And(forest_loss.Not())
            
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
            
            return {
                "analysis_type": "forest_cover",
                "datasets_used": ["UMD/hansen/global_forest_change_2022_v1_10"],
                "forest_area_m2": forest_area_m2,
                "forest_loss_area_m2": loss_area_m2,
                "forest_area_km2": forest_area_m2.get('area', 0) / 1000000,
                "analysis_methods": ["Hansen Global Forest Change"]
            }
            
        except Exception as e:
            return {"error": f"Forest template execution failed: {str(e)}"}
    
    # Placeholder methods for other templates
    def _execute_lulc_template(self, roi, params: Dict[str, Any]) -> Dict[str, Any]:
        return {"analysis_type": "lulc_analysis", "datasets_used": ["ESA/WorldCover/v200"], "status": "template_ready"}
    
    def _execute_population_template(self, roi, params: Dict[str, Any]) -> Dict[str, Any]:
        return {"analysis_type": "population_density", "datasets_used": ["WorldPop/GP/100m/pop"], "status": "template_ready"}
    
    def _execute_soil_template(self, roi, params: Dict[str, Any]) -> Dict[str, Any]:
        return {"analysis_type": "soil_analysis", "datasets_used": ["ISRIC/SoilGrids/v2017_07"], "status": "template_ready"}
    
    def _execute_transport_template(self, roi, params: Dict[str, Any]) -> Dict[str, Any]:
        return {"analysis_type": "transportation_network", "datasets_used": ["COPERNICUS/S2_SR_HARMONIZED"], "status": "template_ready"}
    
    def _execute_climate_template(self, roi, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute climate analysis template (Python equivalent)."""
        try:
            # This mirrors the climate_analysis.js logic
            start_date = params.get('startDate', '2023-01-01')
            end_date = params.get('endDate', '2023-12-31')
            
            # ERA5 Land Climate Data
            era5_collection = ee.ImageCollection('ECMWF/ERA5_LAND/DAILY_AGGR') \
                .filterBounds(roi) \
                .filterDate(start_date, end_date)
            
            # Check if ERA5 collection has data
            era5_count = era5_collection.size().getInfo()
            
            if era5_count > 0:
                # Temperature analysis
                temperature_2m = era5_collection.select('temperature_2m')
                temp_stats = temperature_2m.reduce(ee.Reducer.mean().combine(
                    reducer2=ee.Reducer.min(), sharedInputs=True
                ).combine(
                    reducer2=ee.Reducer.max(), sharedInputs=True
                )).reduceRegion(
                    reducer=ee.Reducer.mean(),
                    geometry=roi,
                    scale=11000,
                    maxPixels=1e9
                ).getInfo()
                
                # Precipitation analysis
                precipitation = era5_collection.select('total_precipitation_sum')
                precip_stats = precipitation.reduce(ee.Reducer.sum()).reduceRegion(
                    reducer=ee.Reducer.mean(),
                    geometry=roi,
                    scale=11000,
                    maxPixels=1e9
                ).getInfo()
            else:
                temp_stats = {"temperature_2m_mean": 0, "temperature_2m_min": 0, "temperature_2m_max": 0}
                precip_stats = {"total_precipitation_sum_sum": 0}
            
            # GLDAS Hydrological Data
            gldas_collection = ee.ImageCollection('NASA/GLDAS/V021/NOAH/G025/T3H') \
                .filterBounds(roi) \
                .filterDate(start_date, end_date)
            
            gldas_count = gldas_collection.size().getInfo()
            
            if gldas_count > 0:
                soil_moisture = gldas_collection.select('SoilMoi0_10cm_inst').mean()
                humidity = gldas_collection.select('Qair_f_inst').mean()
                
                hydro_stats = ee.Image([soil_moisture, humidity]).reduceRegion(
                    reducer=ee.Reducer.mean(),
                    geometry=roi,
                    scale=25000,
                    maxPixels=1e9
                ).getInfo()
            else:
                hydro_stats = {"SoilMoi0_10cm_inst": 0, "Qair_f_inst": 0}
            
            # Sentinel-5P Air Quality (simplified)
            try:
                no2_collection = ee.ImageCollection('COPERNICUS/S5P/NRTI/L3_NO2') \
                    .filterBounds(roi) \
                    .filterDate(start_date, end_date) \
                    .select('tropospheric_NO2_column_number_density')
                
                no2_count = no2_collection.size().getInfo()
                
                if no2_count > 0:
                    no2_mean = no2_collection.mean().reduceRegion(
                        reducer=ee.Reducer.mean(),
                        geometry=roi,
                        scale=7000,
                        maxPixels=1e9
                    ).getInfo()
                else:
                    no2_mean = {"tropospheric_NO2_column_number_density": 0}
            except Exception as e:
                no2_mean = {"tropospheric_NO2_column_number_density": 0}
            
            # Sentinel-2 Vegetation Health
            s2_collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
                .filterBounds(roi) \
                .filterDate(start_date, end_date) \
                .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
            
            s2_count = s2_collection.size().getInfo()
            
            if s2_count > 0:
                s2_composite = s2_collection.median().clip(roi)
                ndvi = s2_composite.normalizedDifference(['B8', 'B4']).rename('NDVI')
                
                veg_stats = ndvi.reduceRegion(
                    reducer=ee.Reducer.mean().combine(
                        reducer2=ee.Reducer.min(), sharedInputs=True
                    ).combine(
                        reducer2=ee.Reducer.max(), sharedInputs=True
                    ),
                    geometry=roi,
                    scale=10,
                    maxPixels=1e9
                ).getInfo()
            else:
                veg_stats = {"NDVI_mean": 0, "NDVI_min": 0, "NDVI_max": 0}
            
            # Calculate ROI area
            pixel_area = ee.Image.pixelArea()
            roi_area_m2 = pixel_area.reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=roi,
                scale=1000,
                maxPixels=1e9
            ).getInfo().get('area', 0)
            
            roi_area_km2 = roi_area_m2 / 1e6
            
            return {
                "analysis_type": "climate_analysis",
                "datasets_used": [
                    "ECMWF/ERA5_LAND/DAILY_AGGR",
                    "NASA/GLDAS/V021/NOAH/G025/T3H", 
                    "COPERNICUS/S5P/NRTI/L3_NO2",
                    "COPERNICUS/S2_SR_HARMONIZED"
                ],
                "climate_statistics": temp_stats,
                "precipitation_statistics": precip_stats,
                "hydrological_statistics": hydro_stats,
                "air_quality_statistics": no2_mean,
                "vegetation_statistics": veg_stats,
                "roi_area_m2": roi_area_m2,
                "roi_area_km2": roi_area_km2,
                "image_counts": {
                    "era5_images": era5_count,
                    "gldas_images": gldas_count,
                    "s5p_images": 0,  # S5P count not easily available
                    "s2_images": s2_count
                },
                "analysis_methods": [
                    "ERA5 Land Climate Reanalysis",
                    "GLDAS Hydrological Data", 
                    "Sentinel-5P Air Quality",
                    "Sentinel-2 Vegetation Health"
                ]
            }
            
        except Exception as e:
            return {
                "error": f"Climate template execution failed: {str(e)}",
                "analysis_type": "climate_analysis",
                "datasets_used": []
            }
