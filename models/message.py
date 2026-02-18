"""
Message model for storing conversation history.

Stores both questions (assistant) and answers (user) with rich metadata
to support analytics and conversation reconstruction.
"""

from sqlmodel import SQLModel, Field, Column
from sqlalchemy import Text, JSON
from datetime import datetime
from typing import Optional, Dict, Any
import uuid


class Message(SQLModel, table=True):
    """
    Stores all conversation messages with rich metadata.

    Supports both assistant messages (questions) and user messages (answers).

    Meta structure (JSON field):

    For assistant messages (questions):
    {
        "question_type": "first_question" | "followup" | "explanation" | "example",
        "response_type": "question" | "explanation" | "example" | "followup_question",
        "intent_detected": "first_question" | "normal" | "explanation_request" | "example_request" | "partial_answer",
        "gap_id": "uuid-of-gap",  # Which gap this addresses
        "gap_description": "Description of the gap",
        "gap_category": "technical_skill",
        "gap_severity": 0.8,
        "targets_attributes": ["duration", "scale"],  # Skill attributes being probed
        "question_number": 1  # Sequential number
    }

    For user messages (answers):
    {
        "answer_type": "direct_answer" | "partial_answer" | "off_topic" | "clarification_request",
        "engagement_level": "engaged" | "disengaged",
        "detail_score": 1-5,
        "relevance_score": 0.0-1.0,
        "enthusiasm_detected": true | false,
        "reasoning": "LLM's explanation of assessment",
        "answer_length": 150,
        "gap_id": "uuid-of-gap",  # Which gap this was answering
        "skills_extracted": ["Python", "Docker"],  # Skills extracted from this answer
        "gap_resolved": false  # Whether this answer resolved the gap
    }
    """
    __tablename__ = "messages"

    id: int = Field(default=None, primary_key=True)

    # Foreign key to session
    session_id: str = Field(foreign_key="interview_sessions.id", index=True)

    # Message role
    role: str = Field(index=True)  # "user" | "assistant"

    # Message content
    content: str = Field(sa_column=Column(Text))

    # Rich metadata (JSON field) - using "meta" instead of "metadata" (reserved word)
    meta: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    class Config:
        arbitrary_types_allowed = True
