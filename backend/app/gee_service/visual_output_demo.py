#!/usr/bin/env python3
"""
Visual Output Demo for Water Service
Shows how to get tile URLs for map visualization
"""

import ee
import logging
from services.water_service import WaterService

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Earth Engine
try:
    project_id = 'gee-tool-469517'
    ee.Initialize(project=project_id)
    logger.info(f"✅ Earth Engine initialized with project '{project_id}'")
except Exception as e:
    logger.error(f"❌ Failed to initialize Earth Engine: {e}")
    exit(1)

def demo_visual_outputs():
    """Demonstrate visual outputs from water service"""
    
    # Test ROIs
    test_rois = {
        "Delhi_Urban": {
            "type": "Polygon",
            "coordinates": [[
                [77.20, 28.60],
                [77.25, 28.60],
                [77.25, 28.65],
                [77.20, 28.65],
                [77.20, 28.60]
            ]]
        },
        "Yamuna_River": {
            "type": "Polygon", 
            "coordinates": [[
                [77.20, 28.60],
                [77.30, 28.60],
                [77.30, 28.70],
                [77.20, 28.70],
                [77.20, 28.60]
            ]]
        },
        "Mumbai_Coastal": {
            "type": "Polygon",
            "coordinates": [[
                [72.77, 18.89],
                [72.97, 18.89], 
                [72.97, 19.27],
                [72.77, 19.27],
                [72.77, 18.89]
            ]]
        }
    }
    
    water_service = WaterService()
    
    print("🌊 Water Service Visual Output Demo")
    print("=" * 60)
    print("This demo shows how to get tile URLs for map visualization")
    print("You can use these URLs in web mapping applications like Leaflet, Mapbox, etc.")
    print()
    
    for roi_name, roi_geom in test_rois.items():
        print(f"📍 {roi_name}")
        print("-" * 40)
        
        try:
            # Get JRC Official Analysis (with visual outputs)
            result = water_service.analyze_water_presence_jrc_official(
                roi=roi_geom,
                year=2020
            )
            
            if "error" in result:
                print(f"❌ Error: {result['error']}")
                continue
            
            # Display visual outputs
            print("🎨 Visual Outputs:")
            
            # Official JRC Classification Map
            if "urlFormatOfficial" in result and result["urlFormatOfficial"]:
                print(f"   🔵 Official JRC Classification:")
                print(f"      URL: {result['urlFormatOfficial']}")
                print(f"      Legend: {result.get('legendConfigOfficial', {})}")
                print(f"      Description: Permanent/Seasonal/No Water classification")
            
            # Occurrence Heatmap
            if "urlFormatOccurrence" in result and result["urlFormatOccurrence"]:
                print(f"   🌡️ Occurrence Heatmap:")
                print(f"      URL: {result['urlFormatOccurrence']}")
                print(f"      Legend: {result.get('legendConfigOccurrence', {})}")
                print(f"      Description: 0-100% water occurrence probability")
            
            # Custom Threshold Analysis (for comparison)
            custom_result = water_service.analyze_water_presence(
                roi=roi_geom,
                year=2020,
                threshold=20,
                include_seasonal=False
            )
            
            if "urlFormat" in custom_result and custom_result["urlFormat"]:
                print(f"   🎯 Custom Threshold (20%):")
                print(f"      URL: {custom_result['urlFormat']}")
                print(f"      Legend: {custom_result.get('legendConfig', {})}")
                print(f"      Description: Binary water/no-water at 20% threshold")
            
            # Display statistics
            stats = result.get('mapStats', {})
            print(f"📊 Statistics:")
            if 'permanent_water' in stats:
                print(f"   🔵 Permanent water: {stats['permanent_water']['percentage']}%")
            if 'seasonal_water' in stats:
                print(f"   🟢 Seasonal water: {stats['seasonal_water']['percentage']}%")
            if 'no_water' in stats:
                print(f"   ⚪ No water: {stats['no_water']['percentage']}%")
            
            print()
            
        except Exception as e:
            print(f"❌ Error processing {roi_name}: {e}")
            print()
    
    print("=" * 60)
    print("🎨 How to Use These URLs:")
    print("1. Copy the URL from any of the outputs above")
    print("2. Use in web mapping libraries like Leaflet, Mapbox, or Google Maps")
    print("3. The URLs are tile services that can be added as map layers")
    print("4. Each URL represents a different visualization:")
    print("   - Official JRC: Permanent/Seasonal/No Water classification")
    print("   - Occurrence: 0-100% water probability heatmap")
    print("   - Custom Threshold: Binary water/no-water classification")
    print()
    print("💡 Example Leaflet usage:")
    print("   L.tileLayer('YOUR_TILE_URL_HERE').addTo(map)")
    print()
    print("🌊 Visual Output Demo Complete!")

if __name__ == "__main__":
    demo_visual_outputs()
