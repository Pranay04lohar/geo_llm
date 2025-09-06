#!/usr/bin/env python3
"""
Direct test of Nominatim API to debug the search issue
"""

import requests
import json

def test_nominatim_direct():
    """Test Nominatim API directly"""
    try:
        print("🔍 Testing Nominatim API directly for Bikaner...")
        
        # Test different search queries
        queries = [
            "Bikaner, India",
            "Bikaner, city, India", 
            "Bikaner",
            "Bikaner city"
        ]
        
        for query in queries:
            print(f"\n📝 Testing query: '{query}'")
            
            params = {
                'q': query,
                'format': 'json',
                'polygon_geojson': 1,
                'addressdetails': 1,
                'limit': 5,
                'extratags': 1
            }
            
            headers = {
                'User-Agent': 'GeoLLM-SearchService/1.0 (geospatial analysis tool)'
            }
            
            response = requests.get(
                'https://nominatim.openstreetmap.org/search',
                params=params,
                headers=headers,
                timeout=15
            )
            
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                results = response.json()
                print(f"Found {len(results)} results")
                
                if results:
                    for i, result in enumerate(results[:3]):  # Show first 3 results
                        print(f"  {i+1}. {result.get('display_name', 'No name')}")
                        print(f"     Type: {result.get('class')}/{result.get('type')}")
                        print(f"     Coords: {result.get('lat')}, {result.get('lon')}")
                        print(f"     Has geojson: {'geojson' in result}")
                        print(f"     Has boundingbox: {'boundingbox' in result}")
                else:
                    print("  No results found")
            else:
                print(f"  Error: {response.text}")
                
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_nominatim_direct()
