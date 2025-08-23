#!/usr/bin/env python3
"""
Minimal debug to trace the exact error location
"""

import sys
import os
import traceback

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

def minimal_debug():
    """Minimal debug to find exact error location."""
    
    try:
        from app.services.gee import GEETool
        
        print("🔍 Minimal Debug - Tracing Error Location")
        print("=" * 50)
        
        # Initialize GEE tool
        gee_tool = GEETool()
        
        # Test climate-related query
        climate_query = "Analyze climate patterns and air quality in Mumbai"
        print(f"📊 Query: '{climate_query}'")
        
        # Process the query with detailed error tracing
        print("🔄 Processing query...")
        result = gee_tool.process_query(
            query=climate_query,
            locations=["Mumbai"],
            evidence=["test:minimal_debug"]
        )
        
        print("✅ Result received!")
        print(f"📊 Analysis: {result.get('analysis', 'No analysis')}")
        print(f"🗺️ ROI: {result.get('roi', 'No ROI')}")
        print(f"📋 Evidence: {result.get('evidence', [])}")
        
        return result
        
    except Exception as e:
        print(f"❌ Detailed error: {e}")
        print("\n🔍 Full traceback:")
        traceback.print_exc()
        return None

if __name__ == "__main__":
    minimal_debug()
