#!/usr/bin/env python3
"""
Quick test script to check Search API Service response for Bikaner
"""

import requests
import json

def test_search_api():
    """Test Search API Service with Nominatim integration for Bikaner"""
    try:
        print("🔍 Testing Search API Service with Nominatim for Bikaner...")
        
        
        response = requests.post(
            'http://localhost:8001/search/location-data',
            json={'location_name': 'Jodhpur', 'location_type': 'city'},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Search API Response:")
            print(json.dumps(data, indent=2))
            
            if data.get("success"):
                coords = data.get("coordinates", {})
                area = data.get("area_km2")
                print(f"\n📍 Coordinates: {coords.get('lat', 'N/A')}°N, {coords.get('lng', 'N/A')}°E")
                print(f"📊 Area: {area} km²")
            else:
                print(f"❌ API returned success=False: {data.get('error', 'Unknown error')}")
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_search_api()
