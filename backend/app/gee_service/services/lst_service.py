"""
Advanced Land Surface Temperature (LST) Service for Google Earth Engine.

This service provides comprehensive Land Surface Temperature analysis using MODIS MOD11A2 data
with advanced Urban Heat Island (UHI) calculation capabilities.

Key Features:
- MODIS MOD11A2 8-day composite data (1km resolution)
- Advanced temperature statistics (mean, min, max, std dev, percentiles)
- Multi-method UHI intensity calculation:
  * Dynamic World LULC data (10m resolution)
  * MODIS Land Cover data (500m resolution)
  * ESA WorldCover data (10m resolution)
  * Statistical approach (temperature percentiles)
- Robust fallback system for reliable UHI analysis
- Time series analysis with monthly composites
- High-quality visualization tile generation
- Polygon geometry support with intelligent tiling for large areas
- Detailed UHI reporting with method selection and pixel counts

Phase 2 Enhancements:
- Multiple data source integration for accurate urban/rural classification
- Statistical UHI calculation as reliable fallback
- Comprehensive error handling and method selection
- Detailed reporting of UHI calculation methodology

Author: GeoLLM Team
"""

import ee
import logging
from typing import Dict, List, Any, Optional, Tuple
import json
import time
# Removed unused imports for service account authentication

# Set up logging
logger = logging.getLogger(__name__)

# Initialize Earth Engine at module level for thread safety
try:
    project_id = 'gee-tool-469517'
    ee.Initialize(project=project_id)
    logger.info(f"✅ Earth Engine initialized with user auth for project '{project_id}'")
except Exception as e:
    logger.error(f"❌ Failed to initialize Earth Engine: {e}")
    logger.info("💡 Run 'earthengine authenticate' to set up user credentials.")

