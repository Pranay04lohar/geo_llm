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
    def analyze_dynamic_world(
        geometry: Dict[str, Any],
        start_date: str = "2023-01-01",
        end_date: str = "2023-12-31",
        confidence_threshold: float = 0.5,
        scale: int = 10,
        max_pixels: int = 1e13
    ) -> Dict[str, Any]:
        """
        Fast LULC analysis using Google Dynamic World
        
        Returns:
        - Tile URL for immediate map rendering
        - Frequency histogram for class statistics
        - Metadata and processing info
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
            
            # Filter by confidence and get most common class (mode)
            dw_confident = dw_collection.select(['label', 'confidence']) \
                .filter(ee.Filter.gte('confidence', confidence_threshold))
            
            # Get the mode (most frequent class) for the time period
            logger.info("Computing mode across time period...")
            dw_mode = dw_confident.select('label').mode().clip(ee_geometry)
            
            # Calculate ROI area (quick calculation)
            roi_area_m2 = ee_geometry.area(maxError=1000).getInfo()
            roi_area_km2 = roi_area_m2 / 1_000_000
            
            logger.info(f"ROI area: {roi_area_km2:.2f} km²")
            
            # Generate frequency histogram using a different approach
            logger.info("Computing frequency histogram...")
            
            # Try histogram with smaller scale for better coverage
            try:
                histogram_result = dw_mode.reduceRegion(
                    reducer=ee.Reducer.frequencyHistogram(),
                    geometry=ee_geometry,
                    scale=max(scale, 100),  # Use larger scale for faster computation
                    maxPixels=max_pixels,
                    bestEffort=True,
                    tileScale=4  # Add tile scale for large areas
                ).getInfo()
                
                logger.info(f"Raw histogram result: {histogram_result}")
                
                # Extract histogram data - the key might be 'label', 'label_mode', or the first key
                histogram = None
                if histogram_result:
                    if 'label' in histogram_result:
                        histogram = histogram_result['label']
                        logger.info("Using 'label' key for histogram")
                    elif 'label_mode' in histogram_result:
                        histogram = histogram_result['label_mode']
                        logger.info("Using 'label_mode' key for histogram")
                    else:
                        # Use the first available key
                        keys = list(histogram_result.keys())
                        if keys:
                            histogram = histogram_result[keys[0]]
                            logger.info(f"Using histogram key: {keys[0]}")
                
                logger.info(f"Histogram keys available: {list(histogram_result.keys()) if histogram_result else 'None'}")
                logger.info(f"Histogram data: {histogram}")
                
            except Exception as e:
                logger.warning(f"Histogram computation failed: {e}")
                histogram = None
            
            # Process histogram to get percentages
            if histogram:
                total_pixels = sum(histogram.values())
                class_percentages = {}
                class_areas_km2 = {}
                
                for class_id, pixel_count in histogram.items():
                    class_id = int(float(class_id))
                    if class_id in LULCService.DYNAMIC_WORLD_CLASSES:
                        percentage = (pixel_count / total_pixels) * 100
                        area_km2 = (pixel_count * scale * scale) / 1_000_000
                        
                        class_name = LULCService.DYNAMIC_WORLD_CLASSES[class_id]
                        class_percentages[class_name] = round(percentage, 2)
                        class_areas_km2[class_name] = round(area_km2, 4)
            else:
                logger.warning("No histogram data returned")
                class_percentages = {}
                class_areas_km2 = {}
            
            # Generate map tiles
            logger.info("Generating map tiles...")
            vis_params = {
                'min': 0,
                'max': 8,
                'palette': LULCService.DYNAMIC_WORLD_PALETTE
            }
            
            map_id = dw_mode.getMapId(vis_params)
            tile_url = f"https://earthengine.googleapis.com/map/{map_id['mapid']}/{{z}}/{{x}}/{{y}}?token={map_id['token']}"
            
            processing_time = time.time() - start_time
            logger.info(f"✅ LULC analysis completed in {processing_time:.2f}s")
            
            # Prepare response
            result = {
                "urlFormat": tile_url,
                "mapStats": {
                    "class_percentages": class_percentages,
                    "class_areas_km2": class_areas_km2,
                    "total_pixels": total_pixels if histogram else 0,
                    "dominant_class": max(class_percentages.items(), key=lambda x: x[1])[0] if class_percentages else "Unknown"
                },
                "analysis_type": "lulc_dynamic_world",
                "datasets_used": ["GOOGLE/DYNAMICWORLD/V1"],
                "processing_time_seconds": round(processing_time, 2),
                "roi_area_km2": round(roi_area_km2, 4),
                "class_definitions": LULCService.DYNAMIC_WORLD_CLASSES_STR,
                "visualization": {
                    "palette": LULCService.DYNAMIC_WORLD_PALETTE,
                    "min": 0,
                    "max": 8
                },
                "metadata": {
                    "start_date": start_date,
                    "end_date": end_date,
                    "confidence_threshold": confidence_threshold,
                    "scale_meters": scale,
                    "max_pixels": max_pixels,
                    "collection_size": dw_collection.size().getInfo() if dw_collection else 0
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
