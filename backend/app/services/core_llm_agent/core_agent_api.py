"""
Core LLM Agent API - Simple endpoint for GEE and Search services
"""

import logging
import time
import json
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

try:
    from .agent import CoreLLMAgent
except ImportError:
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent.parent))
    from app.services.core_llm_agent.agent import CoreLLMAgent

logger = logging.getLogger(__name__)

def generate_ndvi_analysis(mean_val, min_val, max_val, location="the region"):
    """Generate natural language analysis of NDVI statistics."""
    try:
        mean_val = float(mean_val)
        min_val = float(min_val) if min_val is not None else None
        max_val = float(max_val) if max_val is not None else None
    except (ValueError, TypeError):
        return f"NDVI analysis completed for {location}, but statistical values could not be processed."
    
    # Interpret NDVI values
    if mean_val > 0.6:
        health_status = "excellent vegetation health"
        vegetation_desc = "dense, healthy vegetation cover"
    elif mean_val > 0.4:
        health_status = "good vegetation health"
        vegetation_desc = "moderate to dense vegetation"
    elif mean_val > 0.2:
        health_status = "moderate vegetation health"
        vegetation_desc = "sparse to moderate vegetation"
    elif mean_val > 0:
        health_status = "poor vegetation health"
        vegetation_desc = "very sparse vegetation"
    else:
        health_status = "minimal vegetation"
        vegetation_desc = "predominantly non-vegetated areas"
    
    # Build natural language analysis
    analysis = f"The NDVI analysis of {location} reveals {health_status} with an average NDVI value of {mean_val:.3f}. "
    analysis += f"This indicates {vegetation_desc} across the analyzed area.\n\n"
    
    if min_val is not None and max_val is not None:
        range_val = max_val - min_val
        analysis += f"The vegetation shows significant spatial variation, with NDVI values ranging from {min_val:.3f} to {max_val:.3f} (range: {range_val:.3f}). "
        
        if min_val < -0.1:
            analysis += "The negative minimum values suggest the presence of water bodies, urban infrastructure, or bare soil. "
        
        if max_val > 0.7:
            analysis += "The high maximum values indicate areas of very healthy, dense vegetation such as parks, forests, or well-maintained green spaces. "
        elif max_val > 0.4:
            analysis += "The maximum values show good vegetation coverage in the healthiest areas. "
    
    # Contextual interpretation
    if mean_val < 0.3:
        analysis += f"\n\nFor an urban area like {location}, this NDVI pattern is typical, reflecting a mix of built-up areas, roads, and scattered green spaces. "
        analysis += "The moderate values suggest opportunities for urban greening initiatives to improve vegetation coverage."
    else:
        analysis += f"\n\nThis vegetation profile indicates a good balance of green cover for {location}, suggesting effective urban planning or natural vegetation preservation."
    
    return analysis

# Request/Response Models
class QueryRequest(BaseModel):
    """Request model for the /query endpoint."""
    query: str = Field(..., min_length=1, max_length=2000, description="User query")
    rag_session_id: Optional[str] = Field(None, description="RAG session ID if available")

class QueryResponse(BaseModel):
    """Response model for the /query endpoint."""
    analysis: str = Field(..., description="Analysis result from GEE or Search service")
    service_used: str = Field(..., description="Which service was used (GEE/Search)")
    roi: Optional[Dict[str, Any]] = Field(None, description="Region of interest data")
    analysis_data: Optional[Dict[str, Any]] = Field(None, description="Raw analysis data including tile URLs")
    success: bool = Field(..., description="Whether the query was successful")
    error: Optional[str] = Field(None, description="Error message if any")
    processing_time: float = Field(..., description="Processing time in seconds")

class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    services: Dict[str, bool]
    timestamp: float

