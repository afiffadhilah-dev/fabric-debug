from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field
import sqlalchemy as sa


class Candidate(SQLModel, table=True):
    """Candidate model for storing candidate information."""
    id: str = Field(primary_key=True)
    name: str = Field()
    # Email is scoped by organization - uniqueness enforced per org
    # sa_column handles the nullable and indexing, not the Field
    email: Optional[str] = Field(default=None, sa_column=sa.Column(sa.String(), nullable=True))
    organization_id: Optional[int] = Field(default=None, foreign_key="organizations.id", nullable=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    resume: Optional[str] = Field(default=None, nullable=True)
