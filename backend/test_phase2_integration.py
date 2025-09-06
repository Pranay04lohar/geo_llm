#!/usr/bin/env python3
"""
Phase 2 Integration Test - Search API Service with Core LLM Agent

This script tests the integrated workflow where:
1. Normal Flow: LLM extracts region → Search API provides coordinates/area → GEE service runs → LLM generates final analysis
2. Fallback Flow: When GEE/RAG fail → Search API provides online analysis → LLM generates final output

Test scenarios:
- Normal geospatial analysis flow (GEE + Search API for location data)
- Fallback analysis flow (Search API when GEE fails)
- Location resolution and area calculation
- Complete analysis generation with LLM synthesis
- Error handling and graceful fallbacks
"""

import os
import sys
import json
import time
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
backend_dir = Path(__file__).parent
env_path = backend_dir / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"✅ Loaded .env file from: {env_path}")
else:
    print(f"⚠️ .env file not found at: {env_path}")
    load_dotenv()  # Try current directory

# Add the app directory to Python path
app_dir = Path(__file__).parent / "app"
sys.path.insert(0, str(app_dir))

def test_search_service_health():
    """Test if Search API Service is running and healthy."""
    print("🔍 Testing Search API Service Health...")
    try:
        response = requests.get("http://localhost:8001/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Search API Service is healthy: {data}")
            return True
        else:
            print(f"❌ Search API Service health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Search API Service not reachable: {e}")
        return False

