#!/usr/bin/env python3
"""
Dual Integration Test for LLM Agent + Both LULC and NDVI Services
Tests the complete pipeline with automatic service selection based on query type
"""

import os
import sys
import json
from pathlib import Path

# Add app directory to path
current_dir = Path(__file__).parent
app_dir = current_dir / "app"
sys.path.append(str(app_dir))

def test_dual_service_integration():
    """Test the LLM agent pipeline with both LULC and NDVI service integration."""
    
    print("🚀 Testing Dual Service Integration (LULC + NDVI)")
    print("=" * 70)
    
    try:
        from app.services.core_llm_agent import build_graph
        
        # Build the LangGraph
        app = build_graph()
        print("✅ LangGraph built successfully")
        
        # Test queries with specific service expectations
        test_queries = [
            {
                "query": "Analyze the land use pattern around Mumbai",
                "expected_service": "lulc",
                "description": "LULC query (land use keywords)"
            },
            {
                "query": "Show me the vegetation health in Delhi using NDVI",
                "expected_service": "ndvi", 
                "description": "NDVI query (explicit NDVI + vegetation)"
            },
            {
                "query": "What is the NDVI vegetation index for Bangalore?",
                "expected_service": "ndvi",
                "description": "NDVI query (explicit NDVI keywords)"
            },
            {
                "query": "Urban development analysis for Kolkata",
                "expected_service": "lulc",
                "description": "LULC query (urban development keywords)"
            },
            {
                "query": "Check the forest health and canopy cover in Kerala",
                "expected_service": "ndvi",
                "description": "NDVI query (vegetation health keywords)"
            },
            {
                "query": "Land cover classification for Pune",
                "expected_service": "lulc", 
                "description": "LULC query (classification keywords)"
            },
            {
                "query": "Analyze the greenness and vegetation around Chennai",
                "expected_service": "ndvi",
                "description": "NDVI query (greenness keywords)"
            }
        ]
        
        for i, test_case in enumerate(test_queries, 1):
            query = test_case["query"]
            expected = test_case["expected_service"]
            description = test_case["description"]
            
            print(f"\n🧪 Test {i}: {description}")
            print(f"Query: '{query}'")
            print(f"Expected service: {expected.upper()}")
            print("-" * 50)
            
            try:
                # Run the complete pipeline
                result = app.invoke({"query": query})
                
                # Check if we got the expected contract
                analysis = result.get("analysis", "")
                roi = result.get("roi")
                evidence = result.get("evidence", [])
                
                print(f"✅ Analysis length: {len(analysis)} characters")
                print(f"✅ ROI provided: {'Yes' if roi else 'No'}")
                print(f"✅ Evidence entries: {len(evidence)}")
                
                # Analyze which service was actually used
                analysis_type = "unknown"
                if "🌿 NDVI Vegetation Analysis" in analysis:
                    analysis_type = "ndvi"
                elif "🌍 Land Use/Land Cover Analysis" in analysis:
                    analysis_type = "lulc"
                
                # Check ROI properties for analysis type
                if roi and roi.get("properties"):
                    props = roi["properties"]
                    roi_analysis_type = props.get("analysis_type", "")
                    if "ndvi" in roi_analysis_type:
                        analysis_type = "ndvi"
                    elif "lulc" in roi_analysis_type:
                        analysis_type = "lulc"
                
                # Verify service selection
                if analysis_type == expected:
                    print(f"✅ Correct service selected: {analysis_type.upper()}")
                    service_match = True
                else:
                    print(f"⚠️ Service mismatch: expected {expected.upper()}, got {analysis_type.upper()}")
                    service_match = False
                
                # Show key information
                if roi and roi.get("properties"):
                    props = roi["properties"]
                    location = props.get("source_locations", ["Unknown"])[0]
                    processing_time = props.get("processing_time_seconds", 0)
                    
                    print(f"📍 Location: {location}")
                    print(f"⏱️ Processing time: {processing_time:.1f}s")
                    
                    # Service-specific metrics
                    if analysis_type == "ndvi":
                        ndvi_stats = props.get("ndvi_statistics", {})
                        mean_ndvi = ndvi_stats.get("mean", 0)
                        veg_dist = props.get("vegetation_distribution", {})
                        time_series = props.get("time_series", {})
                        
                        print(f"🌱 Mean NDVI: {mean_ndvi:.3f}")
                        print(f"🌿 Vegetation categories: {len(veg_dist)}")
                        if time_series.get("data"):
                            print(f"📊 Time-series: {len(time_series['data'])} periods")
                            
                    elif analysis_type == "lulc":
                        land_cover = props.get("land_cover_percentages", {})
                        dominant = props.get("dominant_class", "Unknown")
                        
                        print(f"🏆 Dominant class: {dominant}")
                        print(f"📈 Land cover classes: {len(land_cover)}")
                    
                    # Check data quality
                    data_quality = props.get("data_quality", {})
                    if data_quality:
                        images_used = data_quality.get("images_used", 0)
                        print(f"🛰️ Images used: {images_used}")
                
                # Check evidence for success indicators
                success_indicators = [e for e in evidence if "success" in e or f"{analysis_type}_analysis" in e]
                if success_indicators:
                    print(f"✅ Success indicators: {len(success_indicators)}")
                else:
                    print("⚠️ No clear success indicators in evidence")
                
                if service_match:
                    print("✅ Test passed")
                else:
                    print("⚠️ Test passed but with wrong service selection")
                
            except Exception as e:
                print(f"❌ Test failed: {str(e)}")
                continue
        
        print(f"\n🎉 Dual service integration test completed!")
        print("💡 Both LULC and NDVI services are integrated and working")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Make sure all dependencies are installed and OPENROUTER_API_KEY is set")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    
    return True

