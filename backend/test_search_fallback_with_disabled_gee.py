"""
Search Service Fallback Test with Disabled GEE

This test script disables GEE services and verifies that the search service
(Tavily) is used as a fallback. It's designed to test the fallback mechanism
by forcing all GEE requests to go through the search service.

Usage:
    python test_search_fallback_with_disabled_gee.py
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

def test_with_disabled_gee():
    """Test search service fallback with GEE services disabled."""
    print("🧪 Testing Search Service Fallback with Disabled GEE...")
    print("=" * 60)
    
    try:
        # Import the disabled GEE configuration
        import test_config_disable_gee
        print("✅ GEE services disabled for testing")
        
        # Import and create the core LLM agent
        from app.services.core_llm_agent.agent import create_agent
        from app.services.core_llm_agent.config import get_openrouter_config
        
        # Show model configuration
        config = get_openrouter_config()
        print("🤖 Model Configuration:")
        print(f"   NER Model (Location Extraction): {config['ner_model']}")
        print(f"   Intent Model (Classification): {config['intent_model']}")
        print(f"   Response Model (Analysis): {config['response_model']}")
        print()
        
        agent = create_agent(enable_debug=True)
        print("✅ Core LLM Agent initialized")
        
        # Test queries that would normally go to GEE
        test_cases = [
            # {
            #     "query": "Analyze NDVI vegetation health around Mumbai",
            #     "expected_analysis_type": "ndvi",
            #     "description": "NDVI analysis with Mumbai"
            # },
            {
                "query": "Show land surface temperature for Delhi",
                "expected_analysis_type": "lst", 
                "description": "LST analysis with Delhi"
            },
            # {
            #     "query": "What is the land use classification for Bangalore?",
            #     "expected_analysis_type": "lulc",
            #     "description": "LULC analysis with Bangalore"
            # },
            # {
            #     "query": "Analyze water bodies in Chennai",
            #     "expected_analysis_type": "water",
            #     "description": "Water analysis with Chennai"
            # }
        ]
        
        results = []
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n🔍 Test {i}: {test_case['description']}")
            print(f"   Query: {test_case['query']}")
            print("-" * 50)
            
            try:
                # Process the query
                print(f"   🔄 Processing with models:")
                print(f"      NER: {config['ner_model']}")
                print(f"      Intent: {config['intent_model']}")
                print(f"      Response: {config['response_model']}")
                print()
                
                result = agent.process_query(test_case['query'])
                
                # Analyze the result
                evidence = result.get("evidence", [])
                analysis = result.get("analysis", "")
                roi = result.get("roi")
                
                # Debug: Print evidence array
                print(f"   DEBUG - Evidence array: {evidence}")
                print(f"   DEBUG - Evidence type: {type(evidence)}")
                print(f"   DEBUG - Evidence length: {len(evidence) if evidence else 0}")
                
                # Check if search service was used
                search_used = any("search_service" in str(evidence) for evidence in evidence)
                gee_used = any("_service:success" in str(evidence) for evidence in evidence)
                
                # Determine success
                success = search_used and not gee_used and len(analysis) > 100
                
                # Log result
                status = "✅ PASS" if success else "❌ FAIL"
                print(f"   {status}")
                print(f"   Search Service Used: {'Yes' if search_used else 'No'}")
                print(f"   GEE Service Used: {'Yes' if gee_used else 'No'}")
                print(f"   Analysis Length: {len(analysis)} chars")
                print(f"   ROI Available: {'Yes' if roi else 'No'}")
                print(f"   Evidence: {evidence}")
                
                # Always show full analysis for debugging
                print(f"   Full Analysis:")
                print("   " + "="*50)
                print(f"   {analysis}")
                print("   " + "="*50)
                
                # Show additional enhanced data if available
                if "structured_data" in result:
                    print(f"   📊 Structured Data:")
                    print(f"   {result.get('structured_data', {})}")
                
                if "data_quality" in result:
                    print(f"   📈 Data Quality:")
                    print(f"   {result.get('data_quality', {})}")
                
                if "extracted_metrics_count" in result:
                    print(f"   🔢 Extracted Metrics Count: {result.get('extracted_metrics_count', 0)}")
                
                results.append({
                    "test_name": test_case['description'],
                    "query": test_case['query'],
                    "success": success,
                    "search_used": search_used,
                    "gee_used": gee_used,
                    "analysis_length": len(analysis),
                    "roi_available": roi is not None
                })
                
            except Exception as e:
                print(f"   ❌ Test failed with exception: {e}")
                results.append({
                    "test_name": test_case['description'],
                    "query": test_case['query'],
                    "success": False,
                    "error": str(e)
                })
        
        # Generate summary
        print(f"\n📊 Test Summary")
        print("=" * 30)
        
        total_tests = len(results)
        passed_tests = sum(1 for r in results if r["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        # Check if search service was used in all tests
        search_used_count = sum(1 for r in results if r.get("search_used", False))
        print(f"Search Service Used: {search_used_count}/{total_tests} tests")
        
        return passed_tests == total_tests
        
    except Exception as e:
        print(f"❌ Test setup failed: {e}")
        return False

def check_search_service():
    """Check if search service is available."""
    print("\n🔧 Checking Search Service Availability...")
    print("-" * 40)
    
    try:
        import requests
        response = requests.get("http://localhost:8001/health", timeout=5)
        
        if response.status_code == 200:
            print("✅ Search Service: Available")
            return True
        else:
            print(f"⚠️ Search Service: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Search Service: Not available ({e})")
        return False

def main():
    """Main function."""
    print("🚀 Search Service Fallback Test (GEE Disabled)")
    print("=" * 60)
    
    # Check search service availability
    if not check_search_service():
        print("\n❌ Search Service not available!")
        print("🔧 Please start the search service:")
        print("   cd backend/app/search_service")
        print("   python start.py")
        return 1
    
    # Run the test
    success = test_with_disabled_gee()
    
    if success:
        print("\n🎉 All tests passed! Search service fallback is working correctly.")
        print("\n💡 This confirms that:")
        print("   • GEE services are properly disabled")
        print("   • Search service is used as fallback")
        print("   • Analysis is generated from web search data")
        return 0
    else:
        print("\n⚠️ Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
