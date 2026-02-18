from pydantic import BaseModel, Field
from typing import List, Optional

class CandidateBase(BaseModel):
    id: str
    name: str
    email: Optional[str] = None

class CandidateUpsertRequest(BaseModel):
    name: str
    email: Optional[str] = None

class CandidateDetailResponse(BaseModel):
    candidate: CandidateBase

class CandidateListResponse(BaseModel):
    candidates: List[CandidateBase]
    total: int
    page: int
    page_size: int

class SessionBase(BaseModel):
    id: str
    candidate_id: str
    created_at: Optional[str] = None
    completed_at: Optional[str] = None

class SessionListResponse(BaseModel):
    sessions: List[SessionBase]

class ResumeRequest(BaseModel):
    """Request body for uploading a candidate resume."""
    resume: str = Field(..., min_length=1, description="Full resume text")

class ResumeResponse(BaseModel):
    """Response for resume get/upload endpoints."""
    candidate_id: str = Field(..., description="Candidate identifier")
    resume: Optional[str] = Field(None, description="Stored resume text")
    status: str = Field(default="success", description="Operation status")
