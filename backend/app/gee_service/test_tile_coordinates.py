#!/usr/bin/env python3
"""
Test GEE tile URLs with real coordinates for Mumbai
"""

import requests
import math

def deg2num(lat_deg, lon_deg, zoom):
    """Convert lat/lon to tile coordinates"""
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    x = int((lon_deg + 180.0) / 360.0 * n)
    y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return (x, y)

def test_tile_url():
    """Test tile URL with real Mumbai coordinates"""
    
    # Mumbai coordinates
    mumbai_lat = 19.0760
    mumbai_lon = 72.8777
    zoom = 10
    
    # Convert to tile coordinates
    tile_x, tile_y = deg2num(mumbai_lat, mumbai_lon, zoom)
    
    print(f"🏙️  Testing tile URL for Mumbai")
    print(f"   Lat/Lon: {mumbai_lat}, {mumbai_lon}")
    print(f"   Zoom: {zoom}")
    print(f"   Tile coordinates: x={tile_x}, y={tile_y}")
    
    # Use the fresh tile URL from the recent LULC test
    base_url = "https://earthengine.googleapis.com/v1/projects/gee-tool-469517/maps/43e1ee9cdb1b9f273bc1f0015066a68b-fbd734f8a4a0bfd5ed2959d6f7afc0f4/tiles"
    tile_url = f"{base_url}/{tile_y}/{zoom}/{tile_x}"
    
    print(f"\n🔗 Real tile URL:")
    print(f"   {tile_url}")
    
    # Test if the URL responds (should return image data, not JSON error)
    try:
        response = requests.head(tile_url, timeout=10)
        print(f"\n📡 Response:")
        print(f"   Status: {response.status_code}")
        print(f"   Content-Type: {response.headers.get('content-type', 'N/A')}")
        
        if response.status_code == 200:
            print(f"   ✅ Tile URL is working! (Returns image data)")
        else:
            print(f"   ⚠️  Status {response.status_code} - may be expired or invalid coordinates")
            
    except Exception as e:
        print(f"   ❌ Request failed: {e}")

if __name__ == "__main__":
    test_tile_url()
