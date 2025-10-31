"""
RAG Services Module

This module provides document-based question answering using RAG (Retrieval-Augmented Generation).
The RAG service requires Redis and embeddings for operation.

Services:
- RAGStore: Main RAG service for document ingestion and querying
"""

# Import RAG store
RAGStore = None  # Will be imported at runtime to avoid circular dependencies

try:
    import sys
    from pathlib import Path
    
    # Add RAG service path
    rag_path = Path(__file__).parent.parent.parent / "rag_service" / "dynamic_rag" / "app"
    if rag_path.exists():
        sys.path.insert(0, str(rag_path))
        from services.rag_store import RAGStore as _RAGStore
        RAGStore = _RAGStore
        print(f"✅ Successfully imported RAGStore from {rag_path}")
    else:
        print(f"⚠️  RAG service path not found: {rag_path}")
except ImportError as e:
    print(f"⚠️  Warning: Could not import RAGStore: {e}")
    RAGStore = None

__all__ = [
    "RAGStore",
]

