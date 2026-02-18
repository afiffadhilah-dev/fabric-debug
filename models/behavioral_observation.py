from __future__ import annotations

from typing import Optional
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime

from models.candidate import Candidate

class BehavioralObservation(SQLModel, table=True):
    __tablename__ = "behavioral_observations"

    id: Optional[int] = Field(default=None, primary_key=True)
    candidate_id: Optional[str] = Field(default=None, foreign_key="candidate.id")

    category: str
    observation: str
    confidence: str     # Low | Low-Medium | Medium | Medium-High | High
    created_at: datetime = Field(default_factory=datetime.utcnow)

