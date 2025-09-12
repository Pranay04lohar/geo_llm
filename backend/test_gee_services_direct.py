#!/usr/bin/env python3
"""
Direct GEE Services Test - Bypass Core LLM Agent

This test directly calls the GEE services to verify they work correctly
before testing the full integration with Core LLM Agent.
"""

import requests
import time
import json
from typing import Dict, Any

# Test configuration
GEE_SERVICE_URL = "http://localhost:8000"

# Test geometries
MUMBAI_GEOMETRY = {
    "type": "Polygon",
    "coordinates": [[
        [72.77, 18.89],
        [72.97, 18.89], 
        [72.97, 19.27],
        [72.77, 19.27],
        [72.77, 18.89]
    ]]
}

DELHI_GEOMETRY = {
    "type": "Polygon",
    "coordinates": [[
        [77.0, 28.4],
        [77.5, 28.4],
        [77.5, 28.8],
        [77.0, 28.8],
        [77.0, 28.4]
    ]]
}

def test_gee_service_health():
    """Test GEE service health"""
    print("🏥 Testing GEE Service Health")
    print("-" * 40)
    
    try:
        response = requests.get(f"{GEE_SERVICE_URL}/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ GEE Service is healthy: {data}")
            return data.get("gee_initialized", False)
        else:
            print(f"❌ GEE Service health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to GEE service: {e}")
        return False

def test_water_service():
    """Test Water Analysis Service directly"""
    print("\n🌊 Testing Water Analysis Service")
    print("-" * 40)
    
    # Test 1: Basic water analysis
    payload = {
        "roi": MUMBAI_GEOMETRY,
        "year": 2023,
        "threshold": 20,
        "include_seasonal": True
    }
    
    try:
        start_time = time.time()
        response = requests.post(
            f"{GEE_SERVICE_URL}/water/analyze",
            json=payload,
            timeout=60
        )
        processing_time = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Water analysis successful in {processing_time:.2f}s")
            print(f"📊 Water percentage: {result.get('mapStats', {}).get('water_percentage', 'N/A')}")
            print(f"🗺️ Tile URL: {'✅' if result.get('urlFormat') else '❌'}")
            return True
        else:
            print(f"❌ Water analysis failed: {response.status_code}")
            print(f"Error: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Water service test failed: {e}")
        return False

def test_ndvi_service():
    """Test NDVI Service directly"""
    print("\n🌱 Testing NDVI Service")
    print("-" * 40)
    
    payload = {
        "geometry": MUMBAI_GEOMETRY,
        "startDate": "2023-06-01",
        "endDate": "2023-08-31",
        "cloudThreshold": 30,
        "scale": 30,
        "maxPixels": 1e9,
        "includeTimeSeries": True,
        "exactComputation": False
    }
    
    try:
        start_time = time.time()
        response = requests.post(
            f"{GEE_SERVICE_URL}/ndvi/vegetation-analysis",
            json=payload,
            timeout=120
        )
        processing_time = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ NDVI analysis successful in {processing_time:.2f}s")
            ndvi_stats = result.get('mapStats', {}).get('ndvi_statistics', {})
            print(f"📊 Mean NDVI: {ndvi_stats.get('mean', 'N/A')}")
            print(f"🗺️ Tile URL: {'✅' if result.get('urlFormat') else '❌'}")
            return True
        else:
            print(f"❌ NDVI analysis failed: {response.status_code}")
            print(f"Error: {response.text}")
            return False
    except Exception as e:
        print(f"❌ NDVI service test failed: {e}")
        return False

def test_lulc_service():
    """Test LULC Service directly"""
    print("\n🏗️ Testing LULC Service")
    print("-" * 40)
    
    payload = {
        "geometry": MUMBAI_GEOMETRY,
        "startDate": "2023-01-01",
        "endDate": "2023-12-31",
        "confidenceThreshold": 0.3,
        "scale": 10,
        "maxPixels": 1e13
    }
    
    try:
        start_time = time.time()
        response = requests.post(
            f"{GEE_SERVICE_URL}/lulc/dynamic-world",
            json=payload,
            timeout=120
        )
        processing_time = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ LULC analysis successful in {processing_time:.2f}s")
            class_percentages = result.get('mapStats', {}).get('class_percentages', {})
            print(f"📊 Dominant class: {result.get('mapStats', {}).get('dominant_class', 'N/A')}")
            print(f"🗺️ Tile URL: {'✅' if result.get('urlFormat') else '❌'}")
            return True
        else:
            print(f"❌ LULC analysis failed: {response.status_code}")
            print(f"Error: {response.text}")
            return False
    except Exception as e:
        print(f"❌ LULC service test failed: {e}")
        return False

def test_lst_service():
    """Test LST Service directly"""
    print("\n🌡️ Testing LST Service")
    print("-" * 40)
    
    payload = {
        "geometry": MUMBAI_GEOMETRY,
        "startDate": "2024-01-01",
        "endDate": "2024-08-31",
        "includeUHI": True,
        "includeTimeSeries": False,
        "scale": 1000,
        "maxPixels": 1e6,
        "exactComputation": False
    }
    
    try:
        start_time = time.time()
        response = requests.post(
            f"{GEE_SERVICE_URL}/lst/land-surface-temperature",
            json=payload,
            timeout=120
        )
        processing_time = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ LST analysis successful in {processing_time:.2f}s")
            lst_stats = result.get('lst_stats', {})
            print(f"📊 Mean LST: {lst_stats.get('LST_mean', 'N/A')}°C")
            print(f"🏙️ UHI Intensity: {result.get('uhi_intensity', 'N/A')}°C")
            print(f"🗺️ Tile URL: {'✅' if result.get('urlFormat') else '❌'}")
            return True
        else:
            print(f"❌ LST analysis failed: {response.status_code}")
            print(f"Error: {response.text}")
            return False
    except Exception as e:
        print(f"❌ LST service test failed: {e}")
        return False

def main():
    """Run all direct GEE service tests"""
    print("🧪 Direct GEE Services Test")
    print("=" * 50)
    print("Testing GEE services directly (bypassing Core LLM Agent)")
    print("=" * 50)
    
    # Test health first
    if not test_gee_service_health():
        print("\n❌ GEE service is not healthy. Cannot proceed with tests.")
        return False
    
    # Test all services
    results = {
        "water": test_water_service(),
        "ndvi": test_ndvi_service(),
        "lulc": test_lulc_service(),
        "lst": test_lst_service()
    }
    
    # Print summary
    print("\n" + "=" * 50)
    print("📊 DIRECT GEE SERVICES TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(results.values())
    total = len(results)
    
    for service, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{service.upper()} Service: {status}")
    
    print(f"\n🎯 OVERALL RESULTS:")
    print(f"  Passed: {passed}/{total} services")
    print(f"  Success Rate: {(passed/total*100):.1f}%")
    
    if passed == total:
        print(f"\n🎉 ALL GEE SERVICES WORKING! The issue is with Core LLM Agent integration.")
        print("💡 Next steps:")
        print("  1. Check Core LLM Agent import paths")
        print("  2. Verify service dispatcher configuration")
        print("  3. Debug the query processing pipeline")
    else:
        print(f"\n⚠️ Some GEE services have issues that need to be fixed first.")
    
    return passed == total

if __name__ == "__main__":
    main()
