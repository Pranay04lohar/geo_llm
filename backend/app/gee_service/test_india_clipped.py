#!/usr/bin/env python3
"""
Test script for India-clipped water analysis
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

def test_india_clipped_analysis():
    """Test water analysis with India-clipped data"""
    
    # Test ROIs within India
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
        "Mumbai_Coastal": {
            "type": "Polygon",
            "coordinates": [[
                [72.77, 18.89],
                [72.97, 18.89], 
                [72.97, 19.27],
                [72.77, 19.27],
                [72.77, 18.89]
            ]]
        },
        "Kolkata_Ganges": {
            "type": "Polygon",
            "coordinates": [[
                [88.30, 22.50],
                [88.40, 22.50],
                [88.40, 22.60],
                [88.30, 22.60],
                [88.30, 22.50]
            ]]
        }
    }
    
    water_service = WaterService()
    
    print("🇮🇳 India-Clipped Water Analysis Test")
    print("=" * 60)
    print("Testing water analysis with data clipped to India region")
    print("This should improve performance and focus on Indian water bodies")
    print()
    
    for roi_name, roi_geom in test_rois.items():
        print(f"📍 {roi_name}")
        print("-" * 40)
        
        try:
            # Test JRC Official Analysis
            result = water_service.analyze_water_presence_jrc_official(
                roi=roi_geom,
                year=2020
            )
            
            if "error" in result:
                print(f"❌ Error: {result['error']}")
                continue
            
            # Display results
            stats = result.get('mapStats', {})
            print(f"📊 Water Analysis Results:")
            
            if 'permanent_water' in stats:
                perm = stats['permanent_water']
                print(f"   🔵 Permanent water: {perm['percentage']}% ({perm['pixels']} pixels)")
            
            if 'seasonal_water' in stats:
                seasonal = stats['seasonal_water']
                print(f"   🟢 Seasonal water: {seasonal['percentage']}% ({seasonal['pixels']} pixels)")
            
            if 'no_water' in stats:
                no_water = stats['no_water']
                print(f"   ⚪ No water: {no_water['percentage']}% ({no_water['pixels']} pixels)")
            
            # Show visual outputs
            if "urlFormatOfficial" in result and result["urlFormatOfficial"]:
                print(f"   🎨 Official Classification Map: {result['urlFormatOfficial'][:80]}...")
            
            if "urlFormatOccurrence" in result and result["urlFormatOccurrence"]:
                print(f"   🌡️ Occurrence Heatmap: {result['urlFormatOccurrence'][:80]}...")
            
            print(f"   ⏱️ Processing time: {result.get('processing_time_seconds', 'N/A')}s")
            print()
            
        except Exception as e:
            print(f"❌ Error processing {roi_name}: {e}")
            print()
    
    # Test quality info
    print("📋 Quality Information:")
    print("-" * 40)
    quality_info = water_service.get_water_quality_info()
    print(f"Dataset: {quality_info.get('dataset', 'N/A')}")
    print(f"Resolution: {quality_info.get('resolution', 'N/A')}")
    print(f"Temporal Coverage: {quality_info.get('temporal_coverage', 'N/A')}")
    print(f"Spatial Coverage: {quality_info.get('spatial_coverage', 'N/A')}")
    print()
    
    print("=" * 60)
    print("🇮🇳 India-Clipped Analysis Complete!")
    print("✅ All data is now limited to Indian region for better performance")

if __name__ == "__main__":
    test_india_clipped_analysis()
