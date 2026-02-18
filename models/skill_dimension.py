from __future__ import annotations

from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import datetime

from models.skill import Skill

class SkillDimension(SQLModel, table=True):
    __tablename__ = "skill_dimensions"

    id: Optional[int] = Field(default=None, primary_key=True)
    skill_id: int = Field(foreign_key="skills.id")

    dimension: str  # Duration, Depth, Autonomy, Scale, Constraints, Production
    value: str
    
    created_at: datetime = Field(default_factory=datetime.utcnow)

    
