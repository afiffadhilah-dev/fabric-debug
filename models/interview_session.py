from datetime import datetime
from typing import Optional
import uuid
from uuid import UUID

from sqlmodel import SQLModel, Field, Column
from sqlalchemy import Text


class InterviewSession(SQLModel, table=True):
    """
    Interview session tracking for the interview graph agent.

    Tracks the overall interview metadata, status, and metrics.
    """
    __tablename__ = "interview_sessions"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    candidate_id: str = Field(foreign_key="candidate.id", index=True)
    organization_id: int = Field(foreign_key="organizations.id", nullable=True, index=True)

    # Resume data
    resume_text: str = Field(sa_column=Column(Text))

    # Interview mode
    mode: str = Field(default="dynamic_gap", index=True)  # "dynamic_gap" | "predefined_questions"
    question_set_id: Optional[UUID] = Field(default=None, foreign_key="predefined_question_sets.id")

    # Language preference
    language: Optional[str] = Field(default=None)  # ISO 639-1 code (e.g. "id", "es")

    # Session state
    status: str = Field(default="active")  # active, completed, abandoned
    termination_reason: Optional[str] = None  # complete, disengaged, no_gaps

    # Metrics
    questions_asked: int = Field(default=0)
    questions_answered: Optional[int] = Field(default=None)
    questions_skipped: Optional[int] = Field(default=None)
    skipped_categories: Optional[str] = Field(default=None, sa_column=Column(Text))  # JSON string
    completeness_score: float = Field(default=0.0)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    # LangGraph thread reference
    thread_id: str = Field(index=True)
