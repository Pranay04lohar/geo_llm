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

# CORS configuration: read allowed origins from environment (comma-separated)
allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "*")
allowed_origins = [o.strip() for o in allowed_origins_env.split(",") if o.strip()] or ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Welcome to the GeoSpatial LLM API"}

@app.get("/parse-query")
def parse_query(query: str = Query(..., description="The query string to parse")):
    locations = roi_parser(query)
    return {"found_locations": locations}

# Register routers
app.include_router(query_router.router, prefix="/query")
