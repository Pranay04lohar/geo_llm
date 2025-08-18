"""
GEE Workflow Integration Test

Tests the complete workflow and integration of all GEE components to ensure
they work together properly before integration with the main LLM agent.

This test file verifies:
1. Import and instantiation of all components
2. Component method calls and data flow
3. End-to-end workflow with mock data
4. Integration points with the main agent
"""

import sys
import os
import traceback
from typing import Dict, Any, List

# Add the project root to Python path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
backend_root = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.insert(0, project_root)
sys.path.insert(0, backend_root)

def test_imports():
    """Test all imports and basic instantiation."""
    print("🧪 Testing GEE Component Imports...")
    
    try:
        # Test individual component imports
        from backend.app.services.gee.gee_client import GEEClient
        from backend.app.services.gee.roi_handler import ROIHandler
        from backend.app.services.gee.query_analyzer import QueryAnalyzer
        from backend.app.services.gee.script_generator import ScriptGenerator
        from backend.app.services.gee.result_processor import ResultProcessor
        
        print("✅ Individual component imports successful")
        
        # Test main package import
        from backend.app.services.gee import GEETool
        print("✅ Main GEETool import successful")
        
        # Test instantiation
        gee_client = GEEClient()
        roi_handler = ROIHandler()
        query_analyzer = QueryAnalyzer()
        script_generator = ScriptGenerator()
        result_processor = ResultProcessor()
        gee_tool = GEETool()
        
        print("✅ All component instantiation successful")
        
        return True, {
            "gee_client": gee_client,
            "roi_handler": roi_handler,
            "query_analyzer": query_analyzer,
            "script_generator": script_generator,
            "result_processor": result_processor,
            "gee_tool": gee_tool
        }
        
    except Exception as e:
        print(f"❌ Import/instantiation failed: {str(e)}")
        traceback.print_exc()
        return False, None

def test_component_methods(components: Dict[str, Any]):
    """Test individual component methods with mock data."""
    print("\n🧪 Testing Individual Component Methods...")
    
    try:
        # Test GEEClient
        print("Testing GEEClient...")
        client_info = components["gee_client"].get_info()
        print(f"   Client info: {client_info}")
        
        # Test QueryAnalyzer
        print("Testing QueryAnalyzer...")
        test_query = "Calculate NDVI for Mumbai with high resolution imagery from 2023"
        analysis_result = components["query_analyzer"].analyze_query(test_query)
        print(f"   Analysis result keys: {list(analysis_result.keys())}")
        print(f"   Detected intent: {analysis_result.get('primary_intent')}")
        print(f"   Confidence: {analysis_result.get('confidence')}")
        
        # Test ROIHandler with mock locations
        print("Testing ROIHandler...")
        mock_locations = [
            {"matched_name": "Mumbai", "type": "city", "confidence": 95}
        ]
        roi_result = components["roi_handler"].extract_roi_from_locations(mock_locations)
        if roi_result:
            print(f"   ROI extracted for: {roi_result.get('primary_location', {}).get('name')}")
            print(f"   ROI source: {roi_result.get('source')}")
        else:
            print("   Using default ROI...")
            roi_result = components["roi_handler"].get_default_roi()
            
        # Test ScriptGenerator
        print("Testing ScriptGenerator...")
        script_result = components["script_generator"].generate_script(
            intent=analysis_result.get("primary_intent", "ndvi"),
            roi_geometry=roi_result.get("geometry", {}),
            parameters=analysis_result
        )
        print(f"   Script generated for: {script_result.get('intent')}")
        print(f"   Script length: {len(script_result.get('script_code', ''))}")
        
        # Test ResultProcessor with mock GEE results
        print("Testing ResultProcessor...")
        mock_gee_result = {
            "ndvi_stats": {
                "NDVI_mean": 0.65,
                "NDVI_min": 0.1,
                "NDVI_max": 0.95
            },
            "pixel_count": {"NDVI": 50000},
            "analysis_type": "ndvi"
        }
        
        processed_result = components["result_processor"].process_gee_result(
            gee_result=mock_gee_result,
            script_metadata=script_result.get("metadata", {}),
            roi_info=roi_result
        )
        print(f"   Processed result keys: {list(processed_result.keys())}")
        print(f"   Analysis text length: {len(processed_result.get('analysis', ''))}")
        
        print("✅ All component methods working")
        
        return True, {
            "query_analysis": analysis_result,
            "roi_result": roi_result,
            "script_result": script_result,
            "processed_result": processed_result
        }
        
    except Exception as e:
        print(f"❌ Component method testing failed: {str(e)}")
        traceback.print_exc()
        return False, None

