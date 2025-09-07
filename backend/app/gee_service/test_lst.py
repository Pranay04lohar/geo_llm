# """
# Test script for LST Service

# This script tests the Land Surface Temperature analysis service
# using a simple geometry around Mumbai, India.
# """

# import sys
# import os
# from pathlib import Path

# # Add the services directory to the path
# services_path = Path(__file__).parent / "services"
# sys.path.append(str(services_path))

# def test_lst_service():
#     """Test the LST service with a simple geometry."""
#     try:
#         # Initialize Earth Engine first
#         import ee
#         ee.Initialize()
#         print("✅ Earth Engine initialized")
        
#         from new_lst import LSTService
        
#         print("🧪 Testing LST Service")
#         print("=" * 50)
        
#         # Create a larger test geometry (Mumbai area)
#         test_geometry = {
#             "type": "Polygon",
#             "coordinates": [[
#                 [72.7, 18.9],  # Southwest
#                 [73.0, 18.9],  # Southeast
#                 [73.0, 19.2],  # Northeast
#                 [72.7, 19.2],  # Northwest
#                 [72.7, 18.9]   # Close polygon
#             ]]
#         }
        
#         # Create ROI data
#         roi_data = {
#             "polygon_geometry": test_geometry,
#             "geometry_tiles": [],
#             "is_tiled": False,
#             "is_fallback": False,
#             "area_km2": 0
#         }
        
#         print(f"📍 Test geometry: Mumbai area (larger)")
#         print(f"📅 Date range: 2024-06-01 to 2024-08-31")
#         print(f"🏙️ UHI analysis: Enabled")
#         print()
        
#         # Test LST analysis
#         result = LSTService.analyze_lst_with_polygon(
#             roi_data=roi_data,
#             start_date="2024-06-01",
#             end_date="2024-08-31",
#             include_uhi=True,
#             include_time_series=False,
#             scale=1000,
#             max_pixels=1e6,
#             exact_computation=False
#         )
        
#         if result.get("success"):
#             print("✅ LST analysis completed successfully!")
#             print()
            
#             # Display results
#             lst_stats = result.get("lst_stats", {})
#             print("🌡️ LST Statistics:")
#             print(f"   • Mean Temperature: {lst_stats.get('LST_mean', 0):.2f}°C")
#             print(f"   • Min Temperature: {lst_stats.get('LST_min', 0):.2f}°C")
#             print(f"   • Max Temperature: {lst_stats.get('LST_max', 0):.2f}°C")
#             print(f"   • Std Deviation: {lst_stats.get('LST_stdDev', 0):.2f}°C")
#             print()
            
#             uhi_intensity = result.get("uhi_intensity", 0)
#             uhi_details = result.get("uhi_details", {})
#             print(f"🏙️ UHI Intensity: {uhi_intensity:.2f}°C")
            
#             # Show detailed UHI information
#             if uhi_details:
#                 method = uhi_details.get("method", "unknown")
#                 print(f"   • Method: {method}")
                
#                 urban_lst = uhi_details.get("urban_lst")
#                 rural_lst = uhi_details.get("rural_lst")
#                 if urban_lst is not None and rural_lst is not None:
#                     print(f"   • Urban LST: {urban_lst:.2f}°C")
#                     print(f"   • Rural LST: {rural_lst:.2f}°C")
                
#                 urban_pixels = uhi_details.get("urban_pixels", 0)
#                 rural_pixels = uhi_details.get("rural_pixels", 0)
#                 urban_percentage = uhi_details.get("urban_percentage", 0)
#                 print(f"   • Urban pixels: {urban_pixels}")
#                 print(f"   • Rural pixels: {rural_pixels}")
#                 print(f"   • Urban coverage: {urban_percentage:.1f}%")
#             print()
            
#             area_km2 = result.get("area_km2", 0)
#             print(f"📊 Area analyzed: {area_km2:.2f} km²")
            
#             image_count = result.get("image_count", 0)
#             print(f"🛰️ MODIS images used: {image_count}")
            
#             # Check if visualization is available
#             tile_urls = result.get("tile_urls", {})
#             if tile_urls.get("urlFormat"):
#                 print(f"🗺️ Visualization: ✅ Available")
#             else:
#                 print(f"🗺️ Visualization: ❌ Not available")
                
#         else:
#             print("❌ LST analysis failed!")
#             error = result.get("error", "Unknown error")
#             error_type = result.get("error_type", "unknown")
#             print(f"   Error: {error}")
#             print(f"   Type: {error_type}")
            
#     except ImportError as e:
#         print(f"❌ Import error: {e}")
#         print("💡 Make sure you're running from the gee_service directory")
#     except Exception as e:
#         print(f"❌ Unexpected error: {e}")
#         import traceback
#         print("Full traceback:")
#         print(traceback.format_exc())

# if __name__ == "__main__":
#     test_lst_service()


