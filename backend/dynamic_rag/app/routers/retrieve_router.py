"""
Retrieval API Router for Dynamic RAG System.

What: Exposes POST /retrieve (and helpers) to fetch top-k semantically
      similar chunks for a query within a given session.

Why:  Allow clients to run dynamic, per-session semantic search over
      ephemeral embeddings that were produced during upload.

How:  Embeds the query (GPU-accelerated), searches the FAISS index for the
      session, ranks by cosine similarity (inner product over normalized
      vectors), and returns structured results.
"""

import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from datetime import datetime

from app.services.rag_store import RAGStore
from auth.middleware.firebase_auth_middleware import get_current_user_uid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


class SimpleRetrieveRequest(BaseModel):
    """Minimal request model per spec."""
    query: str = Field(..., min_length=1, max_length=1000, description="Query string to search for")


class SimpleChunkResult(BaseModel):
    """Minimal chunk result per spec."""
    content: str
    score: float


class SimpleRetrieveResponse(BaseModel):
    """Minimal response model per spec."""
    query: str
    retrieved_chunks: List[SimpleChunkResult]


class RetrieveRequest(BaseModel):
    """Request model for document retrieval."""
    session_id: str = Field(..., description="Session ID containing the documents")
    query: str = Field(..., min_length=1, max_length=1000, description="Query string to search for")
    k: int = Field(default=5, ge=1, le=50, description="Number of similar documents to retrieve (1-50)")
    returnVectors: bool = Field(default=False, description="Include vectors for returned chunks")


class DocumentResult(BaseModel):
    """Model for a retrieved document."""
    content: str = Field(..., description="Document content")
    metadata: dict = Field(..., description="Document metadata")
    similarity_score: float = Field(..., description="Similarity score (0-1)")
    index_id: int = Field(..., description="Internal document index ID")
    vector: Optional[list] = Field(default=None, description="Embedding vector if requested")
    vector_dim: Optional[int] = Field(default=None, description="Embedding dimension if vector included")


class RetrieveResponse(BaseModel):
    """Response model for document retrieval."""
    session_id: str = Field(..., description="Session ID")
    query: str = Field(..., description="Original query")
    k: int = Field(..., description="Number of documents requested")
    results_count: int = Field(..., description="Number of documents returned")
    results: List[DocumentResult] = Field(..., description="Retrieved documents")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")


class RetrieveError(BaseModel):
    """Error response model."""
    error: str = Field(..., description="Error message")
    details: Optional[str] = Field(None, description="Additional error details")


def get_rag_store(request: Request) -> RAGStore:
    """Dependency to get RAG store from application state."""
    return request.app.state.rag_store


@router.post(
    "/retrieve",
    response_model=SimpleRetrieveResponse,
    summary="Retrieve top-5 similar chunks (simple)",
    description="Minimal retrieval endpoint returning content and score for top-5 matches."
)
async def retrieve_simple(
    request: Request,
    body: SimpleRetrieveRequest,
    user_id: str = Depends(get_current_user_uid),
    rag_store: RAGStore = Depends(get_rag_store)
):
    """Simple retrieval that matches the requested JSON schema.

    Uses the only active session if exactly one exists; otherwise returns empty results.
    """
    try:
        active_sessions = list(rag_store.sessions.keys())
        if len(active_sessions) != 1:
            logger.warning("Simple /retrieve called without unambiguous session; returning empty results")
            response_obj = SimpleRetrieveResponse(query=body.query, retrieved_chunks=[])
            # Store latest simple retrieval result globally
            setattr(request.app.state, "last_retrieval_simple_latest", response_obj.dict())
            return response_obj

        session_id = active_sessions[0]
        docs = await rag_store.retrieve_similar_docs(session_id=session_id, query=body.query, k=5)
        chunks = [SimpleChunkResult(content=d["content"], score=float(d["similarity_score"])) for d in docs]
        response_obj = SimpleRetrieveResponse(query=body.query, retrieved_chunks=chunks)
        # Store latest simple retrieval result globally
        setattr(request.app.state, "last_retrieval_simple_latest", response_obj.dict())
        return response_obj
    except Exception as e:
        logger.error(f"Unexpected error in retrieve_simple: {str(e)}")
        response_obj = SimpleRetrieveResponse(query=body.query, retrieved_chunks=[])
        setattr(request.app.state, "last_retrieval_simple_latest", response_obj.dict())
        return response_obj


