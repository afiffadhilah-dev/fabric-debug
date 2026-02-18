"""
API schemas for background task status and responses.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class BackgroundTaskStatusResponse(BaseModel):
    """Response schema for background task status."""

    task_id: str = Field(..., description="Unique task identifier")
    task_type: str = Field(..., description="Type of task")
    status: str = Field(
        ...,
        description="Current task status (INITIATED, PENDING, SUCCESS, FAILED)"
    )
    related_entity_type: str = Field(..., description="Type of related entity")
    related_entity_id: str = Field(..., description="ID of related entity")
    result: Optional[str] = Field(None, description="JSON result if task succeeded")
    error_message: Optional[str] = Field(None, description="Error message if task failed")
    started_at: Optional[datetime] = Field(None, description="When task execution started")
    completed_at: Optional[datetime] = Field(None, description="When task execution completed")
    created_at: datetime = Field(..., description="When task was created")

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "task_type": "session_summarization",
                "status": "SUCCESS",
                "related_entity_type": "interview_session",
                "related_entity_id": "session-id-123",
                "result": '{"skills": [...], "behaviors": [...]}',
                "error_message": None,
                "started_at": "2026-02-05T10:00:00",
                "completed_at": "2026-02-05T10:05:30",
                "created_at": "2026-02-05T09:59:00"
            }
        }
