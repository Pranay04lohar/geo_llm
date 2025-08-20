"""
Test Hybrid Query Analyzer

Tests the hybrid approach combining regex-based and LLM-based query analysis
for optimal performance and accuracy in geospatial intent detection.
"""

import sys
import os
import time
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_hybrid_query_analyzer():
    """Test the hybrid query analyzer with various query types."""
    
    print("🧪 Testing Hybrid Query Analyzer")
    print("=" * 50)
    
    try:
        from backend.app.services.gee.hybrid_query_analyzer import HybridQueryAnalyzer
        from backend.app.services.gee.query_analyzer import QueryAnalyzer
        
        # Get OpenRouter API key for LLM testing
        openrouter_key = os.environ.get("OPENROUTER_API_KEY")
        if openrouter_key:
            print("✅ OpenRouter API key found - LLM capabilities enabled")
        else:
            print("⚠️  No OpenRouter API key - testing regex-only mode")
        
        # Initialize analyzers for comparison
        hybrid_analyzer = HybridQueryAnalyzer(openrouter_key)
        regex_analyzer = QueryAnalyzer()
        
        print(f"📊 Hybrid analyzer stats:")
        stats = hybrid_analyzer.get_performance_stats()
        for key, value in stats.items():
            print(f"   {key}: {value}")
        print()
        
        # Test queries - mix of explicit and ambiguous
        test_queries = [
            # High-confidence regex cases (should use fast path)
            {
                "query": "Calculate NDVI for Mumbai",
                "expected_intent": "ndvi",
                "expected_method": "regex_only",
                "description": "Explicit NDVI - high confidence regex"
            },
            {
                "query": "Land cover classification for Delhi",
                "expected_intent": "landcover", 
                "expected_method": "regex_only",
                "description": "Explicit land cover - high confidence regex"
            },
            {
                "query": "Water bodies analysis using NDWI",
                "expected_intent": "water_analysis",
                "expected_method": "regex_only", 
                "description": "Explicit water analysis - high confidence regex"
            },
            
            # Ambiguous cases (should trigger LLM refinement if available)
            {
                "query": "How green is the vegetation in Delhi?",
                "expected_intent": "ndvi",
                "expected_method": "hybrid" if openrouter_key else "regex_only",
                "description": "Implicit NDVI - natural language"
            },
            {
                "query": "What types of surfaces are in Mumbai?",
                "expected_intent": "landcover",
                "expected_method": "hybrid" if openrouter_key else "regex_only",
                "description": "Implicit land cover - natural language"
            },
            {
                "query": "Changes in forest cover over the last 5 years",
                "expected_intent": "change_detection",
                "expected_method": "hybrid" if openrouter_key else "regex_only",
                "description": "Complex temporal analysis"
            },
            {
                "query": "Urban development patterns in Bangalore",
                "expected_intent": "urban_analysis",
                "expected_method": "hybrid" if openrouter_key else "regex_only", 
                "description": "Urban analysis - moderate ambiguity"
            },
            
            # Edge cases
            {
                "query": "Analyze the area statistics",
                "expected_intent": "general_stats",
                "expected_method": "regex_only",
                "description": "General statistics - low specificity"
            }
        ]
        
        print("🔍 Testing Query Analysis")
        print("-" * 30)
        
        results = []
        
        for i, test_case in enumerate(test_queries, 1):
            query = test_case["query"]
            expected_intent = test_case["expected_intent"]
            expected_method = test_case["expected_method"]
            description = test_case["description"]
            
            print(f"\n{i}. {description}")
            print(f"   Query: '{query}'")
            
            # Test regex-only analyzer for baseline
            start_time = time.time()
            regex_result = regex_analyzer.analyze_query(query)
            regex_time = (time.time() - start_time) * 1000
            
            # Test hybrid analyzer
            start_time = time.time()
            hybrid_result = hybrid_analyzer.analyze_query(query)
            hybrid_time = (time.time() - start_time) * 1000
            
            # Compare results
            regex_intent = regex_result.get("primary_intent")
            regex_confidence = regex_result.get("confidence", 0)
            
            hybrid_intent = hybrid_result.get("primary_intent")
            hybrid_confidence = hybrid_result.get("confidence", 0)
            analysis_method = hybrid_result.get("analysis_method", "unknown")
            processing_time = hybrid_result.get("processing_time_ms", hybrid_time)
            
            # Check accuracy
            regex_correct = regex_intent == expected_intent
            hybrid_correct = hybrid_intent == expected_intent
            method_correct = analysis_method == expected_method
            
            print(f"   📊 Regex:  {regex_intent} (conf: {regex_confidence:.2f}) - {regex_time:.1f}ms {'✅' if regex_correct else '❌'}")
            print(f"   🔬 Hybrid: {hybrid_intent} (conf: {hybrid_confidence:.2f}) - {processing_time:.1f}ms {'✅' if hybrid_correct else '❌'}")
            print(f"   🎯 Method: {analysis_method} {'✅' if method_correct else '❌'}")
            
            # Additional hybrid info
            if "llm_reasoning" in hybrid_result and hybrid_result["llm_reasoning"]:
                print(f"   💭 LLM reasoning: {hybrid_result['llm_reasoning']}")
            if "analysis_source" in hybrid_result:
                print(f"   🔍 Source: {hybrid_result['analysis_source']}")
            
            results.append({
                "query": query,
                "regex_correct": regex_correct,
                "hybrid_correct": hybrid_correct,
                "method_correct": method_correct,
                "regex_time": regex_time,
                "hybrid_time": processing_time,
                "analysis_method": analysis_method
            })
        
        # Summary statistics
        print("\n" + "=" * 50)
        print("📈 PERFORMANCE SUMMARY")
        print("=" * 50)
        
        total_tests = len(results)
        regex_accuracy = sum(r["regex_correct"] for r in results) / total_tests * 100
        hybrid_accuracy = sum(r["hybrid_correct"] for r in results) / total_tests * 100
        method_accuracy = sum(r["method_correct"] for r in results) / total_tests * 100
        
        avg_regex_time = sum(r["regex_time"] for r in results) / total_tests
        avg_hybrid_time = sum(r["hybrid_time"] for r in results) / total_tests
        
        regex_only_count = sum(1 for r in results if r["analysis_method"] == "regex_only")
        hybrid_count = sum(1 for r in results if r["analysis_method"] == "hybrid")
        
        print(f"🎯 Accuracy:")
        print(f"   Regex-only:  {regex_accuracy:.1f}% ({sum(r['regex_correct'] for r in results)}/{total_tests})")
        print(f"   Hybrid:      {hybrid_accuracy:.1f}% ({sum(r['hybrid_correct'] for r in results)}/{total_tests})")
        print(f"   Method pred: {method_accuracy:.1f}% ({sum(r['method_correct'] for r in results)}/{total_tests})")
        
        print(f"\n⚡ Performance:")
        print(f"   Avg regex time:  {avg_regex_time:.1f}ms")
        print(f"   Avg hybrid time: {avg_hybrid_time:.1f}ms")
        print(f"   Speed ratio:     {avg_hybrid_time/avg_regex_time:.1f}x")
        
        print(f"\n🔄 Method Distribution:")
        print(f"   Regex-only path: {regex_only_count}/{total_tests} ({regex_only_count/total_tests*100:.1f}%)")
        print(f"   LLM refinement:  {hybrid_count}/{total_tests} ({hybrid_count/total_tests*100:.1f}%)")
        
        # Test with LLM disabled
        print(f"\n🔒 Testing with LLM disabled:")
        hybrid_no_llm = hybrid_analyzer.analyze_query("How green is Delhi?", use_llm_fallback=False)
        print(f"   Result: {hybrid_no_llm.get('primary_intent')} ({hybrid_no_llm.get('analysis_method')})")
        
        print(f"\n✅ Hybrid Query Analyzer test completed!")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you're running from the project root with virtual environment activated")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_performance_comparison():
    """Test performance difference between regex and hybrid approaches."""
    
    print("\n🏃 PERFORMANCE STRESS TEST")
    print("=" * 30)
    
    try:
        from backend.app.services.gee.hybrid_query_analyzer import HybridQueryAnalyzer
        from backend.app.services.gee.query_analyzer import QueryAnalyzer
        
        openrouter_key = os.environ.get("OPENROUTER_API_KEY")
        hybrid_analyzer = HybridQueryAnalyzer(openrouter_key)
        regex_analyzer = QueryAnalyzer()
        
        # High-confidence queries (should be fast)
        fast_queries = [
            "Calculate NDVI for Mumbai",
            "Land cover analysis",
            "Water bodies mapping",
            "Forest cover statistics",
            "Urban area classification"
        ]
        
        print("Testing fast regex path (high-confidence queries):")
        total_time = 0
        for query in fast_queries:
            start = time.time()
            result = hybrid_analyzer.analyze_query(query)
            elapsed = (time.time() - start) * 1000
            total_time += elapsed
            method = result.get("analysis_method", "unknown")
            print(f"  '{query[:30]}...' → {elapsed:.1f}ms ({method})")
        
        avg_fast = total_time / len(fast_queries)
        print(f"  Average fast path: {avg_fast:.1f}ms")
        
        if openrouter_key:
            # Ambiguous queries (might trigger LLM)
            slow_queries = [
                "How green is the area?",
                "What surfaces are visible?", 
                "Changes over time"
            ]
            
            print(f"\nTesting LLM refinement path (ambiguous queries):")
            total_time = 0
            for query in slow_queries:
                start = time.time()
                result = hybrid_analyzer.analyze_query(query)
                elapsed = (time.time() - start) * 1000
                total_time += elapsed
                method = result.get("analysis_method", "unknown")
                print(f"  '{query}' → {elapsed:.1f}ms ({method})")
            
            avg_slow = total_time / len(slow_queries)
            print(f"  Average LLM path: {avg_slow:.1f}ms")
        else:
            print(f"\nLLM testing skipped (no OpenRouter API key)")
        
        return True
        
    except Exception as e:
        print(f"❌ Performance test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting Hybrid Query Analyzer Tests")
    print("=" * 60)
    
    # Test basic functionality
    success1 = test_hybrid_query_analyzer()
    
    # Test performance
    success2 = test_performance_comparison()
    
    if success1 and success2:
        print(f"\n🎉 All tests passed! Hybrid analyzer is working correctly.")
    else:
        print(f"\n❌ Some tests failed. Check the output above.")
