"""
FastAPI Dynamic RAG System - Main Application

What: Application entrypoint that wires together routers, middleware, and
       the lifecycle for an ephemeral, session-scoped RAG system.

Why:  Keep the composition (CORS, routers, background services) in one place
      and ensure clean startup/shutdown that initializes GPU embeddings, Redis
      session/quota tracking, and in-memory FAISS stores.

How:  Uses FastAPI lifespan to initialize a single RAGStore instance on startup
      and gracefully clean up on shutdown. Routers are mounted under /api/v1.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

from app.routers import ingest_router, retrieve_router
from app.services.rag_store import RAGStore
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management for startup and shutdown."""
    # Startup
    print("🚀 Starting Dynamic RAG System...")
    print(f"📊 Redis URL: {settings.redis_url}")
    print(f"🔧 GPU Available: {settings.use_gpu}")
    
    # Initialize RAG store
    app.state.rag_store = RAGStore()
    await app.state.rag_store.initialize()
    
    yield
    
    # Shutdown
    print("🛑 Shutting down Dynamic RAG System...")
    await app.state.rag_store.cleanup()


# Create FastAPI application
app = FastAPI(
    title="Dynamic RAG System",
    description="Ephemeral embeddings and dynamic queries with session-based storage",
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

# Include routers
app.include_router(ingest_router.router, prefix="/api/v1", tags=["ingestion"])
app.include_router(retrieve_router.router, prefix="/api/v1", tags=["retrieval"])


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "message": "Dynamic RAG System is running",
        "version": "1.0.0",
        "status": "healthy"
    }


@app.get("/health")
async def health_check():
    """Detailed health check with system status."""
    try:
        # Check Redis connection
        redis_status = await app.state.rag_store.check_redis_health()
        
        return {
            "status": "healthy",
            "redis": redis_status,
            "sessions_active": len(app.state.rag_store.sessions),
            "gpu_enabled": settings.use_gpu
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Health check failed: {str(e)}")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
