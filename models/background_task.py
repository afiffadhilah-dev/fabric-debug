"""
Background Task model for tracking async task execution.
Stores task metadata, status, timestamps, and references to related entities.
"""

from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field
from uuid import uuid4


class BackgroundTask(SQLModel, table=True):
    """
    Represents a background task execution with tracking and status management.
    
    Attributes:
        id: Unique task identifier (UUID)
        task_type: Type of task (e.g., "session_summarization", "profile_summarization")
        status: Current status (INITIATED, PENDING, SUCCESS, FAILED)
        related_entity_type: Type of related entity (e.g., "interview_session", "candidate")
        related_entity_id: ID of the related entity (session_id or candidate_id)
        result: JSON result/output from the task (optional)
        error_message: Error message if task failed (optional)
        started_at: When the task execution started
        completed_at: When the task execution completed (optional)
        created_at: When the task was created/queued
    """

    __tablename__ = "background_tasks"

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    task_type: str = Field(index=True, description="Type of background task")
    status: str = Field(
        default="INITIATED",
        index=True,
        description="Task status: INITIATED, PENDING, SUCCESS, FAILED"
    )
    related_entity_type: str = Field(
        description="Type of related entity (e.g., 'interview_session', 'candidate')"
    )
    related_entity_id: str = Field(
        index=True,
        description="ID of the related entity"
    )
    result: Optional[str] = Field(
        default=None,
        description="JSON result/output from the task"
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if task failed"
    )
    started_at: Optional[datetime] = Field(
        default=None,
        description="When task execution started"
    )
    completed_at: Optional[datetime] = Field(
        default=None,
        description="When task execution completed"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the task was created/queued"
    )

    class Config:
        """SQLModel configuration."""
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "task_type": "session_summarization",
                "status": "SUCCESS",
                "related_entity_type": "interview_session",
                "related_entity_id": "session-uuid",
                "result": '{"skills": [...], "behaviors": [...]}',
                "error_message": None,
                "started_at": "2026-02-05T10:00:00",
                "completed_at": "2026-02-05T10:05:30",
                "created_at": "2026-02-05T09:59:00"
            }
        }
