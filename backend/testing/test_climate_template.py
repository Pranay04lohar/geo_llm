#!/usr/bin/env python3
"""
Test Climate Analysis Template

Quick test to verify the climate template is properly integrated and functional.
"""

import sys
import os
import json

# Add current directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

def test_climate_template():
    """Test climate analysis template integration."""
    
    try:
        from app.services.gee import GEETool
        
        print("🌤️  Testing Climate Analysis Template")
        print("=" * 50)
        
        # Initialize GEE tool
        gee_tool = GEETool()
        
        # Test climate-related query
        climate_query = "Analyze climate patterns and air quality in Mumbai"
        print(f"📊 Query: '{climate_query}'")
        print()
        
        # Process the query
        print("🔄 Processing query...")
        result = gee_tool.process_query(
            query=climate_query,
            locations=[{
                "matched_name": "Mumbai",
                "type": "city",
                "confidence": 95
            }],
            evidence=["test:climate_template"]
        )
        
        print("✅ Query processed successfully!")
        print()
        
        # Display results
        print("📊 CLIMATE ANALYSIS RESULT:")
        print("-" * 40)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        # Analyze results
        print("\n🔍 TEMPLATE VERIFICATION:")
        print("-" * 25)
        
        evidence = result.get("evidence", [])
        analysis = result.get("analysis", "")
        roi = result.get("roi", {})
        
        # Check if climate template was used
        climate_template_used = any("template_climate_analysis" in ev for ev in evidence)
        
        if roi:
            datasets_used = roi.get("properties", {}).get("processing_metadata", {}).get("datasets_used", [])
            stats = roi.get("properties", {}).get("statistics", {})
        else:
            datasets_used = []
            stats = {}
        
        print(f"✅ Climate Template Used: {climate_template_used}")
        print(f"📦 Datasets Used: {len(datasets_used)} datasets")
        for dataset in datasets_used:
            print(f"   • {dataset}")
        
        # Check for climate-specific data
        print(f"📈 Statistics Available: {len(stats)} metrics")
        for key, value in stats.items():
            print(f"   • {key}: {value}")
        
        # Check if there was an error
        if not roi:
            print("❌ ROI is None - there was likely an error in processing")
            print(f"🔍 Error details: {analysis}")
        else:
            print("✅ ROI successfully generated")
        
        print(f"📄 Analysis Length: {len(analysis)} characters")
        
        return result
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    test_climate_template()
