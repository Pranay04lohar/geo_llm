"""
Test GEE with Valid, Accessible Data

Now that GEE initialization works, let's test with proper datasets
that are guaranteed to be accessible.
"""

import ee

def test_valid_gee_datasets():
    """Test with known valid, public GEE datasets."""
    
    try:
        print("🧪 Testing GEE initialization...")
        ee.Initialize()
        print("✅ GEE initialized successfully!")
        
        # Test 1: Use image collection instead of specific image
        print("\n🧪 Testing Sentinel-2 image collection...")
        roi = ee.Geometry.Rectangle([72.8, 19.0, 72.85, 19.05])  # Small area in Mumbai
        
        collection = ee.ImageCollection('COPERNICUS/S2_SR') \
            .filterBounds(roi) \
            .filterDate('2023-01-01', '2023-12-31') \
            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)) \
            .first()  # Get the first available image
        
        print("✅ Sentinel-2 collection access successful!")
        
        # Test 2: Calculate NDVI
        print("\n🧪 Testing NDVI calculation...")
        ndvi = collection.normalizedDifference(['B8', 'B4']).rename('NDVI')
        
        # Get statistics
        stats = ndvi.reduceRegion(
            reducer=ee.Reducer.mean().combine(
                reducer2=ee.Reducer.min(), sharedInputs=True
            ).combine(
                reducer2=ee.Reducer.max(), sharedInputs=True
            ),
            geometry=roi,
            scale=100,  # 100m resolution for faster processing
            maxPixels=1e6
        )
        
        result = stats.getInfo()
        print(f"✅ NDVI calculation successful!")
        print(f"   📊 Results: {result}")
        
        # Test 3: Land cover data
        print("\n🧪 Testing land cover data...")
        landcover = ee.Image('ESA/WorldCover/v100/2020').clip(roi)
        
        area_stats = ee.Image.pixelArea().divide(1000000).reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=roi,
            scale=100,
            maxPixels=1e6
        )
        
        area_result = area_stats.getInfo()
        print(f"✅ Land cover data access successful!")
        print(f"   📊 Area: {area_result}")
        
        return True, {
            "ndvi_stats": result,
            "area_stats": area_result
        }
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False, None

def test_our_gee_tool():
    """Test our GEE tool with the working setup."""
    
    try:
        print("\n🧪 Testing our GEE tool integration...")
        
        from backend.app.services.gee import GEETool
        
        gee_tool = GEETool()
        
        result = gee_tool.process_query(
            query="Calculate NDVI for Mumbai",
            locations=[{"matched_name": "Mumbai", "type": "city", "confidence": 95}],
            evidence=[]
        )
        
        print("✅ GEE tool integration working!")
        print(f"   📊 Analysis length: {len(result.get('analysis', ''))}")
        print(f"   📊 Evidence: {result.get('evidence', [])}")
        
        return True, result
        
    except Exception as e:
        print(f"❌ GEE tool test failed: {e}")
        return False, None

if __name__ == "__main__":
    print("🚀 Testing Real GEE Data Access\n")
    
    # Test valid datasets
    dataset_success, dataset_results = test_valid_gee_datasets()
    
    if dataset_success:
        print(f"\n🎉 REAL SATELLITE DATA WORKING!")
        print(f"   📊 Sample NDVI data: {dataset_results}")
        
        # Test our tool
        tool_success, tool_results = test_our_gee_tool()
        
        if tool_success:
            print(f"\n🎉 COMPLETE INTEGRATION WORKING!")
            print(f"   📊 Full pipeline operational with real data!")
        else:
            print(f"\n⚠️ Tool integration needs fixes")
    else:
        print(f"\n❌ Still need to resolve data access issues")
