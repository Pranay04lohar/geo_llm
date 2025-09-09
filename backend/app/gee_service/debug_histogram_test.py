#!/usr/bin/env python3
"""
Deep debugging test to understand what's happening with the frequency histogram
"""

import ee
import logging
import json

logging.basicConfig(level=logging.INFO)

def debug_histogram_issue():
    """Debug the histogram issue step by step"""
    
    print("Deep Debugging Water Service Histogram Issue")
    print("=" * 60)
    
    try:
        # Initialize EE
        ee.Initialize(project='gee-tool-469517')
        
        # Load JRC dataset
        jrc_image = ee.Image('JRC/GSW1_4/GlobalSurfaceWater')
        water_occurrence = jrc_image.select('occurrence')
        
        # Test with a small area in Delhi (should be mostly non-water)
        test_roi = ee.Geometry.Polygon([[
            [77.20, 28.55],
            [77.25, 28.55],
            [77.25, 28.60], 
            [77.20, 28.60],
            [77.20, 28.55]
        ]])
        
        print("Step 1: Check raw occurrence values")
        occurrence_stats = water_occurrence.reduceRegion(
            reducer=ee.Reducer.minMax(),
            geometry=test_roi,
            scale=30,
            maxPixels=1e9
        ).getInfo()
        print(f"Raw occurrence stats: {occurrence_stats}")
        
        # Get mean separately
        occurrence_mean = water_occurrence.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=test_roi,
            scale=30,
            maxPixels=1e9
        ).getInfo()
        print(f"Raw occurrence mean: {occurrence_mean}")
        
        # Test different thresholds
        for threshold in [20, 50]:
            print(f"\nStep 2: Testing threshold {threshold}%")
            
            # Create binary mask
            water_mask = water_occurrence.gte(threshold)
            
            print("Step 3: Check mask values")
            mask_stats = water_mask.reduceRegion(
                reducer=ee.Reducer.minMax(),
                geometry=test_roi,
                scale=30,
                maxPixels=1e9
            ).getInfo()
            print(f"Mask stats: {mask_stats}")
            
            mask_mean = water_mask.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=test_roi,
                scale=30,
                maxPixels=1e9
            ).getInfo()
            print(f"Mask mean: {mask_mean}")
            
            print("Step 4: Get frequency histogram")
            histogram = water_mask.reduceRegion(
                reducer=ee.Reducer.frequencyHistogram(),
                geometry=test_roi,
                scale=30,
                maxPixels=1e9
            ).getInfo()
            print(f"Full histogram result: {histogram}")
            
            # Extract the actual histogram data
            for band_name, hist_data in histogram.items():
                if hist_data:
                    print(f"Band '{band_name}' histogram: {hist_data}")
                    if isinstance(hist_data, dict):
                        total_pixels = sum(hist_data.values())
                        water_pixels = hist_data.get('1', 0)
                        no_water_pixels = hist_data.get('0', 0)
                        print(f"  Water pixels (1): {water_pixels}")
                        print(f"  No water pixels (0): {no_water_pixels}")
                        print(f"  Total pixels: {total_pixels}")
                        if total_pixels > 0:
                            water_pct = (water_pixels / total_pixels) * 100
                            print(f"  Water percentage: {water_pct:.2f}%")
            
            print("Step 5: Alternative counting method")
            # Try using count reducer on masked areas
            water_count = water_mask.eq(1).reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=test_roi,
                scale=30,
                maxPixels=1e9
            ).getInfo()
            
            no_water_count = water_mask.eq(0).reduceRegion(
                reducer=ee.Reducer.sum(), 
                geometry=test_roi,
                scale=30,
                maxPixels=1e9
            ).getInfo()
            
            print(f"Water count (method 2): {water_count}")
            print(f"No water count (method 2): {no_water_count}")
            
            print("-" * 60)
        
        # Test with a known water area (Yamuna River area in Delhi)
        print("\nTesting with known water area (Yamuna River):")
        river_roi = ee.Geometry.Polygon([[
            [77.25, 28.65],
            [77.27, 28.65],
            [77.27, 28.67], 
            [77.25, 28.67],
            [77.25, 28.65]
        ]])
        
        river_occurrence_stats = water_occurrence.reduceRegion(
            reducer=ee.Reducer.minMax(),
            geometry=river_roi,
            scale=30,
            maxPixels=1e9
        ).getInfo()
        print(f"River area occurrence stats: {river_occurrence_stats}")
        
        river_occurrence_mean = water_occurrence.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=river_roi,
            scale=30,
            maxPixels=1e9
        ).getInfo()
        print(f"River area occurrence mean: {river_occurrence_mean}")
        
        river_mask = water_occurrence.gte(20)
        river_histogram = river_mask.reduceRegion(
            reducer=ee.Reducer.frequencyHistogram(),
            geometry=river_roi,
            scale=30,
            maxPixels=1e9
        ).getInfo()
        print(f"River area histogram: {river_histogram}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_histogram_issue()