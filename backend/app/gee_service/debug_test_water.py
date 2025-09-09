#!/usr/bin/env python3
"""
Enhanced test script with debugging for the Water/Flood Service
"""

import json
import logging
import sys
import os

# Set up logging to see debug info
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the parent directory to Python path to import the service
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_water_service_with_debug():
    """Test the water service with detailed debugging"""
    
    print("🌊 Testing Water Service with Debug Information")
    print("=" * 70)
    
    try:
        # Import the service
        from services.water_service import WaterService
        
        # Test different ROIs to see if the issue is location-specific
        test_rois = {
            "Mumbai_Large": {
                "type": "Polygon",
                "coordinates": [[
                    [72.77, 18.89],
                    [72.97, 18.89], 
                    [72.97, 19.27],
                    [72.77, 19.27],
                    [72.77, 18.89]
                ]]
            },
            "Mumbai_Small": {
                "type": "Polygon", 
                "coordinates": [[
                    [72.85, 19.05],
                    [72.90, 19.05],
                    [72.90, 19.10],
                    [72.85, 19.10],
                    [72.85, 19.05]
                ]]
            },
            "Mumbai_Point": {
                "type": "Point",
                "coordinates": [72.87, 19.08]
            },
            "Coastal_Area": {
                "type": "Polygon",
                "coordinates": [[
                    [72.80, 18.90],
                    [72.85, 18.90],
                    [72.85, 18.95],
                    [72.80, 18.95],
                    [72.80, 18.90]
                ]]
            }
        }
        
        # Initialize service
        water_service = WaterService()
        
        # Test each ROI
        for roi_name, roi_geom in test_rois.items():
            print(f"\n" + "=" * 70)
            print(f"Testing ROI: {roi_name}")
            print("-" * 70)
            
            # Debug the ROI data first
            debug_info = water_service.debug_roi_data(roi_geom)
            print("🔍 Debug Information:")
            print(json.dumps(debug_info, indent=2))
            
            if not debug_info.get("has_data", False):
                print("❌ No data found in this ROI!")
                continue
            
            # Test with different thresholds
            for threshold in [5, 20, 50, 80]:
                print(f"\n--- Testing with {threshold}% threshold ---")
                
                try:
                    result = water_service.analyze_water_presence(
                        roi=roi_geom,
                        year=2023,
                        threshold=threshold,
                        include_seasonal=False  # Disable for debugging
                    )
                    
                    if "error" in result:
                        print(f"❌ Error: {result['error']}")
                    else:
                        stats = result['mapStats']
                        print(f"🌊 Water: {stats['water_percentage']}%")
                        print(f"🏞️ Non-Water: {stats['non_water_percentage']}%")
                        print(f"📊 Total pixels: {stats['total_pixels']}")
                        print(f"🎯 Threshold: {stats['threshold_used']}%")
                        
                except Exception as e:
                    print(f"❌ Exception: {e}")
        
        # Test a known water-rich area (Ganges Delta)
        print(f"\n" + "=" * 70)
        print("Testing Known Water-Rich Area: Ganges Delta")
        print("-" * 70)
        
        ganges_delta = {
            "type": "Polygon",
            "coordinates": [[
                [89.0, 21.5],
                [90.5, 21.5],
                [90.5, 23.0],
                [89.0, 23.0],
                [89.0, 21.5]
            ]]
        }
        
        debug_info = water_service.debug_roi_data(ganges_delta)
        print("🔍 Ganges Delta Debug Info:")
        print(json.dumps(debug_info, indent=2))
        
        result = water_service.analyze_water_presence(
            roi=ganges_delta,
            threshold=20,
            include_seasonal=False
        )
        
        if "error" not in result:
            stats = result['mapStats']
            print(f"🌊 Ganges Delta Water: {stats['water_percentage']}%")
            print(f"🏞️ Non-Water: {stats['non_water_percentage']}%")
        
        # Test a known dry area (Thar Desert)
        print(f"\n" + "=" * 70)
        print("Testing Known Dry Area: Thar Desert")
        print("-" * 70)
        
        thar_desert = {
            "type": "Polygon", 
            "coordinates": [[
                [70.0, 26.0],
                [72.0, 26.0],
                [72.0, 28.0],
                [70.0, 28.0],
                [70.0, 26.0]
            ]]
        }
        
        debug_info = water_service.debug_roi_data(thar_desert)
        print("🔍 Thar Desert Debug Info:")
        print(json.dumps(debug_info, indent=2))
        
        result = water_service.analyze_water_presence(
            roi=thar_desert,
            threshold=20,
            include_seasonal=False
        )
        
        if "error" not in result:
            stats = result['mapStats']
            print(f"🏜️ Thar Desert Water: {stats['water_percentage']}%")
            print(f"🏞️ Non-Water: {stats['non_water_percentage']}%")
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Make sure you're running from the correct directory")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_water_service_with_debug()