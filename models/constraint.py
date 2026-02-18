from __future__ import annotations

from typing import Optional
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime

from models.candidate import Candidate

class Constraint(SQLModel, table=True):
    __tablename__ = "constraints"

    id: Optional[int] = Field(default=None, primary_key=True)
    candidate_id: Optional[str] = Field(default=None, foreign_key="candidate.id")

    constraint_type: str
    details: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

