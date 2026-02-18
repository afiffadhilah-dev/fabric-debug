from sqlmodel import Field, SQLModel, Relationship, Column, JSON
from typing import Optional, List
from datetime import datetime
from uuid import UUID, uuid4


class PredefinedQuestion(SQLModel, table=True):
    """
    Individual question within a question set.
    Includes the question text, assessment criteria, and expected answer pattern.
    """
    __tablename__ = "predefined_questions"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    question_set_id: UUID = Field(foreign_key="predefined_question_sets.id", index=True)
    category: str = Field(index=True)  # e.g., "Leadership Experience", "Design Process"
    question_text: str  # The actual question to ask
    what_assesses: List[str] = Field(sa_column=Column(JSON))  # Array of assessment criteria
    expected_answer_pattern: Optional[str] = Field(default=None)  # General guidance on expected answer
    order: int = Field(default=0, index=True)  # Sequence within the question set
    is_required: bool = Field(default=True)  # Whether this question must be asked
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    question_set: "PredefinedQuestionSet" = Relationship(back_populates="questions")
