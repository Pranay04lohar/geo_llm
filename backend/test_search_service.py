"""
Test script for the Search API Service.

This script tests the basic functionality of the Search API Service
including location resolution and environmental context search.
"""

import requests
import json
import time
import sys
from pathlib import Path

# Add the search service to path
search_service_path = Path(__file__).parent / "app" / "search_service"
sys.path.insert(0, str(search_service_path))

def test_search_service():
    """Test the Search API Service endpoints."""
    
    base_url = "http://localhost:8001"
    
    print("🔍 Testing Search API Service")
    print("=" * 50)
    
    # Test 1: Health Check
    print("\n1️⃣ Testing Health Check...")
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        if response.status_code == 200:
            print("✅ Health check passed")
            print(f"   Response: {response.json()}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to Search API Service")
        print("💡 Make sure the service is running: cd backend/app/search_service && python start.py")
        return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False
    
    # Test 2: Location Resolution
    print("\n2️⃣ Testing Location Resolution...")
    try:
        location_request = {
            "location_name": "Udaipur",
            "location_type": "city"
        }
        
        response = requests.post(
            f"{base_url}/search/location-data",
            json=location_request,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Location resolution successful")
            print(f"   Location: {data.get('coordinates', {})}")
            print(f"   Area: {data.get('area_km2', 'Unknown')} km²")
            print(f"   Success: {data.get('success', False)}")
        else:
            print(f"❌ Location resolution failed: {response.status_code}")
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"❌ Location resolution error: {e}")
    
    # Test 3: Environmental Context
    print("\n3️⃣ Testing Environmental Context...")
    try:
        context_request = {
            "location": "Udaipur",
            "analysis_type": "ndvi",
            "query": "vegetation analysis for Delhi"
        }
        
        response = requests.post(
            f"{base_url}/search/environmental-context",
            json=context_request,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Environmental context search successful")
            print(f"   Reports: {len(data.get('reports', []))}")
            print(f"   Studies: {len(data.get('studies', []))}")
            print(f"   News: {len(data.get('news', []))}")
            print(f"   Success: {data.get('success', False)}")
        else:
            print(f"❌ Environmental context failed: {response.status_code}")
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"❌ Environmental context error: {e}")
    
    # Test 4: Complete Analysis
    print("\n4️⃣ Testing Complete Analysis...")
    try:
        analysis_request = {
            "query": "vegetation analysis for Delhi",
            "locations": [
                {
                    "matched_name": "Delhi",
                    "type": "city",
                    "confidence": 95
                }
            ],
            "analysis_type": "ndvi"
        }
        
        response = requests.post(
            f"{base_url}/search/complete-analysis",
            json=analysis_request,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Complete analysis successful")
            print(f"   Analysis length: {len(data.get('analysis', ''))} characters")
            print(f"   Sources: {len(data.get('sources', []))}")
            print(f"   Confidence: {data.get('confidence', 0.0)}")
            print(f"   Success: {data.get('success', False)}")
            
            # Show first 200 characters of analysis
            analysis = data.get('analysis', '')
            if analysis:
                print(f"   Preview: {analysis[:200]}...")
        else:
            print(f"❌ Complete analysis failed: {response.status_code}")
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"❌ Complete analysis error: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 Search API Service testing completed!")
    print("💡 Check the results above to verify functionality")
    
    return True

def test_tavily_integration():
    """Test Tavily API integration directly."""
    print("\n🔧 Testing Tavily Integration...")
    
    try:
        from services.tavily_client import TavilyClient
        
        client = TavilyClient()
        
        # Test sync search
        results = client.search_sync("Delhi vegetation analysis", max_results=3)
        
        if results:
            print("✅ Tavily integration successful")
            print(f"   Results: {len(results)}")
            for i, result in enumerate(results[:2], 1):
                print(f"   {i}. {result.get('title', 'No title')[:50]}...")
        else:
            print("⚠️ Tavily integration returned no results")
            print("💡 Check TAVILY_API_KEY environment variable")
            
    except Exception as e:
        print(f"❌ Tavily integration error: {e}")
        print("💡 Make sure TAVILY_API_KEY is set in environment variables")

if __name__ == "__main__":
    print("🚀 Search API Service Test Suite")
    print("=" * 60)
    
    # Test Tavily integration first
    test_tavily_integration()
    
    # Test the full service
    test_search_service()
