"""
Main Query Router - Handles all geospatial query requests
"""

import logging
from typing import Optional, Dict, Any, AsyncGenerator
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================

class QueryRequest(BaseModel):
    """Request model for the /query endpoint"""
    query: str = Field(..., min_length=1, max_length=2000, description="User query")
    rag_session_id: Optional[str] = Field(None, description="RAG session ID if documents were uploaded")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "Analyze NDVI vegetation health for Mumbai",
                "rag_session_id": None
            }
        }


class QueryResponse(BaseModel):
    """Response model for the /query endpoint"""
    analysis: str = Field(..., description="Analysis result from GEE or Search service")
    roi: Optional[Dict[str, Any]] = Field(None, description="Region of interest GeoJSON data")
    service_used: Optional[str] = Field(None, description="Which service was used (GEE/Search/RAG)")
    analysis_data: Optional[Dict[str, Any]] = Field(None, description="Raw analysis data including tile URLs")
    success: bool = Field(..., description="Whether the query was successful")
    error: Optional[str] = Field(None, description="Error message if any")
    processing_time: Optional[float] = Field(None, description="Processing time in seconds")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    class Config:
        json_schema_extra = {
            "example": {
                "analysis": "NDVI analysis completed for Mumbai...",
                "roi": {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": []}},
                "service_used": "GEE",
                "success": True,
                "error": None,
                "processing_time": 3.45
            }
        }


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/query", response_model=QueryResponse)
async def process_query(request_data: QueryRequest, request: Request):
    """
    Process a geospatial query using the Core LLM Agent.
    
    This endpoint:
    1. Accepts user queries in natural language
    2. Routes to appropriate service (GEE, Search, or RAG)
    3. Returns analysis results with ROI data
    
    Args:
        request_data: Query request with query text and optional RAG session ID
        request: FastAPI request object (for accessing app state)
    
    Returns:
        QueryResponse with analysis, ROI, and metadata
    
    Examples:
        - "Analyze NDVI for Mumbai"
        - "Show land surface temperature in Delhi"
        - "What is the water coverage in Bangalore?"
    """
    import time
    start_time = time.time()
    
    try:
        # Get Core LLM Agent from app state
        core_agent = request.app.state.core_agent
        if not core_agent:
            raise HTTPException(
                status_code=503,
                detail="Core LLM Agent not initialized"
            )
        
        # Log the query
        logger.info(f"📝 Processing query: {request_data.query[:100]}...")
        if request_data.rag_session_id:
            logger.info(f"📚 RAG session ID: {request_data.rag_session_id[:8]}...")
        
        # Process query through Core LLM Agent
        result = core_agent.process_query(
            query=request_data.query,
            rag_session_id=request_data.rag_session_id
        )
        
        processing_time = time.time() - start_time
        
        # Extract response fields
        analysis = result.get("analysis", "No analysis generated")
        roi = result.get("roi")
        analysis_data = result.get("analysis_data")
        metadata = result.get("metadata", {})
        service_used = metadata.get("service_type", "unknown")
        success = result.get("success", True)
        error = result.get("error")
        
        logger.info(f"✅ Query processed successfully in {processing_time:.2f}s")
        logger.info(f"🔧 Service used: {service_used}")
        
        return QueryResponse(
            analysis=analysis,
            roi=roi,
            service_used=service_used,
            analysis_data=analysis_data,
            success=success,
            error=error,
            processing_time=processing_time,
            metadata=metadata
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
        
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"❌ Error processing query: {e}")
        
        import traceback
        logger.error(traceback.format_exc())
        
    return QueryResponse(
            analysis=f"Error processing query: {str(e)}",
            roi=None,
            service_used="error",
            analysis_data=None,
            success=False,
            error=str(e),
            processing_time=processing_time,
            metadata={"error_type": type(e).__name__}
        )


@router.get("/status")
async def get_status(request: Request):
    """
    Get current status of the query processing system.
    
    Returns information about:
    - Core agent status
    - Available services
    - System health
    """
    try:
        core_agent = request.app.state.core_agent
        
        if not core_agent:
            return {
                "status": "unavailable",
                "message": "Core LLM Agent not initialized"
            }
        
        # Get component status
        component_status = core_agent.get_component_status()
        
        return {
            "status": "healthy",
            "message": "Query processing system operational",
            "components": component_status
        }
        
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


# ============================================================================
# Streaming CoT Endpoint (minimal reuse of existing SimpleStepProcessor)
# ============================================================================

class StreamQueryRequest(BaseModel):
    """Request model for /query/stream endpoint (minimal extension)."""
    query: str = Field(..., min_length=1, max_length=2000)
    rag_session_id: Optional[str] = None
    roi: Optional[dict] = None  # GeoJSON Polygon/MultiPolygon
    analysis_hint: Optional[str] = Field(
        None,
        description="Optional hint: ndvi|lst|lulc|water; only used by SimpleStepProcessor if provided",
    )


async def _stream_steps(roi: Dict[str, Any], user_prompt: str) -> AsyncGenerator[bytes, None]:
    """Yield SSE lines from the existing SimpleStepProcessor with Azure-compatible streaming."""
    import json
    import logging as _logging
    import asyncio
    import time
    import gc

    stream_start_time = time.time()
    steps_sent = 0
    has_final_result = False
    processor = None
    
    try:
        _logging.info("=" * 80)
        _logging.info("🚀 [AZURE-DEBUG] Starting SSE stream")
        _logging.info(f"   Query: {user_prompt[:100]}...")
        _logging.info(f"   ROI type: {roi.get('type', 'unknown')}")
        _logging.info("=" * 80)
        
        # Import the already working step processor
        from app.services.core_llm_agent.simple_step_processor import SimpleStepProcessor

        processor = SimpleStepProcessor()
        
        # Send initial keep-alive comment to establish connection
        _logging.info("📡 Sending initial keep-alive to establish connection")
        yield ": keep-alive\n\n".encode("utf-8")

        last_heartbeat = asyncio.get_event_loop().time()
        
        async for step in processor.process_analysis_steps(roi, user_prompt):
            steps_sent += 1
            step_num = step.get("step", "?")
            step_status = step.get("status", "?")
            step_progress = step.get("progress", 0)
            
            _logging.info(f"📊 [AZURE-DEBUG] Sending step {step_num} - Status: {step_status}, Progress: {step_progress}%")
            
            # Check if this step contains final_result
            if "final_result" in step:
                has_final_result = True
                final_result_size = len(json.dumps(step.get("final_result", {})))
                _logging.info(f"🎯 [AZURE-DEBUG] Step {step_num} contains final_result (size: {final_result_size} bytes)")
                _logging.info(f"   Final result keys: {list(step.get('final_result', {}).keys())}")
            
            # Send the actual step data
            try:
                payload = f"data: {json.dumps(step)}\n\n".encode("utf-8")
                _logging.debug(f"   Payload size: {len(payload)} bytes")
                yield payload
                _logging.info(f"✅ [AZURE-DEBUG] Step {step_num} sent successfully")
            except Exception as json_err:
                _logging.error(f"❌ [AZURE-DEBUG] Failed to serialize step {step_num}: {json_err}")
                raise
            
            # Azure Fix: Add periodic heartbeat to keep connection alive
            current_time = asyncio.get_event_loop().time()
            if current_time - last_heartbeat > 15:  # Every 15 seconds
                _logging.debug("💓 Sending keep-alive heartbeat")
                yield ": heartbeat\n\n".encode("utf-8")
                last_heartbeat = current_time

        # Safety: if processor ended without a final step, emit a soft-complete
        if not has_final_result:
            _logging.warning("⚠️ [AZURE-DEBUG] No final_result detected in stream, sending soft-complete")
            soft_complete = {"step": 1, "status": "complete", "message": "Analysis complete", "progress": 100}
            yield f"data: {json.dumps(soft_complete)}\n\n".encode("utf-8")
        
        # Final flush to ensure all data is sent
        stream_duration = time.time() - stream_start_time
        _logging.info("=" * 80)
        _logging.info("✅ [AZURE-DEBUG] Streaming completed successfully")
        _logging.info(f"   Total steps sent: {steps_sent}")
        _logging.info(f"   Duration: {stream_duration:.2f}s")
        _logging.info(f"   Has final result: {has_final_result}")
        _logging.info("=" * 80)

    except Exception as e:  # pragma: no cover – best-effort streaming
        stream_duration = time.time() - stream_start_time
        _logging.error("=" * 80)
        _logging.error(f"❌ [AZURE-DEBUG] Streaming failed after {stream_duration:.2f}s")
        _logging.error(f"   Steps sent before failure: {steps_sent}")
        _logging.error(f"   Error: {e}")
        _logging.error("=" * 80)
        import traceback
        _logging.error(traceback.format_exc())
        err = {"step": 0, "status": "error", "message": str(e)}
        yield f"data: {json.dumps(err)}\n\n".encode("utf-8")
    
    finally:
        # PHASE 1 FIX: Force cleanup of stream resources
        _logging.info("🧹 [AZURE-DEBUG] Cleaning up stream resources...")
        if processor:
            del processor
        # Force garbage collection to free Earth Engine resources
        gc.collect()
        _logging.info("✅ [AZURE-DEBUG] Stream resources cleaned up successfully")


@router.post("/query/stream")
async def process_query_stream(request_data: StreamQueryRequest, request: Request):
    """
    Stream real-time Chain-of-Thought analysis steps using the existing
    SimpleStepProcessor. Minimal change: we expect the frontend to provide
    an ROI from /api/search/location-data and the natural-language query.

    If ROI is missing, we emit an immediate error step to keep behavior explicit.
    
    Azure-Compatible: Includes proper headers to prevent buffering and connection drops.
    """
    import json

    # Require ROI for deterministic GEE processing (keeps changes minimal)
    if not request_data.roi:
        def _error_gen():
            err = {
                "step": 0,
                "status": "error",
                "message": "ROI is required for streaming analysis. Resolve location first.",
            }
            yield f"data: {json.dumps(err)}\n\n".encode("utf-8")
        return StreamingResponse(
            _error_gen(), 
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-transform",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
            }
        )

    logger.info(f"🚀 Starting streaming analysis for query: {request_data.query[:100]}...")
    
    # Azure-compatible streaming response with anti-buffering headers
    return StreamingResponse(
        _stream_steps(request_data.roi, request_data.query),
        media_type="text/event-stream",
        headers={
            # Critical Azure headers to prevent buffering
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",  # Nginx/Azure buffering control
            "Connection": "keep-alive",
            "Content-Encoding": "none",  # Prevent compression buffering
            # CORS headers for cross-origin requests
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        }
    )


