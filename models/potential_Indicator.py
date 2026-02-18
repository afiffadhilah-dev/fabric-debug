from __future__ import annotations

from typing import Optional
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime

from models.candidate import Candidate

class PotentialIndicator(SQLModel, table=True):
    __tablename__ = "potential_indicators"

    id: Optional[int] = Field(default=None, primary_key=True)
    candidate_id: Optional[str] = Field(default=None, foreign_key="candidate.id")

    dimension: str    # Learning velocity, Self-direction, etc.
    assessment: str   # Low | Medium | Medium-High | High
    created_at: datetime = Field(default_factory=datetime.utcnow)

