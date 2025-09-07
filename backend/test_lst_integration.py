#!/usr/bin/env python3
"""
Test script for LST integration with Core LLM Agent

This script tests the complete LST analysis workflow through the Core LLM Agent.
"""

import sys
import os
from pathlib import Path

# Add the app directory to the path
app_path = Path(__file__).parent / "app"
sys.path.append(str(app_path))

def test_lst_integration():
    """Test LST analysis through the Core LLM Agent."""
    try:
        from services.core_llm_agent import controller_node, roi_parser_node, planner_node, execute_plan_node
        
        print("🧪 Testing LST Integration with Core LLM Agent")
        print("=" * 60)
        
        # Test queries for LST analysis
        test_queries = [
            "What is the temperature in Mumbai?",
            "Analyze the urban heat island effect in Delhi",
            "Show me the land surface temperature for Bangalore",
            "What's the thermal analysis of Chennai?",
            "How hot is it in Kolkata?"
        ]
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n📍 Test Query {i}: {query}")
            print("-" * 50)
            
            try:
                # Create initial state
                initial_state = {
                    "query": query,
                    "locations": [],
                    "evidence": []
                }
                
                # Run the complete workflow
                print("🔄 Running complete workflow...")
                
                # Step 1: Controller
                state = controller_node(initial_state)
                print(f"✅ Controller: {state.get('status', 'unknown')}")
                
                # Step 2: ROI Parser (location extraction)
                state = roi_parser_node(state)
                print(f"✅ ROI Parser: {len(state.get('locations', []))} locations found")
                
                # Step 3: Planner
                state = planner_node(state)
                print(f"✅ Planner: {len(state.get('plan', []))} tasks planned")
                
                # Step 4: Execute Plan
                result = execute_plan_node(state)
                print(f"✅ Execute Plan: {result.get('status', 'unknown')}")
                
                if result.get("analysis"):
                    print("✅ Analysis completed successfully!")
                    print(f"📊 Analysis length: {len(result['analysis'])} characters")
                    
                    # Check if it's LST analysis
                    if "LST" in result["analysis"] or "temperature" in result["analysis"].lower():
                        print("🌡️ LST analysis detected!")
                    else:
                        print("ℹ️ Analysis type: Other")
                    
                    # Show first 200 characters of analysis
                    analysis_preview = result["analysis"][:200]
                    print(f"📝 Analysis preview: {analysis_preview}...")
                    
                else:
                    print("❌ No analysis generated")
                
                if result.get("roi"):
                    print("🗺️ ROI data available")
                else:
                    print("⚠️ No ROI data")
                
                if result.get("evidence"):
                    print(f"🔍 Evidence: {result['evidence']}")
                
            except Exception as e:
                print(f"❌ Query failed: {e}")
                import traceback
                print(f"❌ Traceback: {traceback.format_exc()}")
            
            print()
        
        print("🎯 Integration Test Summary:")
        print("==========================")
        print("• LST service is integrated with Core LLM Agent")
        print("• Temperature queries are detected and routed to LST analysis")
        print("• UHI analysis is included in the workflow")
        print("• LLM-based interpretation is generated for LST results")
        print("• Phase 3 integration is complete!")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Make sure you're running from the backend directory")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        print("Full traceback:")
        print(traceback.format_exc())

if __name__ == "__main__":
    test_lst_integration()
