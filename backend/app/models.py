# pydantic models are classes that define the structure of the data that will be sent and received by the API

from pydantic import BaseModel
from typing import Optional, Dict, Any

# ROI is a region of interest, it can be a polygon, a circle, a rectangle, etc.
class ROI(BaseModel):
    type: str
    coordinates: list

# What frontend will send to the backend, it can be a text or a roi
class QueryRequest(BaseModel):
    text: str
    roi: Optional[ROI] = None

# What backend will return or send to the frontend
class QueryResponse(BaseModel):
    status: str
    data: Dict[str, Any]
