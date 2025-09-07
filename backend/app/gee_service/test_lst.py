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
                
                # Display tile URL and legend metadata
                print(f"\n🔍 DEBUG - Full response keys: {list(result.keys())}")
                
                visualization = result.get('visualization', {})
                print(f"🔍 DEBUG - Visualization keys: {list(visualization.keys())}")
                
                legend = visualization.get('legend', {})
                print(f"🔍 DEBUG - Legend keys: {list(legend.keys()) if legend else 'No legend found'}")
                
                if legend:
                    print(f"\n🎨 Legend Metadata:")
                    print(f"   Title: {legend.get('title', 'N/A')}")
                    print(f"   Type: {legend.get('type', 'N/A')}")
                    print(f"   Description: {legend.get('description', 'N/A')}")
                    print(f"   Unit: {legend.get('unit', 'N/A')}")
                    
                    palette = legend.get('palette', [])
                    if palette:
                        print(f"   Color Palette: {len(palette)} colors")
                        print(f"   Colors: {', '.join(palette[:5])}{'...' if len(palette) > 5 else ''}")
                    
                    classes = legend.get('classes', [])
                    if classes:
                        print(f"   Classes: {len(classes)} temperature ranges")
                        print(f"   Class Details:")
                        for cls in classes:
                            print(f"     - {cls.get('name', 'Unknown')}: {cls.get('range', 'N/A')} ({cls.get('color', 'N/A')})")
                else:
                    print(f"\n🎨 Legend Information: ❌ No legend data found")
                    print(f"   Available visualization keys: {list(visualization.keys())}")
                
                # Display tile URL details
                tile_url = result.get("urlFormat", "")
                if tile_url:
                    print(f"\n🗺️  Tile URL Details:")
                    print(f"   Complete URL: {tile_url}")
                    print(f"   ✅ Using new GEE tile URL format (authentication handled internally)")
                    
                    # Create a test URL with Mumbai tile coordinates (z=10, x=719, y=456)
                    test_url = tile_url.replace("{z}", "10").replace("{x}", "719").replace("{y}", "456")
                    print(f"   Test URL (z=10, x=719, y=456):")
                    print(f"   {test_url}")
                else:
                    print(f"\n🗺️  Tile URL: ❌ Not available")
                
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