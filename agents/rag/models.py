from pydantic import BaseModel, Field
from typing import Any, Optional, List


class StoreRequest(BaseModel):
    name: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: Optional[int] = Field(10, ge=1, le=50)


class StoreResult(BaseModel):
    success: bool
    stored_chunks: Optional[int] = None
    message: Optional[str] = None


class RetrieveResult(BaseModel):
    success: bool
    results: Optional[List[dict]] = None
    message: Optional[str] = None
