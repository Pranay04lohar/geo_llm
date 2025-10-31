"""
RAG Router - Handles document upload and RAG session management

This router provides endpoints for:
- Document upload and ingestion
- RAG session management
- Direct RAG queries (optional)
"""

import logging
import uuid
from typing import List, Optional
from fastapi import APIRouter, Request, UploadFile, File, HTTPException, Form
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================

class UploadResponse(BaseModel):
    """Response model for document upload"""
    success: bool
    session_id: str
    message: str
    files_processed: int
    chunks_created: int
    error: Optional[str] = None


class SessionInfo(BaseModel):
    """RAG session information"""
    session_id: str
    files_count: int
    chunks_count: int
    created_at: Optional[str] = None
    expires_at: Optional[str] = None


class DirectRAGQueryRequest(BaseModel):
    """Request model for direct RAG query"""
    query: str = Field(..., min_length=1, max_length=2000)
    session_id: str
    top_k: int = Field(5, ge=1, le=20)


class DirectRAGQueryResponse(BaseModel):
    """Response model for direct RAG query"""
    answer: str
    sources: List[dict]
    confidence: float
    success: bool
    error: Optional[str] = None


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/upload", response_model=UploadResponse)
async def upload_documents(
    request: Request,
    files: List[UploadFile] = File(...),
    session_id: Optional[str] = Form(None)
):
    """
    Upload documents for RAG-based question answering.
    
    This endpoint:
    1. Accepts PDF, TXT, or other document files
    2. Creates embeddings for document chunks
    3. Stores them in a session-based FAISS index
    4. Returns a session_id for subsequent queries
    
    Args:
        request: FastAPI request object
        files: List of files to upload
        session_id: Optional session ID (generated if not provided)
    
    Returns:
        UploadResponse with session_id and processing stats
    """
    try:
        # Get RAG store from app state
        rag_store = request.app.state.rag_store
        if not rag_store:
            raise HTTPException(
                status_code=503,
                detail="RAG service not available"
            )
        
        # Generate session ID if not provided
        if not session_id:
            session_id = str(uuid.uuid4())
        
        logger.info(f"📤 Uploading {len(files)} file(s) to session {session_id[:8]}...")
        
        # Process files
        result = await rag_store.ingest_files(files, session_id)
        
        if result.get("success"):
            logger.info(f"✅ Successfully processed {result.get('files_processed', 0)} file(s)")
            logger.info(f"📊 Created {result.get('chunks_created', 0)} chunks")
            
            return UploadResponse(
                success=True,
                session_id=session_id,
                message=f"Successfully processed {result.get('files_processed', 0)} file(s)",
                files_processed=result.get("files_processed", 0),
                chunks_created=result.get("chunks_created", 0)
            )
        else:
            logger.error(f"❌ Upload failed: {result.get('error', 'Unknown error')}")
            return UploadResponse(
                success=False,
                session_id=session_id,
                message="Upload failed",
                files_processed=0,
                chunks_created=0,
                error=result.get("error", "Unknown error")
            )
            
    except Exception as e:
        logger.error(f"❌ Error uploading documents: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        return UploadResponse(
            success=False,
            session_id=session_id or "unknown",
            message="Upload failed",
            files_processed=0,
            chunks_created=0,
            error=str(e)
        )


# Backward-compat route to match old frontend path: /api/rag/api/v1/upload-temp
@router.post("/api/v1/upload-temp", response_model=UploadResponse)
async def upload_documents_compat(
    request: Request,
    files: List[UploadFile] = File(...),
    session_id: Optional[str] = Form(None)
):
    return await upload_documents(request, files, session_id)


@router.get("/sessions/{session_id}", response_model=SessionInfo)
async def get_session_info(session_id: str, request: Request):
    """
    Get information about a RAG session.
    
    Returns details about:
    - Number of files in the session
    - Number of chunks created
    - Session expiration time
    
    Args:
        session_id: The session identifier
        request: FastAPI request object
    
    Returns:
        SessionInfo with session details
    """
    try:
        rag_store = request.app.state.rag_store
        if not rag_store:
            raise HTTPException(
                status_code=503,
                detail="RAG service not available"
            )
        
        # Get session info
        info = await rag_store.get_session_info(session_id)
        
        if not info:
            raise HTTPException(
                status_code=404,
                detail=f"Session {session_id} not found"
            )
        
        return SessionInfo(**info)
        
    except HTTPException:
        raise
        
    except Exception as e:
        logger.error(f"Error getting session info: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, request: Request):
    """
    Delete a RAG session and clean up resources.
    
    This will:
    - Remove the session from memory
    - Clean up FAISS index
    - Remove session data from Redis
    
    Args:
        session_id: The session identifier
        request: FastAPI request object
    
    Returns:
        Success message
    """
    try:
        rag_store = request.app.state.rag_store
        if not rag_store:
            raise HTTPException(
                status_code=503,
                detail="RAG service not available"
            )
        
        await rag_store.delete_session(session_id)
        
        logger.info(f"🗑️  Deleted session {session_id[:8]}...")
        
        return {
            "success": True,
            "message": f"Session {session_id} deleted successfully"
        }
        
    except Exception as e:
        logger.error(f"Error deleting session: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.post("/query", response_model=DirectRAGQueryResponse)
async def query_documents(request_data: DirectRAGQueryRequest, request: Request):
    """
    Query documents directly (alternative to using /api/query with session_id).
    
    This endpoint allows direct RAG queries without going through the
    main query processing pipeline.
    
    Args:
        request_data: Query request with session_id and query text
        request: FastAPI request object
    
    Returns:
        DirectRAGQueryResponse with answer and sources
    """
    try:
        rag_store = request.app.state.rag_store
        if not rag_store:
            raise HTTPException(
                status_code=503,
                detail="RAG service not available"
            )
        
        logger.info(f"🔍 RAG query: {request_data.query[:100]}...")
        logger.info(f"📚 Session: {request_data.session_id[:8]}...")
        
        # Query the RAG store
        result = await rag_store.query(
            query=request_data.query,
            session_id=request_data.session_id,
            top_k=request_data.top_k
        )
        
        if result.get("success"):
            logger.info(f"✅ RAG query successful")
            return DirectRAGQueryResponse(
                answer=result.get("answer", ""),
                sources=result.get("sources", []),
                confidence=result.get("confidence", 0.0),
                success=True
            )
        else:
            return DirectRAGQueryResponse(
                answer="",
                sources=[],
                confidence=0.0,
                success=False,
                error=result.get("error", "Unknown error")
            )
            
    except Exception as e:
        logger.error(f"❌ Error in RAG query: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        return DirectRAGQueryResponse(
            answer="",
            sources=[],
            confidence=0.0,
            success=False,
            error=str(e)
        )


@router.get("/sessions")
async def list_sessions(request: Request):
    """
    List all active RAG sessions.
    
    Returns:
        List of session IDs and their basic information
    """
    try:
        rag_store = request.app.state.rag_store
        if not rag_store:
            raise HTTPException(
                status_code=503,
                detail="RAG service not available"
            )
        
        sessions = await rag_store.list_sessions()
        
        return {
            "success": True,
            "sessions": sessions,
            "count": len(sessions)
        }
        
    except Exception as e:
        logger.error(f"Error listing sessions: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

