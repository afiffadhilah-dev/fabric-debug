from __future__ import annotations

from typing import Optional
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime

from models.candidate import Candidate

class Evidence(SQLModel, table=True):
    __tablename__ = "evidence"

    id: Optional[int] = Field(default=None, primary_key=True)
    candidate_id: Optional[str] = Field(default=None, foreign_key="candidate.id")

    related_entity: str
    related_entity_id: Optional[int] = None
    attribute: Optional[str] = None

    content: str
    source_type: str           # conversation | resume | manager | self
    source_reference: Optional[str] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)