class LSTService:
    """
    Advanced Land Surface Temperature analysis service using MODIS data.
    
    This service provides comprehensive LST analysis with multi-method UHI calculation.
    It automatically selects the best available method for UHI analysis and provides
    detailed reporting of the methodology used.
    
    UHI Calculation Methods (in order of preference):
    1. Dynamic World LULC - High resolution (10m) land cover classification
    2. MODIS Land Cover - Medium resolution (500m) annual land cover
    3. ESA WorldCover - High resolution (10m) global land cover
    4. Statistical - Temperature percentile analysis (always available)
    
    The service automatically falls back to statistical analysis if LULC data
    is insufficient, ensuring reliable UHI analysis for any location.
    """
    
    # MODIS LST dataset (updated to current version)
    MODIS_LST_COLLECTION = "MODIS/061/MOD11A2"
    
    # Temperature visualization parameters
    LST_PALETTE = [
        "#2c7bb6",  # Cool (blue)
        "#abd9e9",  # Cool-moderate (light blue)
        "#ffffbf",  # Moderate (yellow)
        "#fdae61",  # Hot (orange)
        "#d7191c"   # Extreme hot (red)
    ]
    
    # Temperature breaks for visualization (°C)
    LST_BREAKS = [20, 25, 30, 35, 40]
    
    def __init__(self):
        """Initialize the LST service."""
        logger.info("✅ LST service initialized")
    
    @staticmethod
    def analyze_lst_with_polygon(
        roi_data: Dict[str, Any],
        start_date: str = "2023-06-01",
        end_date: str = "2023-08-31",
        include_uhi: bool = True,
        include_time_series: bool = False,
        scale: int = 1000,
        max_pixels: int = 1e8,
        exact_computation: bool = False
    ) -> Dict[str, Any]:
        """
        Analyze Land Surface Temperature using polygon geometry.
        """
        try:
            logger.info(f"🌡️ Starting LST analysis with polygon geometry")
            logger.info(f"📅 Date range: {start_date} to {end_date}")
            logger.info(f"🏙️ UHI analysis: {'Enabled' if include_uhi else 'Disabled'}")
            
            # Extract geometry information
            polygon_geometry = roi_data.get("polygon_geometry")
            geometry_tiles = roi_data.get("geometry_tiles", [])
            is_tiled = roi_data.get("is_tiled", False)
            is_fallback = roi_data.get("is_fallback", False)
            
            if not polygon_geometry:
                raise ValueError("No polygon geometry provided in ROI data")
            
            # Convert to Earth Engine geometry
            ee_polygon = ee.Geometry(polygon_geometry)
            
            # Load and process MODIS LST data
            lst_collection = LSTService._load_lst_collection(start_date, end_date)
            
            if lst_collection.size().getInfo() == 0:
                return {
                    "success": False,
                    "error": "No MODIS LST data available for the specified date range",
                    "error_type": "no_data"
                }
            
            # Process based on tiling
            if is_tiled and geometry_tiles:
                logger.info(f"🔧 Processing tiled geometry with {len(geometry_tiles)} tiles")
                result = LSTService._analyze_tiled_lst(
                    lst_collection, geometry_tiles, polygon_geometry,
                    start_date, end_date, include_uhi, include_time_series,
                    scale, max_pixels, exact_computation
                )
            else:
                logger.info(f"🔧 Processing single polygon geometry")
                result = LSTService._analyze_single_lst(
                    lst_collection, ee_polygon, polygon_geometry,
                    start_date, end_date, include_uhi, include_time_series,
                    scale, max_pixels, exact_computation
                )
            
            # Add metadata
            result["metadata"] = {
                "start_date": start_date,
                "end_date": end_date,
                "scale_meters": scale,
                "max_pixels": max_pixels,
                "exact_computation": exact_computation,
                "include_uhi": include_uhi,
                "include_time_series": include_time_series,
                "polygon_coordinates": len(polygon_geometry.get("coordinates", [[]])[0]) if polygon_geometry else 0,
                "modis_images_used": lst_collection.size().getInfo()
            }
            
            logger.info(f"✅ LST analysis completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error in LST analysis: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": "processing_error"
            }
    
    @staticmethod
    def _load_lst_collection(start_date: str, end_date: str) -> ee.ImageCollection:
        """Load and preprocess MODIS LST collection with better date handling."""
        try:
            # First try the requested date range
            collection = ee.ImageCollection(LSTService.MODIS_LST_COLLECTION) \
                .filterDate(start_date, end_date)
            
            collection_size = collection.size().getInfo()
            logger.info(f"📊 Found {collection_size} MODIS LST images for {start_date} to {end_date}")
            
            # If no data found, try a broader range
            if collection_size == 0:
                logger.info("🔄 Trying broader date range (2023-2024)...")
                collection = ee.ImageCollection(LSTService.MODIS_LST_COLLECTION) \
                    .filterDate("2023-01-01", "2024-12-31")
                collection_size = collection.size().getInfo()
                logger.info(f"📊 Broader search found {collection_size} images")
            
            # Preprocess LST data
            def preprocess_lst(image):
                # Convert Kelvin to Celsius and mask invalid pixels
                lst = image.select("LST_Day_1km") \
                    .multiply(0.02) \
                    .subtract(273.15) \
                    .updateMask(
                        image.select("LST_Day_1km").gt(0)  # Mask invalid LST values
                    )
                
                # Add quality band for additional masking
                qa = image.select("QC_Day")
                # More lenient quality masking - accept good and acceptable quality
                good_quality = qa.bitwiseAnd(3).lte(1)  # Bits 0-1: LST produced, good quality
                lst = lst.updateMask(good_quality)
                
                return lst.rename("LST").copyProperties(image, ['system:time_start'])
            
            processed_collection = collection.map(preprocess_lst)
            
            return processed_collection
            
        except Exception as e:
            logger.error(f"❌ Error loading LST collection: {e}")
            raise

    @staticmethod
    def generate_lst_grid(
        roi_geojson: Dict[str, Any],
        cell_size_km: float = 1.0,
        start_date: str = "2023-06-01",
        end_date: str = "2023-08-31",
        scale: int = 1000
    ) -> Dict[str, Any]:
        """Generate a vector grid over ROI with LST statistics per cell.
        
        Args:
            roi_geojson: GeoJSON Polygon or MultiPolygon for ROI
            cell_size_km: Grid cell size in kilometers (default 1km)
            start_date: Start date for LST data
            end_date: End date for LST data
            scale: Processing scale in meters
            
        Returns:
            GeoJSON FeatureCollection with LST stats per grid cell
        """
        try:
            logger.info(f"🔷 Generating LST grid: cell_size={cell_size_km}km")
            
            # Parse ROI geometry
            roi = ee.Geometry(roi_geojson)
            bounds = roi.bounds().coordinates().getInfo()[0]
            min_lng, min_lat = bounds[0][0], bounds[0][1]
            max_lng, max_lat = bounds[2][0], bounds[2][1]
            
            # Load LST collection
            lst_collection = LSTService._load_lst_collection(start_date, end_date)
            if lst_collection.size().getInfo() == 0:
                return {"success": False, "error": "no_data"}
            
            # Create median composite
            median_lst = lst_collection.select('LST').median()
            
            # Convert km to degrees (approximate at mid-latitude)
            mid_lat = (min_lat + max_lat) / 2
            cell_deg = cell_size_km / 111.0  # 1 degree ≈ 111 km
            
            # Generate grid cells
            features = []
            cell_id = 0
            
            lat = min_lat
            while lat < max_lat:
                lng = min_lng
                while lng < max_lng:
                    # Create cell polygon
                    cell_coords = [
                        [lng, lat],
                        [lng + cell_deg, lat],
                        [lng + cell_deg, lat + cell_deg],
                        [lng, lat + cell_deg],
                        [lng, lat]
                    ]
                    cell_poly = ee.Geometry.Polygon([cell_coords])
                    
                    # Check if cell intersects ROI
                    if not roi.intersects(cell_poly).getInfo():
                        lng += cell_deg
                        continue
                    
                    # Compute LST statistics for this cell
                    try:
                        stats = median_lst.reduceRegion(
                            reducer=ee.Reducer.mean()
                                .combine(ee.Reducer.min(), '', True)
                                .combine(ee.Reducer.max(), '', True)
                                .combine(ee.Reducer.stdDev(), '', True),
                            geometry=cell_poly.intersection(roi),
                            scale=scale,
                            maxPixels=1e8,
                            bestEffort=True
                        ).getInfo()
                        
                        mean_lst = stats.get('LST_mean')
                        min_lst = stats.get('LST_min')
                        max_lst = stats.get('LST_max')
                        std_lst = stats.get('LST_stdDev')
                        
                        # Only include cells with valid data
                        if mean_lst is not None:
                            feature = {
                                "type": "Feature",
                                "geometry": {
                                    "type": "Polygon",
                                    "coordinates": [cell_coords]
                                },
                                "properties": {
                                    "cell_id": cell_id,
                                    "mean_lst": round(float(mean_lst), 2),
                                    "min_lst": round(float(min_lst), 2) if min_lst else None,
                                    "max_lst": round(float(max_lst), 2) if max_lst else None,
                                    "std_lst": round(float(std_lst), 2) if std_lst else None,
                                    "cell_size_km": cell_size_km
                                }
                            }
                            features.append(feature)
                            cell_id += 1
                    except Exception as cell_error:
                        logger.warning(f"Failed to process cell at ({lng}, {lat}): {cell_error}")
                    
                    lng += cell_deg
                lat += cell_deg
            
            logger.info(f"✅ Generated {len(features)} grid cells with LST data")
            
            return {
                "success": True,
                "type": "FeatureCollection",
                "features": features,
                "metadata": {
                    "cell_size_km": cell_size_km,
                    "cell_count": len(features),
                    "date_range": {"start": start_date, "end": end_date},
                    "dataset": "MODIS/061/MOD11A2"
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Error generating LST grid: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def sample_lst_at_point(
        lng: float,
        lat: float,
        start_date: str = "2023-06-01",
        end_date: str = "2023-08-31",
        scale: int = 1000
    ) -> Dict[str, Any]:
        """Sample median LST value at a coordinate.
        Returns a small dict with value in Celsius and metadata.
        """
        try:
            point = ee.Geometry.Point([float(lng), float(lat)])
            lst_collection = LSTService._load_lst_collection(start_date, end_date)
            if lst_collection.size().getInfo() == 0:
                return {"success": False, "error": "no_data"}

            # Median composite
            median_lst = lst_collection.select('LST').median()

            # Buffer the point slightly to avoid nulls at exact pixel edges
            buffer_meters = max(int(scale / 2), 250)
            region = point.buffer(buffer_meters)

            sampled = median_lst.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=region,
                scale=scale,
                maxPixels=1e6,
                bestEffort=True
            ).getInfo()

            value = sampled.get('LST', None)
            if value is None:
                return {"success": False, "error": "no_value"}

            return {
                "success": True,
                "value_celsius": float(value),
                "units": "°C",
                "scale_meters": scale,
                "buffer_meters": buffer_meters,
                "date_range": {"start": start_date, "end": end_date},
                "dataset": LSTService.MODIS_LST_COLLECTION,
                # Simple quality proxy: since we mask using QC_Day bits and use median,
                # return a qualitative score based on whether the value exists and the buffer size
                "quality": {
                    "score": 0.9,
                    "method": "QC mask + median",
                    "notes": "Indicative only; refine with per-pixel QC if needed"
                }
            }
        except Exception as e:
            logger.error(f"❌ Error sampling LST at point: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def sample_lst_batch(
        points: List[Dict[str, float]],
        start_date: str = "2023-06-01",
        end_date: str = "2023-08-31",
        scale: int = 1000
    ) -> Dict[str, Any]:
        """Sample LST at multiple points in batch.
        
        Args:
            points: List of {"lng": x, "lat": y} dicts
            start_date: Start date for LST data
            end_date: End date for LST data
            scale: Processing scale in meters
            
        Returns:
            Dict with "success" and "results" list
        """
        try:
            logger.info(f"🔷 Batch sampling {len(points)} points")
            
            # Load LST collection once
            lst_collection = LSTService._load_lst_collection(start_date, end_date)
            if lst_collection.size().getInfo() == 0:
                return {"success": False, "error": "no_data"}
            
            median_lst = lst_collection.select('LST').median()
            
            results = []
            for idx, pt in enumerate(points):
                try:
                    lng, lat = pt["lng"], pt["lat"]
                    point = ee.Geometry.Point([float(lng), float(lat)])
                    buffer_meters = max(int(scale / 2), 250)
                    region = point.buffer(buffer_meters)
                    
                    sampled = median_lst.reduceRegion(
                        reducer=ee.Reducer.mean(),
                        geometry=region,
                        scale=scale,
                        maxPixels=1e6,
                        bestEffort=True
                    ).getInfo()
                    
                    value = sampled.get('LST', None)
                    
                    if value is not None:
                        results.append({
                            "index": idx,
                            "lng": lng,
                            "lat": lat,
                            "value_celsius": float(value),
                            "success": True
                        })
                    else:
                        results.append({
                            "index": idx,
                            "lng": lng,
                            "lat": lat,
                            "success": False,
                            "error": "no_value"
                        })
                except Exception as pt_error:
                    logger.warning(f"Failed to sample point {idx}: {pt_error}")
                    results.append({
                        "index": idx,
                        "lng": pt.get("lng"),
                        "lat": pt.get("lat"),
                        "success": False,
                        "error": str(pt_error)
                    })
            
            logger.info(f"✅ Batch sampled {len(results)} points")
            
            return {
                "success": True,
                "count": len(results),
                "results": results
            }
            
        except Exception as e:
            logger.error(f"❌ Error in batch sampling: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def _analyze_single_lst(
        lst_collection: ee.ImageCollection,
        ee_polygon: ee.Geometry,
        polygon_geometry: Dict[str, Any],
        start_date: str,
        end_date: str,
        include_uhi: bool,
        include_time_series: bool,
        scale: int,
        max_pixels: int,
        exact_computation: bool
    ) -> Dict[str, Any]:
        """Analyze LST for a single polygon geometry with improved UHI."""
        try:
            logger.info(f"🌡️ SINGLE POLYGON LST ANALYSIS STARTING...")
            
            # Get median LST clipped to polygon
            median_lst = lst_collection.select('LST').median().clip(ee_polygon)
            
            # Calculate polygon area
            polygon_area_m2 = ee_polygon.area(maxError=1000).getInfo()
            polygon_area_km2 = polygon_area_m2 / 1_000_000
            
            logger.info(f"🌡️ Polygon area: {polygon_area_km2:.2f} km²")
            
            # Compute LST statistics
            logger.info(f"🌡️ Computing LST statistics...")
            lst_stats = median_lst.reduceRegion(
                reducer=ee.Reducer.mean().combine(
                    ee.Reducer.minMax(), '', True
                ).combine(ee.Reducer.stdDev(), '', True),
                geometry=ee_polygon,
                scale=scale,
                maxPixels=max_pixels,
                bestEffort=not exact_computation
            ).getInfo()
            
            # Format LST stats
            if lst_stats:
                formatted_lst_stats = {
                    "LST_mean": lst_stats.get("LST_mean", lst_stats.get("mean", 0)),
                    "LST_min": lst_stats.get("LST_min", lst_stats.get("min", 0)),
                    "LST_max": lst_stats.get("LST_max", lst_stats.get("max", 0)),
                    "LST_stdDev": lst_stats.get("LST_stdDev", lst_stats.get("stdDev", 0))
                }
            else:
                logger.warning(f"⚠️ No valid LST stats found, using defaults")
                formatted_lst_stats = {
                    "LST_mean": 0.0,
                    "LST_min": 0.0,
                    "LST_max": 0.0,
                    "LST_stdDev": 0.0
                }
            
            # Calculate UHI intensity if requested
            uhi_intensity = 0.0
            uhi_details = {}
            if include_uhi:
                logger.info(f"🏙️ Computing UHI intensity...")
                uhi_result = LSTService._calculate_uhi_intensity_improved(
                    median_lst, ee_polygon, scale, max_pixels
                )
                uhi_intensity = uhi_result.get("intensity", 0.0)
                uhi_details = uhi_result.get("details", {})
            
            # Generate visualization tiles
            vis_params = {
                'min': 20,
                'max': 40,
                'palette': LSTService.LST_PALETTE
            }
            map_id = median_lst.getMapId(vis_params)
            # Use proper GEE tile URL format with authentication handled internally
            tile_url = f"https://earthengine.googleapis.com/v1/{map_id['mapid']}/tiles/{{z}}/{{x}}/{{y}}"
            tile_urls = {"urlFormat": tile_url}
            
            # Time series analysis if requested
            time_series_data = {}
            if include_time_series:
                time_series_data = LSTService._compute_lst_time_series(
                    lst_collection, ee_polygon, scale, start_date, end_date
                )
            
            # Get image count
            image_count = lst_collection.size().getInfo()
            
            return {
                "success": True,
                "analysis_type": "lst_analysis",
                "geometry_type": "single_polygon",
                "roi_area_km2": polygon_area_km2,
                "urlFormat": tile_urls.get("urlFormat", ""),
                "mapStats": {
                    "lst_statistics": formatted_lst_stats,
                    "uhi_intensity": uhi_intensity,
                    "uhi_details": uhi_details,
                    "image_count": image_count
                },
                "datasets_used": ["MODIS/061/MOD11A2"],
                "processing_time_seconds": 0,  # Will be calculated by the calling function
                "class_definitions": {},
                "tile_urls": tile_urls,
                "time_series": time_series_data,
                "image_count": image_count,
                "legend_config": {
                    "labelNames": ["Cool", "Moderate", "Hot", "Extreme"],
                    "palette": LSTService.LST_PALETTE,
                    "breaks": LSTService.LST_BREAKS,
                    "unit": "°C"
                },
                "visualization": {
                    "tile_url": tile_urls.get("urlFormat", ""),
                    "palette": LSTService.LST_PALETTE,
                    "min": 20,
                    "max": 40,
                    "legend": {
                        "type": "continuous",
                        "title": "Land Surface Temperature (LST)",
                        "description": "Surface temperature in Celsius from MODIS satellite data",
                        "palette": LSTService.LST_PALETTE,
                        "min_value": 20,
                        "max_value": 40,
                        "unit": "°C",
                        "classes": [
                            {"name": "Cool", "range": "(20 to 25)°C", "color": "#2c7bb6", "description": "Cool surface temperatures"},
                            {"name": "Cool-Moderate", "range": "(25 to 30)°C", "color": "#abd9e9", "description": "Cool-moderate surface temperatures"},
                            {"name": "Moderate", "range": "(30 to 35)°C", "color": "#ffffbf", "description": "Moderate surface temperatures"},
                            {"name": "Hot", "range": "(35 to 40)°C", "color": "#fdae61", "description": "Hot surface temperatures"},
                            {"name": "Extreme", "range": "(40+ °C)", "color": "#d7191c", "description": "Extreme surface temperatures"}
                        ]
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Error in single polygon LST analysis: {e}")
            raise
    
    @staticmethod
    def _calculate_uhi_intensity_improved(
        lst_image: ee.Image,
        geometry: ee.Geometry,
        scale: int,
        max_pixels: int
    ) -> Dict[str, Any]:
        """Improved UHI calculation with multiple data sources and methods."""
        try:
            logger.info(f"🏙️ Starting improved UHI intensity calculation...")
            
            # Method 1: Try Dynamic World LULC data
            uhi_result = LSTService._try_dynamic_world_uhi(lst_image, geometry, scale, max_pixels)
            if uhi_result.get("success", False):
                return uhi_result
            
            # Method 2: Try MODIS Land Cover
            uhi_result = LSTService._try_modis_lulc_uhi(lst_image, geometry, scale, max_pixels)
            if uhi_result.get("success", False):
                return uhi_result
            
            # Method 3: Try ESA WorldCover
            uhi_result = LSTService._try_esa_worldcover_uhi(lst_image, geometry, scale, max_pixels)
            if uhi_result.get("success", False):
                return uhi_result
            
            # Method 4: Statistical approach (temperature percentiles)
            uhi_result = LSTService._calculate_statistical_uhi(lst_image, geometry, scale, max_pixels)
            return uhi_result
            
        except Exception as e:
            logger.warning(f"⚠️ All UHI calculation methods failed: {e}")
            return {
                "intensity": 0.0,
                "details": {
                    "method": "error_fallback",
                    "error": str(e)
                }
            }
    
    @staticmethod
    def _try_dynamic_world_uhi(lst_image, geometry, scale, max_pixels) -> Dict[str, Any]:
        """Try UHI calculation using Dynamic World LULC data."""
        try:
            logger.info(f"🌍 Attempting Dynamic World UHI calculation...")
            
            # Try multiple date ranges for Dynamic World data
            date_ranges = [
                ("2024-01-01", "2024-12-31"),
                ("2023-01-01", "2023-12-31"),
                ("2022-01-01", "2022-12-31")
            ]
            
            lulc_collection = None
            for start_date, end_date in date_ranges:
                temp_collection = ee.ImageCollection("GOOGLE/DYNAMICWORLD/V1") \
                    .filterDate(start_date, end_date) \
                    .filterBounds(geometry)
                
                if temp_collection.size().getInfo() > 0:
                    lulc_collection = temp_collection
                    logger.info(f"✅ Found Dynamic World data for {start_date} to {end_date}")
                    break
            
            if not lulc_collection:
                return {"success": False, "reason": "no_dynamic_world_data"}
            
            # Get the mode (most common) land cover over time
            lulc_image = lulc_collection.select('label').mode()
            
            # Create more inclusive urban and rural masks
            # Urban: Built area (0) + some mixed areas with high built probability
            urban_mask = lulc_image.eq(0)  # Built area
            
            # Rural: Trees (1), flooded vegetation (2), crops (4), shrub/scrub (5), grassland (6)
            rural_mask = lulc_image.eq(1).Or(lulc_image.eq(2)).Or(lulc_image.eq(4)).Or(lulc_image.eq(5)).Or(lulc_image.eq(6))
            
            # Use a larger scale for pixel counting to avoid timeout
            count_scale = max(scale * 2, 100)
            
            # Count pixels
            urban_pixels = urban_mask.reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=geometry,
                scale=count_scale,
                maxPixels=max_pixels // 4,
                bestEffort=True
            ).getInfo()
            
            rural_pixels = rural_mask.reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=geometry,
                scale=count_scale,
                maxPixels=max_pixels // 4,
                bestEffort=True
            ).getInfo()
            
            urban_count = urban_pixels.get('label', 0)
            rural_count = rural_pixels.get('label', 0)
            
            logger.info(f"🏙️ Dynamic World - Urban pixels: {urban_count}, Rural pixels: {rural_count}")
            
            # Need at least 3 pixels of each type (reduced threshold)
            if urban_count < 3 or rural_count < 3:
                return {"success": False, "reason": f"insufficient_pixels_u{urban_count}_r{rural_count}"}
            
            # Calculate urban and rural LST
            urban_lst_stats = lst_image.updateMask(urban_mask).reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=geometry,
                scale=scale,
                maxPixels=max_pixels,
                bestEffort=True
            ).getInfo()
            
            rural_lst_stats = lst_image.updateMask(rural_mask).reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=geometry,
                scale=scale,
                maxPixels=max_pixels,
                bestEffort=True
            ).getInfo()
            
            urban_temp = urban_lst_stats.get("LST", None)
            rural_temp = rural_lst_stats.get("LST", None)
            
            if urban_temp is None or rural_temp is None:
                return {"success": False, "reason": "no_temperature_data"}
            
            uhi_intensity = urban_temp - rural_temp
            
            logger.info(f"🌡️ Dynamic World UHI - Urban: {urban_temp:.2f}°C, Rural: {rural_temp:.2f}°C, Intensity: {uhi_intensity:.2f}°C")
            
            return {
                "intensity": max(0, uhi_intensity),
                "details": {
                    "method": "dynamic_world_lulc",
                    "urban_lst": urban_temp,
                    "rural_lst": rural_temp,
                    "urban_pixels": urban_count,
                    "rural_pixels": rural_count,
                    "urban_percentage": (urban_count / (urban_count + rural_count)) * 100,
                    "data_source": "Dynamic World",
                    "count_scale": count_scale
                }
            }
            
        except Exception as e:
            logger.info(f"⚠️ Dynamic World UHI calculation failed: {e}")
            return {"success": False, "reason": f"error_{str(e)[:50]}"}
    
    @staticmethod
    def _try_modis_lulc_uhi(lst_image, geometry, scale, max_pixels) -> Dict[str, Any]:
        """Try UHI calculation using MODIS Land Cover data."""
        try:
            logger.info(f"🛰️ Attempting MODIS Land Cover UHI calculation...")
            
            # MODIS Land Cover Type 1 (annual, 500m)
            modis_lc = ee.ImageCollection("MODIS/061/MCD12Q1") \
                .filterDate("2023-01-01", "2023-12-31") \
                .select('LC_Type1') \
                .mode()  # Get most common land cover
            
            # Urban: Urban and Built-up Lands (13)
            urban_mask = modis_lc.eq(13)
            
            # Rural: Grasslands (10), Croplands (12), Deciduous Forest (4), Evergreen Forest (1), Mixed Forest (5)
            rural_mask = modis_lc.eq(10).Or(modis_lc.eq(12)).Or(modis_lc.eq(4)).Or(modis_lc.eq(1)).Or(modis_lc.eq(5))
            
            # Count pixels
            urban_pixels = urban_mask.reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=geometry,
                scale=scale,
                maxPixels=max_pixels // 4,
                bestEffort=True
            ).getInfo()
            
            rural_pixels = rural_mask.reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=geometry,
                scale=scale,
                maxPixels=max_pixels // 4,
                bestEffort=True
            ).getInfo()
            
            urban_count = urban_pixels.get('LC_Type1', 0)
            rural_count = rural_pixels.get('LC_Type1', 0)
            
            logger.info(f"🛰️ MODIS LC - Urban pixels: {urban_count}, Rural pixels: {rural_count}")
            
            if urban_count < 2 or rural_count < 2:
                return {"success": False, "reason": f"insufficient_modis_pixels_u{urban_count}_r{rural_count}"}
            
            # Calculate temperatures
            urban_temp = lst_image.updateMask(urban_mask).reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=geometry,
                scale=scale,
                maxPixels=max_pixels,
                bestEffort=True
            ).getInfo().get("LST")
            
            rural_temp = lst_image.updateMask(rural_mask).reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=geometry,
                scale=scale,
                maxPixels=max_pixels,
                bestEffort=True
            ).getInfo().get("LST")
            
            if urban_temp is None or rural_temp is None:
                return {"success": False, "reason": "no_modis_temperature_data"}
            
            uhi_intensity = urban_temp - rural_temp
            
            logger.info(f"🌡️ MODIS UHI - Urban: {urban_temp:.2f}°C, Rural: {rural_temp:.2f}°C, Intensity: {uhi_intensity:.2f}°C")
            
            return {
                "intensity": max(0, uhi_intensity),
                "details": {
                    "method": "modis_land_cover",
                    "urban_lst": urban_temp,
                    "rural_lst": rural_temp,
                    "urban_pixels": urban_count,
                    "rural_pixels": rural_count,
                    "data_source": "MODIS MCD12Q1"
                }
            }
            
        except Exception as e:
            logger.info(f"⚠️ MODIS Land Cover UHI calculation failed: {e}")
            return {"success": False, "reason": f"modis_error_{str(e)[:50]}"}
    
    @staticmethod
    def _try_esa_worldcover_uhi(lst_image, geometry, scale, max_pixels) -> Dict[str, Any]:
        """Try UHI calculation using ESA WorldCover data."""
        try:
            logger.info(f"🌍 Attempting ESA WorldCover UHI calculation...")
            
            # ESA WorldCover 10m resolution
            esa_wc = ee.ImageCollection("ESA/WorldCover/v200") \
                .first() \
                .select('Map')
            
            # Urban: Built-up (50)
            urban_mask = esa_wc.eq(50)
            
            # Rural: Tree cover (10), Shrubland (20), Grassland (30), Cropland (40)
            rural_mask = esa_wc.eq(10).Or(esa_wc.eq(20)).Or(esa_wc.eq(30)).Or(esa_wc.eq(40))
            
            # Use larger scale for ESA data due to high resolution
            esa_scale = max(scale, 100)
            
            # Count pixels
            urban_pixels = urban_mask.reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=geometry,
                scale=esa_scale,
                maxPixels=max_pixels // 10,
                bestEffort=True
            ).getInfo()
            
            rural_pixels = rural_mask.reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=geometry,
                scale=esa_scale,
                maxPixels=max_pixels // 10,
                bestEffort=True
            ).getInfo()
            
            urban_count = urban_pixels.get('Map', 0)
            rural_count = rural_pixels.get('Map', 0)
            
            logger.info(f"🌍 ESA WC - Urban pixels: {urban_count}, Rural pixels: {rural_count}")
            
            if urban_count < 5 or rural_count < 5:
                return {"success": False, "reason": f"insufficient_esa_pixels_u{urban_count}_r{rural_count}"}
            
            # Calculate temperatures
            urban_temp = lst_image.updateMask(urban_mask).reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=geometry,
                scale=scale,
                maxPixels=max_pixels,
                bestEffort=True
            ).getInfo().get("LST")
            
            rural_temp = lst_image.updateMask(rural_mask).reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=geometry,
                scale=scale,
                maxPixels=max_pixels,
                bestEffort=True
            ).getInfo().get("LST")
            
            if urban_temp is None or rural_temp is None:
                return {"success": False, "reason": "no_esa_temperature_data"}
            
            uhi_intensity = urban_temp - rural_temp
            
            logger.info(f"🌡️ ESA UHI - Urban: {urban_temp:.2f}°C, Rural: {rural_temp:.2f}°C, Intensity: {uhi_intensity:.2f}°C")
            
            return {
                "intensity": max(0, uhi_intensity),
                "details": {
                    "method": "esa_worldcover",
                    "urban_lst": urban_temp,
                    "rural_lst": rural_temp,
                    "urban_pixels": urban_count,
                    "rural_pixels": rural_count,
                    "data_source": "ESA WorldCover",
                    "scale_used": esa_scale
                }
            }
            
        except Exception as e:
            logger.info(f"⚠️ ESA WorldCover UHI calculation failed: {e}")
            return {"success": False, "reason": f"esa_error_{str(e)[:50]}"}
    
    @staticmethod
    def _calculate_statistical_uhi(lst_image, geometry, scale, max_pixels) -> Dict[str, Any]:
        """Statistical UHI calculation based on temperature distribution."""
        try:
            logger.info(f"📊 Using statistical approach for UHI calculation...")
            
            # Get detailed temperature statistics
            temp_stats = lst_image.reduceRegion(
                reducer=ee.Reducer.percentile([10, 25, 50, 75, 90]).combine(
                    ee.Reducer.mean().combine(ee.Reducer.stdDev(), '', True), '', True
                ),
                geometry=geometry,
                scale=scale,
                maxPixels=max_pixels,
                bestEffort=True
            ).getInfo()
            
            # Extract percentiles
            p10 = temp_stats.get('LST_p10', 0)
            p25 = temp_stats.get('LST_p25', 0)
            p50 = temp_stats.get('LST_p50', 0)  # Median
            p75 = temp_stats.get('LST_p75', 0)
            p90 = temp_stats.get('LST_p90', 0)
            mean_temp = temp_stats.get('LST_mean', 0)
            std_temp = temp_stats.get('LST_stdDev', 0)
            
            # Calculate UHI intensity as the difference between hot spots (P90) and cool areas (P10)
            uhi_intensity = p90 - p10
            
            # Alternative: difference between upper quartile and lower quartile
            alt_uhi = p75 - p25
            
            logger.info(f"📊 Statistical UHI - P90-P10: {uhi_intensity:.2f}°C, P75-P25: {alt_uhi:.2f}°C")
            logger.info(f"📊 Temperature distribution - P10: {p10:.1f}, P25: {p25:.1f}, P50: {p50:.1f}, P75: {p75:.1f}, P90: {p90:.1f}")
            
            return {
                "intensity": uhi_intensity,
                "details": {
                    "method": "statistical_percentiles",
                    "p90_temperature": p90,
                    "p10_temperature": p10,
                    "p75_temperature": p75,
                    "p25_temperature": p25,
                    "median_temperature": p50,
                    "mean_temperature": mean_temp,
                    "std_temperature": std_temp,
                    "alternative_uhi_p75_p25": alt_uhi,
                    "interpretation": "UHI calculated as temperature range (P90-P10) within the area"
                }
            }
            
        except Exception as e:
            logger.warning(f"⚠️ Statistical UHI calculation failed: {e}")
            return {
                "intensity": 0.0,
                "details": {
                    "method": "error_fallback",
                    "error": str(e)
                }
            }
    
    @staticmethod
    def _analyze_tiled_lst(
        lst_collection: ee.ImageCollection,
        geometry_tiles: List[Dict[str, Any]],
        polygon_geometry: Dict[str, Any],
        start_date: str,
        end_date: str,
        include_uhi: bool,
        include_time_series: bool,
        scale: int,
        max_pixels: int,
        exact_computation: bool
    ) -> Dict[str, Any]:
        """Analyze LST for tiled geometry by processing each tile and merging results."""
        try:
            tile_results = []
            total_area_km2 = 0
            
            logger.info(f"Processing {len(geometry_tiles)} tiles...")
            
            for i, tile_geometry in enumerate(geometry_tiles):
                logger.info(f"Processing tile {i+1}/{len(geometry_tiles)}...")
                
                try:
                    # Convert tile to EE geometry
                    ee_tile = ee.Geometry(tile_geometry)
                    
                    # Calculate tile area
                    tile_area_m2 = ee_tile.area(maxError=1000).getInfo()
                    tile_area_km2 = tile_area_m2 / 1_000_000
                    total_area_km2 += tile_area_km2
                    
                    # Get median LST clipped to tile
                    median_lst = lst_collection.select('LST').median().clip(ee_tile)
                    
                    # Compute LST statistics for the tile
                    lst_stats = median_lst.reduceRegion(
                        reducer=ee.Reducer.mean().combine(
                            ee.Reducer.minMax(), '', True
                        ).combine(ee.Reducer.stdDev(), '', True),
                        geometry=ee_tile,
                        scale=scale,
                        maxPixels=max_pixels,
                        bestEffort=not exact_computation
                    ).getInfo()
                    
                    # Format LST stats
                    if lst_stats:
                        formatted_lst_stats = {
                            "LST_mean": lst_stats.get("LST_mean", lst_stats.get("mean", 0)),
                            "LST_min": lst_stats.get("LST_min", lst_stats.get("min", 0)),
                            "LST_max": lst_stats.get("LST_max", lst_stats.get("max", 0)),
                            "LST_stdDev": lst_stats.get("LST_stdDev", lst_stats.get("stdDev", 0))
                        }
                    else:
                        formatted_lst_stats = {
                            "LST_mean": 0.0, "LST_min": 0.0, "LST_max": 0.0, "LST_stdDev": 0.0
                        }
                    
                    # Calculate UHI intensity for tile using improved method
                    uhi_intensity = 0.0
                    uhi_details = {}
                    if include_uhi:
                        uhi_result = LSTService._calculate_uhi_intensity_improved(
                            median_lst, ee_tile, scale, max_pixels
                        )
                        uhi_intensity = uhi_result.get("intensity", 0.0)
                        uhi_details = uhi_result.get("details", {})
                    
                    tile_results.append({
                        "tile_id": i,
                        "area_km2": tile_area_km2,
                        "lst_stats": formatted_lst_stats,
                        "uhi_intensity": uhi_intensity,
                        "uhi_details": uhi_details
                    })
                    
                except Exception as tile_e:
                    logger.error(f"Error processing tile {i+1}: {tile_e}")
                    tile_results.append({
                        "tile_id": i,
                        "area_km2": 0.0,
                        "lst_stats": {"LST_mean": 0.0, "LST_min": 0.0, "LST_max": 0.0, "LST_stdDev": 0.0},
                        "uhi_intensity": 0.0,
                        "uhi_details": {"method": "error", "error": str(tile_e)},
                        "error": str(tile_e)
                    })
            
            # Merge results from all tiles
            merged_stats = LSTService._merge_tile_lst_results(tile_results, total_area_km2)
            
            # Generate visualization tiles for the full polygon
            vis_params = {
                'min': 20,
                'max': 40,
                'palette': LSTService.LST_PALETTE
            }
            ee_polygon_full = ee.Geometry(polygon_geometry)
            median_lst_full = lst_collection.select('LST').median().clip(ee_polygon_full)
            map_id = median_lst_full.getMapId(vis_params)
            # Use proper GEE tile URL format with authentication handled internally
            tile_url = f"https://earthengine.googleapis.com/v1/{map_id['mapid']}/tiles/{{z}}/{{x}}/{{y}}"
            tile_urls = {"urlFormat": tile_url}
            
            # Time series analysis if requested
            time_series_data = {}
            if include_time_series:
                time_series_data = LSTService._compute_lst_time_series(
                    lst_collection, ee_polygon_full, scale, start_date, end_date
                )
            
            # Get image count
            image_count = lst_collection.size().getInfo()
            
            return {
                "success": True,
                "analysis_type": "lst_analysis",
                "geometry_type": "tiled_polygon",
                "tiles_processed": len(tile_results),
                "total_tiles": len(geometry_tiles),
                "roi_area_km2": total_area_km2,
                "urlFormat": tile_urls.get("urlFormat", ""),
                "mapStats": {
                    "lst_statistics": merged_stats,
                    "tiles_processed": len(tile_results),
                    "total_tiles": len(geometry_tiles)
                },
                "datasets_used": ["MODIS/061/MOD11A2"],
                "processing_time_seconds": 0,  # Will be calculated by the calling function
                "class_definitions": {},
                "merged_stats": merged_stats,
                "tile_results": tile_results,
                "tile_urls": tile_urls,
                "time_series": time_series_data,
                "image_count": image_count,
                "legend_config": {
                    "labelNames": ["Cool", "Moderate", "Hot", "Extreme"],
                    "palette": LSTService.LST_PALETTE,
                    "breaks": LSTService.LST_BREAKS,
                    "unit": "°C"
                },
                "visualization": {
                    "tile_url": tile_urls.get("urlFormat", ""),
                    "palette": LSTService.LST_PALETTE,
                    "min": 20,
                    "max": 40,
                    "legend": {
                        "type": "continuous",
                        "title": "Land Surface Temperature (LST)",
                        "description": "Surface temperature in Celsius from MODIS satellite data",
                        "palette": LSTService.LST_PALETTE,
                        "min_value": 20,
                        "max_value": 40,
                        "unit": "°C",
                        "classes": [
                            {"name": "Cool", "range": "(20 to 25)°C", "color": "#2c7bb6", "description": "Cool surface temperatures"},
                            {"name": "Cool-Moderate", "range": "(25 to 30)°C", "color": "#abd9e9", "description": "Cool-moderate surface temperatures"},
                            {"name": "Moderate", "range": "(30 to 35)°C", "color": "#ffffbf", "description": "Moderate surface temperatures"},
                            {"name": "Hot", "range": "(35 to 40)°C", "color": "#fdae61", "description": "Hot surface temperatures"},
                            {"name": "Extreme", "range": "(40+ °C)", "color": "#d7191c", "description": "Extreme surface temperatures"}
                        ]
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"Error in tiled LST analysis: {e}")
            raise
    
    @staticmethod
    def _merge_tile_lst_results(tile_results: List[Dict[str, Any]], total_area_km2: float) -> Dict[str, Any]:
        """Merge LST results from multiple tiles into overall statistics."""
        try:
            # Initialize merged statistics
            merged_lst_stats = {
                "LST_mean": 0.0,
                "LST_min": float('inf'),
                "LST_max": float('-inf'),
                "LST_stdDev": 0.0
            }
            
            # For proper standard deviation calculation
            tile_means = []
            tile_stddevs = []
            tile_areas = []
            uhi_intensities = []
            
            logger.info(f"Merging {len(tile_results)} tile LST results for total area {total_area_km2:.2f} km²")
            
            for i, tile in enumerate(tile_results):
                tile_area = tile.get("area_km2", 0)
                if tile_area <= 0:
                    continue
                    
                weight = tile_area / total_area_km2
                
                # Merge LST statistics
                lst_stats = tile.get("lst_stats", {})
                if "LST_mean" in lst_stats:
                    merged_lst_stats["LST_mean"] += lst_stats["LST_mean"] * weight
                    merged_lst_stats["LST_min"] = min(merged_lst_stats["LST_min"], lst_stats.get("LST_min", 0))
                    merged_lst_stats["LST_max"] = max(merged_lst_stats["LST_max"], lst_stats.get("LST_max", 0))
                    
                    # Collect data for standard deviation calculation
                    tile_means.append(lst_stats["LST_mean"])
                    tile_stddevs.append(lst_stats.get("LST_stdDev", 0))
                    tile_areas.append(tile_area)
                
                # Collect UHI intensities
                uhi_intensities.append(tile.get("uhi_intensity", 0))
            
            # Calculate proper standard deviation
            if len(tile_means) > 1:
                weighted_variance = 0.0
                for i, (mean, stddev, area) in enumerate(zip(tile_means, tile_stddevs, tile_areas)):
                    weight = area / total_area_km2
                    weighted_variance += weight * (stddev ** 2)
                
                between_tile_variance = 0.0
                overall_mean = merged_lst_stats["LST_mean"]
                for i, (mean, area) in enumerate(zip(tile_means, tile_areas)):
                    weight = area / total_area_km2
                    between_tile_variance += weight * ((mean - overall_mean) ** 2)
                
                total_variance = weighted_variance + between_tile_variance
                merged_lst_stats["LST_stdDev"] = (total_variance ** 0.5) if total_variance > 0 else 0.0
            elif len(tile_means) == 1:
                merged_lst_stats["LST_stdDev"] = tile_stddevs[0]
            
            # Calculate average UHI intensity
            avg_uhi_intensity = sum(uhi_intensities) / len(uhi_intensities) if uhi_intensities else 0.0
            
            return {
                "lst_stats": merged_lst_stats,
                "uhi_intensity": avg_uhi_intensity
            }
            
        except Exception as e:
            logger.error(f"Error merging tile LST results: {e}")
            return {
                "lst_stats": {"LST_mean": 0.0, "LST_min": 0.0, "LST_max": 0.0, "LST_stdDev": 0.0},
                "uhi_intensity": 0.0
            }
    
    @staticmethod
    def _compute_lst_time_series(
        lst_collection: ee.ImageCollection,
        geometry: ee.Geometry,
        scale: int,
        start_date: str,
        end_date: str
    ) -> Dict[str, Any]:
        """Compute LST time series data."""
        try:
            # Create monthly composites
            def create_monthly_composite(month):
                start = ee.Date.fromYMD(2023, month, 1)
                end = start.advance(1, 'month')
                
                monthly_collection = lst_collection.filterDate(start, end)
                if monthly_collection.size().getInfo() > 0:
                    return monthly_collection.select('LST').median().clip(geometry)
                return None
            
            time_series_data = []
            for month in range(6, 9):  # June, July, August
                monthly_lst = create_monthly_composite(month)
                if monthly_lst:
                    stats = monthly_lst.reduceRegion(
                        reducer=ee.Reducer.mean(),
                        geometry=geometry,
                        scale=scale,
                        maxPixels=1e6,
                        bestEffort=True
                    ).getInfo()
                    
                    time_series_data.append({
                        "date": f"2023-{month:02d}-01",
                        "mean_lst": stats.get("LST", 0)
                    })
            
            return {
                "method": "monthly_composites",
                "data": time_series_data
            }
            
        except Exception as e:
            logger.warning(f"Time series computation failed: {e}")
            return {"method": "failed", "data": []}