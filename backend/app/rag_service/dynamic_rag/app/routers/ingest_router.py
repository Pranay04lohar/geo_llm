"""
File Upload API Router for Dynamic RAG System.

What: Exposes POST /upload-temp and session/quota helper endpoints.

Why:  Accept user files, extract text/table/graph content, generate
      ephemeral embeddings, and attach them to a session-specific FAISS
      index for subsequent semantic retrieval.

How:  Validates inputs and quotas (via Redis), creates a new session in
      the in-memory RAG store, runs the data ingestion pipeline, stores
      normalized document chunks and metadata, and returns a session_id.
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uuid

from app.services.rag_store import RAGStore
from app.utils.data_ingestion_pipeline import DataIngestionPipeline
from app.config import FILE_PROCESSING_CONFIG

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Initialize pipeline
pipeline = DataIngestionPipeline()


class UploadResponse(BaseModel):
    """Response model for file upload."""
    session_id: str
    message: str
    files_processed: int
    documents_extracted: int
    user_quota_remaining: int
    vectors_created: int
    ocr_available: bool = False
    warnings: list = []


class UploadError(BaseModel):
    """Error response model."""
    error: str
    details: Optional[str] = None


def get_rag_store(request: Request) -> RAGStore:
    """Dependency to get RAG store from application state."""
    return request.app.state.rag_store


def validate_file_size(file: UploadFile) -> bool:
    """Validate file size against configured limits."""
    max_size = FILE_PROCESSING_CONFIG["max_size_bytes"]
    
    # Check if file size is available
    if hasattr(file, 'size') and file.size:
        return file.size <= max_size
    
    # If size is not available, we'll check during processing
    return True


def validate_file_type(filename: str) -> bool:
    """Validate file type against allowed extensions."""
    allowed_extensions = FILE_PROCESSING_CONFIG["allowed_extensions"]
    file_extension = filename.lower().split('.')[-1] if '.' in filename else ''
    return f".{file_extension}" in allowed_extensions


@router.post(
    "/upload-temp",
    response_model=UploadResponse,
    responses={
        400: {"model": UploadError, "description": "Bad request - invalid files or quota exceeded"},
        413: {"model": UploadError, "description": "File too large"},
        429: {"model": UploadError, "description": "Quota exceeded"},
        500: {"model": UploadError, "description": "Internal server error"}
    },
    summary="Upload files for temporary processing",
    description="""
    Upload up to 2 files (max 100MB each) for temporary processing.
    Files are processed to extract text, tables, and graphs, then stored
    in an ephemeral session with a 1-hour TTL.
    
    **Quota Limits:**
    - 10 files per user per 24 hours
    - 2 files per request
    - 100MB per file
    
    **Supported Formats:**
    - PDF (with text, table, and graph extraction)
    - TXT (plain text)
    - DOCX (with table extraction)
    - MD (markdown)
    """
)
async def upload_files(
    request: Request,
    files: List[UploadFile] = File(..., description="Files to upload (max 2 files)"),
    user_id: str = "default_user",  # In production, get from authentication
    rag_store: RAGStore = Depends(get_rag_store)
):
    """
    Upload files for temporary processing and create a session.
    
    Args:
        request: FastAPI request object
        files: List of uploaded files
        user_id: User identifier (from authentication in production)
        rag_store: RAG store dependency
        
    Returns:
        UploadResponse with session_id and processing results
    """
    try:
        # Validate number of files
        if len(files) > FILE_PROCESSING_CONFIG.get("max_files_per_request", 2):
            raise HTTPException(
                status_code=400,
                detail=f"Too many files. Maximum {FILE_PROCESSING_CONFIG.get('max_files_per_request', 2)} files per request."
            )
        
        if len(files) == 0:
            raise HTTPException(
                status_code=400,
                detail="No files provided"
            )
        
        # Validate files
        for file in files:
            if not file.filename:
                raise HTTPException(
                    status_code=400,
                    detail="One or more files have no filename"
                )
            
            if not validate_file_type(file.filename):
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported file type: {file.filename}. Allowed types: {FILE_PROCESSING_CONFIG['allowed_extensions']}"
                )
        
        # Check user quota
        has_quota, current_count = await rag_store.check_user_quota(user_id)
        if not has_quota:
            raise HTTPException(
                status_code=429,
                detail=f"Quota exceeded. User has uploaded {current_count} files in the last 24 hours."
            )
        
        # Create session
        session_id = await rag_store.create_session(user_id)
        logger.info(f"Created session {session_id} for user {user_id}")
        
        # Process files
        processed_files = []
        total_documents = 0
        
        for file in files:
            try:
                # Read file content
                content = await file.read()
                
                # Validate file size
                if len(content) > FILE_PROCESSING_CONFIG["max_size_bytes"]:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File {file.filename} is too large. Maximum size: {FILE_PROCESSING_CONFIG['max_size_bytes'] // (1024*1024)}MB"
                    )
                
                processed_files.append((file.filename, content))
                logger.info(f"Read file {file.filename} ({len(content)} bytes)")
                
            except Exception as e:
                logger.error(f"Error reading file {file.filename}: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Error reading file {file.filename}: {str(e)}"
                )
        
        # Extract content from files
        try:
            documents = await pipeline.process_files(processed_files)
            total_documents = len(documents)
            logger.info(f"Extracted {total_documents} documents from {len(processed_files)} files")
            
        except Exception as e:
            logger.error(f"Error processing files: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error processing files: {str(e)}"
            )
        
        # Store documents in session
        if documents:
            success = await rag_store.store_documents(session_id, documents)
            if not success:
                logger.error(f"Failed to store documents in session {session_id}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to store processed documents"
                )
        
        # Increment user quota
        quota_success = await rag_store.increment_user_quota(user_id)
        if not quota_success:
            logger.warning(f"Failed to increment quota for user {user_id}")
            # Don't fail the request, just log the warning
        
        # Get updated quota info
        _, updated_count = await rag_store.check_user_quota(user_id)
        max_files = FILE_PROCESSING_CONFIG.get("max_files_per_user_per_day", 10)
        remaining_quota = max(0, max_files - updated_count)
        
        # Add warnings
        warnings = []
        warnings.append("OCR and advanced table extraction are currently unavailable. Images, graphs, and complex tables in PDFs will not be processed. Basic table text may be captured through text extraction.")
        
        return UploadResponse(
            session_id=session_id,
            message=f"Successfully processed {len(processed_files)} files and extracted {total_documents} documents",
            files_processed=len(processed_files),
            documents_extracted=total_documents,
            user_quota_remaining=remaining_quota,
            vectors_created=total_documents,
            ocr_available=False,
            warnings=warnings
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Unexpected error in upload_files: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get(
    "/session/{session_id}",
    summary="Get session information",
    description="Retrieve information about a specific session including document count and metadata."
)
async def get_session_info(
    session_id: str,
    rag_store: RAGStore = Depends(get_rag_store)
):
    """Get information about a session."""
    try:
        session_info = await rag_store.get_session_info(session_id)
        
        if not session_info:
            raise HTTPException(
                status_code=404,
                detail=f"Session {session_id} not found or expired"
            )
        
        return session_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session info: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving session information: {str(e)}"
        )


@router.get(
    "/session/{session_id}/stats",
    summary="Get session statistics",
    description="Get detailed statistics about a session including vector count and progress."
)
async def get_session_stats(
    session_id: str,
    rag_store: RAGStore = Depends(get_rag_store)
):
    """Get session statistics for progress tracking."""
    try:
        session_info = await rag_store.get_session_info(session_id)
        
        if not session_info:
            raise HTTPException(
                status_code=404,
                detail=f"Session {session_id} not found or expired"
            )
        
        return {
            "session_id": session_id,
            "vectors_created": session_info.get("document_count", 0),
            "status": "completed",
            "ocr_available": False
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session stats: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving session statistics: {str(e)}"
        )


@router.delete(
    "/session/{session_id}",
    summary="Delete session",
    description="Delete a session and all its associated data."
)
async def delete_session(
    session_id: str,
    rag_store: RAGStore = Depends(get_rag_store)
):
    """Delete a session."""
    try:
        success = await rag_store.delete_session(session_id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Session {session_id} not found"
            )
        
        return {"message": f"Session {session_id} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting session: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting session: {str(e)}"
        )


@router.get(
    "/quota/{user_id}",
    summary="Get user quota information",
    description="Get current quota usage for a user."
)
async def get_user_quota(
    user_id: str,
    rag_store: RAGStore = Depends(get_rag_store)
):
    """Get user quota information."""
    try:
        has_quota, current_count = await rag_store.check_user_quota(user_id)
        max_files = FILE_PROCESSING_CONFIG.get("max_files_per_user_per_day", 10)
        
        return {
            "user_id": user_id,
            "current_count": current_count,
            "max_files": max_files,
            "has_quota": has_quota,
            "remaining": max(0, max_files - current_count)
        }
        
    except Exception as e:
        logger.error(f"Error getting user quota: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving quota information: {str(e)}"
        )
