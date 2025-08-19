"""
Google Earth Engine Authentication Test

This script tests GEE authentication and basic functionality.
Run this to verify your GEE setup before running the full workflow.
"""

import sys
import os

# Add project to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
sys.path.insert(0, project_root)

def test_gee_import():
    """Test if Google Earth Engine can be imported."""
    print("🧪 Testing Google Earth Engine import...")
    
    try:
        import ee
        print("✅ Google Earth Engine imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Failed to import Google Earth Engine: {e}")
        return False

def test_gee_authentication():
    """Test Google Earth Engine authentication."""
    print("\n🧪 Testing Google Earth Engine authentication...")
    
    try:
        import ee
        
        # Try to authenticate
        try:
            ee.Initialize()
            print("✅ Google Earth Engine authenticated successfully")
            return True
        except Exception as auth_error:
            print(f"❌ Authentication failed: {auth_error}")
            print("\n💡 To authenticate Google Earth Engine:")
            print("   1. Install the Earth Engine CLI: pip install earthengine-api")
            print("   2. Authenticate: earthengine authenticate")
            print("   3. Or set up service account credentials")
            return False
            
    except ImportError:
        print("❌ Google Earth Engine not available")
        return False

def test_basic_gee_operation():
    """Test a basic Google Earth Engine operation."""
    print("\n🧪 Testing basic Google Earth Engine operation...")
    
    try:
        import ee
        
        # Simple test: get image information
        image = ee.Image('LANDSAT/LC08/C02/T1_L2/LC08_044034_20140318')
        info = image.getInfo()
        
        print("✅ Successfully retrieved Landsat image info")
        print(f"   Image ID: {info.get('id', 'Unknown')}")
        print(f"   Bands: {len(info.get('bands', []))}")
        return True
        
    except Exception as e:
        print(f"❌ Basic GEE operation failed: {e}")
        return False

def test_gee_client():
    """Test our custom GEE client."""
    print("\n🧪 Testing custom GEE client...")
    
    try:
        from backend.app.services.gee.gee_client import GEEClient
        
        client = GEEClient()
        
        # Test initialization
        init_success = client.initialize()
        print(f"   Initialization: {'✅ Success' if init_success else '❌ Failed'}")
        
        # Test connection
        if init_success:
            conn_success = client.test_connection()
            print(f"   Connection test: {'✅ Success' if conn_success else '❌ Failed'}")
        
        # Print client info
        info = client.get_info()
        print(f"   Client info: {info}")
        
        return init_success
        
    except Exception as e:
        print(f"❌ GEE client test failed: {e}")
        return False

def test_geocoding():
    """Test geocoding functionality."""
    print("\n🧪 Testing geocoding functionality...")
    
    try:
        from backend.app.services.gee.roi_handler import ROIHandler
        
        handler = ROIHandler()
        
        # Test location extraction
        test_locations = [
            {"matched_name": "Mumbai", "type": "city", "confidence": 95}
        ]
        
        roi = handler.extract_roi_from_locations(test_locations)
        
        if roi:
            print("✅ ROI extraction successful")
            print(f"   Location: {roi.get('primary_location', {}).get('name')}")
            print(f"   Source: {roi.get('source')}")
            print(f"   Geocoder type: {getattr(handler, 'geocoder_type', 'unknown')}")
            return True
        else:
            print("❌ ROI extraction failed")
            return False
            
    except Exception as e:
        print(f"❌ Geocoding test failed: {e}")
        return False

def main():
    """Run all authentication tests."""
    print("🚀 Google Earth Engine Setup Tests\n")
    
    tests = [
        test_gee_import,
        test_gee_authentication,
        test_basic_gee_operation,
        test_gee_client,
        test_geocoding
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            results.append(False)
    
    print("\n" + "="*60)
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! GEE is ready for use.")
    elif passed >= 3:
        print(f"⚠️ {passed}/{total} tests passed. Basic functionality available.")
    else:
        print(f"❌ {passed}/{total} tests passed. GEE setup needs attention.")
        
    print("\n📋 Authentication Status:")
    if results[1]:  # Authentication test
        print("   ✅ GEE Authentication: Working")
    else:
        print("   ❌ GEE Authentication: Failed")
        print("   💡 Run: earthengine authenticate")
        
    print("="*60)
    
    return passed >= 3

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
