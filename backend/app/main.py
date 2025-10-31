from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import os
from .routers import query_router
from .services.roi_parser import roi_parser

This is the main entry point for the monolithic backend service that combines:
- Core LLM Agent (orchestration)
- GEE Services (geospatial analysis)
- Search Services (location resolution, web search)
- RAG Services (document Q&A)

All services are integrated as direct Python imports (no HTTP calls between services).
"""

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings

# Setup logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager - handles startup and shutdown.
    
    Startup:
    - Initialize RAG store (Redis, embeddings, FAISS)
    - Initialize Core LLM Agent with all services
    - Initialize GEE client
    
    Shutdown:
    - Cleanup RAG store
    - Close connections
    """
    logger.info("=" * 80)
    logger.info(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info("=" * 80)
    
    try:
        # ========================================================================
        # Initialize RAG Store
        # ========================================================================
        logger.info("📚 Initializing RAG store...")
        try:
            from app.services.rag.rag_store import RAGStore
            app.state.rag_store = RAGStore()
            await app.state.rag_store.initialize()
            logger.info("✅ RAG store initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize RAG store: {e}")
            logger.warning("⚠️  Continuing without RAG functionality")
            app.state.rag_store = None
        
        # ========================================================================
        # Initialize Google Earth Engine
        # ========================================================================
        logger.info("🌍 Initializing Google Earth Engine...")
        try:
            import ee
            ee.Initialize()
            logger.info("✅ Google Earth Engine initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize GEE: {e}")
            logger.warning("⚠️  GEE services may not work properly")
        
        # ========================================================================
        # Initialize Core LLM Agent
        # ========================================================================
        logger.info("🤖 Initializing Core LLM Agent...")
        try:
            from app.services.core_llm_agent.agent import CoreLLMAgent
            app.state.core_agent = CoreLLMAgent(
                enable_debug=settings.DEBUG,
                rag_store=app.state.rag_store
            )
            logger.info("✅ Core LLM Agent initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Core LLM Agent: {e}")
            raise
        
        # ========================================================================
        # Startup Complete
        # ========================================================================
        logger.info("=" * 80)
        logger.info("✅ GeoLLM Backend started successfully!")
        logger.info(f"📡 Listening on {settings.HOST}:{settings.PORT}")
        logger.info(f"📖 API Documentation: http://{settings.HOST}:{settings.PORT}/docs")
        logger.info("=" * 80)
        
        yield
        
        # ========================================================================
        # Shutdown
        # ========================================================================
        logger.info("🛑 Shutting down GeoLLM Backend...")
        
        if app.state.rag_store:
            try:
                await app.state.rag_store.cleanup()
                logger.info("✅ RAG store cleaned up")
            except Exception as e:
                logger.error(f"❌ Error cleaning up RAG store: {e}")
        
        logger.info("👋 Shutdown complete")
        
    except Exception as e:
        logger.error(f"💥 Fatal error during startup: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise


# ============================================================================
# Create FastAPI Application
# ============================================================================
app = FastAPI(
    title=settings.APP_NAME,
    description="Monolithic geospatial analysis service with LLM-powered query processing",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration: read allowed origins or regex from environment
allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "")
allowed_origins = [o.strip() for o in allowed_origins_env.split(",") if o.strip()]

# Optional regex to allow dynamic preview domains (e.g., Vercel previews)
allowed_origin_regex = os.getenv("ALLOWED_ORIGIN_REGEX")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if allowed_origins else ["*"],
    allow_origin_regex=allowed_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "healthy",
        "endpoints": {
            "main_query": "/api/query",
            "rag_upload": "/api/rag/upload",
            "rag_query": "/api/rag/query",
            "health": "/health",
            "docs": "/docs"
        }
    }

@app.get("/health")
def health_check():
    return {
        "status": "healthy", 
        "service": "geollm-backend",
        "services": {
            "search": "loaded" if "search_service" in str(app.routes) else "not loaded",
            "gee": "loaded" if "gee_service" in str(app.routes) else "not loaded",
            "rag": "loaded" if "rag_service" in str(app.routes) else "not loaded",
            "core_agent": "loaded" if "cot-stream" in str(app.routes) else "not loaded"
        }
    }

@app.get("/parse-query")
def parse_query(query: str = Query(..., description="The query string to parse")):
    locations = roi_parser(query)
    return {"found_locations": locations}

# Register routers
app.include_router(query_router.router, prefix="/query")

# Include Search Service routes
try:
    from .search_service.main import app as search_app
    for route in search_app.routes:
        if hasattr(route, 'path') and hasattr(route, 'endpoint'):
            # Skip root and duplicate endpoints
            if route.path not in ['/', '/openapi.json', '/docs', '/redoc', '/health']:
                app.routes.append(route)
    print("✅ Search service routes loaded")
except Exception as e:
    print(f"⚠️ Search service not available: {e}")

# Include GEE Service routes
try:
    from .gee_service.main import app as gee_app
    for route in gee_app.routes:
        if hasattr(route, 'path') and hasattr(route, 'endpoint'):
            # Skip root and duplicate health endpoints
            if route.path not in ['/', '/openapi.json', '/docs', '/redoc', '/health']:
                app.routes.append(route)
    print("✅ GEE service routes loaded")
except Exception as e:
    print(f"⚠️ GEE service not available: {e}")

# Include RAG Service routes
try:
    from .rag_service.dynamic_rag.app.main import app as rag_app
    for route in rag_app.routes:
        if hasattr(route, 'path') and hasattr(route, 'endpoint'):
            # Skip root and duplicate endpoints, keep /api/v1 prefix
            if route.path not in ['/', '/openapi.json', '/docs', '/redoc', '/health']:
                app.routes.append(route)
    print("✅ RAG service routes loaded")
except Exception as e:
    print(f"⚠️ RAG service not available: {e}")

# Include Core LLM Agent routes
try:
    from .services.core_llm_agent.core_agent_api import app as agent_app
    for route in agent_app.routes:
        if hasattr(route, 'path') and hasattr(route, 'endpoint'):
            # Skip root and duplicate endpoints
            if route.path not in ['/', '/openapi.json', '/docs', '/redoc', '/health']:
                app.routes.append(route)
    print("✅ Core LLM Agent routes loaded")
except Exception as e:
    print(f"⚠️ Core LLM Agent not available: {e}")
