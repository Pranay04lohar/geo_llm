# routers are used to handle the requests and responses from the frontend

from fastapi import APIRouter
from ..models import QueryRequest, QueryResponse

router = APIRouter()

@router.get("/")
def read_query_root():
    return {"message": "This is the query endpoint. Use POST to send data."}

@router.post("/", response_model=QueryResponse)
async def handle_query(payload: QueryRequest):
    # processed response coming back from the logic layer(GEE,RAG,LLM) of backend
    return QueryResponse(
        status="success",
        data={
            "message": f"Received text: {payload.text}",
            "roi": payload.roi.dict() if payload.roi else None
        }
    )
