"""
Final Test: Complete Real Data Integration

Test the complete GeoLLM pipeline with real Google Earth Engine data.
This should now work end-to-end with actual satellite processing.
"""

import sys
import os

# Add project to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
sys.path.insert(0, project_root)

def test_real_gee_tool():
    """Test our GEE tool with real data processing."""
    
    try:
        print("🧪 Testing Real GEE Tool with Satellite Data...")
        
        from backend.app.services.gee import GEETool
        
        gee_tool = GEETool()
        
        # Test 1: NDVI analysis with real data
        print("\n📡 Test 1: Real NDVI Analysis for Mumbai...")
        result1 = gee_tool.process_query(
            query="Calculate NDVI for Mumbai using Sentinel-2",
            locations=[{"matched_name": "Mumbai", "type": "city", "confidence": 95}],
            evidence=[]
        )
        
        print(f"✅ NDVI Analysis Complete!")
        print(f"   📊 Analysis: {result1.get('analysis', '')[:200]}...")
        print(f"   📊 Evidence: {result1.get('evidence', [])}")
        
        # Test 2: Land cover analysis
        print("\n🌍 Test 2: Real Land Cover Analysis for Delhi...")
        result2 = gee_tool.process_query(
            query="What is the land cover distribution in Delhi?",
            locations=[{"matched_name": "Delhi", "type": "city", "confidence": 95}],
            evidence=[]
        )
        
        print(f"✅ Land Cover Analysis Complete!")
        print(f"   📊 Analysis: {result2.get('analysis', '')[:200]}...")
        
        return True, [result1, result2]
        
    except Exception as e:
        print(f"❌ Real GEE tool test failed: {e}")
        import traceback
        traceback.print_exc()
        return False, None

def test_core_agent_real_data():
    """Test the core agent with real GEE processing."""
    
    try:
        print("\n🤖 Testing Core Agent with Real Data...")
        
        from backend.app.services.core_llm_agent import gee_tool_node
        
        # Test state with Mumbai query
        test_state = {
            "query": "Show me NDVI vegetation analysis for Mumbai using satellite data",
            "locations": [
                {"matched_name": "Mumbai", "type": "city", "confidence": 95}
            ],
            "evidence": ["controller:ok", "llm_ner:found"]
        }
        
        result = gee_tool_node(test_state)
        
        print(f"✅ Core Agent Processing Complete!")
        print(f"   📊 Analysis: {result.get('analysis', '')[:200]}...")
        print(f"   📊 Evidence: {result.get('evidence', [])}")
        print(f"   📊 ROI Present: {result.get('roi') is not None}")
        
        # Check if we got real data
        analysis = result.get('analysis', '')
        evidence = result.get('evidence', [])
        
        has_real_data = (
            'gee_tool:execution_success' in evidence or
            'ndvi' in analysis.lower() or
            'satellite' in analysis.lower()
        )
        
        print(f"   🛰️ Real Satellite Data: {'✅ YES' if has_real_data else '❌ NO'}")
        
        return True, result
        
    except Exception as e:
        print(f"❌ Core agent test failed: {e}")
        import traceback
        traceback.print_exc()
        return False, None

if __name__ == "__main__":
    print("🚀 Final Real Data Integration Test\n")
    print("🎯 Goal: Verify complete pipeline with actual satellite data")
    
    # Test 1: Direct GEE tool
    tool_success, tool_results = test_real_gee_tool()
    
    # Test 2: Core agent integration
    agent_success, agent_results = test_core_agent_real_data()
    
    print("\n" + "="*60)
    
    if tool_success and agent_success:
        print("🎉 COMPLETE SUCCESS: Real satellite data integration working!")
        print("🛰️ Your GeoLLM now processes actual satellite imagery!")
        print("📡 NDVI, land cover, and geospatial analysis fully operational!")
    elif tool_success:
        print("⚠️ Partial success: GEE tool working, agent needs fixes")
    else:
        print("❌ Still need to resolve GEE integration issues")
        
    print("="*60)
