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
        analysis_parts.append(f"🎯 Analysis Type: {analysis_type.replace('_', ' ').title()}")
        analysis_parts.append("")
        
        # Analysis-specific results
        if analysis_type == "ndvi":
            analysis_parts.extend(self._format_ndvi_results(gee_result))
        elif analysis_type == "landcover":
            analysis_parts.extend(self._format_landcover_results(gee_result))
        elif analysis_type == "water_analysis":
            analysis_parts.extend(self._format_water_results(gee_result))
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
        """Format water analysis results."""
        results = []
        results.append("💧 Water Body Analysis:")
        
        water_area = gee_result.get("water_area_m2", {}).get("area", 0)
        if water_area:
            water_area_km2 = water_area / 1000000
            results.append(f"   • Water Area: {water_area_km2:.3f} km²")
            
        ndwi_stats = gee_result.get("ndwi_stats", {})
        if ndwi_stats:
            mean_ndwi = ndwi_stats.get("NDWI_mean", 0)
            results.append(f"   • Average NDWI: {mean_ndwi:.3f}")
            results.append("   • NDWI > 0.3 indicates water presence")
            
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
        
        return {
            "type": "Feature",
            "properties": {
                "name": f"GEE Analysis - {primary_location.get('name', 'Unknown')}",
                "source_locations": [primary_location.get("name", "Unknown")],
                "analysis_type": metadata.get("analysis_type", "general"),
                "statistics": self._extract_key_statistics(gee_result, metadata.get("analysis_type")),
                "processing_metadata": {
                    "datasets_used": metadata.get("datasets_used", []),
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
            water_area = gee_result.get("water_area_m2", {}).get("area", 0)
            key_stats.update({
                "water_area_km2": water_area / 1000000 if water_area else 0,
                "mean_ndwi": gee_result.get("ndwi_stats", {}).get("NDWI_mean", 0)
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
