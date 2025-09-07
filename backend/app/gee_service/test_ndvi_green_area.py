#!/usr/bin/env python3
"""
Test NDVI with a more vegetated area in Mumbai (Sanjay Gandhi National Park)
"""

import ee
import requests
import math

def deg2num(lat_deg, lon_deg, zoom):
    """Convert lat/lon to tile coordinates"""
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    x = int((lon_deg + 180.0) / 360.0 * n)
    y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return (x, y)

def test_vegetated_area():
    """Test NDVI with Sanjay Gandhi National Park (more vegetation)"""
    
    # Initialize Earth Engine
    ee.Initialize(project='gee-tool-469517')
    print("✅ Earth Engine initialized")
    
    # Sanjay Gandhi National Park coordinates (more vegetation)
    park_lat = 19.2147
    park_lon = 72.9101
    
    # Create larger region around the park for better visualization
    park_point = ee.Geometry.Point([park_lon, park_lat])
    park_region = park_point.buffer(5000)  # 5km buffer (increased from 2km)
    
    print(f"\n🌳 Testing NDVI for Sanjay Gandhi National Park area")
    print(f"   Lat/Lon: {park_lat}, {park_lon}")
    
    # Get Sentinel-2 NDVI for the area
    collection = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED") \
        .filterDate('2023-01-01', '2023-12-31') \
        .filterBounds(park_region) \
        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
    
    # Calculate NDVI
    def calculate_ndvi(image):
        ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
        return image.addBands(ndvi)
    
    ndvi_collection = collection.map(calculate_ndvi)
    median_ndvi = ndvi_collection.select('NDVI').median().clip(park_region)
    
    # Adjusted visualization parameters for better contrast
    vis_params = {
        'min': -0.3,
        'max': 0.8,  # Higher max for vegetation
        'palette': [
            "#d73027",  # Very low NDVI (red)
            "#f46d43",  # Low NDVI (orange-red)
            "#fdae61",  # Low-moderate NDVI (orange)
            "#fee08b",  # Moderate NDVI (yellow)
            "#e6f598",  # Moderate-high NDVI (light green)
            "#abdda4",  # High NDVI (green)
            "#66c2a5",  # Very high NDVI (blue-green)
            "#3288bd"   # Highest NDVI (blue)
        ]
    }
    
    # Generate map ID
    map_id_info = median_ndvi.getMapId(vis_params)
    mapid = map_id_info['mapid']
    
    print(f"   Map ID: {mapid[:40]}...")
    
    # Calculate tile coordinates for this area (higher zoom = bigger vegetation areas)
    zoom = 13  # Increased from 10 to 13 for more detail
    tile_x, tile_y = deg2num(park_lat, park_lon, zoom)
    
    print(f"   Tile coordinates: z={zoom}, x={tile_x}, y={tile_y}")
    
    # Test the tile URL
    tile_url = f"https://earthengine.googleapis.com/v1/{mapid}/tiles/{zoom}/{tile_x}/{tile_y}"
    print(f"\n🔗 Tile URL: {tile_url}")
    
    try:
        response = requests.get(tile_url, timeout=10)
        print(f"\n📡 Response:")
        print(f"   Status: {response.status_code}")
        print(f"   Content-Type: {response.headers.get('content-type', 'N/A')}")
        print(f"   Content-Length: {response.headers.get('content-length', 'N/A')} bytes")
        
        if response.status_code == 200 and 'image' in response.headers.get('content-type', ''):
            print(f"   ✅ SUCCESS! NDVI tile with vegetation data!")
        else:
            print(f"   ❌ Failed or no image data")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")

if __name__ == "__main__":
    test_vegetated_area()
