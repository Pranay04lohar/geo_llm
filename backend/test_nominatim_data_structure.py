#!/usr/bin/env python3
"""
Test LocationResponse with actual Nominatim client data structure
"""

import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent
sys.path.append(str(backend_path))

def test_with_nominatim_data():
    """Test LocationResponse with actual Nominatim client data."""
    
    print("🧪 Testing LocationResponse with Nominatim Client Data")
    print("=" * 60)
    
    try:
        from app.search_service.models import LocationResponse
        from app.search_service.services.nominatim_client import NominatimClient
        
        # Get actual data from Nominatim client
        nominatim_client = NominatimClient()
        nominatim_data = nominatim_client.search_location("Bikaner")
        
        if not nominatim_data:
            print("❌ No data from Nominatim client")
            return False
        
        print("🔍 Nominatim client data structure:")
        print(f"   Keys: {list(nominatim_data.keys())}")
        print(f"   polygon_geometry: {bool(nominatim_data.get('polygon_geometry'))}")
        print(f"   geometry_tiles: {len(nominatim_data.get('geometry_tiles', []))}")
        print(f"   bounding_box: {bool(nominatim_data.get('bounding_box'))}")
        print(f"   is_tiled: {nominatim_data.get('is_tiled')}")
        print(f"   is_fallback: {nominatim_data.get('is_fallback')}")
        
        # Map the data exactly like the Search API service does
        response_data = {
            "coordinates": nominatim_data.get("coordinates", {"lat": 0.0, "lng": 0.0}),
            "boundaries": None,  # Not used in new format
            "area_km2": nominatim_data.get("area_km2"),
            "population": nominatim_data.get("population"),
            "administrative_info": nominatim_data.get("administrative_info"),
            "sources": nominatim_data.get("sources", []),
            "polygon_geometry": nominatim_data.get("polygon_geometry"),
            "geometry_tiles": nominatim_data.get("geometry_tiles", []),
            "bounding_box": nominatim_data.get("bounding_box"),
            "is_tiled": nominatim_data.get("is_tiled", False),
            "is_fallback": nominatim_data.get("is_fallback", False),
            "success": True,
            "error": None
        }
        
        print(f"\n🔍 Mapped response_data:")
        print(f"   polygon_geometry: {bool(response_data.get('polygon_geometry'))}")
        print(f"   geometry_tiles: {len(response_data.get('geometry_tiles', []))}")
        print(f"   bounding_box: {bool(response_data.get('bounding_box'))}")
        print(f"   is_tiled: {response_data.get('is_tiled')}")
        print(f"   is_fallback: {response_data.get('is_fallback')}")
        
        # Test creating LocationResponse with this data
        try:
            response = LocationResponse(**response_data)
            print("✅ LocationResponse created successfully!")
            
            # Check the response fields
            response_dict = response.model_dump()  # Use model_dump instead of dict()
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
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_with_nominatim_data()
