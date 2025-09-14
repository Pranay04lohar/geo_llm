"""
Test Service for Search Service Fallback Verification

This test service verifies that the search service (Tavily) can be used as a fallback
when GEE services are turned off or unavailable. It simulates various failure scenarios
and ensures the system gracefully falls back to the search service.

Usage:
    python test_search_service_fallback.py
"""

import os
import sys
import time
import logging
import requests
from pathlib import Path
from typing import Dict, Any, List

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Import the core LLM agent
from app.services.core_llm_agent.agent import CoreLLMAgent, create_agent

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SearchServiceFallbackTester:
    """Test service for verifying search service fallback functionality."""
    
    def __init__(self):
        """Initialize the tester."""
        self.agent = None
        self.search_service_url = "http://localhost:8001"
        self.gee_service_url = "http://localhost:8000"
        self.test_results = []
        
    def setup(self):
        """Setup the test environment."""
        logger.info("🔧 Setting up Search Service Fallback Tester...")
        
        # Initialize the core LLM agent
        try:
            self.agent = create_agent(enable_debug=True)
            logger.info("✅ Core LLM Agent initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Core LLM Agent: {e}")
            return False
        
        # Check service availability
        self.check_service_availability()
        return True
    
    def check_service_availability(self):
        """Check which services are available."""
        logger.info("🔍 Checking service availability...")
        
        # Check Search Service
        try:
            response = requests.get(f"{self.search_service_url}/health", timeout=5)
            if response.status_code == 200:
                logger.info("✅ Search Service is available")
                self.search_service_available = True
            else:
                logger.warning("⚠️ Search Service returned non-200 status")
                self.search_service_available = False
        except Exception as e:
            logger.warning(f"⚠️ Search Service not available: {e}")
            self.search_service_available = False
        
        # Check GEE Service
        try:
            response = requests.get(f"{self.gee_service_url}/health", timeout=5)
            if response.status_code == 200:
                logger.info("✅ GEE Service is available")
                self.gee_service_available = True
            else:
                logger.warning("⚠️ GEE Service returned non-200 status")
                self.gee_service_available = False
        except Exception as e:
            logger.warning(f"⚠️ GEE Service not available: {e}")
            self.gee_service_available = False
    
    def run_fallback_tests(self):
        """Run comprehensive fallback tests."""
        logger.info("🚀 Starting Search Service Fallback Tests...")
        
        # Test queries that should trigger GEE services but fall back to search
        test_queries = [
            {
                "query": "Analyze NDVI vegetation health around Mumbai",
                "expected_intent": "GEE",
                "expected_analysis_type": "ndvi",
                "description": "NDVI analysis with Mumbai location"
            },
            {
                "query": "Show land surface temperature for Delhi",
                "expected_intent": "GEE", 
                "expected_analysis_type": "lst",
                "description": "LST analysis with Delhi location"
            },
            {
                "query": "What is the land use classification for Bangalore?",
                "expected_intent": "GEE",
                "expected_analysis_type": "lulc", 
                "description": "LULC analysis with Bangalore location"
            },
            {
                "query": "Analyze water bodies in Chennai",
                "expected_intent": "GEE",
                "expected_analysis_type": "water",
                "description": "Water analysis with Chennai location"
            }
        ]
        
        for i, test_case in enumerate(test_queries, 1):
            logger.info(f"\n{'='*60}")
            logger.info(f"🧪 TEST {i}: {test_case['description']}")
            logger.info(f"{'='*60}")
            
            result = self.run_single_test(test_case)
            self.test_results.append(result)
            
            # Brief pause between tests
            time.sleep(2)
        
        return self.test_results
    
    def run_single_test(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Run a single test case."""
        query = test_case["query"]
        expected_intent = test_case["expected_intent"]
        expected_analysis_type = test_case["expected_analysis_type"]
        description = test_case["description"]
        
        logger.info(f"📝 Query: {query}")
        logger.info(f"🎯 Expected Intent: {expected_intent}")
        logger.info(f"🔬 Expected Analysis Type: {expected_analysis_type}")
        
        start_time = time.time()
        
        try:
            # Process the query through the core LLM agent
            result = self.agent.process_query(query)
            processing_time = time.time() - start_time
            
            # Analyze the result
            test_result = self.analyze_test_result(
                query, result, expected_intent, expected_analysis_type, processing_time
            )
            
            # Log the result
            self.log_test_result(test_result)
            
            return test_result
            
        except Exception as e:
            logger.error(f"❌ Test failed with exception: {e}")
            return {
                "test_name": description,
                "query": query,
                "success": False,
                "error": str(e),
                "processing_time": time.time() - start_time,
                "fallback_used": False,
                "analysis_type": None,
                "service_used": "error"
            }
    
    def analyze_test_result(
        self, 
        query: str, 
        result: Dict[str, Any], 
        expected_intent: str,
        expected_analysis_type: str,
        processing_time: float
    ) -> Dict[str, Any]:
        """Analyze the test result to determine if fallback was used correctly."""
        
        # Extract key information from result
        analysis = result.get("analysis", "")
        roi = result.get("roi")
        evidence = result.get("evidence", [])
        metadata = result.get("metadata", {})
        
        # Determine if fallback was used
        fallback_used = any("search_service" in str(evidence) for evidence in evidence)
        gee_used = any("_service:success" in str(evidence) for evidence in evidence)
        
        # Determine service used
        if fallback_used:
            service_used = "search_service"
        elif gee_used:
            service_used = "gee_service"
        else:
            service_used = "unknown"
        
        # Check if analysis contains search-related content
        search_indicators = [
            "search analysis", "web search", "tavily", "fallback",
            "search service", "environmental context", "reports", "studies"
        ]
        has_search_content = any(indicator.lower() in analysis.lower() for indicator in search_indicators)
        
        # Determine success criteria
        success = (
            fallback_used and  # Fallback was used
            has_search_content and  # Analysis contains search content
            len(analysis) > 100 and  # Analysis is substantial
            processing_time < 60  # Processing completed in reasonable time
        )
        
        return {
            "test_name": f"Fallback test for {expected_analysis_type}",
            "query": query,
            "success": success,
            "processing_time": processing_time,
            "fallback_used": fallback_used,
            "analysis_type": expected_analysis_type,
            "service_used": service_used,
            "analysis_length": len(analysis),
            "has_search_content": has_search_content,
            "roi_available": roi is not None,
            "evidence": evidence,
            "analysis_preview": analysis[:200] + "..." if len(analysis) > 200 else analysis
        }
    
    def log_test_result(self, result: Dict[str, Any]):
        """Log the test result in a readable format."""
        status = "✅ PASS" if result["success"] else "❌ FAIL"
        
        logger.info(f"\n{status} - {result['test_name']}")
        logger.info(f"   Query: {result['query']}")
        logger.info(f"   Processing Time: {result['processing_time']:.2f}s")
        logger.info(f"   Fallback Used: {'Yes' if result['fallback_used'] else 'No'}")
        logger.info(f"   Service Used: {result['service_used']}")
        logger.info(f"   Analysis Length: {result['analysis_length']} chars")
        logger.info(f"   Has Search Content: {'Yes' if result['has_search_content'] else 'No'}")
        logger.info(f"   ROI Available: {'Yes' if result['roi_available'] else 'No'}")
        
        if result.get("error"):
            logger.error(f"   Error: {result['error']}")
        
        logger.info(f"   Analysis Preview: {result['analysis_preview']}")
    
    def generate_test_report(self):
        """Generate a comprehensive test report."""
        logger.info(f"\n{'='*80}")
        logger.info("📊 SEARCH SERVICE FALLBACK TEST REPORT")
        logger.info(f"{'='*80}")
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Passed: {passed_tests} ✅")
        logger.info(f"Failed: {failed_tests} ❌")
        logger.info(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        # Service availability summary
        logger.info(f"\n🔧 Service Availability:")
        logger.info(f"   Search Service: {'✅ Available' if self.search_service_available else '❌ Unavailable'}")
        logger.info(f"   GEE Service: {'✅ Available' if self.gee_service_available else '❌ Unavailable'}")
        
        # Detailed results
        logger.info(f"\n📋 Detailed Results:")
        for i, result in enumerate(self.test_results, 1):
            status = "✅" if result["success"] else "❌"
            logger.info(f"   {i}. {status} {result['test_name']}")
            logger.info(f"      Service: {result['service_used']} | Time: {result['processing_time']:.2f}s")
        
        # Recommendations
        logger.info(f"\n💡 Recommendations:")
        if not self.search_service_available:
            logger.info("   ⚠️ Start the Search Service: cd backend/app/search_service && python start.py")
        
        if self.gee_service_available:
            logger.info("   ℹ️ GEE Service is available - tests may not trigger fallback")
            logger.info("   ℹ️ To test fallback, stop the GEE service first")
        
        if failed_tests > 0:
            logger.info("   🔍 Check failed tests for specific error messages")
        
        return {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "success_rate": (passed_tests/total_tests)*100,
            "search_service_available": self.search_service_available,
            "gee_service_available": self.gee_service_available,
            "results": self.test_results
        }
    
    def test_search_service_direct(self):
        """Test the search service directly to verify it's working."""
        logger.info("\n🔍 Testing Search Service Directly...")
        
        try:
            # Test location resolution
            location_response = requests.post(
                f"{self.search_service_url}/search/location-data",
                json={
                    "location_name": "Mumbai",
                    "location_type": "city"
                },
                timeout=10
            )
            
            if location_response.status_code == 200:
                location_data = location_response.json()
                logger.info("✅ Location resolution working")
                logger.info(f"   Coordinates: {location_data.get('coordinates')}")
                logger.info(f"   Success: {location_data.get('success')}")
            else:
                logger.warning(f"⚠️ Location resolution failed: {location_response.status_code}")
            
            # Test environmental context
            env_response = requests.post(
                f"{self.search_service_url}/search/environmental-context",
                json={
                    "location": "Mumbai",
                    "analysis_type": "ndvi",
                    "query": "vegetation analysis for Mumbai"
                },
                timeout=10
            )
            
            if env_response.status_code == 200:
                env_data = env_response.json()
                logger.info("✅ Environmental context working")
                logger.info(f"   Total sources: {env_data.get('statistics', {}).get('total_sources', 0)}")
                logger.info(f"   Success: {env_data.get('success')}")
            else:
                logger.warning(f"⚠️ Environmental context failed: {env_response.status_code}")
            
            # Test complete analysis
            analysis_response = requests.post(
                f"{self.search_service_url}/search/complete-analysis",
                json={
                    "query": "vegetation analysis for Mumbai",
                    "locations": [{"matched_name": "Mumbai", "type": "city", "confidence": 95}],
                    "analysis_type": "ndvi"
                },
                timeout=15
            )
            
            if analysis_response.status_code == 200:
                analysis_data = analysis_response.json()
                logger.info("✅ Complete analysis working")
                logger.info(f"   Analysis length: {len(analysis_data.get('analysis', ''))}")
                logger.info(f"   Success: {analysis_data.get('success')}")
            else:
                logger.warning(f"⚠️ Complete analysis failed: {analysis_response.status_code}")
                
        except Exception as e:
            logger.error(f"❌ Direct search service test failed: {e}")

def main():
    """Main function to run the fallback tests."""
    print("🚀 Search Service Fallback Tester")
    print("=" * 50)
    
    tester = SearchServiceFallbackTester()
    
    # Setup
    if not tester.setup():
        print("❌ Setup failed. Exiting.")
        return
    
    # Test search service directly first
    tester.test_search_service_direct()
    
    # Run fallback tests
    print("\n🧪 Running Fallback Tests...")
    tester.run_fallback_tests()
    
    # Generate report
    report = tester.generate_test_report()
    
    # Return exit code based on results
    if report["failed_tests"] == 0:
        print("\n🎉 All tests passed! Search service fallback is working correctly.")
        return 0
    else:
        print(f"\n⚠️ {report['failed_tests']} tests failed. Check the logs for details.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
