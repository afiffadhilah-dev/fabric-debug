from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


# ============ Request Schemas ============

class SummarizeSessionRequest(BaseModel):
    """Schema for summarizing an interview session"""
    session_id: str = Field(..., min_length=1, description="Unique identifier for the interview session")
    mode: str = Field(default="SELF_REPORT", description="Interview mode (e.g., SELF_REPORT, RECRUITER_REPORT)")

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "18426303-9f4f-49ec-bb82-bb7820bb7485",
                "mode": "SELF_REPORT"
            }
        }


class SummarizeProfileRequest(BaseModel):
    """Schema for summarizing a candidate's profile"""
    candidate_id: str = Field(..., min_length=1, description="Unique identifier for the candidate")

    class Config:
        json_schema_extra = {
            "example": {
                "candidate_id": "0c6dec64-5292-4293-859f-700411c57e6c"
            }
        }


class SummarizeSessionProfileRequest(BaseModel):
    """Schema for session profile summarization request"""
    session_id: str = Field(..., min_length=1, description="Unique identifier for the interview session")
    mode: str = Field(default="SELF_REPORT", description="Interview mode (e.g., SELF_REPORT, RECRUITER_REPORT)")

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "18426303-9f4f-49ec-bb82-bb7820bb7485",
                "mode": "SELF_REPORT"
            }
        }


# ============ Response Schemas ============

class SummarizeSessionResponse(BaseModel):
    """Schema for session summarization response"""
    session_id: str = Field(..., description="Session identifier")
    mode: str = Field(..., description="Interview mode")
    skills: Optional[list] = Field(None, description="Extracted skills")
    behavior_observations: Optional[list] = Field(None, description="Behavioral observations")
    infra_contexts: Optional[list] = Field(None, description="Infrastructure contexts")
    domain_contexts: Optional[list] = Field(None, description="Domain contexts")
    status: str = Field(default="success", description="Status of the summarization")

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "18426303-9f4f-49ec-bb82-bb7820bb7485",
                "mode": "SELF_REPORT",
                "skills": [],
                "behavior_observations": [],
                "infra_contexts": [],
                "domain_contexts": [],
                "status": "success"
            }
        }


class SummarizeProfileResponse(BaseModel):
    """Schema for profile summarization response"""
    candidate_id: str = Field(..., description="Candidate identifier")
    summary: str = Field(..., description="Long-form markdown profile summary")
    status: str = Field(default="success", description="Status of the summarization")

    class Config:
        json_schema_extra = {
            "example": {
                "candidate_id": "0c6dec64-5292-4293-859f-700411c57e6c",
                "summary": "# Candidate Profile Summary\n\nThe candidate has experience...",
                "status": "success"
            }
        }


class CandidateProfileResponse(BaseModel):
    """Schema for candidate profile response"""
    candidate_id: Optional[str] = Field(None, description="Candidate identifier")
    profile: Dict[str, Any] = Field(..., description="Complete candidate profile in JSON format")
    status: str = Field(default="success", description="Status of the request")

    class Config:
        json_schema_extra = {
            "example": {
                "candidate_id": "0c6dec64-5292-4293-859f-700411c57e6c",
                "profile": {
                    "candidate": {"id": "123", "name": "John Doe"},
                    "skills": [],
                    "behavioral_observations": []
                },
                "status": "success"
            }
        }


class ProfileSummaryResponse(BaseModel):
    """Schema for profile summary response"""
    candidate_id: str = Field(..., description="Candidate identifier")
    summary: str = Field(..., description="Profile summary text")
    summary_type: str = Field(default="GENERAL", description="Type of summary")
    status: str = Field(default="success", description="Status of the request")

    class Config:
        json_schema_extra = {
            "example": {
                "candidate_id": "0c6dec64-5292-4293-859f-700411c57e6c",
                "summary": "# Candidate Profile Summary\n\nBased on database profile...",
                "summary_type": "GENERAL",
                "status": "success"
            }
        }


class ErrorResponse(BaseModel):
    """Schema for error responses"""
    detail: str = Field(..., description="Error message")
    status_code: int = Field(..., description="HTTP status code")

class TaskStatusResponse(BaseModel):
    """Schema for background task status response"""
    task_id: str = Field(..., description="UUID of the background task")
    status: str = Field(..., description="Current task status")
    message: str = Field(..., description="Human-readable status message")
    error: Optional[str] = Field(None, description="Error message if task failed")

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "INITIATED",
                "message": "Session summarization task queued. Task ID: 550e8400-e29b-41d4-a716-446655440000",
                "error": None
            }
        }

class SummarizeSessionProfileResponse(BaseModel):
    """Schema for session profile summarization response"""
    session_id: str = Field(..., description="Session identifier")
    candidate_id: str = Field(..., description="Candidate identifier")
    summary: str = Field(..., description="Long-form markdown profile summary")
    status: str = Field(default="success", description="Status of the summarization")

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "18426303-9f4f-49ec-bb82-bb7820bb7485",
                "candidate_id": "0c6dec64-5292-4293-859f-700411c57e6c",
                "summary": "# Candidate Session Profile Summary\n\nThe candidate has experience...",
                "status": "success"
            }
        }
