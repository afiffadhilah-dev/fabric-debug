from __future__ import annotations
from typing import Optional, Any, Dict
from sqlmodel import SQLModel, Field
from sqlalchemy import Column
from sqlalchemy import JSON


class DomainContext(SQLModel, table=True):
    __tablename__ = "domain_contexts"

    id: Optional[int] = Field(default=None, primary_key=True)
    candidate_id: Optional[str] = Field(default=None, foreign_key="candidate.id")

    # Arbitrary structured data for the domain context (stored as JSON)
    data: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
