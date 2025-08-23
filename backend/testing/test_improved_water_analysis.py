#!/usr/bin/env python3
"""
Test Improved Water Analysis

This script tests the enhanced water analysis with proper datasets and water detection logic.
"""

import sys
import os
import json
from typing import Dict, Any

# Add parent directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

def test_improved_water_analysis():
    """Test the improved water analysis implementation."""
    
    try:
        # Import the GEE tool
        from app.services.gee import GEETool
        
        print("🚀 Testing IMPROVED Water Analysis")
        print("=" * 60)
        print("Query: 'Analyze water bodies in Delhi'")
        print("-" * 60)
        
        # Initialize GEE tool
        gee_tool = GEETool()
        
        # Test query
        query = "Analyze water bodies in Delhi"
        locations = [{"matched_name": "Delhi", "type": "city", "confidence": 95}]
        evidence = ["test:improved_water_analysis"]
        
        print("🔄 Processing query with improved water detection...")
        print("   • Using JRC Global Surface Water dataset")
        print("   • Implementing NDWI + MNDWI + JRC fusion")
        print("   • Proper water area calculation")
        print("")
        
        # Process the query
        result = gee_tool.process_query(
            query=query,
            locations=locations,
            evidence=evidence
        )
        
        print("✅ Query processed successfully!")
        print("\n📊 IMPROVED GEE RESPONSE (JSON):")
        print("=" * 60)
        
        # Pretty print the JSON response
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        print("\n🔍 IMPROVEMENTS VERIFICATION:")
        print("-" * 40)
        
        # Check for the improvements
        roi = result.get('roi', {})
        properties = roi.get('properties', {})
        
        # Check datasets_used
        datasets_used = properties.get('processing_metadata', {}).get('datasets_used', [])
        if datasets_used:
            print(f"✅ Datasets Used: {len(datasets_used)} datasets")
            for dataset in datasets_used:
                print(f"   • {dataset}")
        else:
            print("❌ Datasets Used: Still empty")
        
        # Check water area
        water_area_km2 = properties.get('statistics', {}).get('water_area_km2', 0)
        if water_area_km2 > 0:
            print(f"✅ Water Area: {water_area_km2:.3f} km² (Previously was 0)")
        else:
            print(f"❌ Water Area: Still {water_area_km2} km²")
        
        # Check water percentage
        water_percentage = properties.get('statistics', {}).get('water_percentage', 0)
        if water_percentage > 0:
            print(f"✅ Water Percentage: {water_percentage:.2f}% of ROI")
        else:
            print(f"❌ Water Percentage: Still {water_percentage}%")
        
        # Check analysis length
        analysis = result.get('analysis', '')
        if len(analysis) > 500:  # Should be much more detailed now
            print(f"✅ Analysis Detail: {len(analysis)} characters (Much more comprehensive)")
        else:
            print(f"❌ Analysis Detail: Only {len(analysis)} characters")
        
        return result
        
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print("Please ensure GEE dependencies are installed.")
        return None
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    test_improved_water_analysis()
