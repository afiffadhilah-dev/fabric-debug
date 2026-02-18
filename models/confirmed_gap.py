from __future__ import annotations

from typing import Optional
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime

from models.candidate import Candidate

class ConfirmedGap(SQLModel, table=True):
    __tablename__ = "confirmed_gaps"

    id: Optional[int] = Field(default=None, primary_key=True)
    candidate_id: Optional[str] = Field(default=None, foreign_key="candidate.id")

    skill_name: str
    description: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

