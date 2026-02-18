"""
Repository for PredefinedQuestion entities.

Provides query helpers to fetch questions for a question set.
"""
from typing import List
from sqlmodel import Session, select

from models.predefined_question import PredefinedQuestion
from repositories.base_repository import BaseRepository


class PredefinedQuestionRepository(BaseRepository[PredefinedQuestion]):
    """Repository for fetching PredefinedQuestion records."""

    def __init__(self, db_session: Session):
        super().__init__(db_session, PredefinedQuestion)

    def get_by_question_set(self, question_set_id: str) -> List[PredefinedQuestion]:
        statement = (
            select(PredefinedQuestion)
            .where(PredefinedQuestion.question_set_id == question_set_id)
            .order_by(PredefinedQuestion.order)
        )
        return list(self.db.exec(statement).all())
