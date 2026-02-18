"""
Repository for PredefinedQuestionSet entities.

Provides basic accessors; built on top of `BaseRepository`.
"""
from typing import Optional
from sqlmodel import Session

from models.predefined_question_set import PredefinedQuestionSet
from repositories.base_repository import BaseRepository


class PredefinedQuestionSetRepository(BaseRepository[PredefinedQuestionSet]):
    """Repository for managing PredefinedQuestionSet and its related questions."""

    def __init__(self, db_session: Session):
        super().__init__(db_session, PredefinedQuestionSet)

    def get_by_id(self, id: object) -> Optional[PredefinedQuestionSet]:
        # Use base get_by_id; kept for explicitness and future extensions
        return super().get_by_id(id)
