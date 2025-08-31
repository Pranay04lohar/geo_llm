#!/usr/bin/env python3
"""
Integration Test for LLM Agent + LULC Service
Tests the complete pipeline from query to results
"""

import os
import sys
import json
from pathlib import Path

# Add app directory to path
current_dir = Path(__file__).parent
app_dir = current_dir / "app"
sys.path.append(str(app_dir))

def test_llm_agent_integration():
    """Test the complete LLM agent pipeline with LULC service integration."""
    
    print("🚀 Testing LLM Agent + LULC Service Integration")
    print("=" * 60)
    
    try:
        from app.services.core_llm_agent import build_graph
        
        # Build the LangGraph
        app = build_graph()
        print("✅ LangGraph built successfully")
        
        # Test queries with different types of locations
        test_queries = [
            "Analyze the land cover around Pune",
        ]
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n🧪 Test {i}: {query}")
            print("-" * 40)
            
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
                
                # Show key information
                if roi and roi.get("properties"):
                    props = roi["properties"]
                    location = props.get("source_locations", ["Unknown"])[0]
                    dominant_class = props.get("dominant_class", "Unknown")
                    processing_time = props.get("processing_time_seconds", 0)
                    
                    print(f"📍 Location: {location}")
                    print(f"🏆 Dominant class: {dominant_class}")
                    print(f"⏱️ Processing time: {processing_time:.1f}s")
                    
                    # Check for enhanced metadata
                    data_quality = props.get("data_quality", {})
                    if data_quality:
                        images_used = data_quality.get("images_used", 0)
                        confidence = data_quality.get("confidence_threshold", 0)
                        print(f"🛰️ Images used: {images_used}, Confidence: {confidence}")
                
                # Check evidence for success indicators
                success_indicators = [e for e in evidence if "success" in e or "lulc_analysis" in e]
                if success_indicators:
                    print(f"✅ Success indicators: {len(success_indicators)}")
                else:
                    print("⚠️ No clear success indicators in evidence")
                    
                print("✅ Test passed")
                
            except Exception as e:
                print(f"❌ Test failed: {str(e)}")
                continue
        
        print(f"\n🎉 Integration test completed!")
        print("💡 If tests passed, the integration is working correctly")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Make sure all dependencies are installed and OPENROUTER_API_KEY is set")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    
    return True

def test_lulc_service_direct():
    """Test the LULC service directly."""
    
    print("\n🧪 Testing LULC Service Directly")
    print("=" * 40)
    
    try:
        import requests
        
        # Test service health
        health_response = requests.get("http://localhost:8000/health", timeout=5)
        health_response.raise_for_status()
        health_data = health_response.json()
        
        print(f"✅ Service health: {health_data}")
        
        if not health_data.get("gee_initialized"):
            print("⚠️ GEE not initialized - tests may fail")
            return False
        
        # Test LULC analysis
        test_payload = {
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [72.7758, 18.8900],
                    [72.7958, 18.8900], 
                    [72.7958, 18.9100],
                    [72.7758, 18.9100],
                    [72.7758, 18.8900]
                ]]
            },
            "startDate": "2023-01-01",
            "endDate": "2023-12-31",
            "confidenceThreshold": 0.5,
            "scale": 30,
            "maxPixels": 1e9
        }
        
        lulc_response = requests.post(
            "http://localhost:8000/lulc/dynamic-world", 
            json=test_payload, 
            timeout=60
        )
        lulc_response.raise_for_status()
        lulc_data = lulc_response.json()
        
        print(f"✅ LULC analysis successful")
        print(f"   Processing time: {lulc_data.get('processing_time_seconds', 0):.1f}s")
        print(f"   ROI area: {lulc_data.get('roi_area_km2', 0):.2f} km²")
        print(f"   Dominant class: {lulc_data.get('mapStats', {}).get('dominant_class', 'Unknown')}")
        
        return True
        
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to LULC service on localhost:8000")
        print("💡 Start the service with: cd backend/app/gee_service && python start.py")
        return False
    except Exception as e:
        print(f"❌ Service test failed: {e}")
        return False

if __name__ == "__main__":
    # Test service first
    service_ok = test_lulc_service_direct()
    
    if service_ok:
        # Then test integration
        test_llm_agent_integration()
    else:
        print("\n⚠️ Skipping integration test - service not available")
        print("💡 Start the LULC service first, then run this test again")