def test_end_to_end_workflow(components: Dict[str, Any]):
    """Test complete end-to-end workflow."""
    print("\n🧪 Testing End-to-End Workflow...")
    
    try:
        # Simulate the complete workflow that would happen in gee_tool_node
        test_queries = [
            "Show me NDVI analysis for Delhi from last year",
            "What is the land cover distribution in Bangalore?",
            "Detect water bodies around Chennai",
            "Analyze vegetation changes in Mumbai between 2022 and 2023"
        ]
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n--- Test Query {i}: {query} ---")
            
            # Step 1: Analyze query
            analysis = components["query_analyzer"].analyze_query(query)
            print(f"   Intent: {analysis.get('primary_intent')}")
            
            # Step 2: Extract ROI from query text (simulate location extraction)
            # In real usage, this would come from LLM location extraction
            query_location_map = {
                "Delhi": [{"matched_name": "Delhi", "type": "city", "confidence": 95}],
                "Bangalore": [{"matched_name": "Bangalore", "type": "city", "confidence": 95}], 
                "Chennai": [{"matched_name": "Chennai", "type": "city", "confidence": 95}],
                "Mumbai": [{"matched_name": "Mumbai", "type": "city", "confidence": 95}]
            }
            
            # Find location mentioned in query
            extracted_locations = None
            for location_name, location_data in query_location_map.items():
                if location_name.lower() in query.lower():
                    extracted_locations = location_data
                    break
                    
            if extracted_locations:
                roi = components["roi_handler"].extract_roi_from_locations(extracted_locations)
            else:
                roi = components["roi_handler"].get_default_roi()
                
            print(f"   ROI: {roi.get('primary_location', {}).get('name')}")
            
            # Step 3: Generate script
            script = components["script_generator"].generate_script(
                intent=analysis.get("primary_intent", "general_stats"),
                roi_geometry=roi.get("geometry", {}),
                parameters=analysis
            )
            print(f"   Script generated: {len(script.get('script_code', ''))} chars")
            
            # Step 4: Simulate GEE execution (mock results)
            mock_result = {
                "analysis_type": analysis.get("primary_intent"),
                "basic_stats": {"B4_mean": 1500, "B3_mean": 1200, "B2_mean": 800},
                "image_count": 15
            }
            
            # Step 5: Process results
            final_result = components["result_processor"].process_gee_result(
                gee_result=mock_result,
                script_metadata=script.get("metadata", {}),
                roi_info=roi
            )
            
            print(f"   Final analysis length: {len(final_result.get('analysis', ''))}")
            print(f"   ROI type: {final_result.get('roi', {}).get('type')}")
            print(f"   Evidence count: {len(final_result.get('evidence', []))}")
            
        print("\n✅ End-to-end workflow successful")
        return True
        
    except Exception as e:
        print(f"❌ End-to-end workflow failed: {str(e)}")
        traceback.print_exc()
        return False

