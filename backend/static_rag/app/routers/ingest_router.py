"""
PDF Ingestion Router

This module handles PDF file uploads and processes them through the RAG pipeline.
It extracts text, tables, and graphs from PDFs, generates embeddings, and stores
them in the PostgreSQL database with pgvector.

The ingestion process:
1. Validates PDF file format
2. Saves uploaded file temporarily
3. Parses PDF content (text, tables, graphs) into document chunks
4. Generates embeddings using SentenceTransformers on GPU
5. Stores chunks with metadata and year information in database
6. Cleans up temporary files

Author: RAG Pipeline Team
Version: 0.1.0
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import tempfile
import os

from ..utils.data_ingestion_pipeline import parse_pdf_to_documents
from ..services.rag_store import store_documents


router = APIRouter()


@router.post("")
async def ingest_pdf(file: UploadFile = File(...)):
    """
    Ingest a PDF file and store its content as vector embeddings.
    
    This endpoint accepts a PDF file upload, processes it to extract text, tables,
    and graphs, generates embeddings using SentenceTransformers, and stores the
    results in the PostgreSQL database with pgvector.
    
    The year is automatically extracted from the filename (e.g., "report_2019.pdf" -> year=2019).
    
    Args:
        file (UploadFile): PDF file to be processed
        
    Returns:
        JSONResponse: Response containing the number of chunks stored
        
    Raises:
        HTTPException: 400 if file is not a PDF
        HTTPException: 500 if processing fails
        
    Example:
        POST /ingest
        Content-Type: multipart/form-data
        Body: PDF file
        
        Response:
        {
            "chunks_stored": 156
        }
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            contents = await file.read()
            tmp.write(contents)
            tmp_path = tmp.name

        # Parse PDF into document chunks
        documents = parse_pdf_to_documents(tmp_path)
        
        # Store documents with embeddings in database
        num_chunks = await store_documents(documents)
        
        return JSONResponse({"chunks_stored": num_chunks})
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        # Clean up temporary file
        try:
            if 'tmp_path' in locals() and os.path.exists(tmp_path):
                os.unlink(tmp_path)
        except Exception:
            pass


