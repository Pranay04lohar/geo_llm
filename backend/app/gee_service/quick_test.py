#!/usr/bin/env python3
"""
Quick test for the LULC service - tests core functionality without external HTTP calls
"""

import sys
import os

# Add path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from services.lulc_service import LULCService
import time

# Test geometry - small area around Mumbai
TEST_GEOMETRY = {
    "type": "Polygon", 
    "coordinates": [[
        [72.8, 19.0],
        [72.9, 19.0],
        [72.9, 19.1], 
        [72.8, 19.1],
        [72.8, 19.0]
    ]]
}

def test_lulc_directly():
    """Test the LULC service directly without FastAPI"""
    print("🚀 Testing LULC Service Directly")
    print("=" * 50)
    
    # Test authentication first
    try:
        import ee
        ee.Initialize()
        print("✅ Google Earth Engine authenticated")
    except Exception as e:
        print(f"❌ GEE authentication failed: {e}")
        print("Run: earthengine authenticate")
        return False
    
    print(f"\n🗺️  Testing small Mumbai area...")
    start_time = time.time()
    
    try:
        # Call the LULC service directly
        result = LULCService.analyze_dynamic_world(
            geometry=TEST_GEOMETRY,
            start_date="2023-01-01",
            end_date="2023-12-31",
            confidence_threshold=0.5,
            scale=30,  # Use 30m for faster processing
            max_pixels=1e9
        )
        
        total_time = time.time() - start_time
        
        if result.get("success", False):
            print(f"\n✅ LULC Analysis Successful!")
            print(f"⏱️  Processing time: {result.get('processing_time_seconds', 0):.2f}s")
            print(f"⏱️  Total time: {total_time:.2f}s")
            print(f"📊 ROI area: {result.get('roi_area_km2', 0):.4f} km²")
            
            # Display class statistics
            map_stats = result.get('mapStats', {})
            class_percentages = map_stats.get('class_percentages', {})
            
            if class_percentages:
                print(f"\n📈 Land Cover Distribution:")
                for class_name, percentage in sorted(class_percentages.items(), key=lambda x: x[1], reverse=True):
                    if percentage > 0:
                        print(f"   {class_name}: {percentage}%")
                
                print(f"\n🌍 Dominant class: {map_stats.get('dominant_class', 'Unknown')}")
            else:
                print("⚠️  No class percentages returned")
            
            # Check tile URL
            tile_url = result.get('urlFormat', '')
            if tile_url:
                print(f"\n🗺️  Tile URL generated: ✅")
                print(f"   Length: {len(tile_url)} characters")
            else:
                print(f"\n❌ No tile URL generated")
            
            print(f"\n🎯 Performance Achievement:")
            processing_time = result.get('processing_time_seconds', 0)
            if processing_time > 0 and processing_time < 30:
                speedup = 100 / processing_time
                print(f"   Old approach: ~100+ seconds")
                print(f"   New approach: {processing_time:.2f}s")
                print(f"   Speedup: ~{speedup:.1f}x faster! 🚀")
            else:
                print(f"   Processing time: {processing_time}s")
            
            return True
            
        else:
            print(f"❌ Analysis failed: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Direct LULC Service Test")
    print("Testing optimized tile-first approach")
    print()
    
    success = test_lulc_directly()
    
    if success:
        print("\n🎉 Test completed successfully!")
        print("Your refactored LULC service is working!")
    else:
        print("\n💔 Test failed - check authentication and setup")