"""
Improved test script for LST Service

This script tests the improved Land Surface Temperature analysis service
with better UHI calculation methods.
"""

import sys
import os
from pathlib import Path

# Add the services directory to the path
services_path = Path(__file__).parent / "services"
sys.path.append(str(services_path))

def test_improved_lst_service():
    """Test the improved LST service with better UHI analysis."""
    try:
        # Initialize Earth Engine first
        import ee
        ee.Initialize()
        print("✅ Earth Engine initialized")
        
        from lst_service import LSTService
        
        print("🧪 Testing Improved LST Service")
        print("=" * 60)
        
        # Test multiple geometries to verify robustness
        test_cases = [
            {
                "name": "Mumbai Urban Area",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [72.8, 19.0],  # Southwest - more central Mumbai
                        [72.9, 19.0],  # Southeast
                        [72.9, 19.1],  # Northeast
                        [72.8, 19.1],  # Northwest
                        [72.8, 19.0]   # Close polygon
                    ]]
                },
                "date_range": ("2024-01-01", "2024-08-31")
            },
            {
                "name": "Delhi Urban Area",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [77.1, 28.5],  # Southwest
                        [77.3, 28.5],  # Southeast
                        [77.3, 28.7],  # Northeast
                        [77.1, 28.7],  # Northwest
                        [77.1, 28.5]   # Close polygon
                    ]]
                },
                "date_range": ("2024-01-01", "2024-08-31")
            }
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n📍 Test Case {i}: {test_case['name']}")
            print("-" * 50)
            
            # Create ROI data
            roi_data = {
                "polygon_geometry": test_case["geometry"],
                "geometry_tiles": [],
                "is_tiled": False,
                "is_fallback": False,
                "area_km2": 0
            }
            
            start_date, end_date = test_case["date_range"]
            print(f"📅 Date range: {start_date} to {end_date}")
            print(f"🏙️ UHI analysis: Enabled with improved methods")
            print()
            
            # Test LST analysis
            result = LSTService.analyze_lst_with_polygon(
                roi_data=roi_data,
                start_date=start_date,
                end_date=end_date,
                include_uhi=True,
                include_time_series=False,
                scale=1000,
                max_pixels=1e6,
                exact_computation=False
            )
            
            if result.get("success"):
                print("✅ LST analysis completed successfully!")
                print()
                
                # Display basic LST results
                lst_stats = result.get("lst_stats", {})
                print("🌡️ LST Statistics:")
                print(f"   • Mean Temperature: {lst_stats.get('LST_mean', 0):.2f}°C")
                print(f"   • Min Temperature: {lst_stats.get('LST_min', 0):.2f}°C")
                print(f"   • Max Temperature: {lst_stats.get('LST_max', 0):.2f}°C")
                print(f"   • Std Deviation: {lst_stats.get('LST_stdDev', 0):.2f}°C")
                print()
                
                # Display improved UHI results
                uhi_intensity = result.get("uhi_intensity", 0)
                uhi_details = result.get("uhi_details", {})
                print(f"🏙️ UHI Analysis Results:")
                print(f"   • UHI Intensity: {uhi_intensity:.2f}°C")
                
                if uhi_details:
                    method = uhi_details.get("method", "unknown")
                    print(f"   • Method Used: {method}")
                    
                    # Show method-specific details
                    if method == "dynamic_world_lulc":
                        print(f"   • Data Source: {uhi_details.get('data_source', 'N/A')}")
                        print(f"   • Urban LST: {uhi_details.get('urban_lst', 0):.2f}°C")
                        print(f"   • Rural LST: {uhi_details.get('rural_lst', 0):.2f}°C")
                        print(f"   • Urban Pixels: {uhi_details.get('urban_pixels', 0)}")
                        print(f"   • Rural Pixels: {uhi_details.get('rural_pixels', 0)}")
                        print(f"   • Urban Coverage: {uhi_details.get('urban_percentage', 0):.1f}%")
                    
                    elif method == "modis_land_cover":
                        print(f"   • Data Source: {uhi_details.get('data_source', 'N/A')}")
                        print(f"   • Urban LST: {uhi_details.get('urban_lst', 0):.2f}°C")
                        print(f"   • Rural LST: {uhi_details.get('rural_lst', 0):.2f}°C")
                        print(f"   • Urban Pixels: {uhi_details.get('urban_pixels', 0)}")
                        print(f"   • Rural Pixels: {uhi_details.get('rural_pixels', 0)}")
                    
                    elif method == "esa_worldcover":
                        print(f"   • Data Source: {uhi_details.get('data_source', 'N/A')}")
                        print(f"   • Urban LST: {uhi_details.get('urban_lst', 0):.2f}°C")
                        print(f"   • Rural LST: {uhi_details.get('rural_lst', 0):.2f}°C")
                        print(f"   • Scale Used: {uhi_details.get('scale_used', 0)} meters")
                    
                    elif method == "statistical_percentiles":
                        print(f"   • P90 Temperature: {uhi_details.get('p90_temperature', 0):.2f}°C")
                        print(f"   • P10 Temperature: {uhi_details.get('p10_temperature', 0):.2f}°C")
                        print(f"   • Median Temperature: {uhi_details.get('median_temperature', 0):.2f}°C")
                        print(f"   • Alternative UHI (P75-P25): {uhi_details.get('alternative_uhi_p75_p25', 0):.2f}°C")
                        print(f"   • Interpretation: {uhi_details.get('interpretation', 'N/A')}")
                    
                    elif "error" in method or "fallback" in method:
                        error = uhi_details.get("error", "Unknown error")
                        print(f"   • Error: {error}")
                        print(f"   • Note: Using fallback calculation method")
                
                print()
                
                # Display metadata
                area_km2 = result.get("area_km2", 0)
                print(f"📊 Analysis Details:")
                print(f"   • Area analyzed: {area_km2:.2f} km²")
                
                image_count = result.get("image_count", 0)
                print(f"   • MODIS images used: {image_count}")
                
                # Check if visualization is available
                tile_urls = result.get("tile_urls", {})
                if tile_urls.get("urlFormat"):
                    print(f"   • Visualization: ✅ Available")
                else:
                    print(f"   • Visualization: ❌ Not available")
                
                # Show metadata if available
                metadata = result.get("metadata", {})
                if metadata:
                    print(f"   • Processing scale: {metadata.get('scale_meters', 0)} meters")
                    print(f"   • Date range used: {metadata.get('start_date')} to {metadata.get('end_date')}")
                
            else:
                print("❌ LST analysis failed!")
                error = result.get("error", "Unknown error")
                error_type = result.get("error_type", "unknown")
                print(f"   Error: {error}")
                print(f"   Type: {error_type}")
            
            print()
        
        print("🎯 Test Summary:")
        print("================")
        print("• The improved LST service now tries multiple UHI calculation methods:")
        print("  1. Dynamic World LULC data (10m resolution)")
        print("  2. MODIS Land Cover data (500m resolution)")
        print("  3. ESA WorldCover data (10m resolution)")
        print("  4. Statistical approach (temperature percentiles)")
        print("• Each method has specific advantages for different scenarios")
        print("• The service automatically selects the best available method")
        print("• Fallback methods ensure UHI analysis always provides meaningful results")
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Make sure you're running from the gee_service directory")
        print("💡 Make sure the improved lst_service.py is in the services/ directory")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        print("Full traceback:")
        print(traceback.format_exc())

