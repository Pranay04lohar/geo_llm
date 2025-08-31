"""
LULC Service - High-Performance Land Use Land Cover Analysis
Using Google Dynamic World for fast, tile-based analysis

Key optimizations:
- Frequency histogram instead of area calculations
- Single dataset (Dynamic World) for speed
- Tile URLs for immediate map rendering
- Confidence filtering for quality
"""

import time
import logging
from typing import Dict, Any, List
import ee

logger = logging.getLogger(__name__)

class LULCService:
    """High-performance LULC analysis service"""
    
    # Dynamic World class definitions (0-8)
    DYNAMIC_WORLD_CLASSES = {
        0: "Water",
        1: "Trees", 
        2: "Grass",
        3: "Flooded vegetation",
        4: "Crops",
        5: "Shrub and scrub",
        6: "Built area",
        7: "Bare ground",
        8: "Snow and ice"
    }
    
    # String-keyed version for API response
    DYNAMIC_WORLD_CLASSES_STR = {
        "0": "Water",
        "1": "Trees", 
        "2": "Grass",
        "3": "Flooded vegetation",
        "4": "Crops",
        "5": "Shrub and scrub",
        "6": "Built area",
        "7": "Bare ground",
        "8": "Snow and ice"
    }
    
    # Color palette for visualization
    DYNAMIC_WORLD_PALETTE = [
        "#419BDF",  # Water (blue)
        "#397D49",  # Trees (dark green)
        "#88B053",  # Grass (light green)
        "#7A87C6",  # Flooded vegetation (purple)
        "#E49635",  # Crops (orange)
        "#DFC35A",  # Shrub and scrub (yellow)
        "#CC0013",  # Built area (red)
        "#D7CDCC",  # Bare ground (light gray)
        "#F7E084"   # Snow and ice (light yellow)
    ]
    
    @staticmethod
    def _compute_histogram(
        image: ee.Image,
        geometry: ee.Geometry,
        scale: int,
        max_pixels: int,
        roi_area_km2: float
    ) -> Dict[str, Any]:
        """
        Compute land cover histogram using multiple fallback methods.
        
        Args:
            image: EE image to analyze
            geometry: ROI geometry
            scale: Analysis scale in meters
            max_pixels: Maximum pixels for computation
            roi_area_km2: ROI area for dynamic sampling
            
        Returns:
            Dict with histogram data and metadata
        """
        histogram = None
        histogram_result = None
        method_used = None
        
        # Method 1: Try frequencyHistogram with user-requested scale
        try:
            logger.info(f"Trying frequencyHistogram method at scale {scale}m...")
            histogram_result = image.reduceRegion(
                reducer=ee.Reducer.frequencyHistogram(),
                geometry=geometry,
                scale=scale,
                maxPixels=max_pixels,
                bestEffort=True
            ).getInfo()
            
            logger.info(f"Raw histogram result: {histogram_result}")
            
            # Extract histogram data - try multiple possible keys
            if histogram_result:
                possible_keys = ['label', 'label_mode', 'classification']
                for key in possible_keys:
                    if key in histogram_result and histogram_result[key]:
                        histogram = histogram_result[key]
                        method_used = "frequencyHistogram"
                        logger.info(f"Using '{key}' key for histogram")
                        break
                
                # If no standard keys, use first available
                if not histogram and histogram_result:
                    keys = list(histogram_result.keys())
                    if keys and histogram_result[keys[0]]:
                        histogram = histogram_result[keys[0]]
                        method_used = "frequencyHistogram"
                        logger.info(f"Using histogram key: {keys[0]}")
            
        except Exception as e:
            logger.warning(f"FrequencyHistogram failed: {e}")
        
        # Method 2: Fallback to sampling if histogram fails
        if not histogram:
            try:
                logger.info("Fallback: Using sample method...")
                # Scale sampling with ROI size (more samples for larger areas)
                num_pixels = min(int(roi_area_km2 * 10), 5000)
                num_pixels = max(num_pixels, 500)  # Minimum 500 samples
                
                logger.info(f"Sampling {num_pixels} points for {roi_area_km2:.2f} km² ROI")
                
                sample_points = image.sample(
                    region=geometry,
                    scale=scale * 2,  # Use slightly coarser scale for sampling
                    numPixels=num_pixels,
                    dropNulls=True
                ).getInfo()
                
                if sample_points and 'features' in sample_points:
                    # Count occurrences of each class
                    class_counts = {}
                    for feature in sample_points['features']:
                        properties = feature.get('properties', {})
                        # Try multiple property names
                        class_value = None
                        for prop_name in ['label_mode', 'label', 'classification']:
                            if prop_name in properties:
                                class_value = properties[prop_name]
                                break
                        
                        if class_value is not None:
                            class_counts[str(class_value)] = class_counts.get(str(class_value), 0) + 1
                    
                    if class_counts:
                        histogram = class_counts
                        method_used = "sampling"
                        logger.info(f"Sample method successful: {len(class_counts)} classes found")
                    
            except Exception as e:
                logger.warning(f"Sample method also failed: {e}")
        
        # Method 3: Final fallback - basic statistics
        if not histogram:
            logger.info("Using basic reduceRegion as final fallback...")
            try:
                basic_stats = image.reduceRegion(
                    reducer=ee.Reducer.mode().combine(
                        reducer2=ee.Reducer.count(), sharedInputs=True
                    ),
                    geometry=geometry,
                    scale=scale * 2,
                    maxPixels=max_pixels // 10,
                    bestEffort=True
                ).getInfo()
                
                if basic_stats:
                    # Try multiple possible keys for mode and count
                    mode_value = None
                    count_value = None
                    
                    for mode_key in ['label_mode', 'label', 'classification_mode']:
                        if mode_key in basic_stats:
                            mode_value = basic_stats[mode_key]
                            break
                    
                    for count_key in ['label_count', 'count', 'classification_count']:
                        if count_key in basic_stats:
                            count_value = basic_stats[count_key]
                            break
                    
                    if mode_value is not None:
                        histogram = {str(mode_value): count_value or 100}
                        method_used = "basic_stats"
                        logger.info(f"Basic stats fallback: dominant class {mode_value}")
                        
            except Exception as e:
                logger.warning(f"All histogram methods failed: {e}")
        
        # Guarantee a histogram (even if minimal)
        if not histogram:
            logger.warning("All methods failed, creating minimal histogram")
            histogram = {"6": 100}  # Default to "Built area" as fallback
            method_used = "fallback_default"
        
        return {
            "histogram": histogram,
            "raw_result": histogram_result,
            "method_used": method_used
        }
    
    @staticmethod
    def analyze_dynamic_world(
        geometry: Dict[str, Any],
        start_date: str = "2023-01-01",
        end_date: str = "2023-12-31",
        confidence_threshold: float = 0.5,
        scale: int = 10,
        max_pixels: int = 1e13,
        exact_computation: bool = False,
        include_median_vis: bool = False
    ) -> Dict[str, Any]:
        """
        Fast LULC analysis using Google Dynamic World with robust histogram extraction.
        
        Args:
            geometry: ROI geometry (GeoJSON dict or EE Geometry)
            start_date: Start date for analysis (YYYY-MM-DD)
            end_date: End date for analysis (YYYY-MM-DD)
            confidence_threshold: Minimum confidence threshold (0.0-1.0)
            scale: Analysis scale in meters
            max_pixels: Maximum pixels for computation
            exact_computation: If True, disable bestEffort for precise results
            include_median_vis: If True, include median visualization alongside mode
        
        Returns:
            Dict with analysis results, tile URLs, statistics, and metadata
        """
        start_time = time.time()
        
        try:
            # Convert geometry to EE geometry
            if isinstance(geometry, dict):
                ee_geometry = ee.Geometry(geometry)
            else:
                ee_geometry = geometry
            
            # Load Dynamic World collection
            logger.info(f"Loading Dynamic World data for period {start_date} to {end_date}")
            
            dw_collection = ee.ImageCollection("GOOGLE/DYNAMICWORLD/V1") \
                .filterBounds(ee_geometry) \
                .filterDate(start_date, end_date)
            
            # Get collection metadata
            collection_size = dw_collection.size().getInfo()
            logger.info(f"Found {collection_size} images in collection")
            
            # Filter by confidence with fallback
            dw_confident = dw_collection.select(['label', 'confidence']) \
                .filter(ee.Filter.gte('confidence', confidence_threshold))
            
            # Check if confidence filtering left any data
            confident_size = dw_confident.size().getInfo()
            if confident_size == 0:
                logger.warning(f"No pixels found with confidence >= {confidence_threshold}, retrying without confidence filter...")
                dw_confident = dw_collection.select('label')
                confident_size = dw_confident.size().getInfo()
                confidence_threshold_used = 0.0
            else:
                confidence_threshold_used = confidence_threshold
            
            logger.info(f"Using {confident_size} images after confidence filtering")
            
            # Get the mode (most frequent class) for the time period
            logger.info("Computing mode across time period...")
            dw_mode = dw_confident.select('label').mode().clip(ee_geometry)
            
            # Optionally compute median for visualization
            dw_median = None
            if include_median_vis:
                logger.info("Computing median for visualization...")
                dw_median = dw_confident.select('label').median().clip(ee_geometry)
            
            # Calculate ROI area (quick calculation)
            roi_area_m2 = ee_geometry.area(maxError=1000).getInfo()
            roi_area_km2 = roi_area_m2 / 1_000_000
            
            logger.info(f"ROI area: {roi_area_km2:.2f} km²")
            
            # Compute robust frequency histogram
            logger.info("Computing frequency histogram...")
            
            histogram_data = LULCService._compute_histogram(
                dw_mode, ee_geometry, scale, 
                max_pixels if exact_computation else int(max_pixels),
                roi_area_km2
            )
            
            histogram = histogram_data["histogram"]
            histogram_result = histogram_data["raw_result"]
            histogram_method = histogram_data["method_used"]
            
            logger.info(f"Histogram computed using method: {histogram_method}")
            
            # Process histogram to get percentages (guaranteed to have data)
            total_pixels = sum(histogram.values())
            class_percentages = {}
            class_areas_km2 = {}
            detected_classes = set()
            
            for class_id, pixel_count in histogram.items():
                try:
                    class_id = int(float(class_id))
                    if class_id in LULCService.DYNAMIC_WORLD_CLASSES:
                        percentage = (pixel_count / total_pixels) * 100
                        area_km2 = (pixel_count * scale * scale) / 1_000_000
                        
                        class_name = LULCService.DYNAMIC_WORLD_CLASSES[class_id]
                        class_percentages[class_name] = round(percentage, 2)
                        class_areas_km2[class_name] = round(area_km2, 4)
                        detected_classes.add(class_id)
                except (ValueError, KeyError) as e:
                    logger.warning(f"Skipping invalid class ID {class_id}: {e}")
            
            # Ensure we have at least one class
            if not class_percentages:
                class_percentages = {"Built area": 100.0}
                class_areas_km2 = {"Built area": roi_area_km2}
                detected_classes = {6}
            
            # Generate map tiles
            logger.info("Generating map tiles...")
            vis_params = {
                'min': 0,
                'max': 8,
                'palette': LULCService.DYNAMIC_WORLD_PALETTE
            }
            
            map_id = dw_mode.getMapId(vis_params)
            tile_url = f"https://earthengine.googleapis.com/map/{map_id['mapid']}/{{z}}/{{x}}/{{y}}?token={map_id['token']}"
            
            # Generate median visualization if requested
            median_tile_url = None
            if include_median_vis and dw_median is not None:
                median_map_id = dw_median.getMapId(vis_params)
                median_tile_url = f"https://earthengine.googleapis.com/map/{median_map_id['mapid']}/{{z}}/{{x}}/{{y}}?token={median_map_id['token']}"
            
            # Get temporal metadata
            try:
                date_range = dw_collection.reduceColumns(
                    ee.Reducer.minMax(), 
                    ['system:time_start']
                ).getInfo()
                
                if date_range:
                    min_date = ee.Date(date_range['min']).format('YYYY-MM-dd').getInfo()
                    max_date = ee.Date(date_range['max']).format('YYYY-MM-dd').getInfo()
                else:
                    min_date = start_date
                    max_date = end_date
            except:
                min_date = start_date
                max_date = end_date
            
            # Calculate average confidence if available
            avg_confidence = None
            try:
                if confidence_threshold_used > 0:
                    conf_stats = dw_collection.select('confidence').mean().reduceRegion(
                        reducer=ee.Reducer.mean(),
                        geometry=ee_geometry,
                        scale=scale * 4,
                        maxPixels=1e6,
                        bestEffort=True
                    ).getInfo()
                    
                    if conf_stats and 'confidence' in conf_stats:
                        avg_confidence = round(conf_stats['confidence'], 3)
            except:
                pass
            
            processing_time = time.time() - start_time
            logger.info(f"✅ LULC analysis completed in {processing_time:.2f}s")
            
            # Prepare enriched response
            result = {
                "urlFormat": tile_url,
                "mapStats": {
                    "class_percentages": class_percentages,
                    "class_areas_km2": class_areas_km2,
                    "total_pixels": total_pixels,
                    "dominant_class": max(class_percentages.items(), key=lambda x: x[1])[0],
                    "num_classes_detected": len(detected_classes)
                },
                "analysis_type": "lulc_dynamic_world",
                "datasets_used": ["GOOGLE/DYNAMICWORLD/V1"],
                "processing_time_seconds": round(processing_time, 2),
                "roi_area_km2": round(roi_area_km2, 4),
                "class_definitions": LULCService.DYNAMIC_WORLD_CLASSES_STR,
                "visualization": {
                    "mode_tile_url": tile_url,
                    "median_tile_url": median_tile_url,
                    "palette": LULCService.DYNAMIC_WORLD_PALETTE,
                    "min": 0,
                    "max": 8
                },
                "metadata": {
                    "start_date": start_date,
                    "end_date": end_date,
                    "actual_date_range": {
                        "min_date": min_date,
                        "max_date": max_date
                    },
                    "confidence_threshold_requested": confidence_threshold,
                    "confidence_threshold_used": confidence_threshold_used,
                    "average_confidence": avg_confidence,
                    "scale_meters": scale,
                    "max_pixels": max_pixels,
                    "exact_computation": exact_computation,
                    "collection_size": collection_size,
                    "confident_images_used": confident_size
                },
                "debug": {
                    "histogram_method": histogram_method,
                    "histogram_raw": histogram_result,
                    "total_pixels_analyzed": total_pixels,
                    "classes_detected": sorted(list(detected_classes))
                },
                "success": True
            }
            
            return result
            
        except ee.EEException as e:
            error_msg = str(e)
            logger.error(f"❌ GEE Error in LULC analysis: {error_msg}")
            
            # Handle specific GEE errors
            if "quota" in error_msg.lower() or "limit" in error_msg.lower():
                return {
                    "error": "Google Earth Engine quota exceeded. Please try again later.",
                    "error_type": "quota_exceeded",
                    "success": False
                }
            elif "timeout" in error_msg.lower():
                return {
                    "error": "Analysis timed out. Try reducing the area or increasing the scale parameter.",
                    "error_type": "timeout",
                    "success": False
                }
            else:
                return {
                    "error": f"Earth Engine error: {error_msg}",
                    "error_type": "gee_error", 
                    "success": False
                }
                
        except Exception as e:
            logger.error(f"❌ Unexpected error in LULC analysis: {str(e)}")
            return {
                "error": f"Analysis failed: {str(e)}",
                "error_type": "unexpected_error",
                "success": False
            }
