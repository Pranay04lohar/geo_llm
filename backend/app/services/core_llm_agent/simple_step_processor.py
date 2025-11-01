"""
Simple Step Processor - Uses existing working analysis endpoints
Instead of recreating everything manually, just call the working endpoints
and show real-time progress steps.
"""

import asyncio
import json
import logging
import os
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
    
    def _get_optimized_parameters(self, roi: Dict) -> Dict[str, Any]:
        """Get optimized parameters based on ROI size to prevent timeouts"""
        # Estimate area from geometry (rough calculation)
        area_km2 = self._estimate_area_km2(roi)
        
        if area_km2 > 10000:  # Very large area (>10,000 km²)
            return {
                "scale": 200,  # Coarser resolution
                "maxPixels": 1e7,  # Lower pixel limit
                "timeout": 600,  # 10 minutes timeout
                "exactComputation": False
            }
        elif area_km2 > 1000:  # Large area (1,000-10,000 km²)
            return {
                "scale": 120,  # Medium resolution
                "maxPixels": 1e8,  # Medium pixel limit
                "timeout": 300,  # 5 minutes timeout
                "exactComputation": False
            }
        else:  # Small area (<1,000 km²)
            return {
                "scale": 60,  # Fine resolution
                "maxPixels": 1e9,  # High pixel limit
                "timeout": 180,  # 3 minutes timeout
                "exactComputation": True
            }
    
    def _estimate_area_km2(self, roi: Dict) -> float:
        """Rough estimation of area in km² from geometry"""
        try:
            if roi.get("type") == "Polygon":
                coords = roi.get("coordinates", [[]])
                if coords and len(coords) > 0:
                    # Simple bounding box area estimation
                    lons = [coord[0] for ring in coords for coord in ring]
                    lats = [coord[1] for ring in coords for coord in ring]
                    
                    if lons and lats:
                        # Rough area calculation using bounding box
                        lat_range = max(lats) - min(lats)
                        lon_range = max(lons) - min(lons)
                        # Convert to km (rough approximation)
                        area_deg2 = lat_range * lon_range
                        area_km2 = area_deg2 * 111 * 111  # Rough conversion
                        return area_km2
        except Exception as e:
            logger.warning(f"Could not estimate area: {e}")
        
        return 1000  # Default to medium area
    
    async def _get_fallback_analysis(self, analysis_type: str, roi: Dict, user_prompt: str) -> Dict[str, Any]:
        """Get fallback analysis from search service when GEE service is unavailable"""
        try:
            import requests
            
            # Extract location name from ROI or use a default
            location_name = "the area"  # Default fallback
            
            # Try to get location name from ROI if available
            if "properties" in roi and "name" in roi["properties"]:
                location_name = roi["properties"]["name"]
            
            # Call search service for fallback analysis
            response = requests.post(
                f"{os.getenv('SERVICE_BASE_URL', 'http://localhost:8000')}/search/environmental-context",
                json={
                    "location": location_name,
                    "analysis_type": analysis_type,
                    "query": f"{analysis_type} analysis for {location_name}"
                },
                timeout=30
            )
            response.raise_for_status()
            search_data = response.json()
            
            # Convert search service response to GEE-like format
            fallback_result = {
                "urlFormat": None,  # No tile URL available
                "mapStats": {
                    "analysis_type": analysis_type,
                    "source": "search_service_fallback",
                    "location": location_name,
                    "summary": search_data.get("summary", f"Environmental analysis for {location_name}"),
                    "key_findings": search_data.get("key_findings", []),
                    "data_sources": search_data.get("data_sources", [])
                },
                "processing_time_seconds": 1.0,
                "roi_area_km2": self._estimate_area_km2(roi),
                "fallback_analysis": True
            }
            
            logger.info(f"✅ Fallback {analysis_type} analysis completed using search service")
            return fallback_result
            
        except Exception as e:
            logger.error(f"❌ Fallback analysis failed: {e}")
            # Return a minimal fallback response
            return {
                "urlFormat": None,
                "mapStats": {
                    "analysis_type": analysis_type,
                    "source": "fallback_error",
                    "error": str(e),
                    "message": f"Analysis temporarily unavailable. Please try again later."
                },
                "processing_time_seconds": 0.1,
                "roi_area_km2": self._estimate_area_km2(roi),
                "fallback_analysis": True
            }
    
    async def process_water_analysis_steps(self, roi: Dict, user_prompt: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Process water analysis using existing working endpoint"""
        import gc
        water_service = None
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
                from app.services.gee.water_service import WaterService
                water_service = WaterService()  # Track for cleanup
                
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
            
            # Active delay with progress updates to keep Azure connection alive
            logger.info("⏳ [WATER] Starting 6s delay with heartbeat progress updates")
            for i in range(6):  # 6 seconds, update every 1 second
                await asyncio.sleep(1)
                # Send progress update every second to keep connection alive (80-99%)
                yield {
                    "step": 4,
                    "status": "processing",
                    "message": "Generating interactive map visualization...",
                    "progress": 80 + int((i + 1) * 3.17),  # 83%, 86%, 90%, 93%, 96%, 99% (not 100%)
                    "details": f"Finalizing visualization ({i+1}/6)"
                }
            logger.info("✅ [WATER] Delay complete, preparing Step 5")
            
            # Step 5: Complete
            logger.info(f"🎯 [WATER] Preparing final result with analysis_data keys: {list(analysis_data.keys()) if analysis_data else 'None'}")
            
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
            logger.info(f"🎯 [WATER] Final result created with simplified ROI ({self._count_roi_points(simplified_roi)} points)")
            
            # CRITICAL FIX: Split Step 5 into smaller chunks to avoid Azure buffering
            # Step 5a: Metadata + stats (no ROI) - should be <10KB
            logger.info("📤 [WATER] Sending Step 5a (metadata + stats) to client now...")
            final_result_part1 = {
                "analysis_type": final_result["analysis_type"],
                "tile_url": final_result["tile_url"],
                "stats": final_result["stats"],
                "service_used": final_result["service_used"]
                # ROI sent separately in Step 5b
            }
            yield {
                "step": 5,
                "status": "processing",
                "message": "Water analysis complete!",
                "progress": 100,
                "details": "Delivering results...",
                "final_result": final_result_part1,
                "partial": True  # Signal that ROI is coming in next step
            }
            logger.info("✅ [WATER] Step 5a sent successfully")
            
            # Step 5b: ROI only - CRITICAL: Further simplify ROI to <5KB for Azure
            ultra_simplified_roi = self._ultra_simplify_roi_for_azure(simplified_roi)
            roi_size = len(json.dumps(ultra_simplified_roi))
            logger.info(f"📏 [WATER] Step 5b ROI size: {roi_size} bytes ({'✅ OK' if roi_size < 5000 else '⚠️ LARGE'})")
            
            await asyncio.sleep(0.1)  # Tiny delay between chunks
            logger.info("📤 [WATER] Sending Step 5b (ROI) to client now...")
            yield {
                "step": 5,
                "status": "completed",
                "message": "Water analysis complete!",
                "progress": 100,
                "details": "Interactive map ready with hover sampling",
                "final_result": {"roi": ultra_simplified_roi},
                "partial": True,  # Merge with previous final_result
                "complete": True  # This completes the final_result
            }
            logger.info("✅ [WATER] Step 5b sent successfully")
            
            # Step 6: TINY flush message to force Azure delivery
            await asyncio.sleep(0.1)  # Tiny delay to ensure Step 5b is processed
            yield {
                "step": 6,
                "status": "completed",
                "message": "Complete",
                "progress": 100,
                "flush": True
            }
            logger.info("🔄 [WATER] Tiny flush message sent (<1KB) to force Azure to deliver Steps 5a/5b")
            
        except Exception as e:
            logger.error(f"Error in water analysis steps: {e}")
            yield {
                "step": "error",
                "status": "error",
                "message": f"Analysis failed: {str(e)}",
                "progress": 0,
                "details": "Check server logs for details"
            }
        finally:
            # PHASE 1 FIX: Force cleanup of water service resources
            logger.debug("🧹 [WATER] Cleaning up processor resources")
            if water_service:
                del water_service
            gc.collect()
            logger.debug("✅ [WATER] Cleanup completed")
    
    async def process_lst_analysis_steps(self, roi: Dict, user_prompt: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Process LST analysis using existing working endpoint"""
        import gc
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
            
            # Get optimized parameters based on area size
            params = self._get_optimized_parameters(roi)
            logger.info(f"🔧 [LST] Using optimized parameters: scale={params['scale']}, maxPixels={params['maxPixels']}, timeout={params['timeout']}")
            
            # Step 2: Call existing working endpoint
            yield {
                "step": 2,
                "status": "processing",
                "message": "Analyzing land surface temperature using MODIS data...",
                "progress": 30,
                "details": f"Processing thermal infrared data (scale: {params['scale']}m, maxPixels: {params['maxPixels']:.0e})"
            }
            
            try:
                # Direct service call (monolithic architecture)
                from app.services.gee.lst_service import LSTService
                
                logger.info("🔬 Calling LSTService.analyze_lst_with_polygon directly...")
                result = LSTService.analyze_lst_with_polygon(
                    roi_data={"polygon_geometry": roi},  # Use correct key name
                    start_date="2023-06-01",
                    end_date="2023-08-31",
                    include_uhi=False,  # Disabled for performance (adds 10-30s per analysis)
                    include_time_series=False,
                    scale=params["scale"],
                    max_pixels=int(params["maxPixels"]),
                    exact_computation=params["exactComputation"]
                )
                # Check if LST service returned an error
                if not result.get("success", True):
                    error_msg = result.get("error", "Unknown LST error")
                    logger.error(f"❌ LST service returned error: {error_msg}")
                    raise Exception(f"LST analysis failed: {error_msg}")
                
                logger.info("✅ LST analysis completed successfully (direct call)")
                analysis_data = result
                
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
            
            # Active delay with progress updates to keep Azure connection alive
            logger.info("⏳ [LST] Starting 6s delay with heartbeat progress updates")
            for i in range(6):  # 6 seconds, update every 1 second
                await asyncio.sleep(1)
                # Send progress update every second to keep connection alive (80-99%)
                yield {
                    "step": 4,
                    "status": "processing",
                    "message": "Generating thermal visualization...",
                    "progress": 80 + int((i + 1) * 3.17),  # 83%, 86%, 90%, 93%, 96%, 99% (not 100%)
                    "details": f"Finalizing visualization ({i+1}/6)"
                }
            logger.info("✅ [LST] Delay complete, preparing Step 5")
            
            # Step 5: Complete
            # Simplify ROI for streaming (reduce polygon points to avoid JSON serialization hang)
            logger.info("🎯 [LST] Starting Step 5 preparation")
            simplified_roi = self._simplify_roi_for_streaming(roi)
            logger.info(f"🎯 [LST] Final result with simplified ROI ({self._count_roi_points(simplified_roi)} points)")
            
            # Extract tile URL with debug logging
            tile_url = analysis_data.get("urlFormat") or analysis_data.get("visualization", {}).get("tile_url")
            logger.info(f"🗺️ [LST] Tile_url extracted: {tile_url[:100] if tile_url else 'NONE'}")
            logger.info(f"📦 [LST] Response keys: {list(analysis_data.keys())}")
            
            # CRITICAL FIX: Split Step 5 into smaller chunks to avoid Azure buffering
            # Step 5a: Metadata + stats (no ROI) - should be <10KB
            logger.info("📤 [LST] Sending Step 5a (metadata + stats) to client now...")
            final_result_part1 = {
                "analysis_type": "lst",
                "tile_url": tile_url,
                "stats": {
                    **analysis_data.get("mapStats", {}),
                    "total_area_km2": analysis_data.get("roi_area_km2", 0)
                },
                "service_used": "GEE"
                # ROI sent separately in Step 5b
            }
            yield {
                "step": 5,
                "status": "processing",
                "message": "LST analysis complete!",
                "progress": 100,
                "details": "Delivering results...",
                "final_result": final_result_part1,
                "partial": True  # Signal that ROI is coming in next step
            }
            logger.info("✅ [LST] Step 5a sent successfully")
            
            # Step 5b: ROI only - CRITICAL: Further simplify ROI to <5KB for Azure
            ultra_simplified_roi = self._ultra_simplify_roi_for_azure(simplified_roi)
            roi_size = len(json.dumps(ultra_simplified_roi))
            logger.info(f"📏 [LST] Step 5b ROI size: {roi_size} bytes ({'✅ OK' if roi_size < 5000 else '⚠️ LARGE'})")
            
            await asyncio.sleep(0.1)  # Tiny delay between chunks
            logger.info("📤 [LST] Sending Step 5b (ROI) to client now...")
            yield {
                "step": 5,
                "status": "completed",
                "message": "LST analysis complete!",
                "progress": 100,
                "details": "Interactive thermal map ready",
                "final_result": {"roi": ultra_simplified_roi},
                "partial": True,  # Merge with previous final_result
                "complete": True  # This completes the final_result
            }
            logger.info("✅ [LST] Step 5b sent successfully")
            
            # Step 6: TINY flush message to force Azure delivery
            await asyncio.sleep(0.1)  # Tiny delay to ensure Step 5b is processed
            yield {
                "step": 6,
                "status": "completed",
                "message": "Complete",
                "progress": 100,
                "flush": True
            }
            logger.info("🔄 [LST] Tiny flush message sent (<1KB) to force Azure to deliver Steps 5a/5b")
            
        except Exception as e:
            logger.error(f"Error in LST analysis steps: {e}")
            yield {
                "step": "error",
                "status": "error",
                "message": f"Analysis failed: {str(e)}",
                "progress": 0,
                "details": "Check server logs for details"
            }
        finally:
            # PHASE 1 FIX: Force cleanup of LST analysis resources
            logger.debug("🧹 [LST] Cleaning up processor resources")
            gc.collect()
            logger.debug("✅ [LST] Cleanup completed")
    
    async def process_ndvi_analysis_steps(self, roi: Dict, user_prompt: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Process NDVI analysis using existing working endpoint"""
        import gc
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
            
            # Get optimized parameters based on area size
            params = self._get_optimized_parameters(roi)
            logger.info(f"🔧 [NDVI] Using optimized parameters: scale={params['scale']}, maxPixels={params['maxPixels']}, timeout={params['timeout']}")
            
            # Step 2: Call existing working endpoint
            yield {
                "step": 2,
                "status": "processing",
                "message": "Analyzing vegetation health using Sentinel-2 data...",
                "progress": 30,
                "details": f"Processing NDVI calculations (scale: {params['scale']}m, maxPixels: {params['maxPixels']:.0e})"
            }
            
            try:
                # Direct service call (monolithic architecture)
                from app.services.gee.ndvi_service import NDVIService
                
                logger.info("🔬 Calling NDVIService.analyze_ndvi_with_polygon directly...")
                result = NDVIService.analyze_ndvi_with_polygon(
                    roi_data={"polygon_geometry": roi},  # Use correct key name
                    start_date="2023-06-01",
                    end_date="2023-08-31",
                    cloud_threshold=30,
                    scale=params["scale"],
                    max_pixels=int(params["maxPixels"]),
                    include_time_series=False,
                    exact_computation=params["exactComputation"]
                )
                # Check if NDVI service returned an error
                if not result.get("success", True):
                    error_msg = result.get("error", "Unknown NDVI error")
                    logger.error(f"❌ NDVI service returned error: {error_msg}")
                    raise Exception(f"NDVI analysis failed: {error_msg}")
                
                logger.info("✅ NDVI analysis completed successfully (direct call)")
                analysis_data = result
                
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
            
            # Active delay with progress updates to keep Azure connection alive
            logger.info("⏳ [NDVI] Starting 6s delay with heartbeat progress updates")
            for i in range(6):  # 6 seconds, update every 1 second
                await asyncio.sleep(1)
                # Send progress update every second to keep connection alive (80-99%)
                yield {
                    "step": 4,
                    "status": "processing",
                    "message": "Generating vegetation visualization...",
                    "progress": 80 + int((i + 1) * 3.17),  # 83%, 86%, 90%, 93%, 96%, 99% (not 100%)
                    "details": f"Finalizing visualization ({i+1}/6)"
                }
            logger.info("✅ [NDVI] Delay complete, preparing Step 5")
            
            # Step 5: Complete
            # Simplify ROI for streaming (reduce polygon points to avoid JSON serialization hang)
            logger.info("🎯 [NDVI] Starting Step 5 preparation")
            simplified_roi = self._simplify_roi_for_streaming(roi)
            logger.info(f"🎯 [NDVI] Final result with simplified ROI ({self._count_roi_points(simplified_roi)} points)")
            
            # Extract tile URL with debug logging (same as LST), with NDVI-specific fallback
            tile_url = (
                analysis_data.get("urlFormat")
                or analysis_data.get("visualization", {}).get("tile_url")
                or analysis_data.get("tile_urls", {}).get("urlFormat")
            )
            logger.info(f"🗺️ NDVI tile_url extracted: {tile_url[:100] if tile_url else 'NONE'}")
            logger.info(f"📦 NDVI response keys: {list(analysis_data.keys())}")

            # NDVI stats may come as mapStats.ndvi_statistics or ndvi_stats
            ndvi_stats = (
                analysis_data.get("mapStats", {}).get("ndvi_statistics")
                or analysis_data.get("ndvi_stats", {})
                or {}
            )
            total_area_km2 = analysis_data.get("roi_area_km2", analysis_data.get("area_km2", 0))
            
            # CRITICAL FIX: Split Step 5 into smaller chunks to avoid Azure buffering
            # Step 5a: Metadata + stats (no ROI) - should be <10KB
            logger.info("📤 [NDVI] Sending Step 5a (metadata + stats) to client now...")
            final_result_part1 = {
                "analysis_type": "ndvi",
                "tile_url": tile_url,
                "stats": {
                    **ndvi_stats,
                    "total_area_km2": total_area_km2
                },
                "service_used": "GEE"
                # ROI sent separately in Step 5b
            }
            yield {
                "step": 5,
                "status": "processing",
                "message": "Vegetation analysis complete!",
                "progress": 100,
                "details": "Delivering results...",
                "final_result": final_result_part1,
                "partial": True  # Signal that ROI is coming in next step
            }
            logger.info("✅ [NDVI] Step 5a sent successfully")
            
            # Step 5b: ROI only - CRITICAL: Further simplify ROI to <5KB for Azure
            ultra_simplified_roi = self._ultra_simplify_roi_for_azure(simplified_roi)
            roi_size = len(json.dumps(ultra_simplified_roi))
            logger.info(f"📏 [NDVI] Step 5b ROI size: {roi_size} bytes ({'✅ OK' if roi_size < 5000 else '⚠️ LARGE'})")
            
            await asyncio.sleep(0.1)  # Tiny delay between chunks
            logger.info("📤 [NDVI] Sending Step 5b (ROI) to client now...")
            yield {
                "step": 5,
                "status": "completed",
                "message": "Vegetation analysis complete!",
                "progress": 100,
                "details": "Interactive vegetation map ready",
                "final_result": {"roi": ultra_simplified_roi},
                "partial": True,  # Merge with previous final_result
                "complete": True  # This completes the final_result
            }
            logger.info("✅ [NDVI] Step 5b sent successfully")
            
            # Step 6: TINY flush message to force Azure delivery
            await asyncio.sleep(0.1)  # Tiny delay to ensure Step 5b is processed
            yield {
                "step": 6,
                "status": "completed",
                "message": "Complete",
                "progress": 100,
                "flush": True
            }
            logger.info("🔄 [NDVI] Tiny flush message sent (<1KB) to force Azure to deliver Steps 5a/5b")
            
        except Exception as e:
            logger.error(f"Error in NDVI analysis steps: {e}")
            yield {
                "step": "error",
                "status": "error",
                "message": f"Analysis failed: {str(e)}",
                "progress": 0,
                "details": "Check server logs for details"
            }
        finally:
            # PHASE 1 FIX: Force cleanup of NDVI analysis resources
            logger.debug("🧹 [NDVI] Cleaning up processor resources")
            gc.collect()
            logger.debug("✅ [NDVI] Cleanup completed")
    
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
    
    def _ultra_simplify_roi_for_azure(self, roi: dict) -> dict:
        """
        Ultra-aggressive simplification for Azure streaming.
        Reduces ROI to ~200 points to keep payload <5KB (below Azure buffering threshold).
        """
        if not roi or not isinstance(roi, dict):
            return roi
        
        roi_type = roi.get('type')
        coordinates = roi.get('coordinates')
        
        if roi_type != 'Polygon' or not coordinates or not coordinates[0]:
            return roi
        
        outer_ring = coordinates[0]
        num_points = len(outer_ring)
        
        # Ultra-aggressive limit: 200 points (~4-5KB JSON) to avoid Azure buffering
        MAX_POINTS_FOR_AZURE = 200
        
        if num_points <= MAX_POINTS_FOR_AZURE:
            return roi
        
        # Use aggressive simplification
        simplified_ring = self._adaptive_simplify_polygon(outer_ring, MAX_POINTS_FOR_AZURE)
        
        logger.info(f"Ultra-simplified ROI for Azure: {num_points} → {len(simplified_ring)} points")
        
        return {
            'type': 'Polygon',
            'coordinates': [simplified_ring],
            'display_name': roi.get('display_name'),
            'center': roi.get('center')
        }
