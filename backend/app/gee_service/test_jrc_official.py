#!/usr/bin/env python3
"""
Test script for JRC Official Water Analysis
Demonstrates proper JRC-compliant water analysis using official water classes
"""

import json
import logging
from services.water_service import WaterService

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_jrc_official_analysis():
    """Test the JRC official water analysis methods"""
    
    print("🌊 Testing JRC Official Water Analysis")
    print("=" * 60)
    
    # Test ROIs
    test_rois = {
        "Delhi_Urban": {
            "type": "Polygon",
            "coordinates": [[
                [77.20, 28.55],
                [77.25, 28.55],
                [77.25, 28.60], 
                [77.20, 28.60],
                [77.20, 28.55]
            ]]
        },
        "Yamuna_River": {
            "type": "Polygon",
            "coordinates": [[
                [77.25, 28.65],
                [77.27, 28.65],
                [77.27, 28.67], 
                [77.25, 28.67],
                [77.25, 28.65]
            ]]
        },
        "Mumbai_Coastal": {
            "type": "Polygon",
            "coordinates": [[
                [72.80, 18.90],
                [72.85, 18.90],
                [72.85, 18.95],
                [72.80, 18.95],
                [72.80, 18.90]
            ]]
        }
    }
    
    # Initialize service
    water_service = WaterService()
    
    for roi_name, roi_geom in test_rois.items():
        print(f"\n{'='*60}")
        print(f"Testing: {roi_name}")
        print("-" * 60)
        
        # Test 1: JRC Official Analysis
        print("1. JRC Official Water Classes (seasonality + max_extent):")
        try:
            jrc_result = water_service.analyze_water_presence_jrc_official(
                roi=roi_geom,
                year=2020  # Use valid JRC year (2000-2021)
            )
            
            if "error" in jrc_result:
                print(f"❌ Error: {jrc_result['error']}")
            else:
                stats = jrc_result['mapStats']
                print(f"✅ Total pixels: {stats.get('total_pixels', 0)}")
                
                # Show JRC official class breakdown
                if 'permanent_water' in stats:
                    perm = stats['permanent_water']
                    print(f"🔵 Permanent water: {perm['percentage']}% ({perm['pixels']} pixels)")
                
                if 'seasonal_water' in stats:
                    seasonal = stats['seasonal_water']
                    print(f"🟢 Seasonal water: {seasonal['percentage']}% ({seasonal['pixels']} pixels)")
                
                if 'no_water' in stats:
                    no_water = stats['no_water']
                    print(f"⚪ No water: {no_water['percentage']}% ({no_water['pixels']} pixels)")
                
                # Show water summary
                if 'water_summary' in stats:
                    summary = stats['water_summary']
                    print(f"🌊 Total water: {summary['water_percentage']}%")
                    print(f"🏞️ No water: {summary['no_water_percentage']}%")
                
                # Show occurrence stats
                if 'occurrence_stats' in stats:
                    occ = stats['occurrence_stats']
                    print(f"📊 Occurrence range: {occ['min_occurrence']}-{occ['max_occurrence']}% (mean: {occ['mean_occurrence']}%)")
                
                print(f"🔬 Methodology: {stats.get('methodology', 'N/A')}")
                
        except Exception as e:
            print(f"❌ JRC Official Error: {e}")
        
        # Test 2: Custom Threshold Analysis (for comparison)
        print("\n2. Custom Threshold Analysis (20%):")
        try:
            custom_result = water_service.analyze_water_presence(
                roi=roi_geom,
                year=2020,  # Use valid JRC year
                threshold=20,
                include_seasonal=False
            )
            
            if "error" in custom_result:
                print(f"❌ Error: {custom_result['error']}")
            else:
                stats = custom_result['mapStats']
                print(f"✅ Total pixels: {stats.get('total_pixels', 0)}")
                print(f"🌊 Water percentage: {stats.get('water_percentage', 0)}%")
                print(f"🏞️ No water percentage: {stats.get('non_water_percentage', 0)}%")
                print(f"🎯 Threshold used: {stats.get('threshold_used', 'N/A')}%")
                
        except Exception as e:
            print(f"❌ Custom Threshold Error: {e}")
        
        # Test 3: Time-series Change Analysis
        print("\n3. Time-series Change Analysis (2018-2020):")
        try:
            change_result = water_service.analyze_water_change_time_series(
                roi=roi_geom,
                start_year=2018,
                end_year=2020  # Use valid JRC years
            )
            
            if "error" in change_result:
                print(f"❌ Error: {change_result['error']}")
            else:
                change_analysis = change_result.get('changeAnalysis', {})
                print(f"📅 Period: {change_analysis.get('start_year', 'N/A')} - {change_analysis.get('end_year', 'N/A')}")
                print(f"🌊 Start water: {change_analysis.get('start_water_pct', 'N/A')}%")
                print(f"🌊 End water: {change_analysis.get('end_water_pct', 'N/A')}%")
                print(f"📈 Change: {change_analysis.get('change_percentage', 'N/A')}%")
                print(f"📊 Direction: {change_analysis.get('change_direction', 'N/A')}")
                print(f"🔬 Methodology: {change_analysis.get('methodology', 'N/A')}")
                
        except Exception as e:
            print(f"❌ Change Analysis Error: {e}")
    
    # Test 4: Quality Information
    print(f"\n{'='*60}")
    print("4. Quality Information & Methodology:")
    print("-" * 60)
    
    try:
        quality_info = water_service.get_water_quality_info()
        
        print(f"📊 Dataset: {quality_info['dataset']}")
        print(f"📏 Resolution: {quality_info['resolution']}")
        print(f"📅 Coverage: {quality_info['temporal_coverage']}")
        
        print("\n🔬 Analysis Methods:")
        for method, description in quality_info['analysis_methods'].items():
            print(f"   {method}: {description}")
        
        print("\n⚠️ Limitations:")
        for limitation in quality_info['limitations']:
            print(f"   • {limitation}")
        
        print("\n💡 Recommendations:")
        for rec in quality_info['recommendations']:
            print(f"   • {rec}")
        
        print("\n🔍 Transparency Notes:")
        for note in quality_info['transparency_notes']:
            print(f"   • {note}")
            
    except Exception as e:
        print(f"❌ Quality Info Error: {e}")
    
    print(f"\n{'='*60}")
    print("🌊 JRC Official Analysis Complete!")
    print("=" * 60)

if __name__ == "__main__":
    test_jrc_official_analysis()
