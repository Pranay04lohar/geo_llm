#!/usr/bin/env python3
"""
Test script for the Water/Flood Service
Tests water analysis using JRC Global Surface Water dataset
"""

import json
import time
import requests
from typing import Dict, Any

# Test ROI: Mumbai region (same as used in other tests)
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

# Test ROI: Delhi region
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

# Test ROI: Point (with buffer)
MUMBAI_POINT = {
    "type": "Point",
    "coordinates": [72.87, 19.08]  # Mumbai city center
}

def test_water_service(base_url: str = "http://localhost:8000"):
    """Test the Water Service endpoint"""
    
    print("🌊 Testing Water/Flood FastAPI Service")
    print("=" * 60)
    
    # Test health check first
    try:
        health_response = requests.get(f"{base_url}/health", timeout=10)
        if health_response.status_code == 200:
            print("✅ Service is healthy")
        else:
            print(f"❌ Service health check failed: {health_response.status_code}")
            return
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to service: {e}")
        print("💡 Make sure the service is running on the correct port")
        return
    
    # Test 1: Basic water analysis for Mumbai
    print("\n" + "=" * 60)
    print("Test 1: Basic Water Analysis - Mumbai Region")
    print("-" * 60)
    
    test_payload = {
        "roi": MUMBAI_GEOMETRY,
        "year": 2023,
        "threshold": 20,
        "include_seasonal": True
    }
    
    try:
        start_time = time.time()
        response = requests.post(
            f"{base_url}/water/analyze",
            json=test_payload,
            timeout=60
        )
        end_time = time.time()
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Water analysis completed in {end_time - start_time:.2f}s")
            print(f"🌊 Water Percentage: {result['mapStats']['water_percentage']}%")
            print(f"🏞️ Non-Water Percentage: {result['mapStats']['non_water_percentage']}%")
            print(f"📊 Total Pixels: {result['mapStats']['total_pixels']}")
            
            if 'seasonal_comparison' in result['mapStats']:
                seasonal = result['mapStats']['seasonal_comparison']
                print(f"🌧️ Monsoon Water: {seasonal['monsoon_water_pct']}%")
                print(f"☀️ Dry Season Water: {seasonal['dry_water_pct']}%")
                print(f"📈 Seasonal Variation: {seasonal['seasonal_variation']}%")
            
            print(f"🗺️ Tile URL: {result['urlFormat'][:100]}...")
            print(f"⏱️ Processing Time: {result.get('processing_time_seconds', 'N/A')}s")
            
        else:
            print(f"❌ Water analysis failed: {response.status_code}")
            print(f"Error: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
    
    # Test 2: Water analysis with different threshold
    print("\n" + "=" * 60)
    print("Test 2: Water Analysis - Different Threshold (50%)")
    print("-" * 60)
    
    test_payload_high_threshold = {
        "roi": MUMBAI_GEOMETRY,
        "year": 2023,
        "threshold": 50,  # Higher threshold for permanent water only
        "include_seasonal": False
    }
    
    try:
        start_time = time.time()
        response = requests.post(
            f"{base_url}/water/analyze",
            json=test_payload_high_threshold,
            timeout=60
        )
        end_time = time.time()
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ High threshold analysis completed in {end_time - start_time:.2f}s")
            print(f"🌊 Water Percentage (50% threshold): {result['mapStats']['water_percentage']}%")
            print(f"🏞️ Non-Water Percentage: {result['mapStats']['non_water_percentage']}%")
            print(f"📊 Threshold Used: {result['mapStats']['threshold_used']}%")
            
        else:
            print(f"❌ High threshold analysis failed: {response.status_code}")
            print(f"Error: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
    
    # Test 3: Point-based analysis
    print("\n" + "=" * 60)
    print("Test 3: Point-based Water Analysis - Mumbai City Center")
    print("-" * 60)
    
    test_payload_point = {
        "roi": MUMBAI_POINT,
        "year": 2023,
        "threshold": 20,
        "include_seasonal": True
    }
    
    try:
        start_time = time.time()
        response = requests.post(
            f"{base_url}/water/analyze",
            json=test_payload_point,
            timeout=60
        )
        end_time = time.time()
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Point analysis completed in {end_time - start_time:.2f}s")
            print(f"🌊 Water Percentage: {result['mapStats']['water_percentage']}%")
            print(f"🏞️ Non-Water Percentage: {result['mapStats']['non_water_percentage']}%")
            print(f"📊 Total Pixels: {result['mapStats']['total_pixels']}")
            
        else:
            print(f"❌ Point analysis failed: {response.status_code}")
            print(f"Error: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
    
    # Test 4: Water change analysis
    print("\n" + "=" * 60)
    print("Test 4: Water Change Analysis - Mumbai Region")
    print("-" * 60)
    
    test_payload_change = {
        "roi": MUMBAI_GEOMETRY,
        "start_year": 2020,
        "end_year": 2023,
        "threshold": 20
    }
    
    try:
        start_time = time.time()
        response = requests.post(
            f"{base_url}/water/change",
            json=test_payload_change,
            timeout=60
        )
        end_time = time.time()
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Change analysis completed in {end_time - start_time:.2f}s")
            
            if 'changeAnalysis' in result:
                change = result['changeAnalysis']
                print(f"📅 Period: {change['start_year']} - {change['end_year']}")
                print(f"🌊 Current Water: {change['current_water_pct']}%")
                print(f"📈 Change: {change['change_percentage']}%")
                print(f"📊 Direction: {change['change_direction']}")
            
        else:
            print(f"❌ Change analysis failed: {response.status_code}")
            print(f"Error: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
    
    # Test 5: Different region (Delhi)
    print("\n" + "=" * 60)
    print("Test 5: Water Analysis - Delhi Region")
    print("-" * 60)
    
    test_payload_delhi = {
        "roi": DELHI_GEOMETRY,
        "year": 2023,
        "threshold": 20,
        "include_seasonal": True
    }
    
    try:
        start_time = time.time()
        response = requests.post(
            f"{base_url}/water/analyze",
            json=test_payload_delhi,
            timeout=60
        )
        end_time = time.time()
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Delhi analysis completed in {end_time - start_time:.2f}s")
            print(f"🌊 Water Percentage: {result['mapStats']['water_percentage']}%")
            print(f"🏞️ Non-Water Percentage: {result['mapStats']['non_water_percentage']}%")
            print(f"📊 Total Pixels: {result['mapStats']['total_pixels']}")
            
            if 'seasonal_comparison' in result['mapStats']:
                seasonal = result['mapStats']['seasonal_comparison']
                print(f"🌧️ Monsoon Water: {seasonal['monsoon_water_pct']}%")
                print(f"☀️ Dry Season Water: {seasonal['dry_water_pct']}%")
            
        else:
            print(f"❌ Delhi analysis failed: {response.status_code}")
            print(f"Error: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
    
    # Test 6: Water quality information
    print("\n" + "=" * 60)
    print("Test 6: Water Quality Information")
    print("-" * 60)
    
    try:
        response = requests.get(f"{base_url}/water/quality", timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Quality information retrieved")
            print(f"📊 Dataset: {result['dataset']}")
            print(f"📏 Resolution: {result['resolution']}")
            print(f"📅 Temporal Coverage: {result['temporal_coverage']}")
            print(f"🔬 Methodology: {result['methodology']}")
            print("\n📋 Custom Thresholds:")
            for key, value in result['custom_thresholds'].items():
                print(f"  {key}: {value}%")
            
        else:
            print(f"❌ Quality info failed: {response.status_code}")
            print(f"Error: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
    
    print("\n" + "=" * 60)
    print("🌊 Water Service Testing Complete!")
    print("=" * 60)


def test_water_service_direct():
    """Test the water service directly (without FastAPI)"""
    
    print("🌊 Testing Water Service Directly")
    print("=" * 60)
    
    try:
        from services.water_service import WaterService
        
        # Initialize service
        water_service = WaterService()
        
        # Test basic analysis
        print("Test 1: Basic Water Analysis - Mumbai")
        result = water_service.analyze_water_presence(
            roi=MUMBAI_GEOMETRY,
            year=2023,
            threshold=20,
            include_seasonal=True
        )
        
        print("✅ Direct analysis completed")
        print(f"🌊 Water Percentage: {result['mapStats']['water_percentage']}%")
        print(f"🏞️ Non-Water Percentage: {result['mapStats']['non_water_percentage']}%")
        
        if 'seasonal_comparison' in result['mapStats']:
            seasonal = result['mapStats']['seasonal_comparison']
            print(f"🌧️ Monsoon Water: {seasonal['monsoon_water_pct']}%")
            print(f"☀️ Dry Season Water: {seasonal['dry_water_pct']}%")
        
        # Test change analysis
        print("\nTest 2: Water Change Analysis")
        change_result = water_service.analyze_water_change(
            roi=MUMBAI_GEOMETRY,
            start_year=2020,
            end_year=2023,
            threshold=20
        )
        
        print("✅ Change analysis completed")
        if 'changeAnalysis' in change_result:
            change = change_result['changeAnalysis']
            print(f"🌊 Current Water: {change['current_water_pct']}%")
            print(f"📈 Change: {change['change_percentage']}%")
        
        # Test quality info
        print("\nTest 3: Quality Information")
        quality_info = water_service.get_water_quality_info()
        print("✅ Quality info retrieved")
        print(f"📊 Dataset: {quality_info['dataset']}")
        print(f"📏 Resolution: {quality_info['resolution']}")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Make sure you're running from the correct directory")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "direct":
        test_water_service_direct()
    else:
        test_water_service()