def verify_uhi_methods():
    """Verify that different UHI calculation methods work correctly."""
    print("\n🔍 Verifying UHI Calculation Methods")
    print("=" * 50)
    
    try:
        import ee
        from lst_service import LSTService
        
        # Create a test geometry
        test_geom = ee.Geometry.Polygon([[
            [72.85, 19.05],
            [72.87, 19.05],
            [72.87, 19.07],
            [72.85, 19.07],
            [72.85, 19.05]
        ]])
        
        # Use actual MODIS LST data for realistic testing
        lst_collection = ee.ImageCollection("MODIS/061/MOD11A2") \
            .filterDate("2024-01-01", "2024-08-31") \
            .filterBounds(test_geom) \
            .select("LST_Day_1km", "QC_Day") \
            .map(lambda img: img.select("LST_Day_1km").multiply(0.02).subtract(273.15).rename("LST").addBands(img.select("QC_Day")))
        
        # Get median composite for testing
        dummy_lst = lst_collection.median()
        
        print("Testing individual UHI calculation methods...")
        
        # Test Dynamic World method
        try:
            result1 = LSTService._try_dynamic_world_uhi(dummy_lst, test_geom, 1000, 1e6)
            print(f"✅ Dynamic World method: {'Success' if result1.get('success') else 'Failed - ' + result1.get('reason', 'Unknown')}")
        except Exception as e:
            print(f"❌ Dynamic World method failed: {e}")
        
        # Test MODIS Land Cover method
        try:
            result2 = LSTService._try_modis_lulc_uhi(dummy_lst, test_geom, 1000, 1e6)
            print(f"✅ MODIS Land Cover method: {'Success' if result2.get('success') else 'Failed - ' + result2.get('reason', 'Unknown')}")
        except Exception as e:
            print(f"❌ MODIS Land Cover method failed: {e}")
        
        # Test statistical method (should always work)
        try:
            result3 = LSTService._calculate_statistical_uhi(dummy_lst, test_geom, 1000, 1e6)
            print(f"✅ Statistical method: Success (UHI: {result3.get('intensity', 0):.2f}°C)")
        except Exception as e:
            print(f"❌ Statistical method failed: {e}")
            
    except Exception as e:
        print(f"❌ Method verification failed: {e}")

if __name__ == "__main__":
    test_improved_lst_service()
    verify_uhi_methods()