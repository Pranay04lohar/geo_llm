"""
Embeddings API Router for Dynamic RAG System.

Provides endpoints to list chunk metadata, fetch a single embedding, and
export all embeddings for a session. Vectors are optional and paginated.
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Request, Query
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
import json

from app.services.rag_store import RAGStore


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


router = APIRouter()


def get_rag_store(request: Request) -> RAGStore:
    return request.app.state.rag_store


class Chunk(BaseModel):
    session_id: str
    index_id: int
    content: str
    metadata: dict
    vector_dim: int
    embedding_model: str
    embedding_norm: str = "l2"
    vector: Optional[List[float]] = None


class ListEmbeddingsResponse(BaseModel):
    session_id: str
    total: int
    dimension: int
    model: str
    items: List[Chunk]


@router.get(
    "/session/{session_id}/embeddings",
    response_model=ListEmbeddingsResponse,
    summary="List session embeddings (paginated)",
)
async def list_embeddings(
    request: Request,
    session_id: str,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    includeVectors: bool = Query(False),
    type: Optional[str] = Query(None, pattern=r"^(text|table|graph)$"),
    search: Optional[str] = Query(None, min_length=1, max_length=200),
    rag_store: RAGStore = Depends(get_rag_store),
):
    session_data = rag_store.sessions.get(session_id)
    if not session_data:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found or expired")

    metadata_store = session_data.metadata_store or []

    # Simple filters
    filtered = metadata_store
    if type:
        filtered = [m for m in filtered if m.get("metadata", {}).get("type") == type]
    if search:
        q = search.lower()
        filtered = [m for m in filtered if q in (m.get("content") or "").lower()]

    total = len(filtered)
    window = filtered[offset:offset + limit]

    # Prepare chunks
    items: List[Chunk] = []
    for m in window:
        index_id = m.get("index_id")
        vector = None
        if includeVectors and session_data.faiss_index is not None and index_id is not None:
            try:
                vec = session_data.faiss_index.reconstruct(index_id)
                vector = vec.tolist()
            except Exception as e:
                logger.warning(f"Failed to reconstruct vector for index {index_id}: {e}")
        items.append(Chunk(
            session_id=session_id,
            index_id=index_id,
            content=m.get("content"),
            metadata=m.get("metadata", {}),
            vector_dim=rag_store.embedding_dimension,
            embedding_model="sentence-transformers/all-MiniLM-L6-v2",
            vector=vector,
        ))

    return ListEmbeddingsResponse(
        session_id=session_id,
        total=total,
        dimension=rag_store.embedding_dimension,
        model="sentence-transformers/all-MiniLM-L6-v2",
        items=items,
    )


@router.get(
    "/session/{session_id}/embedding/{index_id}",
    response_model=Chunk,
    summary="Get a single embedding by index id",
)
async def get_embedding(
    request: Request,
    session_id: str,
    index_id: int,
    includeVector: bool = Query(True),
    rag_store: RAGStore = Depends(get_rag_store),
):
    session_data = rag_store.sessions.get(session_id)
    if not session_data:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found or expired")

    if index_id < 0 or index_id >= (session_data.document_count or 0):
        raise HTTPException(status_code=404, detail=f"index_id {index_id} out of range")

    meta = next((m for m in (session_data.metadata_store or []) if m.get("index_id") == index_id), None)
    if not meta:
        raise HTTPException(status_code=404, detail=f"Chunk metadata not found for index_id {index_id}")

    vector = None
    if includeVector and session_data.faiss_index is not None:
        try:
            vec = session_data.faiss_index.reconstruct(index_id)
            vector = vec.tolist()
        except Exception as e:
            logger.warning(f"Failed to reconstruct vector for index {index_id}: {e}")

    return Chunk(
        session_id=session_id,
        index_id=index_id,
        content=meta.get("content"),
        metadata=meta.get("metadata", {}),
        vector_dim=rag_store.embedding_dimension,
        embedding_model="sentence-transformers/all-MiniLM-L6-v2",
        vector=vector,
    )


@router.get(
    "/session/{session_id}/export",
    summary="Export embeddings for a session (NDJSON or JSON)",
)
async def export_embeddings(
    request: Request,
    session_id: str,
    format: str = Query("jsonl", pattern=r"^(jsonl|json)$"),
    includeVectors: bool = Query(True),
    rag_store: RAGStore = Depends(get_rag_store),
):
    session_data = rag_store.sessions.get(session_id)
    if not session_data:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found or expired")

    def iter_ndjson():
        for m in (session_data.metadata_store or []):
            idx = m.get("index_id")
            vec = None
            if includeVectors and session_data.faiss_index is not None and idx is not None:
                try:
                    vec = session_data.faiss_index.reconstruct(idx).tolist()
                except Exception as e:
                    logger.warning(f"Failed to reconstruct vector for index {idx}: {e}")
            obj = {
                "session_id": session_id,
                "index_id": idx,
                "content": m.get("content"),
                "metadata": m.get("metadata", {}),
                "vector_dim": rag_store.embedding_dimension,
                "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
                "embedding_norm": "l2",
                "vector": vec,
            }
            yield json.dumps(obj, ensure_ascii=False) + "\n"

    if format == "jsonl":
        return StreamingResponse(iter_ndjson(), media_type="application/x-ndjson")

    # JSON array (not streamed) for smaller sessions
    data = []
    for line in iter_ndjson():
        data.append(json.loads(line))
    return JSONResponse(content=data)


