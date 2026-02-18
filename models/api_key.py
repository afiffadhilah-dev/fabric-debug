from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field


class APIKey(SQLModel, table=True):
    """Stores hashed API keys and related metadata."""

    __tablename__ = "api_keys"

    id: Optional[int] = Field(default=None, primary_key=True)
    key_hash: str = Field(index=True, nullable=False, sa_column_kwargs={"unique": True})
    name: str = Field(nullable=False)
    organization_id: int = Field(foreign_key="organizations.id", nullable=True, index=True)
    is_active: bool = Field(default=True, nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    last_used_at: Optional[datetime] = Field(default=None, nullable=True)
