#!/usr/bin/env python3
"""
Simple test to isolate NDVI service issues
"""

import os
import sys
import ee

# Add path for imports
sys.path.append('.')

def test_ndvi_direct():
    """Test NDVI service directly"""
    try:
        from services.ndvi_service import NDVIService
        print("✅ NDVI service imported")
        
        # Test geometry
        geometry = {
            "type": "Polygon",
            "coordinates": [[
                [72.85, 19.05],
                [72.87, 19.05], 
                [72.87, 19.07],
                [72.85, 19.07],
                [72.85, 19.05]
            ]]
        }
        
        print("🧪 Testing NDVI analysis directly...")
        
        # Call with minimal parameters
        result = NDVIService.analyze_ndvi(
            geometry=geometry,
            start_date="2023-06-01",
            end_date="2023-08-31",
            cloud_threshold=30,
            scale=30,
            max_pixels=1000000,
            include_time_series=False,
            exact_computation=False
        )
        
        if result.get("success"):
            print("✅ Direct NDVI call successful!")
            print(f"   Processing time: {result.get('processing_time_seconds', 0):.1f}s")
            print(f"   Analysis type: {result.get('analysis_type', 'unknown')}")
        else:
            print(f"❌ Direct NDVI call failed: {result.get('error', 'Unknown error')}")
            print(f"   Error type: {result.get('error_type', 'unknown')}")
            
        return result
        
    except Exception as e:
        print(f"❌ Exception in direct test: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    print("🧪 Simple NDVI Service Test")
    print("=" * 40)
    
    try:
        # Initialize Earth Engine
        ee.Initialize()
        print("✅ Earth Engine initialized")
        
        test_ndvi_direct()
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
