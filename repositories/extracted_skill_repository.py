"""
Repository for ExtractedSkill entities.

Adds a convenience method to query skills by session id.
"""
from typing import List
from sqlmodel import Session, select

from models.extracted_skill import ExtractedSkill
from repositories.base_repository import BaseRepository


class ExtractedSkillRepository(BaseRepository[ExtractedSkill]):
    """Repository for persisting and querying ExtractedSkill records."""

    def __init__(self, db_session: Session):
        super().__init__(db_session, ExtractedSkill)

    def get_by_session(self, session_id: str) -> List[ExtractedSkill]:
        statement = select(ExtractedSkill).where(ExtractedSkill.session_id == session_id)
        return list(self.db.exec(statement).all())
