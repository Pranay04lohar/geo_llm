"""
Simple Search Service Fallback Test

A quick test to verify that the search service (Tavily) can be used as a fallback
when GEE services are unavailable. This is a simplified version for quick testing.

Usage:
    python test_search_fallback_simple.py
"""

import sys
import logging
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_search_fallback():
    """Test search service fallback functionality."""
    print("🧪 Testing Search Service Fallback...")
    print("=" * 50)
    
    try:
        # Import the core LLM agent
        from app.services.core_llm_agent.agent import create_agent
        
        # Create agent with debug enabled
        agent = create_agent(enable_debug=True)
        print("✅ Core LLM Agent initialized")
        
        # Test queries that should trigger GEE but fall back to search
        test_queries = [
            "Analyze NDVI vegetation health around Mumbai",
            "Show land surface temperature for Delhi", 
            "What is the land use classification for Bangalore?",
            "Analyze water bodies in Chennai"
        ]
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n🔍 Test {i}: {query}")
            print("-" * 40)
            
            try:
                # Process the query
                result = agent.process_query(query)
                
                # Check if fallback was used
                evidence = result.get("evidence", [])
                analysis = result.get("analysis", "")
                
                fallback_used = any("search_service" in str(evidence) for evidence in evidence)
                gee_used = any("_service:success" in str(evidence) for evidence in evidence)
                
                if fallback_used:
                    print("✅ Search service fallback used")
                    print(f"   Analysis preview: {analysis[:150]}...")
                elif gee_used:
                    print("ℹ️ GEE service used (fallback not triggered)")
                else:
                    print("⚠️ Unknown service used")
                
                print(f"   Evidence: {evidence}")
                print(f"   ROI available: {'Yes' if result.get('roi') else 'No'}")
                
            except Exception as e:
                print(f"❌ Test failed: {e}")
        
        print("\n🎉 Fallback test completed!")
        return True
        
    except Exception as e:
        print(f"❌ Test setup failed: {e}")
        return False

def check_services():
    """Check which services are available."""
    print("\n🔧 Checking Service Availability...")
    print("-" * 40)
    
    import requests
    
    # Check Search Service
    try:
        response = requests.get("http://localhost:8001/health", timeout=5)
        if response.status_code == 200:
            print("✅ Search Service: Available")
        else:
            print("⚠️ Search Service: Not responding properly")
    except:
        print("❌ Search Service: Not available")
    
    # Check GEE Service
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ GEE Service: Available")
        else:
            print("⚠️ GEE Service: Not responding properly")
    except:
        print("❌ GEE Service: Not available")

def main():
    """Main function."""
    print("🚀 Simple Search Service Fallback Test")
    print("=" * 50)
    
    # Check services first
    check_services()
    
    # Run the test
    success = test_search_fallback()
    
    if success:
        print("\n✅ Test completed successfully!")
        print("\n💡 To test fallback behavior:")
        print("   1. Stop the GEE service (if running)")
        print("   2. Run this test again")
        print("   3. You should see 'Search service fallback used' messages")
    else:
        print("\n❌ Test failed!")
        print("\n🔧 Troubleshooting:")
        print("   1. Ensure Search Service is running: cd backend/app/search_service && python start.py")
        print("   2. Check that TAVILY_API_KEY is set in .env file")
        print("   3. Verify Core LLM Agent can be imported")

if __name__ == "__main__":
    main()
