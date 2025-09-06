#!/usr/bin/env python3
"""
Test LocationResponse model directly to isolate validation issues
"""

import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent
sys.path.append(str(backend_path))

def test_location_response_model():
    """Test LocationResponse model with sample data."""
    
    print("🧪 Testing LocationResponse Model Directly")
    print("=" * 50)
    
    try:
        from app.search_service.models import LocationResponse
        
        # Sample data that should work
        sample_data = {
            "coordinates": {"lat": 28.1161617, "lng": 73.110567},
            "boundaries": None,
            "area_km2": 33682.05,
            "population": None,
            "administrative_info": {
                "name": "Bikaner, Rajasthan, India",
                "type": "administrative",
                "country": "India",
                "state": "Rajasthan",
                "city": "Bikaner"
            },
            "sources": [{
                "title": "OpenStreetMap Nominatim",
                "url": "https://nominatim.openstreetmap.org",
                "score": 1.0
            }],
            "polygon_geometry": {
                "type": "Polygon",
                "coordinates": [[[73.1, 28.1], [73.2, 28.1], [73.2, 28.2], [73.1, 28.2], [73.1, 28.1]]]
            },
            "geometry_tiles": [{
                "type": "Polygon",
                "coordinates": [[[73.1, 28.1], [73.2, 28.1], [73.2, 28.2], [73.1, 28.2], [73.1, 28.1]]]
            }],
            "bounding_box": {
                "west": 73.1,
                "east": 73.2,
                "south": 28.1,
                "north": 28.2
            },
            "is_tiled": True,
            "is_fallback": False,
            "success": True,
            "error": None
        }
        
        print("🔍 Testing with sample data:")
        print(f"   polygon_geometry: {bool(sample_data.get('polygon_geometry'))}")
        print(f"   geometry_tiles: {len(sample_data.get('geometry_tiles', []))}")
        print(f"   bounding_box: {bool(sample_data.get('bounding_box'))}")
        print(f"   is_tiled: {sample_data.get('is_tiled')}")
        print(f"   is_fallback: {sample_data.get('is_fallback')}")
        
        # Test creating LocationResponse
        try:
            response = LocationResponse(**sample_data)
            print("✅ LocationResponse created successfully!")
            
            # Check the response fields
            response_dict = response.dict()
            print(f"\n🔍 Response contains:")
            print(f"   polygon_geometry: {bool(response_dict.get('polygon_geometry'))}")
            print(f"   geometry_tiles: {len(response_dict.get('geometry_tiles', []))}")
            print(f"   bounding_box: {bool(response_dict.get('bounding_box'))}")
            print(f"   is_tiled: {response_dict.get('is_tiled')}")
            print(f"   is_fallback: {response_dict.get('is_fallback')}")
            
            return True
            
        except Exception as e:
            print(f"❌ LocationResponse creation failed: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False

if __name__ == "__main__":
    test_location_response_model()
