"""
Embedding Utilities

This module provides functions for generating vector embeddings using SentenceTransformers.
It handles both document and query embedding generation with GPU acceleration support.

Features:
- GPU-accelerated embedding generation using CUDA when available
- Batch processing for efficient document embedding
- Normalized embeddings for consistent similarity search
- Lazy model loading to optimize memory usage
- Support for both document chunks and search queries

The embedding model used is 'sentence-transformers/all-MiniLM-L6-v2' which provides
384-dimensional embeddings optimized for semantic similarity search.

Author: RAG Pipeline Team
Version: 0.1.0
"""

from typing import Any, Dict, List, Tuple

import torch
from sentence_transformers import SentenceTransformer

from .data_ingestion_pipeline import Document


# Model configuration
_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
_model: SentenceTransformer | None = None


def get_model() -> SentenceTransformer:
    """
    Get or initialize the SentenceTransformer model.
    
    This function implements lazy loading of the embedding model. The model is loaded
    only when first needed and reused for subsequent calls. GPU is used automatically
    if CUDA is available, otherwise falls back to CPU.
    
    Returns:
        SentenceTransformer: The loaded embedding model
        
    Note:
        The model uses 'sentence-transformers/all-MiniLM-L6-v2' which provides
        384-dimensional embeddings optimized for semantic similarity.
    """
    global _model
    if _model is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        _model = SentenceTransformer(_MODEL_NAME, device=device)
    return _model


def embed_documents(docs: List[Document]) -> List[Tuple[str, Dict[str, Any], List[float]]]:
    """
    Generate embeddings for a list of documents.
    
    This function processes multiple documents in batches for efficiency. It extracts
    content from each document, generates embeddings using the SentenceTransformer
    model, and returns tuples of (content, metadata, embedding).
    
    Args:
        docs (List[Document]): List of document objects to embed
        
    Returns:
        List[Tuple[str, Dict[str, Any], List[float]]]: List of tuples containing
            content, metadata, and embedding vector for each document
            
    Note:
        Embeddings are normalized for consistent similarity search results.
        Batch size is set to 64 for optimal performance on most hardware.
    """
    model = get_model()
    contents = [d.content for d in docs]
    embeddings = model.encode(
        contents, 
        batch_size=64, 
        convert_to_numpy=True, 
        show_progress_bar=False, 
        normalize_embeddings=True
    )
    results: List[Tuple[str, Dict[str, Any], List[float]]] = []
    for doc, emb in zip(docs, embeddings):
        results.append((doc.content, doc.metadata, emb.astype(float).tolist()))
    return results


def embed_query(query: str) -> List[float]:
    """
    Generate embedding for a search query.
    
    This function creates a vector embedding for a single query string, which can
    then be used for similarity search against document embeddings.
    
    Args:
        query (str): The search query text to embed
        
    Returns:
        List[float]: The embedding vector as a list of floats
        
    Note:
        The query embedding is normalized to match the document embeddings
        for consistent similarity search results.
    """
    model = get_model()
    emb = model.encode([query], convert_to_numpy=True, normalize_embeddings=True)[0]
    return emb.astype(float).tolist()


