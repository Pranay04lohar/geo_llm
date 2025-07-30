from fastapi import FastAPI
from app.routers import query_router

app = FastAPI(
    title="GeoLLM MVP",
    description="Modular monolith architecture for geospatial chat system",
    version="0.1"
)

@app.get("/")
def read_root():
    return {"message": "Welcome to the GeoSpatial LLM API"}

# Register routers
app.include_router(query_router.router, prefix="/query")