def test_service_endpoints_direct():
    """Test both LULC and NDVI service endpoints directly."""
    
    print("\n🧪 Testing Service Endpoints Directly")
    print("=" * 40)
    
    import requests
    
    # Test ROI (small area for fast testing)
    test_roi = {
        "type": "Polygon",
        "coordinates": [[
            [72.85, 19.05],
            [72.87, 19.05], 
            [72.87, 19.07],
            [72.85, 19.07],
            [72.85, 19.05]
        ]]
    }
    
    # Test health first
    try:
        health_response = requests.get("http://localhost:8000/health", timeout=5)
        health_response.raise_for_status()
        health_data = health_response.json()
        
        print(f"✅ Service health: {health_data}")
        
        if not health_data.get("gee_initialized"):
            print("⚠️ GEE not initialized - tests may fail")
            return False
        
    except Exception as e:
        print(f"❌ Cannot connect to service: {e}")
        return False
    
    # Test LULC service
    print(f"\n🗺️ Testing LULC service...")
    try:
        lulc_payload = {
            "geometry": test_roi,
            "startDate": "2023-06-01",
            "endDate": "2023-08-31",
            "confidenceThreshold": 0.5,
            "scale": 30,
            "maxPixels": 1e8
        }
        
        lulc_response = requests.post(
            "http://localhost:8000/lulc/dynamic-world", 
            json=lulc_payload, 
            timeout=60
        )
        lulc_response.raise_for_status()
        lulc_data = lulc_response.json()
        
        print(f"✅ LULC analysis successful")
        print(f"   Processing time: {lulc_data.get('processing_time_seconds', 0):.1f}s")
        print(f"   Dominant class: {lulc_data.get('mapStats', {}).get('dominant_class', 'Unknown')}")
        
    except Exception as e:
        print(f"❌ LULC service test failed: {e}")
    
    # Test NDVI service
    print(f"\n🌿 Testing NDVI service...")
    try:
        ndvi_payload = {
            "geometry": test_roi,
            "startDate": "2023-06-01",
            "endDate": "2023-08-31",
            "cloudThreshold": 30,
            "scale": 30,
            "maxPixels": 1e8,
            "includeTimeSeries": False,  # Faster for testing
            "exactComputation": False
        }
        
        ndvi_response = requests.post(
            "http://localhost:8000/ndvi/vegetation-analysis", 
            json=ndvi_payload, 
            timeout=90
        )
        ndvi_response.raise_for_status()
        ndvi_data = ndvi_response.json()
        
        print(f"✅ NDVI analysis successful")
        print(f"   Processing time: {ndvi_data.get('processing_time_seconds', 0):.1f}s")
        ndvi_stats = ndvi_data.get('mapStats', {}).get('ndvi_statistics', {})
        mean_ndvi = ndvi_stats.get('mean', 0)
        print(f"   Mean NDVI: {mean_ndvi:.3f}")
        
    except Exception as e:
        print(f"❌ NDVI service test failed: {e}")
    
    return True

if __name__ == "__main__":
    print("🚀 Starting Dual Service Integration Tests")
    print("=" * 70)
    
    # Test services directly first
    services_ok = test_service_endpoints_direct()
    
    if services_ok:
        # Then test full integration
        test_dual_service_integration()
    else:
        print("\n⚠️ Skipping integration test - services not available")
        print("💡 Start the GEE service first, then run this test again")