# ============================================================================
# Point Sampling Endpoint for hover tooltips (NDVI/LST/Water)
# ============================================================================

class SampleRequest(BaseModel):
    analysis_type: str = Field(..., description="ndvi | lst | water")
    lon: float = Field(..., description="Longitude")
    lat: float = Field(..., description="Latitude")
    roi: Optional[dict] = None


@router.post("/query/sample")
async def sample_point(request_data: SampleRequest):
    try:
        atype = request_data.analysis_type.lower()

        if atype == "water":
            from app.services.gee.water_service import WaterService
            svc = WaterService()
            result = svc.sample_water_at_point(request_data.lon, request_data.lat)
            return result

        elif atype == "ndvi":
            from app.services.gee.ndvi_service import NDVIService
            return NDVIService.sample_ndvi_at_point(
                lng=request_data.lon,
                lat=request_data.lat,
                start_date="2023-06-01",
                end_date="2023-08-31",
                scale=30,
                cloud_threshold=20,
            )

        elif atype == "lst":
            from app.services.gee.lst_service import LSTService
            return LSTService.sample_lst_at_point(
                lng=request_data.lon,
                lat=request_data.lat,
                start_date="2023-06-01",
                end_date="2023-08-31",
                scale=1000,
            )

        else:
            return {"success": False, "error": f"Unsupported analysis_type: {atype}"}

    except Exception as e:
        logger.error(f"Sample failed: {e}")
        return {"success": False, "error": str(e)}
