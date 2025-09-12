"""
RAG Pipeline FastAPI Application

This module creates and configures the main FastAPI application for the RAG (Retrieval-Augmented Generation)
pipeline. It provides endpoints for PDF ingestion and document retrieval with vector similarity search.

The application supports:
- PDF document ingestion with text, table, and graph extraction
- GPU-accelerated embedding generation using SentenceTransformers
- Vector storage and retrieval using PostgreSQL with pgvector extension
- Year-based filtering for disaster data (1990-2025)

Author: RAG Pipeline Team
Version: 0.1.0
"""

from fastapi import FastAPI
from .routers.ingest_router import router as ingest_router
from .routers.retrieve_router import router as retrieve_router


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        FastAPI: Configured FastAPI application instance with routers
    """
    app = FastAPI(
        title="RAG Ingestion & Retrieval API",
        description="API for ingesting PDFs and retrieving similar documents using vector embeddings",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # Include routers for ingestion and retrieval endpoints
    app.include_router(ingest_router, prefix="/ingest", tags=["ingest"])
    app.include_router(retrieve_router, prefix="/retrieve", tags=["retrieve"])
    
    return app


# Create the application instance
app = create_app()