@router.post(
    "/retrieve/detailed",
    response_model=RetrieveResponse,
    responses={
        400: {"model": RetrieveError, "description": "Bad request - invalid parameters"},
        404: {"model": RetrieveError, "description": "Session not found or expired"},
        500: {"model": RetrieveError, "description": "Internal server error"}
    },
    summary="Retrieve similar documents",
    description="""
    Retrieve the most similar documents for a given query from a specific session.
    
    **Features:**
    - Semantic search using embeddings
    - Cosine similarity scoring
    - Configurable result count (1-50)
    - Session-based ephemeral storage
    
    **Process:**
    1. Generate embedding for the query
    2. Search FAISS index for similar documents
    3. Return top-k results with similarity scores
    
    **Note:** Sessions expire after 1 hour of inactivity.
    """
)
async def retrieve_documents(
    request: Request,
    retrieve_request: RetrieveRequest,
    user_id: str = Depends(get_current_user_uid),
    rag_store: RAGStore = Depends(get_rag_store)
):
    """
    Retrieve similar documents for a query from a session.
    
    Args:
        request: FastAPI request object
        retrieve_request: Retrieval request with session_id, query, and k
        rag_store: RAG store dependency
        
    Returns:
        RetrieveResponse with similar documents and metadata
    """
    start_time = datetime.utcnow()
    
    try:
        # Validate session exists
        session_info = await rag_store.get_session_info(retrieve_request.session_id)
        if not session_info:
            raise HTTPException(
                status_code=404,
                detail=f"Session {retrieve_request.session_id} not found or expired"
            )
        
        # Check if session has documents
        if session_info["document_count"] == 0:
            return RetrieveResponse(
                session_id=retrieve_request.session_id,
                query=retrieve_request.query,
                k=retrieve_request.k,
                results_count=0,
                results=[],
                processing_time_ms=0.0
            )
        
        # Retrieve similar documents
        logger.info(f"Retrieving documents for session {retrieve_request.session_id} with query: '{retrieve_request.query[:50]}...'")
        
        similar_docs = await rag_store.retrieve_similar_docs(
            session_id=retrieve_request.session_id,
            query=retrieve_request.query,
            k=retrieve_request.k
        )
        
        # Convert to response format
        results = []
        include_vectors = getattr(retrieve_request, "returnVectors", False)
        for doc in similar_docs:
            vector = None
            vector_dim = None
            if include_vectors:
                # Reconstruct vector from FAISS
                try:
                    session_data = rag_store.sessions.get(retrieve_request.session_id)
                    if session_data and session_data.faiss_index is not None:
                        vec = session_data.faiss_index.reconstruct(doc["index_id"])
                        vector = vec.tolist()
                        vector_dim = rag_store.embedding_dimension
                except Exception as e:
                    logger.warning(f"Failed to reconstruct vector for index {doc['index_id']}: {e}")
            result = DocumentResult(
                content=doc["content"],
                metadata=doc["metadata"],
                similarity_score=doc["similarity_score"],
                index_id=doc["index_id"],
                vector=vector,
                vector_dim=vector_dim,
            )
            results.append(result)
        
        # Calculate processing time
        end_time = datetime.utcnow()
        processing_time = (end_time - start_time).total_seconds() * 1000
        
        logger.info(f"Retrieved {len(results)} documents in {processing_time:.2f}ms")
        
        response_obj = RetrieveResponse(
            session_id=retrieve_request.session_id,
            query=retrieve_request.query,
            k=retrieve_request.k,
            results_count=len(results),
            results=results,
            processing_time_ms=processing_time
        )
        # Store latest detailed retrieval results
        setattr(request.app.state, "last_retrieval_detailed_latest", response_obj.dict())
        # Store per-session
        store: Dict[str, Any] = getattr(request.app.state, "last_retrieval_by_session", {})
        store[retrieve_request.session_id] = response_obj.dict()
        setattr(request.app.state, "last_retrieval_by_session", store)
        return response_obj
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Unexpected error in retrieve_documents: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get(
    "/session/{session_id}/stats",
    summary="Get session statistics",
    description="Get detailed statistics about a session including document count and index information."
)
async def get_session_stats(
    session_id: str,
    rag_store: RAGStore = Depends(get_rag_store)
):
    """Get detailed statistics about a session."""
    try:
        session_info = await rag_store.get_session_info(session_id)
        
        if not session_info:
            raise HTTPException(
                status_code=404,
                detail=f"Session {session_id} not found or expired"
            )
        
        # Get additional stats from the session data
        session_data = rag_store.sessions.get(session_id)
        if session_data:
            stats = {
                "session_id": session_id,
                "user_id": session_data.user_id,
                "created_at": session_data.created_at.isoformat(),
                "last_accessed": session_data.last_accessed.isoformat(),
                "document_count": session_data.document_count,
                "has_faiss_index": session_data.faiss_index is not None,
                "index_size": session_data.faiss_index.ntotal if session_data.faiss_index else 0,
                "embedding_dimension": rag_store.embedding_dimension,
                "session_ttl_seconds": rag_store.session_ttl
            }
        else:
            stats = session_info
        
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session stats: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving session statistics: {str(e)}"
        )


