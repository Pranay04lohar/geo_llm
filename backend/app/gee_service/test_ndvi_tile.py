#!/usr/bin/env python3
"""
Quick test of NDVI tile with corrected coordinates
"""

import requests

def test_ndvi_tile():
    """Test NDVI tile URL with Mumbai coordinates"""
    
    # Use the latest NDVI tile URL from the test output
    base_url = "https://earthengine.googleapis.com/v1/projects/gee-tool-469517/maps/f8755e766f32bbc09a2c162d2134e39a-76d572405e2c30b04615eabb6eeab987/tiles"
    
    # Test both coordinate sets
    test_coords = [
        (10, 512, 384, "Germany (old wrong coordinates)"),
        (10, 719, 456, "Mumbai (corrected coordinates)")
    ]
    
    for z, x, y, description in test_coords:
        tile_url = f"{base_url}/{z}/{x}/{y}"
        print(f"\n🧪 Testing {description}:")
        print(f"   URL: {tile_url}")
        
        try:
            response = requests.get(tile_url, timeout=10)
            print(f"   Status: {response.status_code}")
            print(f"   Content-Type: {response.headers.get('content-type', 'N/A')}")
            print(f"   Content-Length: {response.headers.get('content-length', 'N/A')} bytes")
            
            if response.status_code == 200:
                if 'image' in response.headers.get('content-type', ''):
                    print(f"   ✅ SUCCESS: Valid image tile!")
                else:
                    print(f"   ⚠️  WARNING: 200 OK but not an image")
            else:
                print(f"   ❌ FAILED: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ ERROR: {e}")

if __name__ == "__main__":
    test_ndvi_tile()
