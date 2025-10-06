#!/usr/bin/env python3
"""
Test Search API and check logs for validation errors
"""

import requests
import json
import time

def test_search_api_with_logs():
    """Test Search API and analyze the response."""
    
    print("🔍 Testing Search API Service with Log Analysis")
    print("=" * 60)
    
    try:
        # Test the Search API service endpoint
        print("📡 Calling Search API service...")
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
            
            # Check if we have polygon geometry fields
            has_polygon = bool(data.get('polygon_geometry'))
            has_tiles = len(data.get('geometry_tiles', [])) > 0
            has_bbox = bool(data.get('bounding_box'))
            is_tiled = data.get('is_tiled', False)
            is_fallback = data.get('is_fallback', False)
            
            print(f"\n🎯 Polygon Geometry Analysis:")
            print(f"   polygon_geometry: {has_polygon}")
            print(f"   geometry_tiles: {len(data.get('geometry_tiles', []))}")
            print(f"   bounding_box: {has_bbox}")
            print(f"   is_tiled: {is_tiled}")
            print(f"   is_fallback: {is_fallback}")
            
            if not has_polygon and not has_tiles and not has_bbox:
                print("\n❌ ISSUE IDENTIFIED: All polygon geometry fields are missing!")
                print("   This indicates the Search API service is using the minimal LocationResponse")
                print("   due to a validation error. Check the Search API service logs.")
                
                # Check if we have the basic fields that should be present
                basic_fields = ['coordinates', 'area_km2', 'administrative_info', 'success']
                missing_basic = [field for field in basic_fields if field not in data]
                
                if missing_basic:
                    print(f"   ❌ Missing basic fields: {missing_basic}")
                else:
                    print(f"   ✅ Basic fields present: {basic_fields}")
                    
                # Check if this looks like a minimal response
                if data.get('success') and not data.get('error') and len(data) <= 7:
                    print("   🔍 This appears to be a minimal LocationResponse due to validation failure")
                else:
                    print("   🔍 This appears to be a different type of response")
            else:
                print("\n✅ SUCCESS: Polygon geometry fields are present!")
                
        else:
            print(f"❌ Error Response: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_search_api_with_logs()
