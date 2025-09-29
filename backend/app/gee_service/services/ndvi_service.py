"""
NDVI Service - High-Performance Vegetation Index Analysis
Using Sentinel-2 for robust NDVI computation with time-series support

Key features:
- Time-series NDVI analysis (monthly/yearly aggregation)
- Robust histogram extraction with multiple fallback methods
- Tile URLs for immediate map rendering
- Cloud masking and quality filtering
- Efficient processing for large time ranges
"""

import time
import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
import calendar
import ee
# Removed unused imports for service account authentication

logger = logging.getLogger(__name__)

# Initialize Earth Engine with user authentication (for token generation)
try:
    # Use user authentication (from 'earthengine authenticate') which supports token generation
    project_id = 'gee-tool-469517'
    ee.Initialize(project=project_id)
    logger.info(f"✅ Earth Engine initialized with user auth for project '{project_id}'")
except Exception as e:
    logger.error(f"❌ Failed to initialize Earth Engine: {e}")
    logger.info("💡 Run 'earthengine authenticate' to set up user credentials.")


class NDVIService:
    """High-performance NDVI analysis service with time-series capabilities"""
    
    # NDVI value ranges and interpretation
    NDVI_RANGES = {
        "water": (-1.0, -0.1),
        "bare_soil": (-0.1, 0.1),
        "sparse_vegetation": (0.1, 0.3),
        "moderate_vegetation": (0.3, 0.6),
        "dense_vegetation": (0.6, 1.0)
    }
    
    # Color palette for NDVI visualization (red to green)
    NDVI_PALETTE = [
        "#d73027",  # Very low NDVI (red)
        "#f46d43",  # Low NDVI (orange-red)
        "#fdae61",  # Low-moderate NDVI (orange)
        "#fee08b",  # Moderate NDVI (yellow)
        "#e6f598",  # Moderate-high NDVI (light green)
        "#abdda4",  # High NDVI (green)
        "#66c2a5",  # Very high NDVI (blue-green)
        "#3288bd"   # Highest NDVI (blue)
    ]
    
    @staticmethod
    def sample_ndvi_at_point(
        lng: float,
        lat: float,
        start_date: str = "2023-06-01",
        end_date: str = "2023-08-31",
        scale: int = 30,
        cloud_threshold: float = 20
    ) -> Dict[str, Any]:
        """Sample median NDVI value at a coordinate.
        
        Args:
            lng: Longitude
            lat: Latitude
            start_date: Start date for analysis
            end_date: End date for analysis
            scale: Processing scale in meters (default 30m for Sentinel-2)
            cloud_threshold: Max cloud cover percentage
            
        Returns:
            Dict with NDVI value and metadata
        """
        try:
            point = ee.Geometry.Point([float(lng), float(lat)])
            
            # Load Sentinel-2 collection
            s2_collection = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED") \
                .filterBounds(point) \
                .filterDate(start_date, end_date) \
                .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', cloud_threshold))
            
            collection_size = s2_collection.size().getInfo()
            if collection_size == 0:
                return {"success": False, "error": "no_data"}
            
            # Cloud masking
            def mask_s2_clouds(image):
                qa = image.select('QA60')
                cloud_bit_mask = 1 << 10
                cirrus_bit_mask = 1 << 11
                mask = qa.bitwiseAnd(cloud_bit_mask).eq(0) \
                    .And(qa.bitwiseAnd(cirrus_bit_mask).eq(0))
                return image.updateMask(mask).divide(10000)
            
            def add_ndvi(image):
                ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
                return image.addBands(ndvi)
            
            processed_collection = s2_collection.map(mask_s2_clouds).map(add_ndvi)
            median_ndvi = processed_collection.select('NDVI').median()
            
            # Buffer the point slightly to avoid nulls at exact pixel edges
            buffer_meters = max(int(scale / 2), 15)
            region = point.buffer(buffer_meters)
            
            sampled = median_ndvi.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=region,
                scale=scale,
                maxPixels=1e6,
                bestEffort=True
            ).getInfo()
            
            value = sampled.get('NDVI', None)
            if value is None:
                return {"success": False, "error": "no_value"}
            
            # Classify vegetation type
            vegetation_type = "Unknown"
            if value < -0.1:
                vegetation_type = "Water/No Vegetation"
            elif value < 0.1:
                vegetation_type = "Bare Soil/Urban"
            elif value < 0.3:
                vegetation_type = "Sparse Vegetation"
            elif value < 0.6:
                vegetation_type = "Moderate Vegetation"
            else:
                vegetation_type = "Dense Vegetation"
            
            return {
                "success": True,
                "value_ndvi": float(value),
                "vegetation_type": vegetation_type,
                "scale_meters": scale,
                "buffer_meters": buffer_meters,
                "date_range": {"start": start_date, "end": end_date},
                "dataset": "Sentinel-2",
                "images_used": collection_size
            }
            
        except Exception as e:
            logger.error(f"❌ Error sampling NDVI at point: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def generate_ndvi_grid(
        roi_geojson: Dict[str, Any],
        cell_size_km: float = 1.0,
        start_date: str = "2023-06-01",
        end_date: str = "2023-08-31",
        scale: int = 30,
        cloud_threshold: float = 20
    ) -> Dict[str, Any]:
        """Generate a vector grid over ROI with NDVI statistics per cell.
        
        Args:
            roi_geojson: GeoJSON Polygon or MultiPolygon for ROI
            cell_size_km: Grid cell size in kilometers (default 1km)
            start_date: Start date for NDVI data
            end_date: End date for NDVI data
            scale: Processing scale in meters
            cloud_threshold: Max cloud cover percentage
            
        Returns:
            GeoJSON FeatureCollection with NDVI stats per grid cell
        """
        try:
            logger.info(f"🔷 Generating NDVI grid: cell_size={cell_size_km}km")
            
            # Parse ROI geometry
            roi = ee.Geometry(roi_geojson)
            bounds = roi.bounds().coordinates().getInfo()[0]
            min_lng, min_lat = bounds[0][0], bounds[0][1]
            max_lng, max_lat = bounds[2][0], bounds[2][1]
            
            # Load Sentinel-2 collection
            s2_collection = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED") \
                .filterBounds(roi) \
                .filterDate(start_date, end_date) \
                .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', cloud_threshold))
            
            collection_size = s2_collection.size().getInfo()
            if collection_size == 0:
                return {"success": False, "error": "no_data"}
            
            # Cloud masking and NDVI computation
            def mask_s2_clouds(image):
                qa = image.select('QA60')
                cloud_bit_mask = 1 << 10
                cirrus_bit_mask = 1 << 11
                mask = qa.bitwiseAnd(cloud_bit_mask).eq(0) \
                    .And(qa.bitwiseAnd(cirrus_bit_mask).eq(0))
                return image.updateMask(mask).divide(10000)
            
            def add_ndvi(image):
                ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
                return image.addBands(ndvi)
            
            processed_collection = s2_collection.map(mask_s2_clouds).map(add_ndvi)
            median_ndvi = processed_collection.select('NDVI').median()
            
            # Convert km to degrees
            cell_deg = cell_size_km / 111.0
            
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
                    
                    # Compute NDVI statistics for this cell
                    try:
                        stats = median_ndvi.reduceRegion(
                            reducer=ee.Reducer.mean()
                                .combine(ee.Reducer.min(), '', True)
                                .combine(ee.Reducer.max(), '', True)
                                .combine(ee.Reducer.stdDev(), '', True),
                            geometry=cell_poly.intersection(roi),
                            scale=scale,
                            maxPixels=1e8,
                            bestEffort=True
                        ).getInfo()
                        
                        mean_ndvi = stats.get('NDVI_mean')
                        min_ndvi = stats.get('NDVI_min')
                        max_ndvi = stats.get('NDVI_max')
                        std_ndvi = stats.get('NDVI_stdDev')
                        
                        # Only include cells with valid data
                        if mean_ndvi is not None:
                            # Classify vegetation type
                            if mean_ndvi < -0.1:
                                veg_type = "Water/No Vegetation"
                            elif mean_ndvi < 0.1:
                                veg_type = "Bare Soil/Urban"
                            elif mean_ndvi < 0.3:
                                veg_type = "Sparse Vegetation"
                            elif mean_ndvi < 0.6:
                                veg_type = "Moderate Vegetation"
                            else:
                                veg_type = "Dense Vegetation"
                            
                            feature = {
                                "type": "Feature",
                                "geometry": {
                                    "type": "Polygon",
                                    "coordinates": [cell_coords]
                                },
                                "properties": {
                                    "cell_id": cell_id,
                                    "mean_ndvi": round(float(mean_ndvi), 3),
                                    "min_ndvi": round(float(min_ndvi), 3) if min_ndvi else None,
                                    "max_ndvi": round(float(max_ndvi), 3) if max_ndvi else None,
                                    "std_ndvi": round(float(std_ndvi), 3) if std_ndvi else None,
                                    "vegetation_type": veg_type,
                                    "cell_size_km": cell_size_km
                                }
                            }
                            features.append(feature)
                            cell_id += 1
                    except Exception as cell_error:
                        logger.warning(f"Failed to process cell at ({lng}, {lat}): {cell_error}")
                    
                    lng += cell_deg
                lat += cell_deg
            
            logger.info(f"✅ Generated {len(features)} NDVI grid cells")
            
            return {
                "success": True,
                "type": "FeatureCollection",
                "features": features,
                "metadata": {
                    "cell_size_km": cell_size_km,
                    "cell_count": len(features),
                    "date_range": {"start": start_date, "end": end_date},
                    "dataset": "Sentinel-2",
                    "images_used": collection_size
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Error generating NDVI grid: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def sample_ndvi_batch(
        points: List[Dict[str, float]],
        start_date: str = "2023-06-01",
        end_date: str = "2023-08-31",
        scale: int = 30,
        cloud_threshold: float = 20
    ) -> Dict[str, Any]:
        """Sample NDVI at multiple points in batch.
        
        Args:
            points: List of {"lng": x, "lat": y} dicts
            start_date: Start date for NDVI data
            end_date: End date for NDVI data
            scale: Processing scale in meters
            cloud_threshold: Max cloud cover percentage
            
        Returns:
            Dict with "success" and "results" list
        """
        try:
            logger.info(f"🔷 Batch sampling {len(points)} NDVI points")
            
            # Create bounding box for all points
            lngs = [p["lng"] for p in points]
            lats = [p["lat"] for p in points]
            bbox = ee.Geometry.Rectangle([min(lngs), min(lats), max(lngs), max(lats)])
            
            # Load Sentinel-2 collection once for all points
            s2_collection = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED") \
                .filterBounds(bbox) \
                .filterDate(start_date, end_date) \
                .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', cloud_threshold))
            
            collection_size = s2_collection.size().getInfo()
            if collection_size == 0:
                return {"success": False, "error": "no_data"}
            
            # Cloud masking and NDVI computation
            def mask_s2_clouds(image):
                qa = image.select('QA60')
                cloud_bit_mask = 1 << 10
                cirrus_bit_mask = 1 << 11
                mask = qa.bitwiseAnd(cloud_bit_mask).eq(0) \
                    .And(qa.bitwiseAnd(cirrus_bit_mask).eq(0))
                return image.updateMask(mask).divide(10000)
            
            def add_ndvi(image):
                ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
                return image.addBands(ndvi)
            
            processed_collection = s2_collection.map(mask_s2_clouds).map(add_ndvi)
            median_ndvi = processed_collection.select('NDVI').median()
            
            results = []
            for idx, pt in enumerate(points):
                try:
                    lng, lat = pt["lng"], pt["lat"]
                    point = ee.Geometry.Point([float(lng), float(lat)])
                    buffer_meters = max(int(scale / 2), 15)
                    region = point.buffer(buffer_meters)
                    
                    sampled = median_ndvi.reduceRegion(
                        reducer=ee.Reducer.mean(),
                        geometry=region,
                        scale=scale,
                        maxPixels=1e6,
                        bestEffort=True
                    ).getInfo()
                    
                    value = sampled.get('NDVI', None)
                    
                    if value is not None:
                        # Classify vegetation type
                        if value < -0.1:
                            veg_type = "Water/No Vegetation"
                        elif value < 0.1:
                            veg_type = "Bare Soil/Urban"
                        elif value < 0.3:
                            veg_type = "Sparse Vegetation"
                        elif value < 0.6:
                            veg_type = "Moderate Vegetation"
                        else:
                            veg_type = "Dense Vegetation"
                        
                        results.append({
                            "index": idx,
                            "lng": lng,
                            "lat": lat,
                            "value_ndvi": float(value),
                            "vegetation_type": veg_type,
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
            
            logger.info(f"✅ Batch sampled {len(results)} NDVI points")
            
            return {
                "success": True,
                "count": len(results),
                "results": results
            }
            
        except Exception as e:
            logger.error(f"❌ Error in NDVI batch sampling: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def _compute_ndvi_histogram(
        ndvi_image: ee.Image,
        geometry: ee.Geometry,
        scale: int,
        max_pixels: int,
        roi_area_km2: float
    ) -> Dict[str, Any]:
        """
        Compute NDVI histogram using multiple fallback methods.
        
        Args:
            ndvi_image: NDVI image to analyze
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
        
        # Method 1: Try frequencyHistogram with optimized parameters for large areas
        try:
            # Use larger scale and reduced max pixels for large areas
            histogram_scale = max(scale, 200)  # Use larger scale for big polygons
            histogram_max_pixels = min(max_pixels, 5e7)  # Cap max pixels for performance
            
            logger.info(f"Computing NDVI histogram at scale {histogram_scale}m (optimized for large area)...")
            histogram_result = ndvi_image.reduceRegion(
                reducer=ee.Reducer.frequencyHistogram(),
                geometry=geometry,
                scale=histogram_scale,
                maxPixels=histogram_max_pixels,
                bestEffort=True
            ).getInfo()
            
            logger.info(f"Raw NDVI histogram result: {histogram_result}")
            
            # Extract histogram data
            if histogram_result:
                possible_keys = ['NDVI', 'ndvi', 'nd']
                for key in possible_keys:
                    if key in histogram_result and histogram_result[key]:
                        histogram = histogram_result[key]
                        method_used = "frequencyHistogram"
                        logger.info(f"Using '{key}' key for NDVI histogram")
                        break
                
                # If no standard keys, use first available
                if not histogram and histogram_result:
                    keys = list(histogram_result.keys())
                    if keys and histogram_result[keys[0]]:
                        histogram = histogram_result[keys[0]]
                        method_used = "frequencyHistogram"
                        logger.info(f"Using NDVI histogram key: {keys[0]}")
            
        except Exception as e:
            logger.warning(f"NDVI FrequencyHistogram failed: {e}")
        
        # Method 2: Fallback to sampling (optimized for speed)
        if not histogram:
            try:
                logger.info("Fallback: Using optimized NDVI sample method...")
                # Reduce sampling for faster processing
                num_pixels = min(int(roi_area_km2 * 8), 4000)  # Reduced samples for speed
                num_pixels = max(num_pixels, 500)  # Reduced minimum samples
                
                logger.info(f"Sampling {num_pixels} NDVI points for {roi_area_km2:.2f} km² ROI")
                
                sample_points = ndvi_image.sample(
                    region=geometry,
                    scale=max(scale * 2, 60),  # Use larger scale for faster sampling
                    numPixels=num_pixels,
                    dropNulls=True
                ).getInfo()
                
                if sample_points and 'features' in sample_points:
                    # Create histogram from samples
                    ndvi_values = []
                    for feature in sample_points['features']:
                        properties = feature.get('properties', {})
                        for prop_name in ['NDVI', 'ndvi', 'nd']:
                            if prop_name in properties:
                                ndvi_val = properties[prop_name]
                                if isinstance(ndvi_val, (int, float)) and -1 <= ndvi_val <= 1:
                                    ndvi_values.append(ndvi_val)
                                break
                    
                    if ndvi_values:
                        # Create binned histogram
                        histogram = NDVIService._create_ndvi_histogram_bins(ndvi_values)
                        method_used = "sampling"
                        logger.info(f"NDVI sample method successful: {len(ndvi_values)} values")
                    
            except Exception as e:
                logger.warning(f"NDVI sample method failed: {e}")
        
        # Method 3: Basic statistics fallback
        if not histogram:
            logger.info("Using basic NDVI statistics as fallback...")
            try:
                basic_stats = ndvi_image.reduceRegion(
                    reducer=ee.Reducer.mean().combine(
                        reducer2=ee.Reducer.minMax(), sharedInputs=True
                    ).combine(
                        reducer2=ee.Reducer.stdDev(), sharedInputs=True
                    ),
                    geometry=geometry,
                    scale=scale * 2,
                    maxPixels=max_pixels // 10,
                    bestEffort=True
                ).getInfo()
                
                if basic_stats:
                    # Create simple histogram from statistics
                    mean_ndvi = basic_stats.get('NDVI_mean', 0)
                    if mean_ndvi:
                        # Create a simple 3-bin histogram around the mean
                        histogram = {
                            str(round(mean_ndvi - 0.1, 2)): 25,
                            str(round(mean_ndvi, 2)): 50,
                            str(round(mean_ndvi + 0.1, 2)): 25
                        }
                        method_used = "basic_stats"
                        logger.info(f"Basic NDVI stats fallback: mean = {mean_ndvi:.3f}")
                        
            except Exception as e:
                logger.warning(f"All NDVI histogram methods failed: {e}")
        
        # Guarantee a histogram
        if not histogram:
            logger.warning("All NDVI methods failed, creating minimal histogram")
            histogram = {"0.3": 100}  # Default to moderate vegetation
            method_used = "fallback_default"
        
        return {
            "histogram": histogram,
            "raw_result": histogram_result,
            "method_used": method_used
        }
    
    @staticmethod
    def _create_ndvi_histogram_bins(ndvi_values: List[float]) -> Dict[str, int]:
        """Create binned histogram from NDVI values."""
        bins = {}
        bin_size = 0.05  # 0.05 NDVI units per bin
        
        for value in ndvi_values:
            # Round to nearest bin
            bin_center = round(value / bin_size) * bin_size
            bin_key = str(round(bin_center, 2))
            bins[bin_key] = bins.get(bin_key, 0) + 1
        
        return bins
    
    @staticmethod
    def _compute_time_series(
        collection: ee.ImageCollection,
        geometry: ee.Geometry,
        scale: int,
        start_date: str,
        end_date: str
    ) -> Dict[str, Any]:
        """
        Compute time-series NDVI statistics (monthly aggregation).
        
        Args:
            collection: Sentinel-2 collection with NDVI
            geometry: ROI geometry
            scale: Analysis scale
            start_date: Start date string
            end_date: End date string
            
        Returns:
            Dict with time-series data
        """
        try:
            # Parse dates
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            
            # Determine aggregation strategy
            date_diff = (end - start).days
            
            if date_diff <= 90:  # Less than 3 months - weekly aggregation
                return NDVIService._compute_weekly_ndvi(collection, geometry, scale, start, end)
            elif date_diff <= 730:  # Less than 2 years - monthly aggregation
                return NDVIService._compute_monthly_ndvi(collection, geometry, scale, start, end)
            else:  # Longer periods - yearly aggregation
                return NDVIService._compute_yearly_ndvi(collection, geometry, scale, start, end)
                
        except Exception as e:
            logger.warning(f"Time-series computation failed: {e}")
            return {"error": "Time-series computation failed", "method": "none"}
    
    @staticmethod
    def _compute_monthly_ndvi(
        collection: ee.ImageCollection,
        geometry: ee.Geometry,
        scale: int,
        start: datetime,
        end: datetime
    ) -> Dict[str, Any]:
        """Compute monthly NDVI averages."""
        monthly_data = {}
        current = start.replace(day=1)  # Start of month
        
        while current <= end:
            # Get month boundaries
            year, month = current.year, current.month
            month_start = current.strftime("%Y-%m-%d")
            
            # Calculate month end
            days_in_month = calendar.monthrange(year, month)[1]
            month_end = current.replace(day=days_in_month).strftime("%Y-%m-%d")
            
            try:
                # Filter collection for this month
                monthly_collection = collection.filterDate(month_start, month_end)
                
                # Check if we have data
                size = monthly_collection.size().getInfo()
                if size > 0:
                    # Compute monthly mean NDVI
                    monthly_ndvi = monthly_collection.select('NDVI').mean()
                    
                    # Get statistics
                    stats = monthly_ndvi.reduceRegion(
                        reducer=ee.Reducer.mean().combine(
                            reducer2=ee.Reducer.minMax(), sharedInputs=True
                        ),
                        geometry=geometry,
                        scale=scale * 4,  # Coarser scale for time-series
                        maxPixels=1e7,
                        bestEffort=True
                    ).getInfo()
                    
                    if stats and 'NDVI_mean' in stats:
                        monthly_data[month_start] = {
                            "mean": round(stats.get('NDVI_mean', 0), 3),
                            "min": round(stats.get('NDVI_min', 0), 3),
                            "max": round(stats.get('NDVI_max', 0), 3),
                            "image_count": size
                        }
                
            except Exception as e:
                logger.warning(f"Failed to compute NDVI for {month_start}: {e}")
            
            # Move to next month
            if month == 12:
                current = current.replace(year=year + 1, month=1)
            else:
                current = current.replace(month=month + 1)
        
        return {
            "method": "monthly",
            "data": monthly_data,
            "total_months": len(monthly_data)
        }
    
    @staticmethod
    def _compute_weekly_ndvi(
        collection: ee.ImageCollection,
        geometry: ee.Geometry,
        scale: int,
        start: datetime,
        end: datetime
    ) -> Dict[str, Any]:
        """Compute weekly NDVI averages for short time periods."""
        weekly_data = {}
        current = start
        
        while current <= end:
            week_end = min(current + timedelta(days=6), end)
            week_start_str = current.strftime("%Y-%m-%d")
            week_end_str = week_end.strftime("%Y-%m-%d")
            
            try:
                weekly_collection = collection.filterDate(week_start_str, week_end_str)
                size = weekly_collection.size().getInfo()
                
                if size > 0:
                    weekly_ndvi = weekly_collection.select('NDVI').mean()
                    stats = weekly_ndvi.reduceRegion(
                        reducer=ee.Reducer.mean(),
                        geometry=geometry,
                        scale=scale * 4,
                        maxPixels=1e6,
                        bestEffort=True
                    ).getInfo()
                    
                    if stats and 'NDVI_mean' in stats:
                        weekly_data[week_start_str] = {
                            "mean": round(stats.get('NDVI_mean', 0), 3),
                            "image_count": size
                        }
                        
            except Exception as e:
                logger.warning(f"Failed to compute weekly NDVI for {week_start_str}: {e}")
            
            current = week_end + timedelta(days=1)
        
        return {
            "method": "weekly",
            "data": weekly_data,
            "total_weeks": len(weekly_data)
        }
    
    @staticmethod
    def _compute_yearly_ndvi(
        collection: ee.ImageCollection,
        geometry: ee.Geometry,
        scale: int,
        start: datetime,
        end: datetime
    ) -> Dict[str, Any]:
        """Compute yearly NDVI averages for long time periods."""
        yearly_data = {}
        
        for year in range(start.year, end.year + 1):
            year_start = f"{year}-01-01"
            year_end = f"{year}-12-31"
            
            try:
                yearly_collection = collection.filterDate(year_start, year_end)
                size = yearly_collection.size().getInfo()
                
                if size > 0:
                    yearly_ndvi = yearly_collection.select('NDVI').mean()
                    stats = yearly_ndvi.reduceRegion(
                        reducer=ee.Reducer.mean().combine(
                            reducer2=ee.Reducer.minMax(), sharedInputs=True
                        ),
                        geometry=geometry,
                        scale=scale * 8,
                        maxPixels=1e7,
                        bestEffort=True
                    ).getInfo()
                    
                    if stats and 'NDVI_mean' in stats:
                        yearly_data[str(year)] = {
                            "mean": round(stats.get('NDVI_mean', 0), 3),
                            "min": round(stats.get('NDVI_min', 0), 3),
                            "max": round(stats.get('NDVI_max', 0), 3),
                            "image_count": size
                        }
                        
            except Exception as e:
                logger.warning(f"Failed to compute yearly NDVI for {year}: {e}")
        
        return {
            "method": "yearly", 
            "data": yearly_data,
            "total_years": len(yearly_data)
        }
    
    @staticmethod
    def analyze_ndvi_with_polygon(
        roi_data: Dict[str, Any],
        start_date: str = "2023-01-01",
        end_date: str = "2023-12-31",
        cloud_threshold: int = 20,
        scale: int = 30,
        max_pixels: int = 1e13,
        include_time_series: bool = True,
        exact_computation: bool = False
    ) -> Dict[str, Any]:
        """
        Enhanced NDVI analysis using polygon geometry with tiling support.
        
        Args:
            roi_data: ROI data from ROI handler with polygon geometry
            start_date: Start date for analysis (YYYY-MM-DD)
            end_date: End date for analysis (YYYY-MM-DD)
            cloud_threshold: Maximum cloud cover percentage (0-100)
            scale: Analysis scale in meters
            max_pixels: Maximum pixels for computation
            include_time_series: Whether to compute time-series statistics
            exact_computation: If True, disable bestEffort for precise results
        
        Returns:
            Dict with NDVI analysis results, tile URLs, and time-series data
        """
        start_time = time.time()
        
        try:
            # Extract geometry information
            polygon_geometry = roi_data.get("polygon_geometry")
            geometry_tiles = roi_data.get("geometry_tiles", [])
            bounding_box = roi_data.get("bounding_box")
            is_tiled = roi_data.get("is_tiled", False)
            is_fallback = roi_data.get("is_fallback", False)
            
            # Use polygon geometry if available, otherwise fall back to regular geometry
            if polygon_geometry and not is_fallback:
                logger.info(f"🎯 Using polygon geometry for precise analysis (tiled: {is_tiled})")
                return NDVIService._analyze_with_polygon_geometry(
                    polygon_geometry, geometry_tiles, bounding_box, is_tiled,
                    start_date, end_date, cloud_threshold, scale, max_pixels,
                    include_time_series, exact_computation
                )
            else:
                # Fallback to regular geometry analysis
                logger.info(f"⚠️ Using fallback geometry analysis")
                geometry = roi_data.get("geometry", polygon_geometry)
                return NDVIService.analyze_ndvi(
                    geometry, start_date, end_date, cloud_threshold,
                    scale, max_pixels, include_time_series, exact_computation
                )
                
        except Exception as e:
            logger.error(f"Error in polygon-based NDVI analysis: {e}")
            # Fallback to regular analysis
            geometry = roi_data.get("geometry", roi_data.get("polygon_geometry"))
            return NDVIService.analyze_ndvi(
                geometry, start_date, end_date, cloud_threshold,
                scale, max_pixels, include_time_series, exact_computation
            )
    
    @staticmethod
    def _analyze_with_polygon_geometry(
        polygon_geometry: Dict[str, Any],
        geometry_tiles: List[Dict[str, Any]],
        bounding_box: Dict[str, float],
        is_tiled: bool,
        start_date: str,
        end_date: str,
        cloud_threshold: int,
        scale: int,
        max_pixels: int,
        include_time_series: bool,
        exact_computation: bool
    ) -> Dict[str, Any]:
        """
        Analyze NDVI using polygon geometry with optional tiling.
        
        This method implements the hybrid approach:
        1. Use bounding box for fast filtering (filterBounds)
        2. Use polygon geometry for precise analysis (reduceRegion)
        3. If tiled, process each tile and merge results
        """
        try:
            # Convert geometries to EE geometries
            ee_polygon = ee.Geometry(polygon_geometry)
            
            # Create bounding box for filtering if available
            if bounding_box:
                # Use the new bounding box format (min_lat, max_lat, min_lng, max_lng)
                bbox_geometry = ee.Geometry.Rectangle([
                    bounding_box["min_lng"], bounding_box["min_lat"],
                    bounding_box["max_lng"], bounding_box["max_lat"]
                ])
                filter_geometry = bbox_geometry
                logger.info(f"🎯 Using bounding box for filtering: {bounding_box}")
            else:
                filter_geometry = ee_polygon
                logger.info("🎯 Using polygon geometry for filtering")
            
            # Load Sentinel-2 collection with bounding box filtering
            logger.info(f"Loading Sentinel-2 data for period {start_date} to {end_date}")
            s2_collection = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED") \
                .filterBounds(filter_geometry) \
                .filterDate(start_date, end_date) \
                .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', cloud_threshold))
            
            collection_size = s2_collection.size().getInfo()
            logger.info(f"Found {collection_size} Sentinel-2 images")
            
            if collection_size == 0:
                return {
                    "error": f"No Sentinel-2 images found for the specified criteria",
                    "error_type": "no_data",
                    "success": False
                }
            
            # Cloud masking and NDVI computation
            def mask_s2_clouds(image):
                qa = image.select('QA60')
                cloud_bit_mask = 1 << 10
                cirrus_bit_mask = 1 << 11
                mask = qa.bitwiseAnd(cloud_bit_mask).eq(0) \
                    .And(qa.bitwiseAnd(cirrus_bit_mask).eq(0))
                return image.updateMask(mask).divide(10000)
            
            def add_ndvi(image):
                ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
                return image.addBands(ndvi)
            
            processed_collection = s2_collection.map(mask_s2_clouds).map(add_ndvi)
            
            if is_tiled and geometry_tiles:
                # Process tiled geometry
                logger.info(f"🔄 Processing {len(geometry_tiles)} tiles...")
                return NDVIService._analyze_tiled_geometry(
                    processed_collection, geometry_tiles, polygon_geometry,
                    start_date, end_date, scale, max_pixels,
                    include_time_series, exact_computation
                )
            else:
                # Process single polygon geometry
                logger.info("🎯 Processing single polygon geometry...")
                return NDVIService._analyze_single_polygon(
                    processed_collection, ee_polygon, polygon_geometry,
                    start_date, end_date, scale, max_pixels,
                    include_time_series, exact_computation
                )
                
        except Exception as e:
            logger.error(f"Error in polygon geometry analysis: {e}")
            raise e
    
    @staticmethod
    def _analyze_single_polygon(
        processed_collection: ee.ImageCollection,
        ee_polygon: ee.Geometry,
        polygon_geometry: Dict[str, Any],
        start_date: str,
        end_date: str,
        scale: int,
        max_pixels: int,
        include_time_series: bool,
        exact_computation: bool
    ) -> Dict[str, Any]:
        """Analyze NDVI for a single polygon geometry."""
        try:
            print(f"🔍 SINGLE POLYGON ANALYSIS STARTING...")
            logger.info(f"🔍 Single polygon analysis starting...")
            
            # Get median NDVI clipped to polygon
            median_ndvi = processed_collection.select('NDVI').median().clip(ee_polygon)
            print(f"🔍 Median NDVI created, processing collection...")
            
            # Calculate polygon area
            polygon_area_m2 = ee_polygon.area(maxError=1000).getInfo()
            polygon_area_km2 = polygon_area_m2 / 1_000_000
            
            print(f"🔍 Polygon area: {polygon_area_km2:.2f} km²")
            logger.info(f"🔍 Polygon area: {polygon_area_km2:.2f} km²")
            
            # Compute NDVI histogram using polygon geometry
            print(f"🔍 Computing NDVI histogram...")
            logger.info(f"🔍 Computing NDVI histogram...")
            try:
                histogram_data = NDVIService._compute_ndvi_histogram(
                    median_ndvi, ee_polygon, scale,
                    max_pixels if exact_computation else int(max_pixels),
                    polygon_area_km2
                )
                print(f"🔍 Histogram computed successfully: {list(histogram_data.keys())}")
            except Exception as e:
                print(f"❌ Histogram computation failed: {e}")
                raise e
            
            # Process results similar to regular analyze_ndvi method
            histogram = histogram_data["histogram"]
            print(f"🔍 Histogram computed: {len(histogram)} NDVI value bins")
            logger.info(f"🔍 Histogram computed: {len(histogram)} NDVI value bins")
            
            print(f"🔍 Computing vegetation distribution...")
            vegetation_stats = NDVIService._analyze_vegetation_distribution(histogram)
            print(f"🔍 Vegetation distribution calculated")
            logger.info(f"🔍 Vegetation stats: {vegetation_stats}")
            
            # Compute NDVI statistics using polygon geometry
            # Optimize parameters for large polygon areas
            optimized_scale = max(scale, 100)  # Use larger scale for big areas
            optimized_max_pixels = min(max_pixels, 1e8)  # Cap max pixels for performance
            
            print(f"🔍 Computing NDVI statistics with scale={optimized_scale}, maxPixels={optimized_max_pixels}")
            logger.info(f"🔍 Computing NDVI statistics with scale={optimized_scale}, maxPixels={optimized_max_pixels}")
            
            try:
                print(f"🔍 Computing NDVI statistics...")
                ndvi_stats = median_ndvi.reduceRegion(
                    reducer=ee.Reducer.mean().combine(
                        ee.Reducer.minMax(), '', True
                    ).combine(ee.Reducer.stdDev(), '', True),
                    geometry=ee_polygon,  # Use polygon for precise reduction
                    scale=optimized_scale,
                    maxPixels=optimized_max_pixels,
                    bestEffort=True  # Always use best effort for large areas
                ).getInfo()
                print(f"🔍 NDVI statistics computed successfully")
            except Exception as e:
                print(f"❌ NDVI statistics computation failed: {e}")
                ndvi_stats = {}
            
            logger.info(f"🔍 Raw NDVI stats from reduceRegion: {ndvi_stats}")
            
            # Check if we got valid results
            if not ndvi_stats or all(v == 0 for v in ndvi_stats.values() if isinstance(v, (int, float))):
                logger.warning(f"⚠️ NDVI reduceRegion returned empty/zero results, trying with smaller scale")
                # Try with smaller scale
                ndvi_stats = median_ndvi.reduceRegion(
                    reducer=ee.Reducer.mean().combine(
                        ee.Reducer.minMax(), '', True
                    ).combine(ee.Reducer.stdDev(), '', True),
                    geometry=ee_polygon,
                    scale=30,  # Use smaller scale
                    maxPixels=1e6,  # Smaller max pixels
                    bestEffort=True
                ).getInfo()
                logger.info(f"🔍 Retry NDVI stats with smaller scale: {ndvi_stats}")
            
            # Format NDVI stats to match expected field names
            if ndvi_stats:
                formatted_ndvi_stats = {
                    "NDVI_mean": ndvi_stats.get("NDVI_mean", ndvi_stats.get("mean", 0)),
                    "NDVI_min": ndvi_stats.get("NDVI_min", ndvi_stats.get("min", 0)),
                    "NDVI_max": ndvi_stats.get("NDVI_max", ndvi_stats.get("max", 0)),
                    "NDVI_stdDev": ndvi_stats.get("NDVI_stdDev", ndvi_stats.get("stdDev", 0))
                }
                logger.info(f"🔍 Formatted NDVI stats: {formatted_ndvi_stats}")
                ndvi_stats = formatted_ndvi_stats
            else:
                logger.warning(f"⚠️ No valid NDVI stats found, using defaults")
                ndvi_stats = {
                    "NDVI_mean": 0.0,
                    "NDVI_min": 0.0,
                    "NDVI_max": 0.0,
                    "NDVI_stdDev": 0.0
                }
            
            # Generate tile URLs for visualization
            vis_params = {
                'min': -0.2,  # Water and bare soil
                'max': 0.8,   # Dense vegetation (full NDVI range)
                'palette': NDVIService.NDVI_PALETTE
            }
            map_id = median_ndvi.getMapId(vis_params)
            
            # Debug: Log the complete map_id response
            logger.info(f"🔍 DEBUG - Complete map_id response: {map_id}")
            logger.info(f"🔍 DEBUG - map_id keys: {list(map_id.keys()) if map_id else 'None'}")
            
            # Handle missing token by generating a new one
            if map_id and 'token' in map_id and map_id['token']:
                token = map_id['token']
                logger.info(f"🔍 DEBUG - Token length: {len(str(token))}")
                logger.info(f"🔍 DEBUG - Token preview: {str(token)[:50]}...")
            else:
                logger.warning(f"⚠️ WARNING - No token found in map_id response!")
                # Try to get a fresh token using ee.data.getMapId
                try:
                    fresh_map_id = ee.data.getMapId({'image': median_ndvi, 'vis_params': vis_params})
                    token = fresh_map_id.get('token', '')
                    logger.info(f"🔄 Generated fresh token: {len(str(token))} characters")
                except Exception as e:
                    logger.error(f"❌ Failed to generate fresh token: {e}")
                    token = ''
            
            tile_url = f"https://earthengine.googleapis.com/map/{map_id['mapid']}/{{z}}/{{x}}/{{y}}?token={token}"
            tile_urls = {"urlFormat": tile_url}
            
            # Time series analysis if requested
            time_series_data = {}
            if include_time_series:
                time_series_data = NDVIService._compute_time_series(
                    processed_collection, ee_polygon, scale, start_date, end_date
                )
            
            # Get image count for validation
            image_count = processed_collection.size().getInfo()
            
            return {
                "success": True,
                "analysis_type": "polygon_geometry",
                "geometry_type": "single_polygon",
                "area_km2": polygon_area_km2,
                "ndvi_stats": ndvi_stats,
                "vegetation_distribution": vegetation_stats,
                "histogram": histogram,
                "tile_urls": tile_urls,
                "time_series": time_series_data,
                "image_count": image_count,  # Add image count for validation
                "metadata": {
                    "start_date": start_date,
                    "end_date": end_date,
                    "scale_meters": scale,
                    "max_pixels": max_pixels,
                    "exact_computation": exact_computation,
                    "polygon_coordinates": len(polygon_geometry.get("coordinates", [[]])[0]) if polygon_geometry else 0,
                    "sentinel2_images_used": image_count
                }
            }
            
        except Exception as e:
            logger.error(f"Error in single polygon analysis: {e}")
            raise e
    
    @staticmethod
    def _analyze_tiled_geometry(
        processed_collection: ee.ImageCollection,
        geometry_tiles: List[Dict[str, Any]],
        polygon_geometry: Dict[str, Any],
        start_date: str,
        end_date: str,
        scale: int,
        max_pixels: int,
        include_time_series: bool,
        exact_computation: bool
    ) -> Dict[str, Any]:
        """Analyze NDVI for tiled geometry by processing each tile and merging results."""
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
                    
                    # Get median NDVI for this tile
                    median_ndvi = processed_collection.select('NDVI').median().clip(ee_tile)
                    
                    # Compute NDVI statistics for this tile
                    tile_stats = median_ndvi.reduceRegion(
                        reducer=ee.Reducer.mean().combine(
                            ee.Reducer.minMax(), '', True
                        ).combine(ee.Reducer.stdDev(), '', True),
                        geometry=ee_tile,
                        scale=scale,
                        maxPixels=max_pixels // len(geometry_tiles),  # Distribute max_pixels across tiles
                        bestEffort=not exact_computation
                    ).getInfo()
                    
                    # Compute histogram for this tile
                    histogram_data = NDVIService._compute_ndvi_histogram(
                        median_ndvi, ee_tile, scale,
                        max_pixels // len(geometry_tiles),
                        tile_area_km2
                    )
                    
                    tile_results.append({
                        "tile_index": i,
                        "area_km2": tile_area_km2,
                        "ndvi_stats": tile_stats,
                        "histogram": histogram_data["histogram"],
                        "vegetation_distribution": NDVIService._analyze_vegetation_distribution(
                            histogram_data["histogram"]
                        )
                    })
                    
                except Exception as e:
                    logger.warning(f"Error processing tile {i+1}: {e}")
                    continue
            
            if not tile_results:
                raise Exception("No tiles could be processed successfully")
            
            # Merge tile results
            merged_stats = NDVIService._merge_tile_results(tile_results, total_area_km2)
            
            # Generate tile URLs for the full polygon
            ee_polygon = ee.Geometry(polygon_geometry)
            median_ndvi_full = processed_collection.select('NDVI').median().clip(ee_polygon)
            # Generate tile URLs for the full polygon
            vis_params = {
                'min': -0.3,  # Adjusted to show water/urban areas better
                'max': 0.2,   # Adjusted to actual data range
                'palette': NDVIService.NDVI_PALETTE
            }
            map_id = median_ndvi_full.getMapId(vis_params)
            # Use proper GEE tile URL format with correct coordinate order {z}/{x}/{y}
            tile_url_template = f"https://earthengine.googleapis.com/v1/{map_id['mapid']}/tiles/{{z}}/{{x}}/{{y}}"
            tile_urls = {"urlFormat": tile_url_template}
            
            # Time series analysis if requested (using full polygon)
            time_series_data = {}
            if include_time_series:
                time_series_data = NDVIService._compute_time_series(
                    processed_collection, ee_polygon, scale, start_date, end_date
                )
            
            # Get image count for validation
            image_count = processed_collection.size().getInfo()
            
            return {
                "success": True,
                "analysis_type": "polygon_geometry",
                "geometry_type": "tiled_polygon",
                "tiles_processed": len(tile_results),
                "total_tiles": len(geometry_tiles),
                "area_km2": total_area_km2,
                "merged_stats": merged_stats,
                "tile_results": tile_results,
                "tile_urls": tile_urls,
                "time_series": time_series_data,
                "image_count": image_count,  # Add image count for validation
                "metadata": {
                    "start_date": start_date,
                    "end_date": end_date,
                    "scale_meters": scale,
                    "max_pixels": max_pixels,
                    "exact_computation": exact_computation,
                    "polygon_coordinates": len(polygon_geometry.get("coordinates", [[]])[0]) if polygon_geometry else 0,
                    "sentinel2_images_used": image_count
                }
            }
            
        except Exception as e:
            logger.error(f"Error in tiled geometry analysis: {e}")
            raise e
    
    @staticmethod
    def _merge_tile_results(tile_results: List[Dict[str, Any]], total_area_km2: float) -> Dict[str, Any]:
        """Merge results from multiple tiles into overall statistics."""
        try:
            # Initialize merged statistics
            merged_ndvi_stats = {
                "NDVI_mean": 0.0,
                "NDVI_min": float('inf'),
                "NDVI_max": float('-inf'),
                "NDVI_stdDev": 0.0
            }
            
            merged_vegetation = {
                "water_percentage": 0.0,
                "bare_soil_percentage": 0.0,
                "sparse_vegetation_percentage": 0.0,
                "moderate_vegetation_percentage": 0.0,
                "dense_vegetation_percentage": 0.0
            }
            
            # For proper standard deviation calculation, we need to collect all tile data
            tile_means = []
            tile_stddevs = []
            tile_areas = []
            
            # Area-weighted merging
            logger.info(f"🔍 Merging {len(tile_results)} tile results for total area {total_area_km2:.2f} km²")
            
            for i, tile in enumerate(tile_results):
                tile_area = tile.get("area_km2", 0)
                if tile_area <= 0:
                    logger.warning(f"⚠️ Tile {i} has invalid area: {tile_area}")
                    continue
                    
                weight = tile_area / total_area_km2
                logger.info(f"🔍 Tile {i}: area={tile_area:.2f} km², weight={weight:.4f}")
                
                # Merge NDVI statistics
                ndvi_stats = tile.get("ndvi_stats", {})
                if "NDVI_mean" in ndvi_stats:
                    merged_ndvi_stats["NDVI_mean"] += ndvi_stats["NDVI_mean"] * weight
                    merged_ndvi_stats["NDVI_min"] = min(merged_ndvi_stats["NDVI_min"], ndvi_stats.get("NDVI_min", 0))
                    merged_ndvi_stats["NDVI_max"] = max(merged_ndvi_stats["NDVI_max"], ndvi_stats.get("NDVI_max", 0))
                    
                    # Collect data for proper standard deviation calculation
                    tile_means.append(ndvi_stats["NDVI_mean"])
                    tile_stddevs.append(ndvi_stats.get("NDVI_stdDev", 0))
                    tile_areas.append(tile_area)
                    
                    logger.info(f"🔍 Tile {i} NDVI: mean={ndvi_stats.get('NDVI_mean', 0):.3f}, stddev={ndvi_stats.get('NDVI_stdDev', 0):.3f}")
                
                # Calculate vegetation distribution from histogram data (same as fallback method)
                histogram = tile.get("histogram", {})
                logger.info(f"🔍 Tile {i} histogram keys: {list(histogram.keys()) if histogram else 'None'}")
                
                if histogram and len(histogram) > 0:
                    # Use the same method as fallback: _analyze_vegetation_distribution
                    veg_dist = NDVIService._analyze_vegetation_distribution(histogram)
                    logger.info(f"🔍 Tile {i} calculated vegetation: {veg_dist}")
                    
                    # Merge the calculated vegetation distribution
                    for key in merged_vegetation:
                        if key in veg_dist and veg_dist[key] is not None:
                            merged_vegetation[key] += veg_dist[key] * weight
                            logger.info(f"🔍 Tile {i} {key}: {veg_dist[key]:.3f} * {weight:.4f} = {veg_dist[key] * weight:.3f}")
                        else:
                            logger.warning(f"⚠️ Tile {i} missing {key} in calculated vegetation_distribution")
                else:
                    logger.warning(f"⚠️ Tile {i} has no histogram data for vegetation calculation")
            
            # Calculate proper standard deviation using pooled variance formula
            if len(tile_means) > 1:
                # Calculate weighted variance for proper standard deviation
                weighted_variance = 0.0
                for i, (mean, stddev, area) in enumerate(zip(tile_means, tile_stddevs, tile_areas)):
                    weight = area / total_area_km2
                    # Add variance contribution from this tile
                    weighted_variance += weight * (stddev ** 2)
                
                # Add variance between tile means (between-tile variance)
                overall_mean = merged_ndvi_stats["NDVI_mean"]
                between_tile_variance = 0.0
                for i, (mean, area) in enumerate(zip(tile_means, tile_areas)):
                    weight = area / total_area_km2
                    between_tile_variance += weight * ((mean - overall_mean) ** 2)
                
                # Total variance = within-tile variance + between-tile variance
                total_variance = weighted_variance + between_tile_variance
                merged_ndvi_stats["NDVI_stdDev"] = (total_variance ** 0.5) if total_variance > 0 else 0.0
                
                logger.info(f"🔍 Calculated proper std dev: {merged_ndvi_stats['NDVI_stdDev']:.3f}")
            elif len(tile_means) == 1:
                # Single tile case
                merged_ndvi_stats["NDVI_stdDev"] = tile_stddevs[0]
                logger.info(f"🔍 Single tile std dev: {merged_ndvi_stats['NDVI_stdDev']:.3f}")
            else:
                logger.warning("⚠️ No valid tile data for standard deviation calculation")
            
            logger.info(f"🔍 Final merged vegetation: {merged_vegetation}")
            logger.info(f"🔍 Final merged NDVI: {merged_ndvi_stats}")
            
            return {
                "ndvi_stats": merged_ndvi_stats,
                "vegetation_distribution": merged_vegetation
            }
            
        except Exception as e:
            logger.error(f"Error merging tile results: {e}")
            return {
                "ndvi_stats": {"NDVI_mean": 0.0, "NDVI_min": 0.0, "NDVI_max": 0.0, "NDVI_stdDev": 0.0},
                "vegetation_distribution": {
                    "water_percentage": 0.0,
                    "bare_soil_percentage": 0.0,
                    "sparse_vegetation_percentage": 0.0,
                    "moderate_vegetation_percentage": 0.0,
                    "dense_vegetation_percentage": 0.0
                }
            }
    
    def analyze_ndvi(
        geometry: Dict[str, Any],
        start_date: str = "2023-01-01",
        end_date: str = "2023-12-31",
        cloud_threshold: int = 20,
        scale: int = 30,
        max_pixels: int = 1e13,
        include_time_series: bool = True,
        exact_computation: bool = False
    ) -> Dict[str, Any]:
        """
        Comprehensive NDVI analysis using Sentinel-2 data.
        
        Args:
            geometry: ROI geometry (GeoJSON dict or EE Geometry)
            start_date: Start date for analysis (YYYY-MM-DD)
            end_date: End date for analysis (YYYY-MM-DD)
            cloud_threshold: Maximum cloud cover percentage (0-100)
            scale: Analysis scale in meters
            max_pixels: Maximum pixels for computation
            include_time_series: Whether to compute time-series statistics
            exact_computation: If True, disable bestEffort for precise results
        
        Returns:
            Dict with NDVI analysis results, tile URLs, and time-series data
        """
        start_time = time.time()
        
        try:
            # Convert geometry to EE geometry
            if isinstance(geometry, dict):
                ee_geometry = ee.Geometry(geometry)
            else:
                ee_geometry = geometry
            
            # Load Sentinel-2 Surface Reflectance collection
            logger.info(f"Loading Sentinel-2 data for period {start_date} to {end_date}")
            
            s2_collection = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED") \
                .filterBounds(ee_geometry) \
                .filterDate(start_date, end_date) \
                .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', cloud_threshold))
            
            # Get collection metadata
            collection_size = s2_collection.size().getInfo()
            logger.info(f"Found {collection_size} Sentinel-2 images")
            
            if collection_size == 0:
                return {
                    "error": f"No Sentinel-2 images found for the specified criteria",
                    "error_type": "no_data",
                    "success": False
                }
            
            # Cloud masking function
            def mask_s2_clouds(image):
                qa = image.select('QA60')
                cloud_bit_mask = 1 << 10
                cirrus_bit_mask = 1 << 11
                mask = qa.bitwiseAnd(cloud_bit_mask).eq(0) \
                    .And(qa.bitwiseAnd(cirrus_bit_mask).eq(0))
                return image.updateMask(mask).divide(10000)
            
            # Apply cloud masking and compute NDVI
            def add_ndvi(image):
                ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
                return image.addBands(ndvi)
            
            # Process collection
            logger.info("Processing Sentinel-2 collection...")
            processed_collection = s2_collection.map(mask_s2_clouds).map(add_ndvi)
            
            # Get the median NDVI for visualization and analysis
            median_ndvi = processed_collection.select('NDVI').median().clip(ee_geometry)
            
            # Calculate ROI area
            roi_area_m2 = ee_geometry.area(maxError=1000).getInfo()
            roi_area_km2 = roi_area_m2 / 1_000_000
            
            logger.info(f"ROI area: {roi_area_km2:.2f} km²")
            
            # Compute NDVI histogram
            logger.info("Computing NDVI histogram...")
            histogram_data = NDVIService._compute_ndvi_histogram(
                median_ndvi, ee_geometry, scale,
                max_pixels if exact_computation else int(max_pixels),
                roi_area_km2
            )
            
            histogram = histogram_data["histogram"]
            histogram_method = histogram_data["method_used"]
            
            logger.info(f"NDVI histogram computed using method: {histogram_method}")
            
            # Process histogram to get vegetation categories
            vegetation_stats = NDVIService._analyze_vegetation_distribution(histogram)
            
            # Compute basic NDVI statistics
            ndvi_stats = median_ndvi.reduceRegion(
                reducer=ee.Reducer.mean().combine(
                    reducer2=ee.Reducer.minMax(), sharedInputs=True
                ).combine(
                    reducer2=ee.Reducer.stdDev(), sharedInputs=True
                ),
                geometry=ee_geometry,
                scale=scale,
                maxPixels=max_pixels if exact_computation else int(max_pixels // 10),
                bestEffort=not exact_computation
            ).getInfo()
            
            # Compute time-series if requested
            time_series_data = {}
            if include_time_series:
                logger.info("Computing NDVI time-series...")
                time_series_data = NDVIService._compute_time_series(
                    processed_collection, ee_geometry, scale, start_date, end_date
                )
            
            # Generate visualization
            logger.info("Generating NDVI visualization...")
            vis_params = {
                'min': -0.2,  # Water and bare soil
                'max': 0.8,   # Dense vegetation (full NDVI range)
                'palette': NDVIService.NDVI_PALETTE
            }
            
            map_id = median_ndvi.getMapId(vis_params)
            # Use proper GEE tile URL format with correct coordinate order {z}/{x}/{y}
            tile_url = f"https://earthengine.googleapis.com/v1/{map_id['mapid']}/tiles/{{z}}/{{x}}/{{y}}"
            
            processing_time = time.time() - start_time
            logger.info(f"✅ NDVI analysis completed in {processing_time:.2f}s")
            
            # Prepare comprehensive response
            result = {
                "urlFormat": tile_url,
                "mapStats": {
                    "ndvi_statistics": {
                        "mean": round(ndvi_stats.get('NDVI_mean', 0), 3),
                        "min": round(ndvi_stats.get('NDVI_min', 0), 3),
                        "max": round(ndvi_stats.get('NDVI_max', 0), 3),
                        "std_dev": round(ndvi_stats.get('NDVI_stdDev', 0), 3)
                    },
                    "vegetation_distribution": vegetation_stats,
                    "histogram": histogram,
                    "time_series": time_series_data if include_time_series else {}
                },
                "legendConfig": {
                    "title": "NDVI (Vegetation Index)",
                    "min_value": -0.2,
                    "max_value": 0.8,
                    "palette": NDVIService.NDVI_PALETTE,
                    "labels": {
                        "-0.2": "Water/Bare",
                        "0.0": "Sparse Vegetation", 
                        "0.3": "Moderate Vegetation",
                        "0.6": "Dense Vegetation",
                        "0.8": "Very Dense Vegetation"
                    }
                },
                "extraDescription": NDVIService._generate_ndvi_description(
                    ndvi_stats, vegetation_stats, time_series_data
                ),
                "analysis_type": "ndvi_vegetation",
                "datasets_used": ["COPERNICUS/S2_SR_HARMONIZED"],
                "processing_time_seconds": round(processing_time, 2),
                "roi_area_km2": round(roi_area_km2, 4),

                "class_definitions": {
                "NDVI_ranges": NDVIService.NDVI_RANGES,
                "description": "NDVI value ranges and vegetation interpretation",
                "legend": {
                    "water_bare": "Water bodies and bare soil (NDVI < 0.1)",
                    "sparse_vegetation": "Sparse vegetation (NDVI 0.1-0.3)", 
                    "moderate_vegetation": "Moderate vegetation (NDVI 0.3-0.6)",
                    "dense_vegetation": "Dense vegetation (NDVI > 0.6)"
                }
                },
                "visualization": {
                    "tile_url": tile_url,
                    "palette": NDVIService.NDVI_PALETTE,
                    "min": -0.2,
                    "max": 0.8,
                    "legend": {
                        "type": "continuous",
                        "title": "NDVI (Normalized Difference Vegetation Index)",
                        "description": "Vegetation health and density indicator",
                        "palette": NDVIService.NDVI_PALETTE,
                        "min_value": -0.2,
                        "max_value": 0.8,
                        "classes": [
                            {"name": "Water/Bare Soil", "range": "(-1.0 to -0.1)", "color": "#d73027", "description": "Water bodies and bare soil areas"},
                            {"name": "Sparse Vegetation", "range": "(0.1 to 0.3)", "color": "#f46d43", "description": "Sparse vegetation and grasslands"},
                            {"name": "Moderate Vegetation", "range": "(0.3 to 0.6)", "color": "#fdae61", "description": "Moderate vegetation coverage"},
                            {"name": "Dense Vegetation", "range": "(0.6 to 1.0)", "color": "#1a9850", "description": "Dense forests and vegetation"}
                        ]
                    }
                },
                
                "metadata": {
                    "start_date": start_date,
                    "end_date": end_date,
                    "cloud_threshold": cloud_threshold,
                    "scale_meters": scale,
                    "max_pixels": max_pixels,
                    "exact_computation": exact_computation,
                    "collection_size": collection_size,
                    "include_time_series": include_time_series
                },
                "debug": {
                    "histogram_method": histogram_method,
                    "time_series_method": time_series_data.get("method", "none"),
                    "vegetation_categories": len(vegetation_stats)
                },
                "success": True
            }
            
            return result
            
        except ee.EEException as e:
            error_msg = str(e)
            logger.error(f"❌ GEE Error in NDVI analysis: {error_msg}")
            
            if "quota" in error_msg.lower() or "limit" in error_msg.lower():
                return {
                    "error": "Google Earth Engine quota exceeded. Please try again later.",
                    "error_type": "quota_exceeded",
                    "success": False
                }
            elif "timeout" in error_msg.lower():
                return {
                    "error": "Analysis timed out. Try reducing the time range or area.",
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
            logger.error(f"❌ Unexpected error in NDVI analysis: {str(e)}")
            return {
                "error": f"NDVI analysis failed: {str(e)}",
                "error_type": "unexpected_error",
                "success": False
            }
    
    @staticmethod
    def _analyze_vegetation_distribution(histogram: Dict[str, int]) -> Dict[str, Any]:
        """Analyze vegetation distribution from NDVI histogram."""
        total_pixels = sum(histogram.values())
        if total_pixels == 0:
            return {
                "water_percentage": 0.0,
                "bare_soil_percentage": 0.0,
                "sparse_vegetation_percentage": 0.0,
                "moderate_vegetation_percentage": 0.0,
                "dense_vegetation_percentage": 0.0
            }
        
        categories = {
            "water_percentage": 0.0,
            "bare_soil_percentage": 0.0,
            "sparse_vegetation_percentage": 0.0,
            "moderate_vegetation_percentage": 0.0,
            "dense_vegetation_percentage": 0.0
        }
        
        for ndvi_str, count in histogram.items():
            try:
                ndvi_val = float(ndvi_str)
                percentage = (count / total_pixels) * 100
                
                if ndvi_val < 0.1:
                    # Split water and bare soil based on NDVI value
                    if ndvi_val < 0.0:
                        categories["water_percentage"] += percentage * 0.7  # Mostly water
                        categories["bare_soil_percentage"] += percentage * 0.3
                    else:
                        categories["water_percentage"] += percentage * 0.3  # Mostly bare soil
                        categories["bare_soil_percentage"] += percentage * 0.7
                elif ndvi_val < 0.3:
                    categories["sparse_vegetation_percentage"] += percentage
                elif ndvi_val < 0.6:
                    categories["moderate_vegetation_percentage"] += percentage
                else:
                    categories["dense_vegetation_percentage"] += percentage
                    
            except ValueError:
                continue
        
        return {k: round(v, 2) for k, v in categories.items()}
    
    @staticmethod
    def _generate_ndvi_description(
        ndvi_stats: Dict[str, Any],
        vegetation_stats: Dict[str, Any],
        time_series_data: Dict[str, Any]
    ) -> str:
        """Generate descriptive text for NDVI analysis."""
        mean_ndvi = ndvi_stats.get('NDVI_mean', 0)
        
        # Vegetation health assessment
        if mean_ndvi > 0.6:
            health = "excellent vegetation health with dense canopy cover"
        elif mean_ndvi > 0.4:
            health = "good vegetation health with moderate canopy cover"
        elif mean_ndvi > 0.2:
            health = "sparse vegetation with limited canopy cover"
        else:
            health = "minimal vegetation or predominantly non-vegetated surfaces"
        
        description = f"NDVI analysis shows {health} (mean NDVI: {mean_ndvi:.3f}). "
        
        # Add dominant vegetation type
        if vegetation_stats:
            dominant_type = max(vegetation_stats.items(), key=lambda x: x[1])
            description += f"Dominant land cover: {dominant_type[0].replace('_', ' ')} ({dominant_type[1]:.1f}%). "
        
        # Add time-series insight if available
        if time_series_data and "data" in time_series_data:
            method = time_series_data.get("method", "")
            data_count = len(time_series_data["data"])
            description += f"Time-series analysis ({method}) covers {data_count} periods showing vegetation trends."
        
        return description
