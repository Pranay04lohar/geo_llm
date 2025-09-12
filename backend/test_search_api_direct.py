#!/usr/bin/env python3
"""
Test Search API Service Directly

This script tests the Search API service to verify it's working correctly
with Nominatim geocoding and location data retrieval.
"""

import requests
import json
from typing import Dict, Any

# Search API endpoint
SEARCH_API_URL = "http://localhost:8001"

def test_search_api_health():
    """Test Search API health"""
    print("🏥 Testing Search API Health")
    print("-" * 40)

    try:
        response = requests.get(f"{SEARCH_API_URL}/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Search API is healthy: {data}")
            return data.get("status") == "healthy"
        else:
            print(f"❌ Search API health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to Search API: {e}")
        return False

def test_location_data_request():
    """Test location data request"""
    print("\n🔍 Testing Location Data Request")
    print("-" * 40)

    payload = {
        "location_name": "Mumbai",
        "location_type": "city"
    }

    try:
        print(f"📤 Sending request for: {payload['location_name']} ({payload['location_type']})")
        response = requests.post(
            f"{SEARCH_API_URL}/search/location-data",
            json=payload,
            timeout=30
        )

        print(f"📥 Response status: {response.status_code}")
        print(f"📄 Response headers: {dict(response.headers)}")

        if response.status_code == 200:
            data = response.json()
            print("✅ Search API Response:")
            print(json.dumps(data, indent=2))

            if data.get("success"):
                coords = data.get("coordinates", {})
                area = data.get("area_km2")
                polygon = data.get("polygon_geometry")
                print(f"\n📍 Coordinates: {coords}")
                print(f"📏 Area: {area} km²")
                print(f"📐 Polygon geometry: {'✅' if polygon else '❌'}")
                return True
            else:
                print(f"❌ API returned success=False: {data.get('error', 'Unknown error')}")
                return False
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"Response text: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return False

def test_different_locations():
    """Test with different locations"""
    print("\n🌍 Testing Different Locations")
    print("-" * 40)

    test_locations = [
        {"location_name": "Delhi", "location_type": "city"},
        {"location_name": "Mumbai", "location_type": "city"},
        {"location_name": "Bikaner", "location_type": "city"}
    ]

    results = []

    for location in test_locations:
        print(f"\n🧪 Testing: {location['location_name']}")
        print("-" * 30)

        try:
            response = requests.post(
                f"{SEARCH_API_URL}/search/location-data",
                json=location,
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                success = data.get("success", False)
                print(f"✅ Response: {'Success' if success else 'Failed'}")

                if success:
                    coords = data.get("coordinates", {})
                    area = data.get("area_km2")
                    print(f"   📍 Coordinates: {coords.get('lat', 'N/A')}, {coords.get('lng', 'N/A')}")
                    print(f"   📏 Area: {area if area else 'N/A'} km²")
                    results.append(True)
                else:
                    print(f"   ❌ Error: {data.get('error', 'Unknown error')}")
                    results.append(False)
            else:
                print(f"❌ HTTP {response.status_code}: {response.text}")
                results.append(False)

        except Exception as e:
            print(f"❌ Exception: {e}")
            results.append(False)

    # Summary
    passed = sum(results)
    total = len(results)
    print(f"\n📊 Results: {passed}/{total} locations successful")
    return passed > 0

def main():
    """Run all Search API tests"""
    print("🔍 Testing Search API Service")
    print("=" * 50)

    # Test 1: Health check
    health_ok = test_search_api_health()
    if not health_ok:
        print("\n❌ Search API is not healthy. Cannot proceed with tests.")
        return False

    # Test 2: Location data
    location_ok = test_location_data_request()

    # Test 3: Multiple locations
    multiple_ok = test_different_locations()

    # Final summary
    print("\n" + "=" * 50)
    print("📊 SEARCH API TEST SUMMARY")
    print("=" * 50)

    if health_ok and (location_ok or multiple_ok):
        print("✅ Search API is working!")
        return True
    else:
        print("❌ Search API has issues that need to be fixed.")
        return False

if __name__ == "__main__":
    main()