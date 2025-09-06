#!/usr/bin/env python3
"""
Test script for polygon-based NDVI integration
Tests the complete flow: Search API -> ROI Handler -> NDVI Service
"""

import sys
import os
import json
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent
sys.path.append(str(backend_path))

def test_polygon_integration():
    """Test the complete polygon-based integration flow."""
    
    print("🧪 Testing Polygon-Based NDVI Integration")
    print("=" * 50)
    
    try:
        # Test 1: Search API Service
        print("\n1️⃣ Testing Search API Service...")
        from app.search_service.services.nominatim_client import NominatimClient
        
        nominatim_client = NominatimClient()
        search_result = nominatim_client.search_location("Bikaner")
        
        if search_result:
            print(f"✅ Search API: Found {search_result.get('administrative_info', {}).get('name', 'Unknown')}")
            print(f"   📍 Coordinates: {search_result.get('coordinates', {})}")
            print(f"   📐 Area: {search_result.get('area_km2', 0):.2f} km²")
            print(f"   🎯 Has polygon: {bool(search_result.get('polygon_geometry'))}")
            print(f"   🔄 Is tiled: {search_result.get('is_tiled', False)}")
            print(f"   📦 Tiles count: {len(search_result.get('geometry_tiles', []))}")
        else:
            print("❌ Search API: Failed to find location")
            return False
        
        # Test 2: ROI Handler
        print("\n2️⃣ Testing ROI Handler...")
        from app.services.gee.roi_handler import ROIHandler
        
        roi_handler = ROIHandler()
        
        # Create mock location data
        mock_locations = [{
            "matched_name": "Bikaner",
            "type": "city",
            "confidence": 0.9
        }]
        
        roi_data = roi_handler.extract_roi_from_locations(mock_locations)
        
        if roi_data:
            print(f"✅ ROI Handler: Created ROI data")
            print(f"   📍 Source: {roi_data.get('source', 'unknown')}")
            print(f"   🎯 Has polygon: {bool(roi_data.get('polygon_geometry'))}")
            print(f"   🔄 Is tiled: {roi_data.get('is_tiled', False)}")
            print(f"   📦 Tiles count: {len(roi_data.get('geometry_tiles', []))}")
            print(f"   📐 Area: {roi_data.get('area_km2', 0):.2f} km²")
        else:
            print("❌ ROI Handler: Failed to create ROI data")
            return False
        
        # Test 3: NDVI Service (if available)
        print("\n3️⃣ Testing NDVI Service...")
        try:
            from app.gee_service.services.ndvi_service import NDVIService
            
            # Test polygon-based analysis
            if roi_data.get("polygon_geometry"):
                print("🎯 Testing polygon-based NDVI analysis...")
                ndvi_result = NDVIService().analyze_ndvi_with_polygon(
                    roi_data=roi_data,
                    start_date="2023-06-01",
                    end_date="2023-08-31",
                    cloud_threshold=30,
                    scale=30,
                    max_pixels=1e8,
                    include_time_series=False,
                    exact_computation=False
                )
                
                if ndvi_result.get("success"):
                    print(f"✅ NDVI Service: Polygon analysis successful")
                    print(f"   📊 Analysis type: {ndvi_result.get('analysis_type', 'unknown')}")
                    print(f"   🎯 Geometry type: {ndvi_result.get('geometry_type', 'unknown')}")
                    print(f"   📐 Area: {ndvi_result.get('area_km2', 0):.2f} km²")
                    
                    if ndvi_result.get("geometry_type") == "tiled_polygon":
                        print(f"   🔄 Tiles processed: {ndvi_result.get('tiles_processed', 0)}/{ndvi_result.get('total_tiles', 0)}")
                    
                    # Show NDVI stats
                    ndvi_stats = ndvi_result.get("ndvi_stats", {})
                    if ndvi_stats:
                        print(f"   📈 NDVI Mean: {ndvi_stats.get('NDVI_mean', 0):.3f}")
                        print(f"   📈 NDVI Range: {ndvi_stats.get('NDVI_min', 0):.3f} - {ndvi_stats.get('NDVI_max', 0):.3f}")
                else:
                    print(f"❌ NDVI Service: Analysis failed - {ndvi_result.get('error', 'Unknown error')}")
                    return False
            else:
                print("⚠️ NDVI Service: No polygon geometry available, skipping test")
                return False
                
        except ImportError as e:
            print(f"⚠️ NDVI Service: Not available - {e}")
            return False
        except Exception as e:
            print(f"❌ NDVI Service: Error - {e}")
            return False
        
        print("\n🎉 All tests passed! Polygon-based integration is working.")
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_polygon_integration()
    sys.exit(0 if success else 1)
