from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field


class Organization(SQLModel, table=True):
    """Organizations table for multi-tenant data isolation.
    
    Each organization is isolated - API keys and interview sessions
    belong to a single organization and cannot access data from other orgs.
    """

    __tablename__ = "organizations"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, nullable=False, unique=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
