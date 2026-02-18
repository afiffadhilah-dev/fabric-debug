from sqlmodel import Field, SQLModel, Relationship
from typing import Optional, List
from datetime import datetime
from uuid import UUID, uuid4


class PredefinedQuestionSet(SQLModel, table=True):
    """
    A versioned collection of questions for a specific role.
    Only one question set should be active per role at a time.
    """
    __tablename__ = "predefined_question_sets"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    role_id: UUID = Field(foreign_key="predefined_roles.id", index=True)
    name: str  # e.g., "Fullstack Senior - 2026 Q1"
    version: str  # e.g., "v1.0", "v2.1"
    description: Optional[str] = Field(default=None)
    is_active: bool = Field(default=False, index=True)  # Only one active per role
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    role: "PredefinedRole" = Relationship(back_populates="question_sets")
    questions: List["PredefinedQuestion"] = Relationship(back_populates="question_set", cascade_delete=True)
