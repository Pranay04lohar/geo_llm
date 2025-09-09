# #!/usr/bin/env python3
# """
# Simple validation test to verify the water service fix
# """

# import sys
# import os
# import logging

# # Set up logging
# logging.basicConfig(level=logging.INFO)

# def test_fixed_water_service():
#     """Test the fixed water service"""
    
#     print("Testing Fixed Water Service")
#     print("=" * 50)
    
#     try:
#         from services.water_service import WaterService
        
#         # Test areas with known characteristics
#         test_areas = {
#             "Mumbai_City": {
#                 "roi": {
#                     "type": "Polygon",
#                     "coordinates": [[
#                         [72.82, 19.00],
#                         [72.92, 19.00], 
#                         [72.92, 19.15],
#                         [72.82, 19.15],
#                         [72.82, 19.00]
#                     ]]
#                 },
#                 "expected": "mixed - some water bodies"
#             },
#             "Delhi_Urban": {
#                 "roi": {
#                     "type": "Polygon", 
#                     "coordinates": [[
#                         [77.20, 28.55],
#                         [77.30, 28.55],
#                         [77.30, 28.65], 
#                         [77.20, 28.65],
#                         [77.20, 28.55]
#                     ]]
#                 },
#                 "expected": "low water - urban area"
#             }
#         }
        
#         water_service = WaterService()
        
#         for area_name, test_data in test_areas.items():
#             print(f"\nTesting {area_name}:")
#             print(f"Expected: {test_data['expected']}")
#             print("-" * 40)
            
#             # Get debug info
#             debug_info = water_service.debug_roi_data(test_data['roi'])
#             print(f"Data range: {debug_info['data_summary']}")
            
#             # Test with different thresholds
#             for threshold in [20, 50]:
#                 result = water_service.analyze_water_presence(
#                     roi=test_data['roi'],
#                     threshold=threshold,
#                     include_seasonal=False
#                 )
                
#                 if "error" not in result:
#                     stats = result['mapStats']
#                     print(f"Threshold {threshold}%: Water={stats['water_percentage']}%, "
#                           f"Non-Water={stats['non_water_percentage']}%, "
#                           f"Total pixels={stats['total_pixels']}")
#                 else:
#                     print(f"Error with threshold {threshold}%: {result['error']}")
    
#     except Exception as e:
#         print(f"Error: {e}")
#         import traceback
#         traceback.print_exc()

# if __name__ == "__main__":
#     test_fixed_water_service()


#!/usr/bin/env python3
"""
Final test to verify the water service fix is working correctly
"""

import logging
import sys
import os

logging.basicConfig(level=logging.INFO)

def final_test():
    """Final test with known areas"""
    
    print("Final Water Service Test - Verification")
    print("=" * 50)
    
    try:
        from services.water_service import WaterService
        
        water_service = WaterService()
        
        # Test areas with known characteristics
        test_cases = [
            {
                "name": "Delhi Urban (Should be low water)",
                "roi": {
                    "type": "Polygon",
                    "coordinates": [[
                        [77.20, 28.55],
                        [77.25, 28.55],
                        [77.25, 28.60], 
                        [77.20, 28.60],
                        [77.20, 28.55]
                    ]]
                },
                "threshold": 20,
                "expected": "Low water percentage (urban area)"
            },
            {
                "name": "Yamuna River Area (Should have some water)",
                "roi": {
                    "type": "Polygon",
                    "coordinates": [[
                        [77.25, 28.65],
                        [77.27, 28.65],
                        [77.27, 28.67], 
                        [77.25, 28.67],
                        [77.25, 28.65]
                    ]]
                },
                "threshold": 20,
                "expected": "Higher water percentage (river area)"
            }
        ]
        
        for test_case in test_cases:
            print(f"\nTesting: {test_case['name']}")
            print(f"Expected: {test_case['expected']}")
            print("-" * 50)
            
            # Get debug info first
            debug_info = water_service.debug_roi_data(test_case['roi'])
            occurrence_stats = debug_info.get('occurrence_stats', {})
            
            print(f"Raw occurrence - Min: {occurrence_stats.get('occurrence_min', 'N/A')}, "
                  f"Max: {occurrence_stats.get('occurrence_max', 'N/A')}, "
                  f"Mean: {occurrence_stats.get('occurrence_mean', 'N/A'):.2f}")
            
            # Test the water analysis
            result = water_service.analyze_water_presence(
                roi=test_case['roi'],
                threshold=test_case['threshold'],
                include_seasonal=False
            )
            
            if "error" not in result:
                stats = result['mapStats']
                print(f"RESULT: Water={stats['water_percentage']}%, "
                      f"Non-Water={stats['non_water_percentage']}%, "
                      f"Total pixels={stats['total_pixels']}")
                
                # Validate results make sense
                water_pct = float(stats['water_percentage'])
                non_water_pct = float(stats['non_water_percentage'])
                
                if abs(water_pct + non_water_pct - 100) < 0.1:  # Should sum to ~100%
                    print("✅ Percentages sum correctly")
                else:
                    print(f"❌ Percentages don't sum to 100%: {water_pct + non_water_pct}")
                
                if water_pct == 100 and non_water_pct == 0:
                    print("❌ Still getting 100% water - issue not fixed")
                else:
                    print("✅ Getting realistic water percentages")
                    
            else:
                print(f"❌ Error: {result['error']}")
                
        print("\n" + "=" * 50)
        print("Test Summary:")
        print("- If you see realistic percentages (not 100%), the fix worked!")
        print("- Urban areas should show low water percentage")
        print("- River areas should show higher water percentage")
        print("=" * 50)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    final_test()