from sqlmodel import Field, SQLModel, Relationship
from typing import Optional, List
from datetime import datetime
from uuid import UUID, uuid4
from enum import Enum


class SeniorityLevel(str, Enum):
    """Seniority levels for roles"""
    JUNIOR = "Junior"
    MID = "Mid"
    SENIOR = "Senior"
    LEAD = "Lead"
    PRINCIPAL = "Principal"


class PredefinedRole(SQLModel, table=True):
    """
    Represents a job role/position (e.g., "Fullstack Developer", "Product Designer").
    Each role can have multiple question sets for different versions/iterations.
    """
    __tablename__ = "predefined_roles"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(index=True)  # e.g., "Fullstack Developer"
    level: SeniorityLevel = Field(index=True)  # Junior, Mid, Senior, etc.
    description: Optional[str] = Field(default=None)
    is_active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    question_sets: List["PredefinedQuestionSet"] = Relationship(back_populates="role")

    class Config:
        use_enum_values = True
