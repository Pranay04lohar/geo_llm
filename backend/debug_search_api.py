#!/usr/bin/env python3
"""
Debug script to check what the Search API service returns
"""

import requests
import json

def test_search_api_endpoint():
    """Test the Search API service endpoint directly."""
    
    print("🔍 Testing Search API Service Endpoint")
    print("=" * 40)
    
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
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Search API Response Status: {response.status_code}")
            print(f"📊 Success: {data.get('success', False)}")
            print(f"📍 Coordinates: {data.get('coordinates', {})}")
            print(f"📐 Area: {data.get('area_km2', 0)} km²")
            print(f"🎯 Has polygon_geometry: {bool(data.get('polygon_geometry'))}")
            print(f"🔄 Is tiled: {data.get('is_tiled', False)}")
            print(f"📦 Tiles count: {len(data.get('geometry_tiles', []))}")
            
            if data.get('polygon_geometry'):
                polygon = data['polygon_geometry']
                print(f"   📦 Polygon type: {polygon.get('type', 'unknown')}")
                print(f"   📍 Coordinates count: {len(polygon.get('coordinates', [[]])[0]) if polygon else 0}")
            
            print(f"\n📋 Full Response:")
            print(json.dumps(data, indent=2))
            
        else:
            print(f"❌ Search API Response Status: {response.status_code}")
            print(f"📋 Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_search_api_endpoint()
