from datetime import datetime
from typing import Optional
import uuid

from sqlmodel import SQLModel, Field


class ExtractedSkill(SQLModel, table=True):
    """
    Skills extracted during the interview.

    Stores technical skills with 6 key attributes:
    1. Duration: How long they've used the skill
    2. Depth: Complexity level and aspects implemented
    3. Autonomy: Ownership level and independence
    4. Scale: Size/impact (users, traffic, components)
    5. Constraints: Limitations or challenges encountered
    6. Production vs Prototype: Production-ready or PoC/prototype
    """
    __tablename__ = "extracted_skills"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    session_id: str = Field(foreign_key="interview_sessions.id", index=True)

    # Skill data
    name: str = Field(index=True)
    confidence_score: float = Field(default=1.0)

    # 6 skill attributes
    duration: Optional[str] = None
    depth: Optional[str] = None
    autonomy: Optional[str] = None
    scale: Optional[str] = None
    constraints: Optional[str] = None
    production_vs_prototype: Optional[str] = None

    # Evidence
    evidence: str = Field(default="")

    created_at: datetime = Field(default_factory=datetime.utcnow)
