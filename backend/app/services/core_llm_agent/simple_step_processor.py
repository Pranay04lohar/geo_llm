"""
Simple Step Processor - Uses existing working analysis endpoints
Instead of recreating everything manually, just call the working endpoints
and show real-time progress steps.
"""

import asyncio
import logging
from typing import Dict, Any, AsyncGenerator

logger = logging.getLogger(__name__)

class SimpleStepProcessor:
    """Simple step processor that uses existing working analysis endpoints"""
    
    def __init__(self):
        pass
    
    async def process_analysis_steps(self, roi: Dict, user_prompt: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Process analysis using existing working endpoints"""
        analysis_type = self._detect_analysis_type(user_prompt)
        
        if analysis_type == "water":
            async for step in self.process_water_analysis_steps(roi, user_prompt):
                yield step
        elif analysis_type == "lst":
            async for step in self.process_lst_analysis_steps(roi, user_prompt):
                yield step
        elif analysis_type == "ndvi":
            async for step in self.process_ndvi_analysis_steps(roi, user_prompt):
                yield step
        else:
            yield {"step": 1, "status": "error", "message": "Unsupported analysis type", "progress": 0}
    
    def _detect_analysis_type(self, user_prompt: str) -> str:
        """Detect analysis type from user prompt"""
        prompt_lower = user_prompt.lower()
        if "temperature" in prompt_lower or "lst" in prompt_lower or "thermal" in prompt_lower or "heat" in prompt_lower:
            return "lst"
        elif "vegetation" in prompt_lower or "ndvi" in prompt_lower or "green" in prompt_lower or "lulc" in prompt_lower or "land use" in prompt_lower or "land cover" in prompt_lower:
            return "ndvi"
        elif "water" in prompt_lower or "flood" in prompt_lower or "aquatic" in prompt_lower:
            return "water"
        else:
            return "ndvi"  # Default to NDVI/LULC analysis (most common)
    
    async def process_water_analysis_steps(self, roi: Dict, user_prompt: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Process water analysis using existing working endpoint"""
        try:
            # Debug: Log received ROI structure
            logger.info(f"🔍 [WATER] Received ROI - type: {roi.get('type')}, coords_rings: {len(roi.get('coordinates', []))}, first_ring_points: {len(roi.get('coordinates', [[]])[0])}")
            
            # Step 1: Initialize
            yield {
                "step": 1,
                "status": "processing",
                "message": "Initializing water analysis...",
                "progress": 10,
                "details": "Preparing analysis parameters"
            }
            await asyncio.sleep(0.5)
            
            # Step 2: Call existing working endpoint
            yield {
                "step": 2,
                "status": "processing",
                "message": "Analyzing water coverage using JRC Global Surface Water dataset...",
                "progress": 30,
                "details": "Processing 2000-2021 water occurrence data"
            }
            
            try:
                # Use the water service directly instead of HTTP requests
                from app.gee_service.services.water_service import WaterService
                water_service = WaterService()
                
                # Call the analysis method directly with optimized parameters
                analysis_data = water_service.analyze_water_presence(
                    roi,
                    year=2023,
                    threshold=20,
                    include_seasonal=False  # Disable seasonal analysis for faster processing
                )
                logger.info("✅ Water analysis completed successfully")
                
            except Exception as e:
                logger.error(f"❌ Water service failed: {e}")
                raise
            
            # Step 3: Process results
            yield {
                "step": 3,
                "status": "processing",
                "message": "Processing analysis results...",
                "progress": 60,
                "details": "Calculating water coverage statistics"
            }
            await asyncio.sleep(1)
            
            # Step 4: Generate visualization
            yield {
                "step": 4,
                "status": "processing",
                "message": "Generating interactive map visualization...",
                "progress": 80,
                "details": "Creating tile URLs and interactive features"
            }
            await asyncio.sleep(1)
            
            # Step 5: Complete
            logger.info(f"🎯 Preparing final result with analysis_data keys: {list(analysis_data.keys()) if analysis_data else 'None'}")
            
            # Simplify ROI for streaming (reduce polygon points to avoid JSON serialization hang)
            simplified_roi = self._simplify_roi_for_streaming(roi)
            
            # Build final result - use simplified ROI for streaming
            final_result = {
                "analysis_type": "water",
                "tile_url": analysis_data.get("urlFormat"),
                "stats": analysis_data.get("mapStats"),
                "roi": simplified_roi,  # Use simplified ROI to avoid streaming hang
                "service_used": "GEE"
            }
            logger.info(f"🎯 Final result created with simplified ROI ({self._count_roi_points(simplified_roi)} points)")
            
            yield {
                "step": 5,
                "status": "completed",
                "message": "Water analysis complete!",
                "progress": 100,
                "details": "Interactive map ready with hover sampling",
                "final_result": final_result
            }
            
        except Exception as e:
            logger.error(f"Error in water analysis steps: {e}")
            yield {
                "step": "error",
                "status": "error",
                "message": f"Analysis failed: {str(e)}",
                "progress": 0,
                "details": "Check server logs for details"
            }
    
    async def process_lst_analysis_steps(self, roi: Dict, user_prompt: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Process LST analysis using existing working endpoint"""
        try:
            # Debug: Log received ROI structure
            logger.info(f"🔍 [LST] Received ROI - type: {roi.get('type')}, coords_rings: {len(roi.get('coordinates', []))}, first_ring_points: {len(roi.get('coordinates', [[]])[0])}")
            
            # Step 1: Initialize
            yield {
                "step": 1,
                "status": "processing",
                "message": "Initializing LST analysis...",
                "progress": 10,
                "details": "Preparing temperature analysis parameters"
            }
            await asyncio.sleep(0.5)
            
            # Step 2: Call existing working endpoint
            yield {
                "step": 2,
                "status": "processing",
                "message": "Analyzing land surface temperature using MODIS data...",
                "progress": 30,
                "details": "Processing thermal infrared data (this may take 1-2 minutes for satellite data)"
            }
            
            try:
                # Use HTTP for LST (like static COT does) to avoid EE context issues
                import requests
                
                # Use roi directly as geometry (same as static COT)
                response = requests.post(
                    f"{os.getenv('SERVICE_BASE_URL', 'http://localhost:8000')}/lst/land-surface-temperature",
                    json={
                        "geometry": roi,
                        "startDate": "2023-06-01",
                        "endDate": "2023-08-31",
                        "includeUHI": True,
                        "includeTimeSeries": False,
                        "scale": 1000,
                        "maxPixels": 1e8,
                        "exactComputation": False
                    },
                    timeout=180
                )
                response.raise_for_status()
                analysis_data = response.json()
                logger.info("✅ LST analysis completed successfully")
                
            except Exception as e:
                logger.error(f"❌ LST service failed: {e}")
                raise
            
            # Step 3: Process results
            yield {
                "step": 3,
                "status": "processing",
                "message": "Processing temperature results...",
                "progress": 60,
                "details": "Calculating temperature statistics"
            }
            await asyncio.sleep(1)
            
            # Step 4: Generate visualization
            yield {
                "step": 4,
                "status": "processing",
                "message": "Generating thermal visualization...",
                "progress": 80,
                "details": "Creating temperature map tiles"
            }
            await asyncio.sleep(1)
            
            # Step 5: Complete
            # Simplify ROI for streaming (reduce polygon points to avoid JSON serialization hang)
            simplified_roi = self._simplify_roi_for_streaming(roi)
            logger.info(f"🎯 LST final result with simplified ROI ({self._count_roi_points(simplified_roi)} points)")
            
            yield {
                "step": 5,
                "status": "completed",
                "message": "LST analysis complete!",
                "progress": 100,
                "details": "Interactive thermal map ready",
                "final_result": {
                    "analysis_type": "lst",
                    "tile_url": analysis_data.get("urlFormat") or analysis_data.get("visualization", {}).get("tile_url"),
                    "stats": {
                        **analysis_data.get("mapStats", {}),
                        "total_area_km2": analysis_data.get("roi_area_km2", 0)
                    },
                    "roi": simplified_roi,  # Use simplified ROI to avoid streaming hang
                    "service_used": "GEE"
                }
            }
            
        except Exception as e:
            logger.error(f"Error in LST analysis steps: {e}")
            yield {
                "step": "error",
                "status": "error",
                "message": f"Analysis failed: {str(e)}",
                "progress": 0,
                "details": "Check server logs for details"
            }
    
    async def process_ndvi_analysis_steps(self, roi: Dict, user_prompt: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Process NDVI analysis using existing working endpoint"""
        try:
            # Debug: Log received ROI structure
            logger.info(f"🔍 [NDVI] Received ROI - type: {roi.get('type')}, coords_rings: {len(roi.get('coordinates', []))}, first_ring_points: {len(roi.get('coordinates', [[]])[0])}")
            
            # Step 1: Initialize
            yield {
                "step": 1,
                "status": "processing",
                "message": "Initializing vegetation analysis...",
                "progress": 10,
                "details": "Preparing NDVI analysis parameters"
            }
            await asyncio.sleep(0.5)
            
            # Step 2: Call existing working endpoint
            yield {
                "step": 2,
                "status": "processing",
                "message": "Analyzing vegetation health using Sentinel-2 data...",
                "progress": 30,
                "details": "Processing NDVI calculations (this may take 1-2 minutes for satellite data)"
            }
            
            try:
                # Use HTTP for NDVI (like static COT does) to avoid EE context issues
                import requests
                
                # Use roi directly as geometry (same as static COT)
                response = requests.post(
                    f"{os.getenv('SERVICE_BASE_URL', 'http://localhost:8000')}/ndvi/vegetation-analysis",
                    json={
                        "geometry": roi,
                        "startDate": "2023-06-01",
                        "endDate": "2023-08-31",
                        "cloudThreshold": 30,
                        "scale": 60,
                        "maxPixels": 1e9,
                        "includeTimeSeries": False,
                        "exactComputation": False
                    },
                    timeout=180
                )
                response.raise_for_status()
                analysis_data = response.json()
                logger.info("✅ NDVI analysis completed successfully")
                
            except Exception as e:
                logger.error(f"❌ NDVI service failed: {e}")
                raise
            
            # Step 3: Process results
            yield {
                "step": 3,
                "status": "processing",
                "message": "Processing vegetation results...",
                "progress": 60,
                "details": "Calculating NDVI statistics"
            }
            await asyncio.sleep(1)
            
            # Step 4: Generate visualization
            yield {
                "step": 4,
                "status": "processing",
                "message": "Generating vegetation visualization...",
                "progress": 80,
                "details": "Creating NDVI map tiles"
            }
            await asyncio.sleep(1)
            
            # Step 5: Complete
            # Simplify ROI for streaming (reduce polygon points to avoid JSON serialization hang)
            simplified_roi = self._simplify_roi_for_streaming(roi)
            logger.info(f"🎯 NDVI final result with simplified ROI ({self._count_roi_points(simplified_roi)} points)")
            
            yield {
                "step": 5,
                "status": "completed",
                "message": "Vegetation analysis complete!",
                "progress": 100,
                "details": "Interactive vegetation map ready",
                "final_result": {
                    "analysis_type": "ndvi",
                    "tile_url": analysis_data.get("urlFormat") or analysis_data.get("visualization", {}).get("tile_url"),
                    "stats": {
                        **analysis_data.get("mapStats", {}).get("ndvi_statistics", {}),
                        "total_area_km2": analysis_data.get("roi_area_km2", 0)
                    },
                    "roi": simplified_roi,  # Use simplified ROI to avoid streaming hang
                    "service_used": "GEE"
                }
            }
            
        except Exception as e:
            logger.error(f"Error in NDVI analysis steps: {e}")
            yield {
                "step": "error",
                "status": "error",
                "message": f"Analysis failed: {str(e)}",
                "progress": 0,
                "details": "Check server logs for details"
            }
    
    def _simplify_roi_for_streaming(self, roi: dict) -> dict:
        """
        Simplify ROI polygon to reduce JSON size for streaming while preserving accuracy.
        Uses adaptive simplification with max 1000 points (good balance of accuracy vs speed).
        For polygons with angular/important features, preserves key vertices.
        """
        if not roi or not isinstance(roi, dict):
            return roi
        
        roi_type = roi.get('type')
        coordinates = roi.get('coordinates')
        
        if roi_type != 'Polygon' or not coordinates or not coordinates[0]:
            return roi
        
        outer_ring = coordinates[0]
        num_points = len(outer_ring)
        
        # More generous limit: 1000 points is still fast (~55KB JSON vs 150KB original)
        MAX_POINTS = 1000
        
        # If already small enough, return as-is
        if num_points <= MAX_POINTS:
            logger.info(f"ROI already optimal: {num_points} points (≤{MAX_POINTS})")
            return roi
        
        # Use improved simplification that preserves shape better
        simplified_ring = self._adaptive_simplify_polygon(outer_ring, MAX_POINTS)
        
        logger.info(f"Simplified ROI: {num_points} → {len(simplified_ring)} points (preserved {len(simplified_ring)/num_points*100:.1f}% of detail)")
        
        return {
            'type': 'Polygon',
            'coordinates': [simplified_ring],
            'display_name': roi.get('display_name'),
            'center': roi.get('center')
        }
    
    def _adaptive_simplify_polygon(self, ring: list, max_points: int) -> list:
        """
        Adaptively simplify polygon by preserving vertices with significant angular changes.
        This preserves important features like corners, bays, and peninsulas.
        """
        if len(ring) <= max_points:
            return ring
        
        # Calculate angular change at each vertex
        angles = []
        for i in range(1, len(ring) - 1):
            prev = ring[i - 1]
            curr = ring[i]
            next_pt = ring[i + 1]
            
            # Calculate angle using vectors
            v1 = [curr[0] - prev[0], curr[1] - prev[1]]
            v2 = [next_pt[0] - curr[0], next_pt[1] - curr[1]]
            
            # Dot product and magnitudes
            dot = v1[0] * v2[0] + v1[1] * v2[1]
            mag1 = (v1[0]**2 + v1[1]**2)**0.5
            mag2 = (v2[0]**2 + v2[1]**2)**0.5
            
            # Avoid division by zero
            if mag1 > 0 and mag2 > 0:
                # Angular change (higher = more important vertex)
                cos_angle = dot / (mag1 * mag2)
                cos_angle = max(-1, min(1, cos_angle))  # Clamp to [-1, 1]
                angle_importance = abs(1 - cos_angle)  # 0 = straight line, 2 = sharp turn
            else:
                angle_importance = 0
            
            angles.append((i, angle_importance))
        
        # Always keep first and last points (polygon closure)
        important_indices = {0, len(ring) - 1}
        
        # Sort by importance and keep the most important vertices
        angles.sort(key=lambda x: x[1], reverse=True)
        num_to_keep = max_points - 2  # -2 for first and last
        
        for i, _ in angles[:num_to_keep]:
            important_indices.add(i)
        
        # Build simplified ring maintaining order
        simplified = [ring[i] for i in sorted(important_indices)]
        
        # Ensure polygon is closed
        if simplified[0] != simplified[-1]:
            simplified.append(simplified[0])
        
        return simplified
    
    def _count_roi_points(self, roi: dict) -> int:
        """Count the number of points in an ROI polygon."""
        if not roi or not isinstance(roi, dict):
            return 0
        
        coordinates = roi.get('coordinates')
        if not coordinates or not coordinates[0]:
            return 0
        
        return len(coordinates[0])
