#!/usr/bin/env python3
"""
Simple LST test that bypasses the planner to test core workflow

This script tests the LST integration without the complex planner logic.
"""

import sys
import os
from pathlib import Path

# Add the app directory to the path
app_path = Path(__file__).parent / "app"
sys.path.append(str(app_path))

def test_simple_lst():
    """Test LST analysis with a simple direct approach."""
    try:
        from services.core_llm_agent import _run_tool
        
        print("🧪 Testing Simple LST Integration")
        print("=" * 50)
        
        # Test query
        query = "What is the temperature in Mumbai?"
        print(f"📍 Test Query: {query}")
        print("-" * 30)
        
        # Create a simple state with locations
        state = {
            "query": query,
            "locations": [
                {"matched_name": "Mumbai", "type": "city", "confidence": 100.0}
            ],
            "evidence": []
        }
        
        print("🔄 Running GEE Tool directly...")
        
        try:
            # Call the GEE tool directly
            result = _run_tool("GEE_Tool", state)
            
            print(f"✅ GEE Tool Result: {result.get('status', 'unknown')}")
            
            if result.get("analysis"):
                print("✅ Analysis completed successfully!")
                print(f"📊 Analysis length: {len(result['analysis'])} characters")
                print(f"ℹ️ Analysis type: {result.get('analysis_type', 'Other')}")
                print(f"📝 Analysis preview: {result['analysis'][:300]}...")
                
                # Check if it's LST analysis
                if "LST" in result['analysis'] or "temperature" in result['analysis'].lower():
                    print("🌡️ ✅ LST Analysis detected!")
                else:
                    print("❌ LST Analysis NOT detected - still using wrong service")
                    
            else:
                print("❌ No analysis generated")
                
            print(f"🗺️ ROI data available: {bool(result.get('roi'))}")
            print(f"🔍 Evidence: {result.get('evidence', [])}")
            
        except Exception as e:
            print(f"❌ GEE Tool Error: {e}")
            import traceback
            print(f"❌ Traceback: {traceback.format_exc()}")
        
        print("\n🎯 Simple LST Test Summary:")
        print("==========================")
        print("• Direct GEE tool call bypasses planner issues")
        print("• Tests LST detection and routing")
        print("• Verifies analysis generation")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        print("Full traceback:")
        print(traceback.format_exc())

if __name__ == "__main__":
    test_simple_lst()
