from __future__ import annotations

from typing import Optional
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime

from models.candidate import Candidate

class PresentState(SQLModel, table=True):
    __tablename__ = "present_state"

    id: Optional[int] = Field(default=None, primary_key=True)
    candidate_id: Optional[str] = Field(default=None, foreign_key="candidate.id", unique=True)

    team_satisfaction: str
    manager_relationship: str  # Weak | Neutral | Strong
    created_at: datetime = Field(default_factory=datetime.utcnow)

