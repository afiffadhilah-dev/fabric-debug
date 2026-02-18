from __future__ import annotations
from typing import Optional
from sqlmodel import SQLModel, Field


class CandidateProfileSummary(SQLModel, table=True):
    __tablename__ = "candidate_profile_summaries"

    id: Optional[int] = Field(default=None, primary_key=True)
    candidate_id: Optional[str] = Field(default=None, foreign_key="candidate.id")
    session_id: Optional[str] = Field(default=None, description="Session ID for session-based summaries")
    summary_type: Optional[str] = Field(default=None, description="Type of summary (e.g., general, skills, infra, domain, etc)")
    summary: Optional[str] = Field(default=None, description="Long-form markdown profile summary")
