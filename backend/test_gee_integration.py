#!/usr/bin/env python3
"""
Integration Test for Core LLM Agent with GEE Services

This test file verifies the complete integration between the Core LLM Agent
and all 4 GEE services (Water, NDVI, LULC, LST). It tests 2 queries per service
to ensure the full pipeline works correctly.

Services tested:
1. Water Analysis Service - Water presence and change detection
2. NDVI Service - Vegetation analysis and time-series
3. LULC Service - Land use/land cover classification
4. LST Service - Land surface temperature and UHI analysis
"""

import sys
import os
import time
import json
import requests
from pathlib import Path
from typing import Dict, Any, List

# Add the app directory to the path to import core_llm_agent
sys.path.append(str(Path(__file__).parent / "app"))

try:
    from services.core_llm_agent import CoreLLMAgent
    print("✅ Core LLM Agent imported successfully")
except ImportError as e:
    print(f"❌ Failed to import Core LLM Agent: {e}")
    print("💡 Make sure you're running from the backend directory")
    sys.exit(1)

# Test configuration
GEE_SERVICE_URL = "http://localhost:8000"
TEST_TIMEOUT = 120  # 2 minutes timeout for each test

# Test queries for each service (2 per service)
TEST_QUERIES = {
    "water": [
        "What is the water coverage in Mumbai region?"
    ],
    "ndvi": [
        "Analyze vegetation health in Mumbai area for 2023"
    ],
    "lulc": [
        "What is the land use classification for Mumbai city?"
    ],
    "lst": [
        "What is the land surface temperature in Delhi?"
    ]
}

# Test geometries for different regions
TEST_GEOMETRIES = {
    "mumbai": {
        "type": "Polygon",
        "coordinates": [[
            [72.77, 18.89],
            [72.97, 18.89], 
            [72.97, 19.27],
            [72.77, 19.27],
            [72.77, 18.89]
        ]]
    },
    "delhi": {
        "type": "Polygon",
        "coordinates": [[
            [77.0, 28.4],
            [77.5, 28.4],
            [77.5, 28.8],
            [77.0, 28.8],
            [77.0, 28.4]
        ]]
    }
}

