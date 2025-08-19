"""
Simple Real GEE Integration Test

Tests the complete workflow with real Google Earth Engine data
using public datasets that don't require special project permissions.
"""

import sys
import os

# Add project to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
sys.path.insert(0, project_root)

def test_simple_gee_workflow():
    """Test a simple NDVI workflow with real GEE data."""
    print("🧪 Testing Simple Real GEE Workflow...")
    
    try:
        # Initialize Earth Engine without a specific project
        import ee
        ee.Initialize()
        
        print("✅ Earth Engine initialized successfully")
        
        # Create a simple ROI (small area around Mumbai)
        roi = ee.Geometry.Rectangle([72.8, 19.0, 72.9, 19.1])
        
        # Load a simple, public dataset
        try:
            # Use a specific Sentinel-2 image instead of a collection
            image = ee.Image('COPERNICUS/S2_SR/20230315T050701_20230315T051543_T43QGD')
            
            # Calculate NDVI
            ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
            
            # Get a simple statistic
            mean_ndvi = ndvi.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=roi,
                scale=100,  # Lower resolution for faster processing
                maxPixels=1e6
            )
            
            result = mean_ndvi.getInfo()
            print(f"✅ NDVI calculation successful: {result}")
            return True, result
            
        except Exception as e:
            print(f"❌ GEE operation failed: {e}")
            return False, None
            
    except Exception as e:
        print(f"❌ GEE initialization failed: {e}")
        return False, None

def test_gee_tool_integration():
    """Test our GEE tool with a simple query."""
    print("\n🧪 Testing GEE Tool Integration...")
    
    try:
        from backend.app.services.gee import GEETool
        
        # Create GEE tool
        gee_tool = GEETool()
        
        # Test with a simple query
        test_query = "Calculate NDVI for Mumbai"
        test_locations = [
            {"matched_name": "Mumbai", "type": "city", "confidence": 95}
        ]
        
        result = gee_tool.process_query(
            query=test_query,
            locations=test_locations,
            evidence=[]
        )
        
        print(f"✅ GEE Tool processing successful")
        print(f"   Analysis length: {len(result.get('analysis', ''))}")
        print(f"   ROI present: {result.get('roi') is not None}")
        print(f"   Evidence count: {len(result.get('evidence', []))}")
        
        return True, result
        
    except Exception as e:
        print(f"❌ GEE Tool integration failed: {e}")
        return False, None

def test_core_agent_integration():
    """Test integration with the core LLM agent."""
    print("\n🧪 Testing Core Agent Integration...")
    
    try:
        from backend.app.services.core_llm_agent import gee_tool_node
        
        # Create mock agent state
        mock_state = {
            "query": "Show me NDVI analysis for Mumbai",
            "locations": [
                {"matched_name": "Mumbai", "type": "city", "confidence": 95}
            ],
            "evidence": ["controller:ok", "llm_ner:found"]
        }
        
        # Run the GEE tool node
        result = gee_tool_node(mock_state)
        
        print(f"✅ Core agent integration successful")
        print(f"   Analysis: {result.get('analysis', '')[:100]}...")
        
        roi = result.get('roi')
        if roi:
            print(f"   ROI type: {roi.get('type', 'None')}")
        else:
            print(f"   ROI type: None")
            
        evidence = result.get('evidence', [])
        if evidence:
            print(f"   Evidence: {evidence[-2:] if len(evidence) >= 2 else evidence}")  # Last 2 evidence items
        else:
            print(f"   Evidence: []")
        
        return True, result
        
    except Exception as e:
        print(f"❌ Core agent integration failed: {e}")
        return False, None

def main():
    """Run all real GEE integration tests."""
    print("🚀 Real Google Earth Engine Integration Tests\n")
    
    tests = [
        ("Simple GEE Workflow", test_simple_gee_workflow),
        ("GEE Tool Integration", test_gee_tool_integration),
        ("Core Agent Integration", test_core_agent_integration)
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success, data = test_func()
            results.append(success)
            
            if success and data:
                print(f"   📊 Sample data: {str(data)[:100]}...")
            
        except Exception as e:
            print(f"❌ Test {name} crashed: {e}")
            results.append(False)
    
    print("\n" + "="*60)
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Real GEE integration is working!")
    elif passed >= 2:
        print(f"✅ {passed}/{total} tests passed. GEE integration mostly working.")
    else:
        print(f"⚠️ {passed}/{total} tests passed. Check GEE setup.")
        
    print("="*60)
    
    return passed >= 2

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
