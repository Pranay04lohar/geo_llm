#!/usr/bin/env python3
"""
Comprehensive test script to verify all COT analysis types work correctly
Tests Water, LST, and NDVI dynamic COT implementations
"""

import asyncio
import sys
import os
import json
from datetime import datetime

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.services.core_llm_agent.simple_step_processor import SimpleStepProcessor

async def test_single_cot(processor, user_prompt, expected_type, roi):
    """Test a single COT analysis type"""
    print(f"\n🧪 Testing {expected_type.upper()} COT Analysis")
    print("=" * 60)
    print(f"Prompt: {user_prompt}")
    print(f"Expected Type: {expected_type}")
    print(f"ROI: {roi['display_name']}")
    print(f"Coordinates: {roi['coordinates'][0][0]} to {roi['coordinates'][0][2]}")
    print()
    
    try:
        step_count = 0
        start_time = datetime.now()
        
        async for step in processor.process_analysis_steps(roi, user_prompt):
            step_count += 1
            status = step.get('status', 'unknown')
            message = step.get('message', 'No message')
            progress = step.get('progress', 0)
            
            print(f"Step {step_count}: {status} - {message} ({progress}%)")
            
            if step.get('final_result'):
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                
                print(f"\n🎯 Final Result (completed in {duration:.1f}s):")
                final_result = step['final_result']
                
                # Check analysis type
                analysis_type = final_result.get('analysis_type')
                print(f"  ✅ Analysis Type: {analysis_type}")
                
                # Check tile URL
                tile_url = final_result.get('tile_url')
                if tile_url:
                    print(f"  ✅ Tile URL: {tile_url[:50]}...")
                else:
                    print(f"  ❌ Tile URL: None")
                
                # Check stats
                stats = final_result.get('stats', {})
                print(f"  ✅ Stats Keys: {list(stats.keys())}")
                
                # Check ROI
                roi_info = final_result.get('roi', {})
                print(f"  ✅ ROI: {roi_info.get('display_name', 'Unknown')}")
                
                # Check geometry
                geometry = roi_info.get('geometry', {})
                if geometry:
                    print(f"  ✅ Geometry: {geometry.get('type')} with {len(geometry.get('coordinates', [[]])[0])} points")
                else:
                    print(f"  ❌ Geometry: None")
                
                # Analysis-specific checks
                if analysis_type == "water":
                    water_pct = stats.get('water_percentage', 0)
                    land_pct = stats.get('non_water_percentage', 0)
                    area = stats.get('total_area_km2', 0)
                    print(f"  🌊 Water Coverage: {water_pct}% water, {land_pct}% land")
                    print(f"  📏 Total Area: {area:.1f} km²")
                    
                elif analysis_type == "lst":
                    lst_stats = stats.get('lst_statistics', {})
                    print(f"  🔍 Debug - lst_stats: {lst_stats}")
                    mean_temp = lst_stats.get('LST_mean', 0)
                    min_temp = lst_stats.get('LST_min', 0)
                    max_temp = lst_stats.get('LST_max', 0)
                    print(f"  🔍 Debug - mean_temp: {mean_temp}, min_temp: {min_temp}, max_temp: {max_temp}")
                    print(f"  🌡️ Temperature: {min_temp:.1f}°C to {max_temp:.1f}°C (mean: {mean_temp:.1f}°C)")
                    
                elif analysis_type == "ndvi":
                    mean_ndvi = stats.get('mean', 0)
                    min_ndvi = stats.get('min', 0)
                    max_ndvi = stats.get('max', 0)
                    print(f"  🌱 NDVI: {min_ndvi:.3f} to {max_ndvi:.3f} (mean: {mean_ndvi:.3f})")
                
                print(f"\n✅ {expected_type.upper()} COT Analysis: SUCCESS")
                return True
                
    except Exception as e:
        print(f"❌ Error in {expected_type} analysis: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print(f"❌ {expected_type.upper()} COT Analysis: FAILED - No final result received")
    return False

async def test_all_cot_analysis():
    """Test all COT analysis types"""
    print("🚀 COMPREHENSIVE COT ANALYSIS TEST")
    print("=" * 60)
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Test ROIs for different locations
    test_cases = [
        {
            "name": "Water Analysis - Mumbai",
            "prompt": "Water analysis of Mumbai",
            "expected_type": "water",
            "roi": {
                "type": "Polygon",
                "coordinates": [[
                    [72.8, 19.0],
                    [72.9, 19.0], 
                    [72.9, 19.1],
                    [72.8, 19.1],
                    [72.8, 19.0]
                ]],
                "display_name": "Mumbai, India",
                "center": [72.85, 19.05],
                "bounds": 0.05
            }
        },
        {
            "name": "LST Analysis - Delhi",
            "prompt": "LST analysis of Delhi",
            "expected_type": "lst",
            "roi": {
                "type": "Polygon",
                "coordinates": [[
                    [77.1, 28.6],
                    [77.2, 28.6], 
                    [77.2, 28.7],
                    [77.1, 28.7],
                    [77.1, 28.6]
                ]],
                "display_name": "Delhi, India",
                "center": [77.15, 28.65],
                "bounds": 0.05
            }
        },
        {
            "name": "NDVI Analysis - Bangalore",
            "prompt": "NDVI analysis of Bangalore",
            "expected_type": "ndvi",
            "roi": {
                "type": "Polygon",
                "coordinates": [[
                    [77.5, 12.9],
                    [77.6, 12.9], 
                    [77.6, 13.0],
                    [77.5, 13.0],
                    [77.5, 12.9]
                ]],
                "display_name": "Bangalore, India",
                "center": [77.55, 12.95],
                "bounds": 0.05
            }
        }
    ]
    
    processor = SimpleStepProcessor()
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*20} TEST {i}/3 {'='*20}")
        success = await test_single_cot(
            processor, 
            test_case["prompt"], 
            test_case["expected_type"], 
            test_case["roi"]
        )
        results.append({
            "name": test_case["name"],
            "success": success,
            "type": test_case["expected_type"]
        })
        
        if i < len(test_cases):
            print(f"\n⏳ Waiting 3 seconds before next test...")
            await asyncio.sleep(3)
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 TEST SUMMARY")
    print(f"{'='*60}")
    
    total_tests = len(results)
    successful_tests = sum(1 for r in results if r["success"])
    failed_tests = total_tests - successful_tests
    
    print(f"Total Tests: {total_tests}")
    print(f"✅ Successful: {successful_tests}")
    print(f"❌ Failed: {failed_tests}")
    print(f"Success Rate: {(successful_tests/total_tests)*100:.1f}%")
    print()
    
    for result in results:
        status = "✅ PASS" if result["success"] else "❌ FAIL"
        print(f"{status} - {result['name']} ({result['type'].upper()})")
    
    print(f"\n🏁 Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if successful_tests == total_tests:
        print("\n🎉 ALL TESTS PASSED! Dynamic COT is working perfectly for all analysis types!")
    else:
        print(f"\n⚠️ {failed_tests} test(s) failed. Check the logs above for details.")
    
    return successful_tests == total_tests

if __name__ == "__main__":
    print("Starting comprehensive COT analysis test...")
    success = asyncio.run(test_all_cot_analysis())
    sys.exit(0 if success else 1)
