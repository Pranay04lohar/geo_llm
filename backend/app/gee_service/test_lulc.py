#!/usr/bin/env python3
"""
Test script for the new LULC FastAPI service
Tests the performance-optimized, tile-first approach
"""

import json
import time
import requests
from typing import Dict, Any

# Test ROI: Mumbai region (same as used in original tests)
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

def test_lulc_service(base_url: str = "http://localhost:8001"):
    """Test the LULC Dynamic World endpoint"""
    
    print("🚀 Testing LULC FastAPI Service")
    print("=" * 50)
    
    # Test health check first
    try:
        health_response = requests.get(f"{base_url}/health")
        health_data = health_response.json()
        print(f"Health Check: {health_data}")
        
        if not health_data.get("gee_initialized", False):
            print("❌ GEE not initialized. Please check authentication.")
            return
            
    except Exception as e:
        print(f"❌ Failed to connect to service: {e}")
        return
    
    # Prepare LULC request
    lulc_request = {
        "geometry": MUMBAI_GEOMETRY,
        "startDate": "2023-01-01",
        "endDate": "2023-12-31",
        "confidenceThreshold": 0.5,
        "scale": 10,
        "maxPixels": 1e13
    }
    
    print(f"\n🗺️  Testing LULC analysis for Mumbai region...")
    print(f"ROI: {MUMBAI_GEOMETRY['type']}")
    
    start_time = time.time()
    
    try:
        # Call the LULC endpoint
        response = requests.post(
            f"{base_url}/lulc/dynamic-world",
            json=lulc_request,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            processing_time = time.time() - start_time
            
            print(f"\n✅ LULC Analysis Successful!")
            print(f"⏱️  Total time (including HTTP): {processing_time:.2f}s")
            print(f"⏱️  GEE processing time: {result.get('processing_time_seconds', 0)}s")
            print(f"📊 ROI area: {result.get('roi_area_km2', 0)} km²")
            
            # Display class statistics
            map_stats = result.get('mapStats', {})
            class_percentages = map_stats.get('class_percentages', {})
            
            print(f"\n📈 Land Cover Distribution:")
            for class_name, percentage in sorted(class_percentages.items(), key=lambda x: x[1], reverse=True):
                print(f"   {class_name}: {percentage}%")
            
            print(f"\n🌍 Dominant class: {map_stats.get('dominant_class', 'Unknown')}")
            
            # Display tile URL info
            tile_url = result.get('urlFormat', '')
            if tile_url:
                print(f"\n🗺️  Tile URL generated: ✅")
                print(f"   URL pattern: {tile_url[:80]}...")
            
            # Display datasets used
            datasets = result.get('datasets_used', [])
            print(f"\n📚 Datasets used: {', '.join(datasets)}")
            
            print(f"\n🎯 Performance vs. Old Approach:")
            print(f"   Old approach: ~100+ seconds")
            print(f"   New approach: ~{result.get('processing_time_seconds', 0)}s")
            print(f"   Speedup: ~{100 / max(result.get('processing_time_seconds', 1), 1):.1f}x faster!")
            
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")

def main():
    """Run the test"""
    print("LULC Service Performance Test")
    print("Testing tile-first, histogram-based approach")
    print("\nMake sure to start the service first:")
    print("cd backend/gee_service")
    print("uvicorn main:app --reload --port 8000")
    print()
    
    test_lulc_service()

if __name__ == "__main__":
    main()
