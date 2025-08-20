"""
Test Google Geocoding API After Enabling

Check if the Geocoding API is now working properly after being enabled.
"""

import sys
import os
import time
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_geocoding_after_enable():
    """Test if Google Geocoding API is working after being enabled."""
    
    print("🧪 TESTING GEOCODING API AFTER ENABLING")
    print("=" * 60)
    
    try:
        from dotenv import load_dotenv
        load_dotenv('backend/.env')
        
        # Check API key status
        api_key = os.environ.get('GOOGLE_MAPS_API_KEY')
        print(f"API Key: {'✅ Found' if api_key else '❌ Missing'}")
        
        # Test ROI handler configuration
        from backend.app.services.gee.roi_handler import ROIHandler
        
        roi_handler = ROIHandler()
        print(f"Geocoder type: {getattr(roi_handler, 'geocoder_type', 'unknown')}")
        print(f"Geocoder available: {roi_handler.geocoder is not None}")
        
        # Test direct geocoding first
        print(f"\n📡 Direct Geocoding Test:")
        print("-" * 30)
        
        try:
            from geopy.geocoders import GoogleV3
            from geopy.exc import GeocoderServiceError
            
            geocoder = GoogleV3(api_key=api_key)
            
            # Test simple location
            location = geocoder.geocode("Mumbai", timeout=10)
            if location:
                print(f"✅ Direct Google geocoding works!")
                print(f"   Mumbai: {location.address}")
                print(f"   Coordinates: ({location.latitude:.4f}, {location.longitude:.4f})")
            else:
                print("❌ Direct geocoding returned no results")
                
        except GeocoderServiceError as e:
            print(f"❌ Geocoding API error: {str(e)}")
            if "not authorized" in str(e).lower():
                print("   → Geocoding API might still not be enabled")
            return False
        except Exception as e:
            print(f"❌ Unexpected error: {str(e)}")
            return False
        
        # Test global locations through ROI handler
        print(f"\n🌍 ROI Handler Global Location Test:")
        print("-" * 40)
        
        test_locations = [
            {
                "name": "Paris", 
                "data": {"matched_name": "Paris", "type": "city", "confidence": 90},
                "expected_lat_range": (48, 49),
                "expected_lng_range": (2, 3)
            },
            {
                "name": "Tokyo", 
                "data": {"matched_name": "Tokyo", "type": "city", "confidence": 90},
                "expected_lat_range": (35, 36),
                "expected_lng_range": (139, 140)
            },
            {
                "name": "New York", 
                "data": {"matched_name": "New York", "type": "city", "confidence": 90},
                "expected_lat_range": (40, 41),
                "expected_lng_range": (-75, -73)
            },
            {
                "name": "Mumbai", 
                "data": {"matched_name": "Mumbai", "type": "city", "confidence": 90},
                "expected_lat_range": (19, 20),
                "expected_lng_range": (72, 73)
            },
            {
                "name": "London", 
                "data": {"matched_name": "London", "type": "city", "confidence": 90},
                "expected_lat_range": (51, 52),
                "expected_lng_range": (-1, 1)
            }
        ]
        
        success_count = 0
        total_count = len(test_locations)
        
        for location_test in test_locations:
            location_name = location_test["name"]
            location_data = location_test["data"]
            expected_lat = location_test["expected_lat_range"]
            expected_lng = location_test["expected_lng_range"]
            
            start_time = time.time()
            result = roi_handler.extract_roi_from_locations([location_data])
            elapsed_ms = (time.time() - start_time) * 1000
            
            if result and result.get("primary_location"):
                lat = result["primary_location"]["lat"]
                lng = result["primary_location"]["lng"]
                
                # Check if coordinates are reasonable
                lat_correct = expected_lat[0] <= lat <= expected_lat[1]
                lng_correct = expected_lng[0] <= lng <= expected_lng[1]
                
                if lat_correct and lng_correct:
                    print(f"  ✅ {location_name}: ({lat:.2f}, {lng:.2f}) - {elapsed_ms:.0f}ms")
                    success_count += 1
                else:
                    print(f"  ❌ {location_name}: ({lat:.2f}, {lng:.2f}) - Wrong location")
            else:
                print(f"  ❌ {location_name}: Failed to geocode")
        
        # Performance and accuracy summary
        accuracy = (success_count / total_count) * 100
        print(f"\n📊 Results Summary:")
        print(f"   Accuracy: {success_count}/{total_count} ({accuracy:.1f}%)")
        print(f"   Geocoder: {roi_handler.geocoder_type}")
        
        if accuracy >= 80:
            print("🎉 EXCELLENT: Google Geocoding API working properly!")
        elif accuracy >= 60:
            print("✅ GOOD: Most locations working correctly")
        else:
            print("⚠️ POOR: Geocoding accuracy low, check API setup")
        
        # Test edge cases
        print(f"\n🔧 Edge Case Tests:")
        print("-" * 20)
        
        # Test invalid location
        invalid_result = roi_handler.extract_roi_from_locations([
            {"matched_name": "NonExistentCity12345", "type": "city", "confidence": 80}
        ])
        
        if invalid_result is None:
            print("  ✅ Properly handles invalid locations (returns None)")
        else:
            print("  ⚠️ Invalid location returned result (might be issue)")
        
        # Test fallback
        fallback = roi_handler.get_default_roi()
        fallback_name = fallback.get("primary_location", {}).get("name", "Unknown")
        print(f"  Default fallback: {fallback_name}")
        
        return accuracy >= 60
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_geocoding_after_enable()
    
    print(f"\n📋 FINAL ASSESSMENT:")
    if success:
        print("   🎉 Geocoding API enabled successfully!")
        print("   🌍 ROI Handler ready for global deployment")
        print("   🚀 Production readiness improved significantly")
    else:
        print("   ⚠️ Issues remain with geocoding setup")
        print("   🔧 Check Google Cloud Console API settings")
