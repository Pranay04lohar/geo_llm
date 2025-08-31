"""
Result Processor

Processes Google Earth Engine results and formats them for the LLM agent pipeline.
Handles result extraction, analysis generation, and output formatting.
"""

from typing import Dict, Any, List, Optional
import json
from datetime import datetime


class ResultProcessor:
    """Processes and formats Google Earth Engine analysis results."""
    
    def __init__(self):
        """Initialize result processor."""
        pass
        
    def process_gee_result(
        self, 
        gee_result: Dict[str, Any], 
        script_metadata: Dict[str, Any],
        roi_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process raw GEE results into formatted output for the LLM agent.
        
        Args:
            gee_result: Raw result from GEE script execution
            script_metadata: Metadata from script generation
            roi_info: Information about the ROI used
            
        Returns:
            Dict with 'analysis', 'roi', and 'evidence' keys
        """
        analysis_type = script_metadata.get("analysis_type", "general")
        
        # Generate analysis text
        analysis_text = self._generate_analysis_text(
            gee_result=gee_result,
            analysis_type=analysis_type,
            roi_info=roi_info,
            metadata=script_metadata
        )
        
        # Format ROI for output
        formatted_roi = self._format_roi_output(roi_info, gee_result, script_metadata)
        
        # Generate evidence
        evidence = self._generate_evidence(gee_result, script_metadata)
        
        return {
            "analysis": analysis_text,
            "roi": formatted_roi,
            "evidence": evidence
        }
        
    def _generate_analysis_text(
        self,
        gee_result: Dict[str, Any],
        analysis_type: str,
        roi_info: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> str:
        """Generate human-readable analysis text from GEE results."""
        
        # Extract basic info
        location_name = roi_info.get("primary_location", {}).get("name", "Unknown Location")
        area_km2 = metadata.get("roi_area_km2", 0)
        
        # Start building analysis
        analysis_parts = []
        
        # Header
        analysis_parts.append(f"Geospatial Analysis Results for {location_name}")
        analysis_parts.append("=" * 50)
        
        # ROI Information
        analysis_parts.append(f"📍 Region: {location_name}")
        analysis_parts.append(f"📐 Area: {area_km2:.2f} km²")
        analysis_parts.append(f"🎯 Analysis Type: {(analysis_type or 'general').replace('_', ' ').title()}")
        analysis_parts.append("")
        
        # Analysis-specific results
        if analysis_type == "ndvi":
            analysis_parts.extend(self._format_ndvi_results(gee_result))
        elif analysis_type == "landcover":
            analysis_parts.extend(self._format_landcover_results(gee_result))
        elif analysis_type == "water_analysis":
            analysis_parts.extend(self._format_water_results(gee_result))
        elif analysis_type == "climate_analysis":
            analysis_parts.extend(self._format_climate_results(gee_result))
        elif analysis_type == "change_detection":
            analysis_parts.extend(self._format_change_results(gee_result))
        else:
            analysis_parts.extend(self._format_general_results(gee_result))
            
        # Technical details
        analysis_parts.append("")
        analysis_parts.append("🔧 Technical Details:")
        datasets_used = metadata.get("datasets_used", ["Unknown"])
        analysis_parts.append(f"   • Dataset: {datasets_used[0] if datasets_used else 'Unknown'}")
        analysis_parts.append(f"   • Processing Time: {metadata.get('expected_processing_time_seconds', 0)}s")
        analysis_parts.append(f"   • Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        
        return "\n".join(analysis_parts)
        
    def _format_ndvi_results(self, gee_result: Dict[str, Any]) -> List[str]:
        """Format NDVI analysis results."""
        results = []
        
        # Extract NDVI statistics
        ndvi_stats = gee_result.get("ndvi_stats", {})
        if ndvi_stats:
            mean_ndvi = ndvi_stats.get("NDVI_mean", 0)
            min_ndvi = ndvi_stats.get("NDVI_min", 0)
            max_ndvi = ndvi_stats.get("NDVI_max", 0)
            
            results.append("🌱 Vegetation Health Analysis (NDVI):")
            results.append(f"   • Average NDVI: {mean_ndvi:.3f}")
            results.append(f"   • Range: {min_ndvi:.3f} to {max_ndvi:.3f}")
            
            # Interpret NDVI values
            if mean_ndvi > 0.6:
                health_status = "Excellent (Dense, healthy vegetation)"
            elif mean_ndvi > 0.4:
                health_status = "Good (Moderate vegetation cover)"
            elif mean_ndvi > 0.2:
                health_status = "Fair (Sparse vegetation)"
            else:
                health_status = "Poor (Minimal vegetation)"
                
            results.append(f"   • Health Status: {health_status}")
            
        # Pixel count
        pixel_count = gee_result.get("pixel_count", {}).get("NDVI", 0)
        if pixel_count:
            results.append(f"   • Analyzed Pixels: {pixel_count:,}")
            
        return results
        
    def _format_landcover_results(self, gee_result: Dict[str, Any]) -> List[str]:
        """Format land cover analysis results."""
        results = []
        results.append("🗺️ Land Cover Analysis:")
        
        landcover_stats = gee_result.get("landcover_stats", {})
        total_area = gee_result.get("total_area_km2", {}).get("area", 0)
        
        if landcover_stats and total_area:
            # Land cover class mapping (ESA WorldCover classes)
            class_names = {
                10: "Trees",
                20: "Shrubland", 
                30: "Grassland",
                40: "Cropland",
                50: "Built-up",
                60: "Bare/Sparse vegetation",
                70: "Snow and ice",
                80: "Permanent water bodies",
                90: "Herbaceous wetland",
                95: "Mangroves",
                100: "Moss and lichen"
            }
            
            results.append("   Land Cover Distribution:")
            # This would need proper parsing of the grouped results
            results.append("   • Detailed breakdown available in raw data")
            
        return results
        
    def _format_water_results(self, gee_result: Dict[str, Any]) -> List[str]:
        """Format comprehensive water analysis results."""
        results = []
        results.append("💧 Water Body Analysis:")
        
        # Extract water area information
        water_area_km2 = gee_result.get("water_area_km2", 0)
        water_percentage = gee_result.get("water_percentage", 0)
        roi_area_km2 = gee_result.get("roi_area_km2", 0)
        
        if water_area_km2 > 0:
            results.append(f"   • Total Water Area: {water_area_km2:.3f} km²")
            results.append(f"   • Water Coverage: {water_percentage:.2f}% of ROI")
            results.append(f"   • ROI Total Area: {roi_area_km2:.2f} km²")
            
            # Interpret water coverage
            if water_percentage > 10:
                water_status = "High water coverage (major water bodies present)"
            elif water_percentage > 5:
                water_status = "Moderate water coverage (significant water features)"
            elif water_percentage > 1:
                water_status = "Low water coverage (minor water features)"
            else:
                water_status = "Minimal water coverage"
                
            results.append(f"   • Coverage Status: {water_status}")
        else:
            results.append("   • No significant water bodies detected")
            results.append(f"   • ROI Total Area: {roi_area_km2:.2f} km²")
        
        # NDWI Statistics
        ndwi_stats = gee_result.get("ndwi_stats", {})
        if ndwi_stats:
            results.append("")
            results.append("   📊 NDWI (Normalized Difference Water Index):")
            results.append(f"      • Mean: {ndwi_stats.get('NDWI_mean', 0):.3f}")
            results.append(f"      • Range: {ndwi_stats.get('NDWI_min', 0):.3f} to {ndwi_stats.get('NDWI_max', 0):.3f}")
            results.append(f"      • Standard Deviation: {ndwi_stats.get('NDWI_stdDev', 0):.3f}")
            
            # Interpret NDWI values
            mean_ndwi = ndwi_stats.get('NDWI_mean', 0)
            if mean_ndwi > 0.3:
                ndwi_status = "Strong water signal detected"
            elif mean_ndwi > 0.1:
                ndwi_status = "Moderate water signal"
            elif mean_ndwi > -0.1:
                ndwi_status = "Weak water signal"
            else:
                ndwi_status = "No water signal detected"
                
            results.append(f"      • Signal Strength: {ndwi_status}")
        
        # MNDWI Statistics
        mndwi_stats = gee_result.get("mndwi_stats", {})
        if mndwi_stats:
            results.append("")
            results.append("   📊 MNDWI (Modified NDWI):")
            results.append(f"      • Mean: {mndwi_stats.get('MNDWI_mean', 0):.3f}")
            results.append(f"      • Range: {mndwi_stats.get('MNDWI_min', 0):.3f} to {mndwi_stats.get('MNDWI_max', 0):.3f}")
            results.append(f"      • Standard Deviation: {mndwi_stats.get('MNDWI_stdDev', 0):.3f}")
        
        # Seasonal water information
        seasonal_stats = gee_result.get("seasonal_stats", {})
        if seasonal_stats and "seasonal_water_area_m2" in seasonal_stats:
            seasonal_area = seasonal_stats["seasonal_water_area_m2"].get("area", 0) / 1000000
            if seasonal_area > 0:
                results.append("")
                results.append("   🌊 Seasonal Water Variation:")
                results.append(f"      • Seasonal Water Area: {seasonal_area:.3f} km²")
                results.append("      • Indicates areas that are water-covered seasonally")
        
        # Datasets and methods used
        datasets_used = gee_result.get("datasets_used", [])
        methods_used = gee_result.get("water_detection_methods", [])
        
        if datasets_used:
            results.append("")
            results.append("   🛰️ Data Sources:")
            for dataset in datasets_used:
                results.append(f"      • {dataset}")
        
        if methods_used:
            results.append("")
            results.append("   🔬 Detection Methods:")
            for method in methods_used:
                results.append(f"      • {method}")
        
        # Pixel analysis
        pixel_info = gee_result.get("pixel_count", {})
        if pixel_info:
            total_pixels = pixel_info.get("total_roi", 0)
            water_pixels = pixel_info.get("water_pixels", 0)
            if total_pixels > 0:
                results.append("")
                results.append("   📊 Pixel Analysis:")
                results.append(f"      • Total ROI Pixels: {total_pixels:,}")
                results.append(f"      • Water Pixels: {water_pixels:,}")
                results.append(f"      • Water Pixel Percentage: {(water_pixels/total_pixels*100):.2f}%")
        
        return results
        
    def _format_climate_results(self, gee_result: Dict[str, Any]) -> List[str]:
        """Format climate analysis results."""
        results = []
        results.append("🌤️ Climate and Environmental Analysis:")
        
        # Temperature statistics
        temp_stats = gee_result.get("climate_statistics", {})
        if temp_stats:
            results.append("")
            results.append("🌡️ Temperature Analysis:")
            temp_mean = temp_stats.get("temperature_2m_mean", 0)
            temp_min = temp_stats.get("temperature_2m_min", 0)
            temp_max = temp_stats.get("temperature_2m_max", 0)
            
            if temp_mean > 0:
                temp_mean_c = temp_mean - 273.15  # Convert Kelvin to Celsius
                temp_min_c = temp_min - 273.15
                temp_max_c = temp_max - 273.15
                results.append(f"   • Average Temperature: {temp_mean_c:.1f}°C")
                results.append(f"   • Temperature Range: {temp_min_c:.1f}°C to {temp_max_c:.1f}°C")
            else:
                results.append("   • Temperature data not available")
        
        # Precipitation statistics
        precip_stats = gee_result.get("precipitation_statistics", {})
        if precip_stats:
            results.append("")
            results.append("🌧️ Precipitation Analysis:")
            precip_total = precip_stats.get("total_precipitation_sum_sum", 0)
            if precip_total > 0:
                results.append(f"   • Total Precipitation: {precip_total*1000:.1f} mm")  # Convert m to mm
                results.append(f"   • Rainfall Pattern: {'Heavy' if precip_total > 1 else 'Moderate' if precip_total > 0.5 else 'Light'}")
            else:
                results.append("   • Precipitation data not available")
        
        # Air Quality
        air_quality = gee_result.get("air_quality_statistics", {})
        if air_quality:
            results.append("")
            results.append("🏭 Air Quality Analysis:")
            no2_level = air_quality.get("tropospheric_NO2_column_number_density", 0)
            if no2_level > 0:
                # Convert to meaningful units and classify
                no2_level_formatted = no2_level * 1e15  # Convert to more readable units
                aqi_level = "Poor" if no2_level_formatted > 5 else "Moderate" if no2_level_formatted > 2 else "Good"
                results.append(f"   • NO2 Concentration: {no2_level_formatted:.2f} (10¹⁵ molecules/cm²)")
                results.append(f"   • Air Quality Index: {aqi_level}")
            else:
                results.append("   • Air quality data not available")
        
        # Vegetation Health
        veg_stats = gee_result.get("vegetation_statistics", {})
        if veg_stats:
            results.append("")
            results.append("🌱 Vegetation Health:")
            ndvi_mean = veg_stats.get("NDVI_mean", 0)
            ndvi_max = veg_stats.get("NDVI_max", 0)
            if ndvi_mean > 0:
                health_status = "Excellent" if ndvi_mean > 0.6 else "Good" if ndvi_mean > 0.3 else "Stressed"
                results.append(f"   • Average NDVI: {ndvi_mean:.3f}")
                results.append(f"   • Vegetation Health: {health_status}")
                results.append(f"   • Peak Greenness: {ndvi_max:.3f}")
            else:
                results.append("   • Vegetation data not available")
        
        # Hydrological data
        hydro_stats = gee_result.get("hydrological_statistics", {})
        if hydro_stats:
            results.append("")
            results.append("💧 Hydrological Conditions:")
            soil_moisture = hydro_stats.get("SoilMoi0_10cm_inst", 0)
            humidity = hydro_stats.get("Qair_f_inst", 0)
            if soil_moisture > 0:
                moisture_level = "High" if soil_moisture > 0.3 else "Moderate" if soil_moisture > 0.15 else "Low"
                results.append(f"   • Soil Moisture: {soil_moisture:.3f} m³/m³ ({moisture_level})")
            if humidity > 0:
                results.append(f"   • Atmospheric Humidity: {humidity:.4f} kg/kg")
        
        # Data sources
        analysis_methods = gee_result.get("analysis_methods", [])
        if analysis_methods:
            results.append("")
            results.append("🛰️ Data Sources:")
            for method in analysis_methods:
                results.append(f"   • {method}")
        
        # Image counts
        image_counts = gee_result.get("image_counts", {})
        if image_counts:
            results.append("")
            results.append("📊 Dataset Coverage:")
            for dataset, count in image_counts.items():
                if count > 0:
                    results.append(f"   • {dataset.replace('_', ' ').title()}: {count} images")
        
        return results
        
    def _format_change_results(self, gee_result: Dict[str, Any]) -> List[str]:
        """Format change detection results."""
        results = []
        results.append("📈 Change Detection Analysis:")
        
        change_stats = gee_result.get("change_stats", {})
        if change_stats:
            mean_change = change_stats.get("nd_mean", 0)
            results.append(f"   • Average Change: {mean_change:.3f}")
            
            if mean_change > 0.1:
                change_desc = "Significant positive change (vegetation increase)"
            elif mean_change < -0.1:
                change_desc = "Significant negative change (vegetation decrease)"
            else:
                change_desc = "Minimal change detected"
                
            results.append(f"   • Change Assessment: {change_desc}")
            
        change_area = gee_result.get("change_area_m2", {}).get("area", 0)
        if change_area:
            change_area_km2 = change_area / 1000000
            results.append(f"   • Area with Significant Change: {change_area_km2:.3f} km²")
            
        return results
        
    def _format_general_results(self, gee_result: Dict[str, Any]) -> List[str]:
        """Format general analysis results."""
        results = []
        results.append("📊 General Analysis:")
        
        # Basic statistics
        basic_stats = gee_result.get("basic_stats", {})
        if basic_stats:
            results.append("   Spectral Band Statistics:")
            for band in ["B4", "B3", "B2"]:  # Red, Green, Blue
                mean_val = basic_stats.get(f"{band}_mean", 0)
                if mean_val:
                    results.append(f"   • {band} (avg): {mean_val:.0f}")
                    
        # Image count
        image_count = gee_result.get("image_count", 0)
        if image_count:
            results.append(f"   • Images Used: {image_count}")
            
        # Area
        area_m2 = gee_result.get("area_m2", {}).get("area", 0)
        if area_m2:
            area_km2 = area_m2 / 1000000
            results.append(f"   • Total Area: {area_km2:.3f} km²")
            
        return results
        
    def _format_roi_output(
        self, 
        roi_info: Dict[str, Any], 
        gee_result: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Format ROI information for output."""
        
        primary_location = roi_info.get("primary_location", {})
        
        # Extract datasets_used from GEE results if available, fallback to metadata
        datasets_used = gee_result.get("datasets_used", metadata.get("datasets_used", []))
        
        return {
            "type": "Feature",
            "properties": {
                "name": f"GEE Analysis - {primary_location.get('name', 'Unknown')}",
                "source_locations": [primary_location.get("name", "Unknown")],
                "analysis_type": metadata.get("analysis_type", "general"),
                "statistics": self._extract_key_statistics(gee_result, metadata.get("analysis_type")),
                "processing_metadata": {
                    "datasets_used": datasets_used,
                    "processing_time_s": metadata.get("expected_processing_time_seconds", 0),
                    "roi_area_km2": metadata.get("roi_area_km2", 0),
                    "analysis_timestamp": datetime.now().isoformat()
                },
                "confidence": self._calculate_result_confidence(gee_result, roi_info)
            },
            "geometry": roi_info.get("geometry", {})
        }
        
    def _extract_key_statistics(self, gee_result: Dict[str, Any], analysis_type: str) -> Dict[str, Any]:
        """Extract key statistics based on analysis type."""
        
        key_stats = {}
        
        if analysis_type == "ndvi":
            ndvi_stats = gee_result.get("ndvi_stats", {})
            key_stats.update({
                "mean_ndvi": ndvi_stats.get("NDVI_mean", 0),
                "min_ndvi": ndvi_stats.get("NDVI_min", 0),
                "max_ndvi": ndvi_stats.get("NDVI_max", 0)
            })
            
        elif analysis_type == "water_analysis":
            water_area_km2 = gee_result.get("water_area_km2", 0)
            water_percentage = gee_result.get("water_percentage", 0)
            roi_area_km2 = gee_result.get("roi_area_km2", 0)
            
            key_stats.update({
                "water_area_km2": water_area_km2,
                "water_percentage": water_percentage,
                "roi_area_km2": roi_area_km2,
                "mean_ndwi": gee_result.get("ndwi_stats", {}).get("NDWI_mean", 0),
                "mean_mndwi": gee_result.get("mndwi_stats", {}).get("MNDWI_mean", 0)
            })
            
        elif analysis_type == "climate_analysis":
            # Extract climate statistics from new template format
            key_stats.update({
                "roi_area_km2": gee_result.get("roi_area_km2", 0),
                "temperature_celsius": gee_result.get("temperature_celsius", 0),
                "precipitation_mm": gee_result.get("precipitation_mm", 0),
                "soil_moisture": gee_result.get("soil_moisture_stats", {}).get("SoilMoi0_10cm_inst", 0),
                "evapotranspiration": gee_result.get("evapotranspiration_stats", {}).get("Evap_tavg", 0),
                "humidity": gee_result.get("humidity_stats", {}).get("Qair_f_inst", 0)
            })
            
        elif analysis_type == "population_density":
            # Extract population statistics
            key_stats.update({
                "roi_area_km2": gee_result.get("roi_area_km2", 0),
                "total_population": gee_result.get("total_population", 0),
                "urban_area_km2": gee_result.get("urban_area_km2", 0),
                "population_density_mean": gee_result.get("population_density_stats", {}).get("UN_2015_mean", 0)
            })
            
        elif analysis_type == "forest_cover":
            # Extract forest statistics
            key_stats.update({
                "roi_area_km2": gee_result.get("roi_area_km2", 0),
                "forest_area_km2": gee_result.get("forest_area_km2", 0),
                "forest_loss_area_km2": gee_result.get("forest_loss_area_km2", 0),
                "forest_gain_area_km2": gee_result.get("forest_gain_area_km2", 0),
                "high_vegetation_area_km2": gee_result.get("high_vegetation_area_km2", 0),
                "tree_cover_mean": gee_result.get("tree_cover_stats", {}).get("treecover2000_mean", 0)
            })
            
        elif analysis_type == "lulc_analysis":
            # Extract land use statistics
            key_stats.update({
                "roi_area_km2": gee_result.get("roi_area_km2", 0),
                "built_up_area_km2": gee_result.get("built_up_area_km2", 0),
                "cropland_area_km2": gee_result.get("cropland_area_km2", 0),
                "forest_area_km2": gee_result.get("forest_area_km2", 0),
                "grassland_area_km2": gee_result.get("grassland_area_km2", 0),
                "water_area_km2": gee_result.get("water_area_km2", 0),
                "bare_soil_area_km2": gee_result.get("bare_soil_area_km2", 0)
            })
            
        elif analysis_type == "soil_analysis":
            # Extract soil statistics
            key_stats.update({
                "roi_area_km2": gee_result.get("roi_area_km2", 0),
                "soil_ph_mean": gee_result.get("soil_ph_stats", {}).get("phh2o_0-5cm_mean", 0),
                "organic_carbon_mean": gee_result.get("organic_carbon_stats", {}).get("soc_0-5cm_mean", 0),
                "clay_content_mean": gee_result.get("clay_stats", {}).get("clay_0-5cm_mean", 0),
                "sand_content_mean": gee_result.get("sand_stats", {}).get("sand_0-5cm_mean", 0),
                "silt_content_mean": gee_result.get("silt_stats", {}).get("silt_0-5cm_mean", 0)
            })
            
        elif analysis_type == "transportation_network":
            # Extract transportation statistics
            key_stats.update({
                "roi_area_km2": gee_result.get("roi_area_km2", 0),
                "built_up_area_km2": gee_result.get("built_up_area_km2", 0),
                "ndbi_mean": gee_result.get("ndbi_stats", {}).get("NDBI_mean", 0)
            })
            
        elif analysis_type == "change_detection":
            change_area = gee_result.get("change_area_m2", {}).get("area", 0)
            key_stats.update({
                "change_area_km2": change_area / 1000000 if change_area else 0,
                "mean_change": gee_result.get("change_stats", {}).get("nd_mean", 0)
            })
            
        # Add pixel count if available
        for key, value in gee_result.items():
            if "pixel_count" in key or "image_count" in key:
                key_stats[key] = value
                
        return key_stats
        
    def _calculate_result_confidence(self, gee_result: Dict[str, Any], roi_info: Dict[str, Any]) -> float:
        """Calculate confidence score for the analysis results."""
        confidence = 0.8  # Base confidence
        
        # Boost confidence based on data availability
        if gee_result:
            confidence += 0.1
            
        # Check if we have meaningful statistics
        has_stats = any(
            key in gee_result for key in 
            ["ndvi_stats", "basic_stats", "landcover_stats", "water_area_m2", "change_stats"]
        )
        if has_stats:
            confidence += 0.1
            
        # ROI source affects confidence
        roi_source = roi_info.get("source", "default")
        if roi_source == "llm_locations":
            confidence += 0.05
        elif roi_source == "query_coordinates":
            confidence += 0.1
        elif roi_source == "default_fallback":
            confidence -= 0.1
            
        return min(confidence, 0.99)  # Cap at 99%
        
    def _generate_evidence(self, gee_result: Dict[str, Any], metadata: Dict[str, Any]) -> List[str]:
        """Generate evidence list for tracking."""
        evidence = []
        
        evidence.append("gee_tool:script_generated")
        evidence.append("gee_tool:script_executed")
        
        if gee_result:
            evidence.append("gee_tool:results_obtained")
            
            # Add specific evidence based on analysis type
            analysis_type = metadata.get("analysis_type", "general")
            evidence.append(f"gee_tool:{analysis_type}_analysis")
            
            # Check for specific result types
            if "ndvi_stats" in gee_result:
                evidence.append("gee_tool:ndvi_calculated")
            if "landcover_stats" in gee_result:
                evidence.append("gee_tool:landcover_classified")
            if "water_area_m2" in gee_result:
                evidence.append("gee_tool:water_detected")
                
        else:
            evidence.append("gee_tool:no_results")
            
        return evidence