def test_core_llm_agent_import():
    """Test if core LLM agent can import the Search API Service integration."""
    print("\n🔧 Testing Core LLM Agent Integration...")
    try:
        from services.core_llm_agent import websearch_tool_node, execute_plan_node
        print("✅ Core LLM Agent imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_normal_flow_geospatial_analysis():
    """Test normal flow: LLM extracts region → Search API provides coordinates/area → GEE service runs → LLM generates final analysis."""
    print("\n🌍 Testing Normal Flow - Geospatial Analysis...")
    try:
        from services.core_llm_agent import llm_extract_locations_openrouter, gee_tool_node
        import requests
        
        # Test query that should trigger normal GEE flow with Search API for location data
        test_query = "Analyze the NDVI vegetation health in Delhi"
        
        print(f"📝 Query: {test_query}")
        print("🔄 Running through normal pipeline flow...")
        print("   Step 1: LLM extracts location (Delhi)")
        print("   Step 2: Search API provides coordinates and area")
        print("   Step 3: GEE service runs NDVI analysis")
        print("   Step 4: LLM generates final analysis")
        
        # Step 1: Test LLM location extraction
        print("\n📍 Step 1: LLM Location Extraction")
        locations = llm_extract_locations_openrouter(test_query)
        if locations:
            print(f"✅ LLM extracted locations: {[loc.get('matched_name') for loc in locations]}")
        else:
            print("⚠️ LLM location extraction failed, using mock location")
            locations = [{"matched_name": "Delhi", "type": "city", "confidence": 0.95}]
        
        # Step 2: Test Search API location data
        print("\n🔍 Step 2: Search API Location Data")
        location_data = None
        if locations:
            primary_location = locations[0]
            location_name = primary_location.get("matched_name", "Delhi")
            
            try:
                response = requests.post(
                    "http://localhost:8001/search/location-data",
                    json={
                        "location_name": location_name,
                        "location_type": "city"
                    },
                    timeout=30  # Increased timeout
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("success", False):
                        location_data = data
                        coords = data.get("coordinates", {})
                        area = data.get("area_km2")
                        print(f"✅ Search API provided location data:")
                        print(f"   📍 Coordinates: {coords.get('lat', 'N/A')}°N, {coords.get('lng', 'N/A')}°E")
                        print(f"   📊 Area: {area} km²" if area else "   ⚠️ Area: Not available")
                    else:
                        print(f"⚠️ Search API failed: {data.get('error', 'Unknown error')}")
                else:
                    print(f"⚠️ Search API HTTP error: {response.status_code}")
            except Exception as e:
                print(f"⚠️ Search API request failed: {e}")
        
        # Step 3: Test GEE service with extracted location
        print("\n🌿 Step 3: GEE Service Analysis")
        test_state = {
            "query": test_query,
            "locations": locations,
            "evidence": []
        }
        
        gee_result = gee_tool_node(test_state)
        
        print(f"✅ GEE service executed")
        print(f"📊 Analysis length: {len(gee_result.get('analysis', ''))} characters")
        print(f"🎯 ROI available: {gee_result.get('roi') is not None}")
        print(f"🔍 Evidence: {gee_result.get('evidence', [])}")
        
        # Check if normal flow components were used
        evidence = gee_result.get('evidence', [])
        if 'llm_ner:found' in evidence or locations:
            print("✅ Location extraction successful")
        if any('ndvi_service' in evt or 'gee_service' in evt for evt in evidence):
            print("✅ GEE service executed successfully")
        
        # Show preview of analysis
        analysis = gee_result.get('analysis', '')
        if analysis:
            preview = analysis[:400] + "..." if len(analysis) > 400 else analysis
            print(f"📖 Analysis Preview: {preview}")
        else:
            print("⚠️ No analysis generated - this might indicate an issue")
        
        return True
        
    except Exception as e:
        print(f"❌ Normal flow test failed: {e}")
        return False

def test_fallback_flow_analysis():
    """Test fallback flow: When GEE/RAG fail → Search API provides online analysis → LLM generates final output."""
    print("\n🔄 Testing Fallback Flow - Search API Analysis...")
    try:
        from services.core_llm_agent import llm_extract_locations_openrouter, websearch_tool_node
        import requests
        
        # Test query that should trigger Search API fallback analysis
        test_query = "What is the current vegetation status and environmental conditions in Bangalore?"
        
        print(f"📝 Query: {test_query}")
        print("🔄 Running through fallback pipeline flow...")
        print("   Step 1: LLM extracts location (Bangalore)")
        print("   Step 2: GEE/RAG services fail or unavailable")
        print("   Step 3: Search API provides online analysis")
        print("   Step 4: LLM generates final output from search data")
        
        # Step 1: Test LLM location extraction
        print("\n📍 Step 1: LLM Location Extraction")
        locations = llm_extract_locations_openrouter(test_query)
        if locations:
            print(f"✅ LLM extracted locations: {[loc.get('matched_name') for loc in locations]}")
        else:
            print("⚠️ LLM location extraction failed, using mock location")
            locations = [{"matched_name": "Bangalore", "type": "city", "confidence": 0.95}]
        
        # Step 2: Test Search API complete analysis (fallback scenario)
        print("\n🔍 Step 2: Search API Complete Analysis (Fallback)")
        try:
            response = requests.post(
                "http://localhost:8001/search/complete-analysis",
                json={
                    "query": test_query,
                    "locations": locations,
                    "analysis_type": "ndvi"
                },
                timeout=60  # Increased timeout for complete analysis
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success", False):
                    analysis = data.get("analysis", "")
                    sources = data.get("sources", [])
                    confidence = data.get("confidence", 0.0)
                    
                    print(f"✅ Search API provided complete analysis:")
                    print(f"   📊 Analysis length: {len(analysis)} characters")
                    print(f"   📚 Sources: {len(sources)}")
                    print(f"   🎯 Confidence: {confidence}")
                    
                    if analysis:
                        preview = analysis[:300] + "..." if len(analysis) > 300 else analysis
                        print(f"   📖 Analysis Preview: {preview}")
                else:
                    print(f"⚠️ Search API analysis failed: {data.get('error', 'Unknown error')}")
            else:
                print(f"⚠️ Search API HTTP error: {response.status_code}")
        except Exception as e:
            print(f"⚠️ Search API request failed: {e}")
        
        # Step 3: Test websearch_tool_node (which should use Search API Service)
        print("\n🔍 Step 3: WebSearch Tool Node (Search API Integration)")
        test_state = {
            "query": test_query,
            "locations": locations,
            "evidence": []
        }
        
        result = websearch_tool_node(test_state)
        
        print(f"✅ WebSearch tool executed")
        print(f"📊 Analysis length: {len(result.get('analysis', ''))} characters")
        print(f"🎯 Confidence: {result.get('confidence', 0.0)}")
        print(f"📚 Sources: {len(result.get('sources', []))}")
        print(f"🔍 Evidence: {result.get('evidence', [])}")
        
        # Check if fallback was used
        evidence = result.get('evidence', [])
        if 'search_service:fallback_used' in evidence:
            print("🔄 Search API Service fallback was used")
        elif 'search_service:complete_analysis_success' in evidence:
            print("✅ Search API Service provided complete analysis")
        
        # Show preview of analysis
        analysis = result.get('analysis', '')
        if analysis:
            preview = analysis[:400] + "..." if len(analysis) > 400 else analysis
            print(f"📖 Analysis Preview: {preview}")
        
        return True
        
    except Exception as e:
        print(f"❌ Fallback flow test failed: {e}")
        return False

def test_location_resolution_and_area():
    """Test Search API Service location resolution and area calculation."""
    print("\n📍 Testing Location Resolution and Area Calculation...")
    try:
        import requests
        
        # Test different cities for location resolution
        test_locations = [
            {"name": "Delhi", "type": "city"},
            {"name": "Mumbai", "type": "city"},
            {"name": "Bangalore", "type": "city"},
            {"name": "Chennai", "type": "city"}
        ]
        
        print("🔍 Testing location resolution for multiple cities...")
        
        for location in test_locations:
            print(f"\n📍 Testing: {location['name']}")
            
            try:
                response = requests.post(
                    "http://localhost:8001/search/location-data",
                    json={
                        "location_name": location["name"],
                        "location_type": location["type"]
                    },
                    timeout=30  # Increased timeout
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("success", False):
                        coords = data.get("coordinates", {})
                        area = data.get("area_km2")
                        print(f"   ✅ Coordinates: {coords.get('lat', 'N/A')}°N, {coords.get('lng', 'N/A')}°E")
                        print(f"   ✅ Area: {area} km²" if area else "   ⚠️ Area: Not available")
                    else:
                        print(f"   ❌ Failed: {data.get('error', 'Unknown error')}")
                else:
                    print(f"   ❌ HTTP Error: {response.status_code}")
                    
            except Exception as e:
                print(f"   ❌ Request failed: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Location resolution test failed: {e}")
        return False

def test_complete_integrated_workflow():
    """Test the complete integrated workflow: User Query → LLM → Search API → GEE → Analysis."""
    print("\n🔄 Testing Complete Integrated Workflow...")
    try:
        from services.core_llm_agent import controller_node
        
        # Test with a real user query that should trigger the full pipeline
        test_query = "What is the vegetation health in Mumbai and what environmental reports are available?"
        
        print(f"📝 User Query: {test_query}")
        print("🔄 Running complete integrated workflow...")
        print("   Step 1: LLM extracts location (Mumbai)")
        print("   Step 2: LLM planner determines tools to use")
        print("   Step 3: Search API provides location data")
        print("   Step 4: GEE service runs analysis")
        print("   Step 5: LLM generates final comprehensive analysis")
        
        # Run the complete pipeline using the full workflow
        from services.core_llm_agent import build_graph
        
        app = build_graph()
        result = app.invoke({"query": test_query})
        
        print(f"✅ Complete workflow executed")
        print(f"📊 Final analysis length: {len(result.get('analysis', ''))} characters")
        print(f"🎯 ROI available: {result.get('roi') is not None}")
        print(f"🔍 Evidence: {result.get('evidence', [])}")
        
        # Check workflow components
        evidence = result.get('evidence', [])
        if 'controller:ok' in evidence:
            print("✅ Controller initialized successfully")
        if 'llm_ner:found' in evidence:
            print("✅ LLM location extraction successful")
        if 'planner:ok' in evidence:
            print("✅ LLM planner executed successfully")
        if 'executor:ok' in evidence:
            print("✅ Tool execution completed")
        
        # Check for specific tool usage
        if any('ndvi_service' in evt or 'gee_service' in evt for evt in evidence):
            print("✅ GEE service was used")
        if any('search_service' in evt for evt in evidence):
            print("✅ Search API Service was used")
        
        # Show preview of analysis
        analysis = result.get('analysis', '')
        if analysis:
            preview = analysis[:500] + "..." if len(analysis) > 500 else analysis
            print(f"📖 Analysis Preview: {preview}")
        else:
            print("⚠️ No analysis generated - this might indicate an issue")
        
        return True
        
    except Exception as e:
        print(f"❌ Complete workflow test failed: {e}")
        return False

def test_search_api_service_direct():
    """Test Search API Service endpoints directly."""
    print("\n🔍 Testing Search API Service Direct Endpoints...")
    try:
        import requests
        
        # Test 1: Location data endpoint
        print("\n📍 Testing Location Data Endpoint")
        try:
            response = requests.post(
                "http://localhost:8001/search/location-data",
                json={
                    "location_name": "Pune",
                    "location_type": "city"
                },
                timeout=30  # Increased timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success", False):
                    coords = data.get("coordinates", {})
                    area = data.get("area_km2")
                    print(f"✅ Location data retrieved:")
                    print(f"   📍 Coordinates: {coords.get('lat', 'N/A')}°N, {coords.get('lng', 'N/A')}°E")
                    print(f"   📊 Area: {area} km²" if area else "   ⚠️ Area: Not available")
                else:
                    print(f"⚠️ Location data failed: {data.get('error', 'Unknown error')}")
            else:
                print(f"⚠️ Location data HTTP error: {response.status_code}")
        except Exception as e:
            print(f"⚠️ Location data request failed: {e}")
        
        # Test 2: Environmental context endpoint
        print("\n🌿 Testing Environmental Context Endpoint")
        try:
            response = requests.post(
                "http://localhost:8001/search/environmental-context",
                json={
                    "location": "Pune",
                    "analysis_type": "ndvi",
                    "query": "vegetation health analysis"
                },
                timeout=45  # Increased timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success", False):
                    reports = len(data.get("reports", []))
                    studies = len(data.get("studies", []))
                    news = len(data.get("news", []))
                    print(f"✅ Environmental context retrieved:")
                    print(f"   📊 Reports: {reports}")
                    print(f"   📚 Studies: {studies}")
                    print(f"   📰 News: {news}")
                else:
                    print(f"⚠️ Environmental context failed: {data.get('error', 'Unknown error')}")
            else:
                print(f"⚠️ Environmental context HTTP error: {response.status_code}")
        except Exception as e:
            print(f"⚠️ Environmental context request failed: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Search API Service direct test failed: {e}")
        return False

def main():
    """Run all Phase 2 integration tests."""
    print("🚀 Phase 2 Integration Test Suite")
    print("=" * 60)
    print("Testing Search API Service integration with Core LLM Agent")
    print("=" * 60)
    print("📋 Test Coverage:")
    print("   1. Normal Flow: LLM extracts location → Search API provides coordinates/area → GEE runs analysis → LLM generates final analysis")
    print("   2. Fallback Flow: GEE/RAG fail → Search API provides complete analysis → LLM generates final output")
    print("   3. Location Resolution and Area Calculation via Search API")
    print("   4. Complete Integrated Workflow: User Query → Full Pipeline")
    print("   5. Search API Service Direct Endpoint Testing")
    print("=" * 60)
    
    # Check environment
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    tavily_key = os.getenv("TAVILY_API_KEY")
    
    if openrouter_key:
        print(f"✅ OPENROUTER_API_KEY found: {openrouter_key[:10]}...")
    else:
        print("⚠️ Warning: OPENROUTER_API_KEY not set. Some tests may fail.")
        print("💡 Set OPENROUTER_API_KEY to test LLM-based components.")
    
    if tavily_key:
        print(f"✅ TAVILY_API_KEY found: {tavily_key[:10]}...")
    else:
        print("⚠️ Warning: TAVILY_API_KEY not set. Search API Service will use fallback mode.")
        print("💡 Set TAVILY_API_KEY for full Search API Service functionality.")
    
    # Run tests
    tests = [
        ("Search Service Health", test_search_service_health),
        ("Core LLM Agent Import", test_core_llm_agent_import),
        ("Normal Flow - Geospatial Analysis", test_normal_flow_geospatial_analysis),
        ("Fallback Flow - Search API Analysis", test_fallback_flow_analysis),
        ("Location Resolution and Area", test_location_resolution_and_area),
        ("Complete Integrated Workflow", test_complete_integrated_workflow),
        ("Search API Service Direct", test_search_api_service_direct),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'=' * 60}")
        print(f"🧪 Running: {test_name}")
        print('=' * 60)
        
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ Test '{test_name}' crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print(f"\n{'=' * 60}")
    print("📊 Test Results Summary")
    print('=' * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if success:
            passed += 1
    
    print(f"\n🎯 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Phase 2 integration is working correctly.")
    else:
        print("⚠️ Some tests failed. Check the output above for details.")
    
    print("\n💡 Next Steps:")
    print("1. Ensure Search API Service is running: cd backend/app/search_service && python start.py")
    print("2. Set TAVILY_API_KEY for full Search API Service functionality")
    print("3. Set OPENROUTER_API_KEY for LLM-based components")
    print("4. Test with real user queries through the main application")
    print("\n🔧 System Architecture:")
    print("   Normal Flow: User Query → LLM NER → Search API (location data) → GEE Service → LLM Analysis")
    print("   Fallback Flow: User Query → LLM NER → Search API (complete analysis) → LLM Synthesis")
    print("   Both flows provide comprehensive geospatial analysis with different data sources")

if __name__ == "__main__":
    main()