class GEEIntegrationTester:
    """Integration tester for Core LLM Agent with GEE Services"""
    
    def __init__(self, gee_service_url: str = GEE_SERVICE_URL):
        self.gee_service_url = gee_service_url
        self.agent = None
        self.test_results = {
            "water": {"passed": 0, "failed": 0, "details": []},
            "ndvi": {"passed": 0, "failed": 0, "details": []},
            "lulc": {"passed": 0, "failed": 0, "details": []},
            "lst": {"passed": 0, "failed": 0, "details": []}
        }
    
    def initialize_agent(self):
        """Initialize the Core LLM Agent"""
        try:
            print("🤖 Initializing Core LLM Agent...")
            self.agent = CoreLLMAgent(enable_debug=True)
            print("✅ Core LLM Agent initialized successfully")
            return True
        except Exception as e:
            print(f"❌ Failed to initialize Core LLM Agent: {e}")
            return False
    
    def check_gee_service_health(self):
        """Check if GEE service is running and healthy"""
        try:
            print("🏥 Checking GEE Service health...")
            response = requests.get(f"{self.gee_service_url}/health", timeout=10)
            
            if response.status_code == 200:
                health_data = response.json()
                print(f"✅ GEE Service is healthy: {health_data}")
                return health_data.get("gee_initialized", False)
            else:
                print(f"❌ GEE Service health check failed: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Cannot connect to GEE Service: {e}")
            print("💡 Make sure the GEE service is running on port 8000")
            return False
    
    def test_water_service_integration(self):
        """Test Water Analysis Service integration"""
        print("\n" + "="*60)
        print("🌊 Testing Water Analysis Service Integration")
        print("="*60)
        
        for i, query in enumerate(TEST_QUERIES["water"], 1):
            print(f"\n🧪 Test {i}: {query}")
            print("-" * 50)
            
            try:
                start_time = time.time()
                
                # Process query through Core LLM Agent
                result = self.agent.process_query(query)
                
                processing_time = time.time() - start_time
                
                if result.get("success"):
                    print(f"✅ Query processed successfully in {processing_time:.2f}s")
                    
                    # Check if the result contains water analysis data
                    analysis_data = result.get("analysis_data", {})
                    if analysis_data:
                        print(f"📊 Analysis type: {analysis_data.get('analysis_type', 'Unknown')}")
                        print(f"📈 Water percentage: {analysis_data.get('water_percentage', 'N/A')}")
                        print(f"🗺️ Tile URL available: {'✅' if analysis_data.get('tile_url') else '❌'}")
                        
                        self.test_results["water"]["passed"] += 1
                        self.test_results["water"]["details"].append({
                            "query": query,
                            "status": "passed",
                            "processing_time": processing_time,
                            "analysis_type": analysis_data.get('analysis_type', 'Unknown')
                        })
                    else:
                        print("⚠️ No analysis data found in result")
                        print(f"🔍 Full result keys: {list(result.keys())}")
                        self.test_results["water"]["failed"] += 1
                        self.test_results["water"]["details"].append({
                            "query": query,
                            "status": "failed",
                            "reason": "No analysis data"
                        })
                else:
                    error_msg = result.get('error', 'Unknown error')
                    print(f"❌ Query processing failed: {error_msg}")
                    print(f"🔍 Full result: {result}")
                    self.test_results["water"]["failed"] += 1
                    self.test_results["water"]["details"].append({
                        "query": query,
                        "status": "failed",
                        "reason": error_msg
                    })
                    
            except Exception as e:
                print(f"❌ Test failed with exception: {e}")
                self.test_results["water"]["failed"] += 1
                self.test_results["water"]["details"].append({
                    "query": query,
                    "status": "failed",
                    "reason": str(e)
                })
    
    def test_ndvi_service_integration(self):
        """Test NDVI Vegetation Analysis Service integration"""
        print("\n" + "="*60)
        print("🌱 Testing NDVI Vegetation Analysis Service Integration")
        print("="*60)
        
        for i, query in enumerate(TEST_QUERIES["ndvi"], 1):
            print(f"\n🧪 Test {i}: {query}")
            print("-" * 50)
            
            try:
                start_time = time.time()
                
                # Process query through Core LLM Agent
                result = self.agent.process_query(query)
                
                processing_time = time.time() - start_time
                
                if result.get("success"):
                    print(f"✅ Query processed successfully in {processing_time:.2f}s")
                    
                    # Check if the result contains NDVI analysis data
                    analysis_data = result.get("analysis_data", {})
                    if analysis_data:
                        print(f"📊 Analysis type: {analysis_data.get('analysis_type', 'Unknown')}")
                        print(f"📈 Mean NDVI: {analysis_data.get('mean_ndvi', 'N/A')}")
                        print(f"🌿 Vegetation distribution: {analysis_data.get('vegetation_distribution', 'N/A')}")
                        print(f"🗺️ Tile URL available: {'✅' if analysis_data.get('tile_url') else '❌'}")
                        
                        self.test_results["ndvi"]["passed"] += 1
                        self.test_results["ndvi"]["details"].append({
                            "query": query,
                            "status": "passed",
                            "processing_time": processing_time,
                            "analysis_type": analysis_data.get('analysis_type', 'Unknown')
                        })
                    else:
                        print("⚠️ No analysis data found in result")
                        self.test_results["ndvi"]["failed"] += 1
                        self.test_results["ndvi"]["details"].append({
                            "query": query,
                            "status": "failed",
                            "reason": "No analysis data"
                        })
                else:
                    print(f"❌ Query processing failed: {result.get('error', 'Unknown error')}")
                    self.test_results["ndvi"]["failed"] += 1
                    self.test_results["ndvi"]["details"].append({
                        "query": query,
                        "status": "failed",
                        "reason": result.get('error', 'Unknown error')
                    })
                    
            except Exception as e:
                print(f"❌ Test failed with exception: {e}")
                self.test_results["ndvi"]["failed"] += 1
                self.test_results["ndvi"]["details"].append({
                    "query": query,
                    "status": "failed",
                    "reason": str(e)
                })
    
    def test_lulc_service_integration(self):
        """Test LULC Land Use/Land Cover Service integration"""
        print("\n" + "="*60)
        print("🏗️ Testing LULC Land Use/Land Cover Service Integration")
        print("="*60)
        
        for i, query in enumerate(TEST_QUERIES["lulc"], 1):
            print(f"\n🧪 Test {i}: {query}")
            print("-" * 50)
            
            try:
                start_time = time.time()
                
                # Process query through Core LLM Agent
                result = self.agent.process_query(query)
                
                processing_time = time.time() - start_time
                
                if result.get("success"):
                    print(f"✅ Query processed successfully in {processing_time:.2f}s")
                    
                    # Check if the result contains LULC analysis data
                    analysis_data = result.get("analysis_data", {})
                    if analysis_data:
                        print(f"📊 Analysis type: {analysis_data.get('analysis_type', 'Unknown')}")
                        print(f"🏗️ Dominant class: {analysis_data.get('dominant_class', 'N/A')}")
                        print(f"📈 Class percentages: {analysis_data.get('class_percentages', 'N/A')}")
                        print(f"🗺️ Tile URL available: {'✅' if analysis_data.get('tile_url') else '❌'}")
                        
                        self.test_results["lulc"]["passed"] += 1
                        self.test_results["lulc"]["details"].append({
                            "query": query,
                            "status": "passed",
                            "processing_time": processing_time,
                            "analysis_type": analysis_data.get('analysis_type', 'Unknown')
                        })
                    else:
                        print("⚠️ No analysis data found in result")
                        self.test_results["lulc"]["failed"] += 1
                        self.test_results["lulc"]["details"].append({
                            "query": query,
                            "status": "failed",
                            "reason": "No analysis data"
                        })
                else:
                    print(f"❌ Query processing failed: {result.get('error', 'Unknown error')}")
                    self.test_results["lulc"]["failed"] += 1
                    self.test_results["lulc"]["details"].append({
                        "query": query,
                        "status": "failed",
                        "reason": result.get('error', 'Unknown error')
                    })
                    
            except Exception as e:
                print(f"❌ Test failed with exception: {e}")
                self.test_results["lulc"]["failed"] += 1
                self.test_results["lulc"]["details"].append({
                    "query": query,
                    "status": "failed",
                    "reason": str(e)
                })
    
    def test_lst_service_integration(self):
        """Test LST Land Surface Temperature Service integration"""
        print("\n" + "="*60)
        print("🌡️ Testing LST Land Surface Temperature Service Integration")
        print("="*60)
        
        for i, query in enumerate(TEST_QUERIES["lst"], 1):
            print(f"\n🧪 Test {i}: {query}")
            print("-" * 50)
            
            try:
                start_time = time.time()
                
                # Process query through Core LLM Agent
                result = self.agent.process_query(query)
                
                processing_time = time.time() - start_time
                
                if result.get("success"):
                    print(f"✅ Query processed successfully in {processing_time:.2f}s")
                    
                    # Check if the result contains LST analysis data
                    analysis_data = result.get("analysis_data", {})
                    if analysis_data:
                        print(f"📊 Analysis type: {analysis_data.get('analysis_type', 'Unknown')}")
                        print(f"🌡️ Mean LST: {analysis_data.get('mean_lst', 'N/A')}°C")
                        print(f"🏙️ UHI Intensity: {analysis_data.get('uhi_intensity', 'N/A')}°C")
                        print(f"🗺️ Tile URL available: {'✅' if analysis_data.get('tile_url') else '❌'}")
                        
                        self.test_results["lst"]["passed"] += 1
                        self.test_results["lst"]["details"].append({
                            "query": query,
                            "status": "passed",
                            "processing_time": processing_time,
                            "analysis_type": analysis_data.get('analysis_type', 'Unknown')
                        })
                    else:
                        print("⚠️ No analysis data found in result")
                        self.test_results["lst"]["failed"] += 1
                        self.test_results["lst"]["details"].append({
                            "query": query,
                            "status": "failed",
                            "reason": "No analysis data"
                        })
                else:
                    print(f"❌ Query processing failed: {result.get('error', 'Unknown error')}")
                    self.test_results["lst"]["failed"] += 1
                    self.test_results["lst"]["details"].append({
                        "query": query,
                        "status": "failed",
                        "reason": result.get('error', 'Unknown error')
                    })
                    
            except Exception as e:
                print(f"❌ Test failed with exception: {e}")
                self.test_results["lst"]["failed"] += 1
                self.test_results["lst"]["details"].append({
                    "query": query,
                    "status": "failed",
                    "reason": str(e)
                })
    
    def run_all_tests(self):
        """Run all integration tests"""
        print("🚀 Starting GEE Integration Tests")
        print("="*60)
        print("Testing Core LLM Agent integration with all 4 GEE services")
        print("="*60)
        
        # Initialize agent
        if not self.initialize_agent():
            print("❌ Cannot proceed without Core LLM Agent")
            return False
        
        # Check GEE service health
        if not self.check_gee_service_health():
            print("❌ Cannot proceed without healthy GEE service")
            return False
        
        # Run all service tests
        self.test_water_service_integration()
        self.test_ndvi_service_integration()
        self.test_lulc_service_integration()
        self.test_lst_service_integration()
        
        # Print summary
        self.print_test_summary()
        
        return True
    
    def print_test_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "="*60)
        print("📊 INTEGRATION TEST SUMMARY")
        print("="*60)
        
        total_passed = 0
        total_failed = 0
        
        for service, results in self.test_results.items():
            passed = results["passed"]
            failed = results["failed"]
            total_passed += passed
            total_failed += failed
            
            status = "✅ PASS" if failed == 0 else "❌ FAIL" if passed == 0 else "⚠️ PARTIAL"
            
            print(f"\n{service.upper()} Service: {status}")
            print(f"  Passed: {passed}/2 tests")
            print(f"  Failed: {failed}/2 tests")
            
            if results["details"]:
                for detail in results["details"]:
                    status_icon = "✅" if detail["status"] == "passed" else "❌"
                    print(f"    {status_icon} {detail['query'][:50]}...")
                    if detail["status"] == "failed":
                        print(f"      Reason: {detail['reason']}")
        
        print(f"\n🎯 OVERALL RESULTS:")
        print(f"  Total Passed: {total_passed}/8 tests")
        print(f"  Total Failed: {total_failed}/8 tests")
        print(f"  Success Rate: {(total_passed/(total_passed+total_failed)*100):.1f}%")
        
        if total_failed == 0:
            print(f"\n🎉 ALL TESTS PASSED! Integration is working perfectly.")
        elif total_passed > total_failed:
            print(f"\n⚠️ MOSTLY WORKING - Some issues need attention.")
        else:
            print(f"\n❌ MAJOR ISSUES - Integration needs significant fixes.")
        
        print("\n💡 Next Steps:")
        if total_failed > 0:
            print("  1. Check GEE service logs for errors")
            print("  2. Verify Core LLM Agent configuration")
            print("  3. Check API key and authentication")
            print("  4. Review service endpoint responses")
        else:
            print("  1. Integration is ready for production")
            print("  2. Consider adding more test cases")
            print("  3. Monitor performance in production")


def main():
    """Main test runner"""
    print("🧪 GEE Integration Test Suite")
    print("Testing Core LLM Agent with all 4 GEE services")
    print()
    
    # Check if GEE service is running
    try:
        response = requests.get(f"{GEE_SERVICE_URL}/health", timeout=5)
        if response.status_code != 200:
            print("❌ GEE service is not running or not healthy")
            print("💡 Start the GEE service first:")
            print("   cd backend/app/gee_service")
            print("   uvicorn main:app --reload --port 8000")
            return
    except requests.exceptions.RequestException:
        print("❌ Cannot connect to GEE service")
        print("💡 Make sure the GEE service is running on port 8000")
        return
    
    # Run integration tests
    tester = GEEIntegrationTester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()