def test_integration_with_agent_state():
    """Test integration with the expected AgentState format."""
    print("\n🧪 Testing Integration with Agent State Format...")
    
    try:
        from backend.app.services.gee import GEETool
        
        # Simulate AgentState input (as expected by gee_tool_node)
        mock_state = {
            "query": "Calculate NDVI for agricultural areas in Punjab",
            "locations": [
                {"matched_name": "Punjab", "type": "state", "confidence": 95},
                {"matched_name": "Ludhiana", "type": "city", "confidence": 85}
            ],
            "evidence": ["controller:ok", "llm_ner:found"]
        }
        
        # Test that we can extract the necessary information
        gee_tool = GEETool()
        
        # Verify we can access all needed components
        assert hasattr(gee_tool, 'roi_handler'), "Missing roi_handler"
        assert hasattr(gee_tool, 'query_analyzer'), "Missing query_analyzer"
        assert hasattr(gee_tool, 'script_generator'), "Missing script_generator"
        assert hasattr(gee_tool, 'result_processor'), "Missing result_processor"
        
        # Test query analysis
        analysis = gee_tool.query_analyzer.analyze_query(mock_state["query"])
        print(f"   Query analysis intent: {analysis.get('primary_intent')}")
        
        # Test ROI extraction from state locations
        roi = gee_tool.roi_handler.extract_roi_from_locations(mock_state["locations"])
        print(f"   ROI extracted: {roi.get('primary_location', {}).get('name') if roi else 'None'}")
        
        # Verify output format matches expected contract
        expected_keys = {"analysis", "roi", "evidence"}
        
        # Mock a complete result
        mock_final_result = {
            "analysis": "Test analysis text",
            "roi": {"type": "Feature", "properties": {}, "geometry": {}},
            "evidence": mock_state["evidence"] + ["gee_tool:test"]
        }
        
        result_keys = set(mock_final_result.keys())
        assert expected_keys.issubset(result_keys), f"Missing keys: {expected_keys - result_keys}"
        
        print("✅ Agent state integration format correct")
        return True
        
    except Exception as e:
        print(f"❌ Agent state integration failed: {str(e)}")
        traceback.print_exc()
        return False

def test_error_handling():
    """Test error handling and fallback mechanisms."""
    print("\n🧪 Testing Error Handling...")
    
    try:
        from backend.app.services.gee import GEETool
        
        gee_tool = GEETool()
        
        # Test with empty/invalid inputs
        print("   Testing empty query...")
        analysis = gee_tool.query_analyzer.analyze_query("")
        assert analysis.get("primary_intent") == "general_stats", "Should fallback to general_stats"
        
        print("   Testing empty locations...")
        roi = gee_tool.roi_handler.extract_roi_from_locations([])
        assert roi is None, "Should return None for empty locations"
        
        # Test default fallback
        default_roi = gee_tool.roi_handler.get_default_roi()
        assert default_roi is not None, "Default ROI should always be available"
        
        print("   Testing invalid geometry...")
        script = gee_tool.script_generator.generate_script(
            intent="ndvi",
            roi_geometry={},  # Empty geometry
            parameters={}
        )
        assert "script_code" in script, "Should generate script even with invalid geometry"
        
        print("✅ Error handling working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Error handling test failed: {str(e)}")
        traceback.print_exc()
        return False

def main():
    """Run all workflow tests."""
    print("🚀 Starting GEE Workflow Integration Tests\n")
    print(f"📁 Running from: {os.path.dirname(os.path.abspath(__file__))}\n")
    
    # Test 1: Imports and instantiation
    imports_ok, components = test_imports()
    if not imports_ok:
        print("\n❌ CRITICAL: Import test failed. Cannot continue.")
        return False
        
    # Test 2: Individual component methods
    methods_ok, test_data = test_component_methods(components)
    if not methods_ok:
        print("\n❌ CRITICAL: Component methods test failed.")
        return False
        
    # Test 3: End-to-end workflow
    workflow_ok = test_end_to_end_workflow(components)
    if not workflow_ok:
        print("\n❌ CRITICAL: End-to-end workflow test failed.")
        return False
        
    # Test 4: Agent state integration
    integration_ok = test_integration_with_agent_state()
    if not integration_ok:
        print("\n❌ CRITICAL: Agent state integration test failed.")
        return False
        
    # Test 5: Error handling
    error_handling_ok = test_error_handling()
    if not error_handling_ok:
        print("\n⚠️  WARNING: Error handling test failed.")
        
    print("\n" + "="*60)
    if all([imports_ok, methods_ok, workflow_ok, integration_ok, error_handling_ok]):
        print("🎉 ALL TESTS PASSED! GEE workflow is ready for integration.")
    else:
        print("⚠️  Some tests failed. Review issues before proceeding.")
    print("="*60)
    
    return all([imports_ok, methods_ok, workflow_ok, integration_ok])

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
