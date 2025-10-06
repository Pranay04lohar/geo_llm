#!/usr/bin/env python3
"""
Test Search API with detailed debugging
"""

import requests
import json

def test_search_api_with_debug():
    """Test Search API with detailed debugging."""
    
    print("🔍 Testing Search API with Debug Info")
    print("=" * 50)
    
    try:
        # Test the Search API service endpoint
        response = requests.post(
            "http://localhost:8001/search/location-data",
            json={
                "location_name": "Bikaner",
                "location_type": "city"
            },
            timeout=15
        )
        
        print(f"📊 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ Response Data:")
            print(json.dumps(data, indent=2))
            
            # Check for polygon geometry fields
            print(f"\n🎯 Polygon Geometry Fields:")
            print(f"   polygon_geometry: {bool(data.get('polygon_geometry'))}")
            print(f"   geometry_tiles: {len(data.get('geometry_tiles', []))}")
            print(f"   bounding_box: {bool(data.get('bounding_box'))}")
            print(f"   is_tiled: {data.get('is_tiled', False)}")
            print(f"   is_fallback: {data.get('is_fallback', False)}")
            
            # Check if fields are None vs missing
            print(f"\n🔍 Field Analysis:")
            for field in ['polygon_geometry', 'geometry_tiles', 'bounding_box', 'is_tiled', 'is_fallback']:
                if field in data:
                    print(f"   {field}: Present = {data[field]}")
                else:
                    print(f"   {field}: MISSING")
        else:
            print(f"❌ Error Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_search_api_with_debug()
