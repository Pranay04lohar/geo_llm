#!/usr/bin/env python3
"""
Test Core LLM Agent Integration - Simple Test

This test verifies that the Core LLM Agent can process queries
and connect to GEE services properly.
"""

import sys
import time
from pathlib import Path

# Add the app directory to the path
sys.path.append(str(Path(__file__).parent / "app"))

def test_core_llm_agent():
    """Test Core LLM Agent with a simple query"""
    print("🤖 Testing Core LLM Agent Integration")
    print("=" * 50)
    
    try:
        from services.core_llm_agent import CoreLLMAgent
        
        # Initialize agent
        print("🚀 Initializing Core LLM Agent...")
        agent = CoreLLMAgent(enable_debug=True)
        print("✅ Core LLM Agent initialized")
        
        # Test simple query
        test_query = "What is the water coverage in Mumbai region?"
        print(f"\n🧪 Testing query: {test_query}")
        
        start_time = time.time()
        result = agent.process_query(test_query)
        processing_time = time.time() - start_time
        
        print(f"⏱️ Processing time: {processing_time:.2f}s")
        print(f"🔍 Result keys: {list(result.keys())}")
        
        success = result.get("success") or result.get("metadata", {}).get("success")
        if success:
            print("✅ Query processed successfully!")
            
            # Check analysis data
            analysis_data = result.get("analysis_data", {})
            if analysis_data:
                print(f"📊 Analysis type: {analysis_data.get('analysis_type', 'Unknown')}")
                
                # Show detailed analysis based on type
                analysis_type = analysis_data.get('analysis_type', '').lower()
                if analysis_type == 'water':
                    print(f"   💧 Water percentage: {analysis_data.get('water_percentage', 'N/A')}%")
                    print(f"   🏜️ Non-water percentage: {analysis_data.get('non_water_percentage', 'N/A')}%")
                elif analysis_type == 'ndvi':
                    print(f"   🌱 Mean NDVI: {analysis_data.get('mean_ndvi', 'N/A')}")
                    print(f"   📊 Min NDVI: {analysis_data.get('min_ndvi', 'N/A')}")
                    print(f"   📈 Max NDVI: {analysis_data.get('max_ndvi', 'N/A')}")
                elif analysis_type == 'lulc':
                    print(f"   🏘️ Dominant class: {analysis_data.get('dominant_class', 'N/A')}")
                    class_pct = analysis_data.get('class_percentages', {})
                    if class_pct:
                        print(f"   📊 Class distribution: {class_pct}")
                elif analysis_type == 'lst':
                    print(f"   🌡️ Mean LST: {analysis_data.get('mean_lst', 'N/A')}°C")
                    print(f"   🏙️ UHI intensity: {analysis_data.get('uhi_intensity', 'N/A')}°C")
                
                print(f"🗺️ Tile URL: {'✅' if analysis_data.get('tile_url') else '❌'}")
            else:
                print("⚠️ No analysis data found")

            # Check natural language summary
            summary = result.get("summary", "")
            if summary and summary != "Analysis completed. See details for metrics and map visualization.":
                print(f"🗣️ Natural Language Summary: {summary}")
            else:
                print("⚠️ Natural language summary not generated properly")
                print(f"🔍 Summary field: {summary}")

            # Debug: Show full result if there are issues
            if not analysis_data or not summary:
                print(f"🔍 Full result: {result}")
        else:
            print(f"❌ Query processing failed: {result.get('error', 'Unknown error')}")
            print(f"🔍 Full result: {result}")
        
        return bool(success)
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        print("Full traceback:")
        print(traceback.format_exc())
        return False

def test_multiple_queries():
    """Test multiple queries to verify different services"""
    print("\n🧪 Testing Multiple Queries")
    print("=" * 50)
    
    try:
        from services.core_llm_agent import CoreLLMAgent
        
        agent = CoreLLMAgent(enable_debug=True)
        
        test_queries = [
            "What is the water coverage in Mumbai region?",
            "Analyze vegetation health in Delhi area for 2023",
            "What is the land use classification for Mumbai city?",
            "What is the land surface temperature in Delhi?"
        ]
        
        results = []
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n🧪 Test {i}: {query}")
            print("-" * 40)
            
            start_time = time.time()
            result = agent.process_query(query)
            processing_time = time.time() - start_time
            
            success = result.get("success") or result.get("metadata", {}).get("success")
            status = "✅ PASS" if success else "❌ FAIL"
            
            print(f"{status} - {processing_time:.2f}s")
            
            if success:
                analysis_data = result.get("analysis_data", {})
                print(f"   Analysis type: {analysis_data.get('analysis_type', 'Unknown')}")
            else:
                print(f"   Error: {result.get('error', 'Unknown error')}")
            
            results.append(success)
        
        # Summary
        passed = sum(results)
        total = len(results)
        
        print(f"\n📊 SUMMARY:")
        print(f"   Passed: {passed}/{total} queries")
        print(f"   Success Rate: {(passed/total*100):.1f}%")
        
        return passed == total
        
    except Exception as e:
        print(f"❌ Multiple queries test failed: {e}")
        return False

def main():
    """Run all Core LLM Agent tests"""
    print("🧪 Core LLM Agent Integration Test Suite")
    print("=" * 60)
    
    # Test 1: Single query
    test1_success = test_core_llm_agent()
    
    # Test 2: Multiple queries
    test2_success = test_multiple_queries()
    
    # Final summary
    print("\n" + "=" * 60)
    print("📊 FINAL SUMMARY")
    print("=" * 60)
    
    if test1_success and test2_success:
        print("🎉 ALL TESTS PASSED! Core LLM Agent integration is working!")
        print("💡 The integration tests should now work properly.")
    elif test1_success or test2_success:
        print("⚠️ PARTIAL SUCCESS - Some tests passed, some failed.")
        print("💡 Check the error messages above for specific issues.")
    else:
        print("❌ ALL TESTS FAILED - Core LLM Agent integration has issues.")
        print("💡 Check the error messages above and fix the integration.")
    
    return test1_success and test2_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)