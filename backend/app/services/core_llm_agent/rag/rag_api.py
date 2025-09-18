"""
FastAPI RAG Service with /ask endpoint for Core LLM Agent Integration.

This module provides a FastAPI wrapper around the RAG service to expose
the /ask endpoint for external clients and integration with the core system.
"""

import logging
import time
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from contextlib import asynccontextmanager

try:
    from .rag_service import RAGService, RAGResponse, create_rag_service
except ImportError:
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent.parent.parent))
    from app.services.core_llm_agent.rag.rag_service import RAGService, RAGResponse, create_rag_service

logger = logging.getLogger(__name__)


# Request/Response Models
class AskRequest(BaseModel):
    """Request model for the /ask endpoint."""
    query: str = Field(..., min_length=1, max_length=2000, description="User question")
    session_id: Optional[str] = Field(None, description="Specific session ID for document context")
    k: int = Field(default=5, ge=1, le=20, description="Number of document chunks to retrieve")
    temperature: float = Field(default=0.7, ge=0.0, le=1.0, description="LLM sampling temperature")
    max_tokens: int = Field(default=1000, ge=100, le=4000, description="Maximum tokens in response")
    template_name: Optional[str] = Field(None, description="Specific prompt template to use")
    include_metadata: bool = Field(default=True, description="Include detailed metadata in response")


class SourceInfo(BaseModel):
    """Source information model."""
    content: str = Field(..., description="Source content excerpt")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Source metadata")
    score: float = Field(..., description="Relevance score")
    context_reference: str = Field(..., description="Context reference (e.g., 'Context 1')")
    cited_in_response: bool = Field(..., description="Whether this source was cited in the response")
    source_name: Optional[str] = Field(None, description="Source document name")
    page: Optional[int] = Field(None, description="Page number if available")
    year: Optional[int] = Field(None, description="Publication year if available")


class AskResponse(BaseModel):
    """Response model for the /ask endpoint."""
    answer: str = Field(..., description="Generated answer based on retrieved context")
    sources: List[SourceInfo] = Field(..., description="Source documents used for the answer")
    query: str = Field(..., description="Original user query")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Overall confidence score")
    processing_time: float = Field(..., description="Total processing time in seconds")
    chunks_retrieved: int = Field(..., description="Number of document chunks retrieved")
    model_used: str = Field(..., description="LLM model used for response generation")
    template_used: str = Field(..., description="Prompt template used")
    success: bool = Field(..., description="Whether the request was successful")
    error: Optional[str] = Field(None, description="Error message if request failed")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str = Field(..., description="Error message")
    details: Optional[str] = Field(None, description="Additional error details")
    timestamp: float = Field(..., description="Error timestamp")


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str = Field(..., description="Overall health status")
    components: Dict[str, Any] = Field(..., description="Component health details")
    configuration: Dict[str, Any] = Field(..., description="Service configuration")
    timestamp: float = Field(..., description="Health check timestamp")


# Global RAG service instance
rag_service: Optional[RAGService] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    global rag_service
    
    # Startup
    logger.info("🚀 Starting RAG API Service...")
    rag_service = create_rag_service()
    
    # Test service health
    health = await rag_service.health_check()
    logger.info(f"RAG Service Health: {health['status']}")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down RAG API Service...")
    rag_service = None


# Create FastAPI application
app = FastAPI(
    title="RAG Service API",
    description="Retrieval-Augmented Generation service for grounded question answering",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_rag_service() -> RAGService:
    """Dependency to get the RAG service instance."""
    if rag_service is None:
        raise HTTPException(
            status_code=503,
            detail="RAG service not initialized"
        )
    return rag_service


@app.post(
    "/ask",
    response_model=AskResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Bad request"},
        503: {"model": ErrorResponse, "description": "Service unavailable"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Ask a question with RAG",
    description="""
    Ask a question and get a grounded answer based on retrieved document context.
    
    **Process:**
    1. Retrieve relevant document chunks based on the query
    2. Build a context-aware prompt with the retrieved information
    3. Generate a grounded response using an LLM
    4. Return the answer with source citations
    
    **Features:**
    - Semantic search over uploaded documents
    - Multiple prompt templates for different domains
    - Source citation and confidence scoring
    - Configurable retrieval and generation parameters
    """
)
async def ask_question(
    request: AskRequest,
    service: RAGService = Depends(get_rag_service)
) -> AskResponse:
    """Main RAG endpoint for question answering."""
    try:
        # Call the RAG service
        rag_response = await service.ask(
            query=request.query,
            session_id=request.session_id,
            k=request.k,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            template_name=request.template_name,
            include_metadata=request.include_metadata
        )
        
        # Convert sources to response format
        sources = []
        for source in rag_response.sources:
            source_info = SourceInfo(
                content=source["content"],
                metadata=source["metadata"],
                score=source["score"],
                context_reference=source["context_reference"],
                cited_in_response=source["cited_in_response"],
                source_name=source.get("source_name"),
                page=source.get("page"),
                year=source.get("year")
            )
            sources.append(source_info)
        
        # Build response
        return AskResponse(
            answer=rag_response.answer,
            sources=sources,
            query=rag_response.query,
            confidence=rag_response.confidence,
            processing_time=rag_response.processing_time,
            chunks_retrieved=rag_response.chunks_retrieved,
            model_used=rag_response.model_used,
            template_used=rag_response.template_used,
            success=rag_response.success,
            error=rag_response.error,
            metadata=rag_response.metadata
        )
        
    except Exception as e:
        logger.error(f"Error in ask endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Check the health of the RAG service and its dependencies."
)
async def health_check(
    service: RAGService = Depends(get_rag_service)
) -> HealthResponse:
    """Health check endpoint."""
    try:
        health = await service.health_check()
        
        return HealthResponse(
            status=health["status"],
            components=health["components"],
            configuration=health["configuration"],
            timestamp=time.time()
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Health check failed: {str(e)}"
        )


@app.get(
    "/templates",
    response_model=List[str],
    summary="Get available prompt templates",
    description="Get a list of available prompt templates for different domains."
)
async def get_templates(
    service: RAGService = Depends(get_rag_service)
) -> List[str]:
    """Get available prompt templates."""
    try:
        return service.prompt_builder.get_available_templates()
    except Exception as e:
        logger.error(f"Error getting templates: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving templates: {str(e)}"
        )


@app.get(
    "/",
    summary="Root endpoint",
    description="Basic service information and status."
)
async def root():
    """Root endpoint with service information."""
    return {
        "service": "RAG API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "ask": "/ask",
            "health": "/health",
            "templates": "/templates",
            "docs": "/docs"
        }
    }


# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Handle 404 errors."""
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=404,
        content={
            "error": "Endpoint not found",
            "details": f"The requested endpoint {request.url.path} does not exist",
            "timestamp": time.time()
        }
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """Handle 500 errors."""
    from fastapi.responses import JSONResponse
    logger.error(f"Internal server error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "details": "An unexpected error occurred while processing your request",
            "timestamp": time.time()
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    # Run the FastAPI application
    uvicorn.run(
        "rag_api:app",
        host="0.0.0.0",
        port=8002,  # Different port from the dynamic RAG service
        reload=True,
        log_level="info"
    )