# Initialize FastAPI app
app = FastAPI(
    title="Core LLM Agent API",
    description="API for GEE and Search services via Core LLM Agent",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the agent
agent = None

def get_agent() -> CoreLLMAgent:
    """Get or create the Core LLM Agent instance."""
    global agent
    if agent is None:
        try:
            agent = CoreLLMAgent(enable_debug=True)
            logger.info("Core LLM Agent initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Core LLM Agent: {e}")
            raise HTTPException(
                status_code=503,
                detail="Core LLM Agent service unavailable"
            )
    return agent

@app.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest) -> QueryResponse:
    """Process a query using GEE or Search services."""
    start_time = time.time()
    
    try:
        agent = get_agent()
        
        # Log RAG session if provided
        if request.rag_session_id:
            logger.info(f"RAG session ID provided: {request.rag_session_id[:8]}...")
        else:
            logger.info("No RAG session ID provided")
        
        # Process the query
        result = agent.process_query(request.query, request.rag_session_id)
        
        processing_time = time.time() - start_time
        
        # Extract the analysis text and service used
        # Get the AI-generated analysis
        ai_analysis = result.get("analysis", "")
        analysis_data = result.get("analysis_data", {})
        
        # Build comprehensive analysis combining AI insights with raw data
        # Check if ai_analysis is just formatted display text (starts with emoji/symbols)
        is_display_format = ai_analysis and (ai_analysis.startswith('🔍') or ai_analysis.startswith('==') or 'Query:' in ai_analysis[:100])
        
        if ai_analysis and not ("analysis completed" in ai_analysis.lower() and len(ai_analysis) < 50) and not is_display_format:
            # We have good AI analysis, enhance it with statistics
            analysis = f"🤖 **AI Analysis:**\n{ai_analysis}\n\n"
            
            if analysis_data:
                analysis_type = analysis_data.get("analysis_type", "analysis")
                mean_val = analysis_data.get("mean_ndvi") or analysis_data.get("mean")
                min_val = analysis_data.get("min_ndvi") or analysis_data.get("min")
                max_val = analysis_data.get("max_ndvi") or analysis_data.get("max")
                
                analysis += f"📊 **Statistical Summary:**\n"
                if mean_val is not None:
                    analysis += f"• Mean NDVI: {mean_val}\n"
                if min_val is not None:
                    analysis += f"• Min NDVI: {min_val}\n"
                if max_val is not None:
                    analysis += f"• Max NDVI: {max_val}\n"
                    
        elif analysis_data:
            # If backend signaled an error in analysis_data, surface that directly
            has_error = analysis_data.get("error") is not None
            if has_error:
                analysis = analysis_data.get("error")
                analysis_type = "error"
                mean_val = min_val = max_val = None
            else:
                # Generate natural language analysis from raw data
                analysis_type = analysis_data.get("analysis_type", "analysis")
                mean_val = analysis_data.get("mean_ndvi") or analysis_data.get("mean")
                min_val = analysis_data.get("min_ndvi") or analysis_data.get("min")
                max_val = analysis_data.get("max_ndvi") or analysis_data.get("max")
            
            if not has_error and analysis_type.lower() == "ndvi" and mean_val is not None:
                # Extract location from ROI if available
                location_name = "the region"
                if result.get("roi") and result["roi"].get("display_name"):
                    location_name = result["roi"]["display_name"].split(',')[0]
                
                # Generate natural language NDVI analysis
                natural_analysis = generate_ndvi_analysis(mean_val, min_val, max_val, location_name)
                analysis = f"🤖 **AI Analysis:**\n{natural_analysis}\n\n"
                analysis += f"📊 **Statistical Summary:**\n"
                analysis += f"• Mean NDVI: {mean_val}\n"
                if min_val is not None:
                    analysis += f"• Min NDVI: {min_val}\n"
                if max_val is not None:
                    analysis += f"• Max NDVI: {max_val}\n"
            elif not has_error and analysis_type.lower() == "water":
                # Handle water analysis specifically
                water_percentage = analysis_data.get("water_percentage")
                non_water_percentage = analysis_data.get("non_water_percentage")
                
                # Extract location from ROI if available
                location_name = "the region"
                if result.get("roi") and result["roi"].get("display_name"):
                    location_name = result["roi"]["display_name"].split(',')[0]
                
                if water_percentage is not None:
                    water_pct = float(water_percentage)
                    non_water_pct = float(non_water_percentage) if non_water_percentage else (100 - water_pct)
                    
                    # Generate natural language water analysis
                    if water_pct > 50:
                        water_status = "extensive water coverage"
                        water_desc = "predominantly water bodies such as lakes, rivers, or wetlands"
                    elif water_pct > 20:
                        water_status = "significant water presence"
                        water_desc = "substantial water bodies with mixed land cover"
                    elif water_pct > 5:
                        water_status = "moderate water coverage"
                        water_desc = "scattered water bodies like ponds, streams, or small lakes"
                    elif water_pct > 1:
                        water_status = "limited water coverage"
                        water_desc = "sparse water features with mostly dry land"
                    else:
                        water_status = "minimal water coverage"
                        water_desc = "predominantly dry land with very few water features"
                    
                    natural_analysis = f"The water analysis of {location_name} reveals {water_status} with {water_pct:.2f}% of the area covered by water bodies. "
                    natural_analysis += f"This indicates {water_desc} across the analyzed region.\n\n"
                    natural_analysis += f"The remaining {non_water_pct:.2f}% consists of land areas including urban development, vegetation, and bare soil. "
                    
                    if water_pct < 1:
                        natural_analysis += f"The low water coverage suggests {location_name} is primarily a terrestrial environment with limited surface water resources."
                    elif water_pct > 10:
                        natural_analysis += f"The substantial water coverage indicates {location_name} has significant aquatic ecosystems and water resources."
                    
                    analysis = f"🤖 **AI Analysis:**\n{natural_analysis}\n\n"
                    analysis += f"💧 **Water Coverage Summary:**\n"
                    analysis += f"• Water Coverage: {water_pct:.2f}%\n"
                    analysis += f"• Land Coverage: {non_water_pct:.2f}%\n"
                else:
                    analysis = f"💧 **WATER Analysis Results:**\n\n"
                    analysis += f"📊 Water analysis completed for {location_name}\n"
            else:
                # Fallback for other analysis types
                analysis = f"🌱 **{analysis_type.upper()} Analysis Results:**\n\n"
                analysis += f"📊 Mean Value: {mean_val}\n"
                if min_val is not None:
                    analysis += f"📉 Min Value: {min_val}\n"
                if max_val is not None:
                    analysis += f"📈 Max Value: {max_val}\n"
                # Do NOT append a success line if we don't have tiles; leave concise
        else:
            # Last resort fallback
            analysis = ai_analysis or "No analysis generated"
            
        service_used = result.get("metadata", {}).get("service_type", "unknown")
        roi = result.get("roi")
        success = result.get("success", True)
        error = result.get("error")
        
        # Log the raw result for debugging
        logger.info(f"Raw result keys: {list(result.keys())}")
        if analysis_data:
            logger.info(f"Analysis data keys: {list(analysis_data.keys())}")
            logger.info(f"Analysis data values: {analysis_data}")
        
        logger.info(f"AI analysis length: {len(ai_analysis) if ai_analysis else 0}")
        logger.info(f"AI analysis content: {ai_analysis[:100] if ai_analysis else 'None'}...")
        logger.info(f"Final analysis length: {len(analysis) if analysis else 0}")
        
        return QueryResponse(
            analysis=analysis,
            service_used=service_used,
            roi=roi,
            analysis_data=analysis_data,
            success=success,
            error=error,
            processing_time=processing_time
        )
        
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Error processing query: {e}")
        
        return QueryResponse(
            analysis=f"Error processing query: {str(e)}",
            service_used="error",
            roi=None,
            analysis_data=None,
            success=False,
            error=str(e),
            processing_time=processing_time
        )

