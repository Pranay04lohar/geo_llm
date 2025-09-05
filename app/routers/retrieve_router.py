"""
Document Retrieval Router

This module handles document retrieval requests using vector similarity search.
It accepts text queries, generates embeddings, and finds the most similar
documents from the PostgreSQL database with pgvector.

The retrieval process:
1. Validates query parameters
2. Generates query embedding using SentenceTransformers
3. Performs vector similarity search in database
4. Optionally filters by year for disaster data
5. Returns top-k most similar documents with metadata

Author: RAG Pipeline Team
Version: 0.1.0
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

from ..services.rag_store import retrieve_similar_docs


class RetrieveRequest(BaseModel):
    """
    Request model for document retrieval.
    
    Attributes:
        query (str): Search query text (minimum 1 character)
        k (int): Number of documents to retrieve (1-50, default: 5)
        year (Optional[int]): Filter by specific year (1900-2100, optional)
    """
    query: str = Field(..., min_length=1, description="Search query text")
    k: int = Field(5, ge=1, le=50, description="Number of documents to retrieve")
    year: Optional[int] = Field(None, ge=1900, le=2100, description="Filter by specific year")


router = APIRouter()


@router.post("")
async def retrieve_docs(payload: RetrieveRequest):
    """
    Retrieve similar documents using vector similarity search.
    
    This endpoint takes a text query and returns the most similar documents
    from the database using vector similarity search. Results can be filtered
    by year for disaster data analysis.
    
    Args:
        payload (RetrieveRequest): Query parameters including text, count, and optional year filter
        
    Returns:
        dict: Response containing list of similar documents with content and metadata
        
    Raises:
        HTTPException: 500 if retrieval fails
        
    Example:
        POST /retrieve
        {
            "query": "Kerala floods 2019",
            "k": 5,
            "year": 2019
        }
        
        Response:
        {
            "results": [
                {
                    "content": "Flood damage in Kerala...",
                    "metadata": {"year": 2019, "type": "text", "source": "file.pdf#page=1"}
                }
            ]
        }
    """
    try:
        results = await retrieve_similar_docs(payload.query, payload.k, payload.year)
        return {"results": results}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


