"""
Debug Google Earth Engine Initialization

This script tries different ways to initialize GEE to find what works.
"""

import ee

def test_initialization_methods():
    """Try different GEE initialization methods."""
    
    methods = [
        ("Default ee.Initialize()", lambda: ee.Initialize()),
        ("With default project", lambda: ee.Initialize(project='earthengine-legacy')),
        ("With cloud project", lambda: ee.Initialize(project='ee-project')),
        ("Force legacy", lambda: ee.Initialize(opt_url='https://earthengine.googleapis.com')),
    ]
    
    for name, init_func in methods:
        try:
            print(f"\n🧪 Trying: {name}")
            init_func()
            print(f"✅ SUCCESS: {name} worked!")
            
            # Test with a simple operation
            image = ee.Image('COPERNICUS/S2_SR/20230315T050701_20230315T051543_T43QGD')
            print("✅ Image access successful")
            
            # Test computation
            roi = ee.Geometry.Rectangle([72.8, 19.0, 72.85, 19.05])
            ndvi = image.normalizedDifference(['B8', 'B4'])
            stats = ndvi.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=roi,
                scale=100,
                maxPixels=1e6
            )
            result = stats.getInfo()
            print(f"✅ COMPUTATION SUCCESS: {result}")
            return True, name
            
        except Exception as e:
            print(f"❌ Failed: {e}")
            
    return False, None

if __name__ == "__main__":
    print("🚀 Debugging Google Earth Engine Initialization\n")
    
    success, working_method = test_initialization_methods()
    
    if success:
        print(f"\n🎉 SOLUTION FOUND: {working_method}")
        print("We can now use real GEE data!")
    else:
        print("\n❌ No working initialization method found.")
        print("Need to set up Google Cloud project or check authentication.")