@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    try:
        agent = get_agent()
        
        # Check if services are available (simplified)
        services = {
            "core_agent": True,
            "gee_service": True,  # Assume available for now
            "search_service": True  # Assume available for now
        }
        
        return HealthResponse(
            status="healthy",
            services=services,
            timestamp=time.time()
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            services={"core_agent": False, "gee_service": False, "search_service": False},
            timestamp=time.time()
        )

# Request model for COT streaming
class COTStreamRequest(BaseModel):
    user_prompt: str = Field(..., description="User's analysis request")
    roi: Optional[Dict[str, Any]] = Field(None, description="Region of Interest GeoJSON")

@app.post("/cot-stream")
async def stream_cot_analysis(request: COTStreamRequest):
    """
    Stream Chain of Thought analysis step by step with real backend execution
    
    This endpoint provides real-time COT where each step is actually executed
    in the backend before showing the next step to the user.
    """
    try:
        from .simple_step_processor import SimpleStepProcessor
        
        processor = SimpleStepProcessor()
    
        async def generate_cot_stream():
            try:
                async for step in processor.process_analysis_steps(request.roi or {}, request.user_prompt):
                    yield f"data: {json.dumps(step)}\n\n"
            except Exception as e:
                logger.error(f"Error in COT streaming: {e}")
                error_step = {
                    "step": "error",
                    "status": "error", 
                    "message": f"Streaming failed: {str(e)}",
                    "progress": 0,
                    "details": "Check server logs for details"
                }
                yield f"data: {json.dumps(error_step)}\n\n"
        
        return StreamingResponse(
            generate_cot_stream(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type"
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to start COT streaming: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start COT streaming: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003, reload=True)
