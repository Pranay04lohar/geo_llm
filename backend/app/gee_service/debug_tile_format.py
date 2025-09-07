# #!/usr/bin/env python3
# """
# Debug the correct tile URL format for Google Earth Engine
# """

# import ee
# import requests

# def test_different_formats():
#     """Test different tile URL formats to find the working one"""
    
#     # Initialize Earth Engine
#     ee.Initialize(project='gee-tool-469517')
#     print("✅ Earth Engine initialized")
    
#     # Create a simple test image for Mumbai area
#     mumbai_point = ee.Geometry.Point([72.8777, 19.0760])
#     mumbai_region = mumbai_point.buffer(10000)  # 10km buffer
    
#     # Get a simple image (MODIS NDVI)
#     image = ee.Image("MODIS/006/MOD13A1/2023_01_01").select('NDVI').clip(mumbai_region)
    
#     # Visualization parameters
#     vis_params = {
#         'min': 0,
#         'max': 8000,
#         'palette': ['red', 'yellow', 'green']
#     }
    
#     # Get map ID
#     map_id_info = image.getMapId(vis_params)
#     print(f"Map ID Info: {map_id_info}")
    
#     # Test different URL formats
#     mapid = map_id_info['mapid']
    
#     # CORRECT coordinate order: {z}/{x}/{y} not {y}/{z}/{x}
#     z, x, y = 10, 719, 456
    
#     formats_to_test = [
#         f"https://earthengine.googleapis.com/v1/{mapid}/tiles/{z}/{x}/{y}",  # CORRECTED ORDER
#         f"https://earthengine.googleapis.com/v1/{mapid}/tiles/0/0/0",  # Base tile test
#     ]
    
#     print(f"\n🧪 Testing different tile URL formats:")
#     for i, url in enumerate(formats_to_test, 1):
#         print(f"\nFormat {i}: {url}")
#         try:
#             response = requests.head(url, timeout=5)
#             print(f"   Status: {response.status_code}")
#             print(f"   Content-Type: {response.headers.get('content-type', 'N/A')}")
#             if response.status_code == 200:
#                 print(f"   ✅ SUCCESS!")
#             else:
#                 print(f"   ❌ Failed")
#         except Exception as e:
#             print(f"   ❌ Error: {e}")
    
#     # Also test the ee.data.getTileUrl method we saw in debug earlier
#     print(f"\n🔍 Testing ee.data.getTileUrl method:")
#     try:
#         direct_tile_url = ee.data.getTileUrl(map_id_info, 10, 719, 456)
#         print(f"Direct tile URL: {direct_tile_url}")
        
#         response = requests.head(direct_tile_url, timeout=5)
#         print(f"Status: {response.status_code}")
#         print(f"Content-Type: {response.headers.get('content-type', 'N/A')}")
#         if response.status_code == 200:
#             print(f"✅ ee.data.getTileUrl works!")
        
#     except Exception as e:
#         print(f"❌ ee.data.getTileUrl error: {e}")

# if __name__ == "__main__":
#     test_different_formats()


#!/usr/bin/env python3
"""
Corrected script to debug Google Earth Engine tile URLs.

This version fixes the issue by creating a robust, cloud-free composite image
instead of relying on a single, potentially masked image from one date.
"""

import ee
import requests

def test_tile_url_with_composite():
    """
    Tests the GEE tile URL using a reliable median composite image.
    """
    try:
        # Initialize Earth Engine with your project
        ee.Initialize(project='gee-tool-469517')
        print("✅ Earth Engine initialized")

        # Define the area of interest (Mumbai)
        mumbai_point = ee.Geometry.Point([72.8777, 19.0760])
        mumbai_region = mumbai_point.buffer(10000)  # 10km buffer

        # --- THE FIX: Create a cloud-free composite ---
        # 1. Get the MODIS NDVI image collection for a whole year.
        # 2. Filter it to your area of interest.
        # 3. Use .median() to create a single, cloud-free image from the collection.
        print("\n🔄 Creating a robust, cloud-free median composite for the year 2023...")
        image_collection = ee.ImageCollection("MODIS/006/MOD13A1").filterDate('2023-01-01', '2023-12-31')
        image = image_collection.select('NDVI').median().clip(mumbai_region)
        print("✅ Composite image created.")

        # Define visualization parameters for NDVI
        vis_params = {
            'min': 0,
            'max': 8000,
            'palette': ['red', 'yellow', 'green']
        }

        # Get the map ID for our new, valid image
        map_id_info = image.getMapId(vis_params)
        mapid = map_id_info['mapid']
        print(f"\n🗺️  Generated Map ID: {mapid[:40]}...")

        # Tile coordinates to test (z, x, y)
        # These coordinates should now overlap with the Mumbai region
        z, x, y = 10, 719, 456

        # Construct the correct URL
        url_to_test = f"https://earthengine.googleapis.com/v1/{mapid}/tiles/{z}/{x}/{y}"

        print(f"\n🧪 Testing correct tile URL format:")
        print(f"   URL: {url_to_test}")

        # Use requests.get() to see the actual content, not just headers
        response = requests.get(url_to_test, timeout=10)

        print(f"   Status: {response.status_code}")
        print(f"   Content-Type: {response.headers.get('content-type', 'N/A')}")

        if response.status_code == 200 and 'image' in response.headers.get('content-type', ''):
            print("\n🎉 SUCCESS! Tile fetched correctly. It is a valid image.")
        else:
            print(f"\n❌ FAILED. Status was {response.status_code}. The tile may not contain data or there could be another issue.")
            print(f"   If it still fails, try different x,y,z coordinates that are guaranteed to be over Mumbai.")

    except ee.EEException as e:
        print(f"A Google Earth Engine error occurred: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    test_tile_url_with_composite()