@router.get(
    "/health",
    summary="Retrieval service health check",
    description="Check the health of the retrieval service and its dependencies."
)
async def health_check(
    rag_store: RAGStore = Depends(get_rag_store)
):
    """Health check for the retrieval service."""
    try:
        # Check Redis health
        redis_status = await rag_store.check_redis_health()
        
        # Get basic stats
        active_sessions = len(rag_store.sessions)
        total_documents = sum(session.document_count for session in rag_store.sessions.values())
        
        return {
            "status": "healthy",
            "redis": redis_status,
            "active_sessions": active_sessions,
            "total_documents": total_documents,
            "embedding_dimension": rag_store.embedding_dimension,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail=f"Health check failed: {str(e)}"
        )


@router.post(
    "/batch-retrieve",
    response_model=List[RetrieveResponse],
    summary="Batch retrieve documents",
    description="Retrieve documents for multiple queries in a single request."
)
async def batch_retrieve_documents(
    request: Request,
    queries: List[RetrieveRequest],
    rag_store: RAGStore = Depends(get_rag_store)
):
    """
    Retrieve documents for multiple queries in batch.
    
    Args:
        request: FastAPI request object
        queries: List of retrieval requests
        rag_store: RAG store dependency
        
    Returns:
        List of RetrieveResponse objects
    """
    if len(queries) > 10:  # Limit batch size
        raise HTTPException(
            status_code=400,
            detail="Maximum 10 queries allowed in batch request"
        )
    
    results = []
    
    for query_request in queries:
        try:
            # Use the single retrieve endpoint logic
            result = await retrieve_documents(request, query_request, rag_store)
            results.append(result)
        except HTTPException as e:
            # Create error response for failed queries
            error_response = RetrieveResponse(
                session_id=query_request.session_id,
                query=query_request.query,
                k=query_request.k,
                results_count=0,
                results=[],
                processing_time_ms=0.0
            )
            results.append(error_response)
            logger.warning(f"Batch query failed: {e.detail}")
    
    return results


@router.get(
    "/retrieve/last",
    summary="Get latest simple retrieval result",
    description="Returns the last response produced by POST /retrieve (simple)."
)
async def get_last_simple_retrieval(request: Request):
    latest = getattr(request.app.state, "last_retrieval_simple_latest", None)
    return latest or {"message": "No simple retrieval has been made yet."}


@router.get(
    "/retrieve/last/{session_id}",
    summary="Get latest detailed retrieval result for a session",
    description="Returns the last response produced by POST /retrieve/detailed for the given session."
)
async def get_last_detailed_retrieval(session_id: str, request: Request):
    store = getattr(request.app.state, "last_retrieval_by_session", {}) or {}
    result = store.get(session_id)
    return result or {"message": f"No detailed retrieval found for session {session_id}."}
