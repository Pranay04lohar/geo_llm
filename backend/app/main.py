from fastapi import FastAPI, Query
from app.routers import query_router
from app.services.roi_parser import roi_parser

app = FastAPI(
    title="GeoLLM MVP",
    description="Modular monolith architecture for geospatial chat system",
    version="0.1"
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
