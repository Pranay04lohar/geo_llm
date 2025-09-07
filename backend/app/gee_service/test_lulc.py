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

def test_lulc_service(base_url: str = "http://localhost:8000"):
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
        "confidenceThreshold": 0.3,
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
            tile_url = result.get("urlFormat", "")
            if tile_url:
                print(f"\n🗺️  Tile URL generated: ✅")
                print(f"   Complete URL: {tile_url}")
                
                # The new GEE tile URL format handles authentication internally
                print(f"   ✅ Using new GEE tile URL format (authentication handled internally)")
                
                # Create a test URL with Mumbai tile coordinates (z=10, x=719, y=456)
                test_url = tile_url.replace("{z}", "10").replace("{x}", "719").replace("{y}", "456")
                print(f"   Test URL (z=10, x=719, y=456):")
                print(f"   {test_url}")
            else:
                print(f"\n🗺️  Tile URL generated: ❌")
            
            # Display legend information
            print(f"\n🔍 DEBUG - Full response keys: {list(result.keys())}")
            print(f"🔍 DEBUG - Analysis type: {result.get('analysis_type', 'N/A')}")
            
            visualization = result.get('visualization', {})
            print(f"🔍 DEBUG - Visualization keys: {list(visualization.keys())}")
            
            legend = visualization.get('legend', {})
            print(f"🔍 DEBUG - Legend keys: {list(legend.keys()) if legend else 'No legend found'}")
            
            if legend:
                print(f"\n🎨 Legend Metadata:")
                print(f"   Title: {legend.get('title', 'N/A')}")
                print(f"   Type: {legend.get('type', 'N/A')}")
                print(f"   Description: {legend.get('description', 'N/A')}")
                print(f"   Min Value: {legend.get('min_value', 'N/A')}")
                print(f"   Max Value: {legend.get('max_value', 'N/A')}")
                
                palette = legend.get('palette', [])
                if palette:
                    print(f"   Color Palette: {len(palette)} colors")
                    print(f"   Colors: {', '.join(palette[:5])}{'...' if len(palette) > 5 else ''}")
                
                classes = legend.get('classes', [])
                if classes:
                    print(f"   Classes: {len(classes)} land cover types")
                    print(f"   Class Details:")
                    for cls in classes:
                        print(f"     - {cls.get('name', 'Unknown')}: {cls.get('color', 'N/A')} (ID: {cls.get('id', 'N/A')})")
            else:
                print(f"\n🎨 Legend Information: ❌ No legend data found")
                print(f"   Available visualization keys: {list(visualization.keys())}")
            
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
