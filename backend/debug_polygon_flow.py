#!/usr/bin/env python3
"""
Comprehensive debugging script to track polygon geometry through the entire flow
"""

import sys
import json
import requests
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent
sys.path.append(str(backend_path))

def debug_step(step_name, data, check_fields=None):
    """Debug helper to print step information."""
    print(f"\n{'='*60}")
    print(f"🔍 STEP: {step_name}")
    print(f"{'='*60}")
    
    if data is None:
        print("❌ Data is None")
        return False
    
    if isinstance(data, dict):
        print(f"📊 Data type: dict with {len(data)} keys")
        if check_fields:
            print(f"🎯 Checking fields: {check_fields}")
            for field in check_fields:
                if field in data:
                    value = data[field]
                    if isinstance(value, (dict, list)) and value:
                        print(f"   ✅ {field}: {type(value).__name__} (length: {len(value)})")
                    else:
                        print(f"   ✅ {field}: {value}")
                else:
                    print(f"   ❌ {field}: MISSING")
        else:
            print(f"📋 Available keys: {list(data.keys())}")
    else:
        print(f"📊 Data type: {type(data)}")
        print(f"📋 Data: {data}")
    
    return True

def test_polygon_flow():
    """Test the complete polygon geometry flow."""
    
    print("🧪 COMPREHENSIVE POLYGON GEOMETRY FLOW DEBUG")
    print("=" * 80)
    
    # Step 1: Test Nominatim Client Directly
    print("\n1️⃣ TESTING NOMINATIM CLIENT DIRECTLY")
    try:
        from app.search_service.services.nominatim_client import NominatimClient
        nominatim_client = NominatimClient()
        nominatim_data = nominatim_client.search_location("Jaipur")
        
        debug_step("Nominatim Client Direct", nominatim_data, 
                  ['polygon_geometry', 'geometry_tiles', 'bounding_box', 'is_tiled', 'is_fallback'])
        
        if not nominatim_data or not nominatim_data.get('polygon_geometry'):
            print("❌ Nominatim client failed - stopping here")
            return False
            
    except Exception as e:
        print(f"❌ Nominatim client error: {e}")
        return False
    
    # Step 2: Test Search API Service Endpoint
    print("\n2️⃣ TESTING SEARCH API SERVICE ENDPOINT")
    try:
        response = requests.post(
            "http://localhost:8001/search/location-data",
            json={
                "location_name": "Jaipur",
                "location_type": "city"
            },
            timeout=15
        )
        
        if response.status_code == 200:
            search_api_data = response.json()
            debug_step("Search API Service Response", search_api_data,
                      ['polygon_geometry', 'geometry_tiles', 'bounding_box', 'is_tiled', 'is_fallback'])
        else:
            print(f"❌ Search API failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Search API error: {e}")
        return False
    
    # Step 3: Test ROI Handler
    print("\n3️⃣ TESTING ROI HANDLER")
    try:
        from app.services.gee.roi_handler import ROIHandler
        roi_handler = ROIHandler()
        
        # Create mock location data
        mock_locations = [{
            "matched_name": "Jaipur",
            "type": "city",
            "confidence": 0.9
        }]
        
        roi_data = roi_handler.extract_roi_from_locations(mock_locations)
        debug_step("ROI Handler Result", roi_data,
                  ['polygon_geometry', 'geometry_tiles', 'bounding_box', 'is_tiled', 'is_fallback'])
        
        if not roi_data:
            print("❌ ROI Handler failed - stopping here")
            return False
            
    except Exception as e:
        print(f"❌ ROI Handler error: {e}")
        return False
    
    # Step 4: Test NDVI Service (if available)
    print("\n4️⃣ TESTING NDVI SERVICE")
    try:
        from app.gee_service.services.ndvi_service import NDVIService
        
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
            
            debug_step("NDVI Service Result", ndvi_result,
                      ['success', 'analysis_type', 'geometry_type', 'area_km2'])
        else:
            print("⚠️ No polygon geometry available for NDVI testing")
            
    except Exception as e:
        print(f"❌ NDVI Service error: {e}")
        import traceback
        traceback.print_exc()
    
    # Step 5: Test Core LLM Agent (if available)
    print("\n5️⃣ TESTING CORE LLM AGENT")
    try:
        from app.services.core_llm_agent import gee_tool_node
        
        # Create mock state
        mock_state = {
            "query": "Analyze vegetation in Jaipur",
            "locations": [{
                "matched_name": "Jaipur",
                "type": "city",
                "confidence": 0.9
            }]
        }
        
        agent_result = gee_tool_node(mock_state)
        debug_step("Core LLM Agent Result", agent_result,
                  ['analysis', 'roi'])
        
    except Exception as e:
        print(f"❌ Core LLM Agent error: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n{'='*80}")
    print("🎉 POLYGON FLOW DEBUG COMPLETE")
    print(f"{'='*80}")
    
    return True

if __name__ == "__main__":
    test_polygon_flow()
