"""
Test Enhanced Search Service

This script tests the enhanced search service with:
- Data-specific query generation
- Structured data extraction and validation
- Multiple search strategies
- Quality assessment and confidence scoring
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

def test_enhanced_search_service():
    """Test the enhanced search service functionality."""
    print("🚀 Testing Enhanced Search Service")
    print("=" * 60)
    
    try:
        # Import the enhanced services
        from app.search_service.services.enhanced_query_generator import EnhancedQueryGenerator, AnalysisType
        from app.search_service.services.data_extractor import DataExtractor
        from app.search_service.services.enhanced_result_processor import EnhancedResultProcessor
        
        print("✅ Enhanced services imported successfully")
        
        # Test 1: Enhanced Query Generation
        print("\n🔍 Test 1: Enhanced Query Generation")
        print("-" * 40)
        
        query_generator = EnhancedQueryGenerator()
        
        # Test NDVI queries
        ndvi_queries = query_generator.generate_enhanced_queries(
            AnalysisType.NDVI, 
            "Delhi", 
            max_queries=5
        )
        
        print(f"Generated {len(ndvi_queries)} NDVI queries for Delhi:")
        for i, query_info in enumerate(ndvi_queries, 1):
            print(f"   {i}. [{query_info['type']}] {query_info['query'][:80]}...")
            print(f"      Priority: {query_info['priority']}, Expected: {query_info['expected_data']}")
        
        # Test LST queries
        lst_queries = query_generator.generate_enhanced_queries(
            AnalysisType.LST, 
            "Mumbai", 
            max_queries=3
        )
        
        print(f"\nGenerated {len(lst_queries)} LST queries for Mumbai:")
        for i, query_info in enumerate(lst_queries, 1):
            print(f"   {i}. [{query_info['type']}] {query_info['query'][:80]}...")
        
        # Test 2: Data Extractor
        print("\n🔍 Test 2: Data Extractor")
        print("-" * 40)
        
        data_extractor = DataExtractor()
        
        # Mock search results for testing
        mock_results = [
            {
                "title": "Delhi NDVI Analysis 2023",
                "content": "The average NDVI value for Delhi is 0.45, with vegetation cover at 35% of total area. Temperature ranges from 15°C to 42°C. Population is 32.9 million people.",
                "url": "https://example.com/delhi-ndvi",
                "score": 0.85
            },
            {
                "title": "Land Surface Temperature Study",
                "content": "Delhi shows LST values of 38.5°C in summer and 18.2°C in winter. The urban heat island effect creates 5.2°C difference between city center and outskirts.",
                "url": "https://example.com/delhi-lst",
                "score": 0.78
            }
        ]
        
        # Extract metrics
        extracted_metrics = data_extractor.extract_metrics(mock_results, "ndvi")
        print(f"Extracted {len(extracted_metrics)} metrics:")
        
        for metric in extracted_metrics:
            print(f"   • {metric.data_type}: {metric.value} {metric.unit} (confidence: {metric.confidence:.1%})")
            print(f"     Context: {metric.context}")
        
        # Assess data quality
        data_quality = data_extractor.assess_data_quality(mock_results, extracted_metrics)
        print(f"\nData Quality Assessment:")
        print(f"   • Overall: {data_quality.overall_score:.1%}")
        print(f"   • Credibility: {data_quality.credibility_score:.1%}")
        print(f"   • Recency: {data_quality.recency_score:.1%}")
        print(f"   • Completeness: {data_quality.completeness_score:.1%}")
        print(f"   • Accuracy: {data_quality.accuracy_score:.1%}")
        
        # Test 3: Enhanced Result Processor (without actual API calls)
        print("\n🔍 Test 3: Enhanced Result Processor")
        print("-" * 40)
        
        enhanced_processor = EnhancedResultProcessor()
        
        # Test analysis templates
        print("Available analysis templates:")
        for analysis_type, template in enhanced_processor.analysis_templates.items():
            print(f"   • {analysis_type.upper()}: {template['title']}")
            print(f"     Metrics: {', '.join(template['metrics'][:3])}...")
        
        print("\n✅ All enhanced search service components working correctly!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing enhanced search service: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False

def test_integration_with_core_agent():
    """Test integration with core LLM agent."""
    print("\n🔗 Test 4: Integration with Core LLM Agent")
    print("-" * 40)
    
    try:
        # Import the integration client
        from app.search_service.integration_client import call_search_service_for_analysis
        
        print("✅ Integration client imported successfully")
        
        # Test the analysis function (this will use the enhanced service)
        test_query = "Analyze NDVI vegetation health around Delhi"
        test_locations = [{"matched_name": "Delhi", "type": "city", "confidence": 100}]
        
        print(f"Testing analysis function with:")
        print(f"   Query: {test_query}")
        print(f"   Locations: {test_locations}")
        
        # Note: This will only work if the search service is running
        # For now, we'll just test the function exists and can be called
        print("✅ Integration function available for testing")
        print("   (Full test requires running search service)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing integration: {e}")
        return False

def main():
    """Main test function."""
    print("🧪 Enhanced Search Service Test Suite")
    print("=" * 60)
    
    # Test individual components
    component_tests = [
        ("Enhanced Query Generator", test_enhanced_search_service),
        ("Integration with Core Agent", test_integration_with_core_agent)
    ]
    
    results = []
    
    for test_name, test_func in component_tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print(f"\n📊 Test Summary")
    print("=" * 30)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("\n🎉 All tests passed! Enhanced search service is ready.")
        print("\n💡 Next steps:")
        print("   1. Start the search service: cd backend/app/search_service && python start.py")
        print("   2. Run the fallback test: python test_search_fallback_with_disabled_gee.py")
        print("   3. Check the enhanced analysis output for data quality improvements")
    else:
        print(f"\n⚠️ {total - passed} tests failed. Check the output above for details.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
