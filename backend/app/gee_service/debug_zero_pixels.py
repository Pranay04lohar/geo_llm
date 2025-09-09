#!/usr/bin/env python3
"""
Debug script to investigate zero pixels issue in JRC water analysis
"""

import ee
import logging
from services.water_service import WaterService

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Earth Engine
try:
    project_id = 'gee-tool-469517'
    ee.Initialize(project=project_id)
    logger.info(f"✅ Earth Engine initialized with project '{project_id}'")
except Exception as e:
    logger.error(f"❌ Failed to initialize Earth Engine: {e}")
    exit(1)

def debug_geometry_and_bands():
    """Debug geometry and band information"""
    
    # Test ROIs
    test_rois = {
        "Delhi_Urban": {
            "type": "Polygon",
            "coordinates": [[
                [77.20, 28.60],
                [77.25, 28.60],
                [77.25, 28.65],
                [77.20, 28.65],
                [77.20, 28.60]
            ]]
        },
        "Yamuna_River": {
            "type": "Polygon", 
            "coordinates": [[
                [77.20, 28.60],
                [77.30, 28.60],
                [77.30, 28.70],
                [77.20, 28.70],
                [77.20, 28.60]
            ]]
        }
    }
    
    # Load JRC image
    jrc_image = ee.Image('JRC/GSW1_4/GlobalSurfaceWater')
    
    print("🔍 JRC Image Debug Information")
    print("=" * 60)
    
    # Check band names
    band_names = jrc_image.bandNames().getInfo()
    print(f"📊 Available bands: {band_names}")
    
    # Check image properties
    try:
        image_info = jrc_image.getInfo()
        print(f"📏 Image dimensions: {image_info.get('bands', [{}])[0].get('dimensions', 'Unknown')}")
        print(f"🌍 Image CRS: {image_info.get('bands', [{}])[0].get('crs', 'Unknown')}")
    except Exception as e:
        print(f"⚠️ Could not get image info: {e}")
    
    for roi_name, roi_geom in test_rois.items():
        print(f"\n{'='*60}")
        print(f"Testing: {roi_name}")
        print("-" * 60)
        
        # Convert to EE geometry
        if roi_geom['type'] == 'Polygon':
            coords = roi_geom['coordinates']
            geometry = ee.Geometry.Polygon(coords)
        else:
            coords = roi_geom['coordinates']
            geometry = ee.Geometry.Point(coords[0], coords[1]).buffer(1000)
        
        # Check geometry area
        try:
            area = geometry.area().getInfo()
            print(f"📐 Geometry area: {area:.2f} m²")
        except Exception as e:
            print(f"❌ Error calculating area: {e}")
        
            # Check if geometry intersects with image
            try:
                # Get a small sample to check intersection
                sample = jrc_image.select('seasonality').reduceRegion(
                    reducer=ee.Reducer.count(),
                    geometry=geometry,
                    scale=30,
                    maxPixels=1e13  # Increase limit to avoid pixel count errors
                ).getInfo()
                print(f"🔢 Sample pixel count: {sample}")
            except Exception as e:
                print(f"❌ Error sampling: {e}")
        
            # Check individual bands (separate reducers to avoid combination error)
            for band in ['seasonality', 'max_extent', 'occurrence']:
                try:
                    # MinMax stats
                    minmax_stats = jrc_image.select(band).reduceRegion(
                        reducer=ee.Reducer.minMax(),
                        geometry=geometry,
                        scale=30,
                        maxPixels=1e13
                    ).getInfo()
                    
                    # Mean stats
                    mean_stats = jrc_image.select(band).reduceRegion(
                        reducer=ee.Reducer.mean(),
                        geometry=geometry,
                        scale=30,
                        maxPixels=1e13
                    ).getInfo()
                    
                    print(f"📊 {band}: min={minmax_stats.get(f'{band}_min', 'N/A')}, max={minmax_stats.get(f'{band}_max', 'N/A')}, mean={mean_stats.get(band, 'N/A')}")
                except Exception as e:
                    print(f"❌ Error with {band}: {e}")
        
        # Test the classification logic
        print(f"\n🔬 Testing Classification Logic:")
        try:
            seasonality = jrc_image.select('seasonality')
            max_extent = jrc_image.select('max_extent')
            
            # Test each classification with proper logic
            # Permanent water: seasonality == 12 AND max_extent == 1
            permanent_water = seasonality.eq(12).And(max_extent.eq(1))
            
            # Seasonal water: seasonality 1-11 AND max_extent == 1
            seasonal_water = seasonality.gte(1).And(seasonality.lte(11)).And(max_extent.eq(1))
            
            # No water: max_extent == 0 (water was never detected)
            no_water = max_extent.eq(0)
            
            # Debug: Check max_extent values
            max_extent_stats = max_extent.reduceRegion(
                reducer=ee.Reducer.frequencyHistogram(),
                geometry=geometry,
                scale=30,
                maxPixels=1e13
            ).getInfo()
            print(f"   📊 Max extent histogram: {max_extent_stats}")
            
            # Count pixels for each class
            permanent_count = permanent_water.reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=geometry,
                scale=30,
                maxPixels=1e13
            ).getInfo()
            
            seasonal_count = seasonal_water.reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=geometry,
                scale=30,
                maxPixels=1e13
            ).getInfo()
            
            no_water_count = no_water.reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=geometry,
                scale=30,
                maxPixels=1e13
            ).getInfo()
            
            print(f"   🔵 Permanent water pixels: {permanent_count.get('seasonality', 0)}")
            print(f"   🟢 Seasonal water pixels: {seasonal_count.get('seasonality', 0)}")
            print(f"   ⚪ No water pixels: {no_water_count.get('max_extent', 0)}")
            
            # Debug: Check what bands are being returned
            print(f"   🔍 Permanent count details: {permanent_count}")
            print(f"   🔍 Seasonal count details: {seasonal_count}")
            print(f"   🔍 No water count details: {no_water_count}")
            
            # Test direct max_extent counting
            max_extent_0_count = max_extent.eq(0).reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=geometry,
                scale=30,
                maxPixels=1e13
            ).getInfo()
            print(f"   🔍 Direct max_extent=0 count: {max_extent_0_count}")
            
            # Test with frequency histogram
            print(f"\n📊 Frequency Histogram Test:")
            hist = seasonality.reduceRegion(
                reducer=ee.Reducer.frequencyHistogram(),
                geometry=geometry,
                scale=30,
                maxPixels=1e13
            ).getInfo()
            print(f"   Seasonality histogram: {hist}")
            
        except Exception as e:
            print(f"❌ Error in classification test: {e}")

if __name__ == "__main__":
    debug_geometry_and_bands()
