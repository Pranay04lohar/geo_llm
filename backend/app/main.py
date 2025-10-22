from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import os
from .routers import query_router
from .services.roi_parser import roi_parser

app = FastAPI(
    title="GeoLLM MVP",
    description="Modular monolith architecture for geospatial chat system",
    version="0.1"
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
def read_root():
    return {"message": "Welcome to the GeoSpatial LLM API"}

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
    from backend.app.search_service.main import app as search_app
    # Mount search service at /search
    from fastapi import APIRouter
    search_router = APIRouter()
    for route in search_app.routes:
        if hasattr(route, 'path') and hasattr(route, 'endpoint'):
            # Skip root and duplicate health endpoints
            if route.path not in ['/', '/openapi.json', '/docs', '/redoc']:
                app.routes.append(route)
    print("✅ Search service routes loaded")
except Exception as e:
    print(f"⚠️ Search service not available: {e}")

# Include GEE Service routes
try:
    from backend.app.gee_service.main import app as gee_app
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
    from backend.app.rag_service.dynamic_rag.app.main import app as rag_app
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
    from backend.app.services.core_llm_agent.core_agent_api import app as agent_app
    for route in agent_app.routes:
        if hasattr(route, 'path') and hasattr(route, 'endpoint'):
            # Skip root and duplicate endpoints
            if route.path not in ['/', '/openapi.json', '/docs', '/redoc', '/health']:
                app.routes.append(route)
    print("✅ Core LLM Agent routes loaded")
except Exception as e:
    print(f"⚠️ Core LLM Agent not available: {e}")
