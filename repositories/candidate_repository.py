"""
Candidate repository for candidate persistence.

Handles CRUD operations for candidates table with rich query support.
Provides convenience methods around `Candidate` using `BaseRepository`.
"""

from typing import Optional
from sqlmodel import Session, select, func

from models.candidate import Candidate
from repositories.base_repository import BaseRepository


class CandidateRepository(BaseRepository[Candidate]):
    """Repository for managing candidates."""

    def __init__(self, db_session: Session):
        super().__init__(db_session, Candidate)

    def get_by_id(self, candidate_id: str) -> Optional[Candidate]:
        """
        Get a candidate by ID.

        Args:
            candidate_id: The candidate ID

        Returns:
            Candidate if found, None otherwise
        """
        query = select(Candidate).where(Candidate.id == candidate_id)
        return self.db.exec(query).first()

    def get_or_create(self, candidate_id: str, name: Optional[str] = None) -> Candidate:
        """Return existing candidate or create a new one.

        Args:
            candidate_id: Candidate primary key
            name: Optional display name

        Returns:
            Candidate instance
        """
        candidate = self.get_by_id(candidate_id)
        if candidate:
            return candidate

        candidate = Candidate(id=candidate_id, name=name or "")
        return self.create(candidate)

    def get_by_email_and_org(self, email: str, organization_id: Optional[int] = None) -> Optional[Candidate]:
        """
        Find candidate by email and organization.

        Args:
            email: Candidate email
            organization_id: Organization id (optional)

        Returns:
            Candidate or None
        """
        if not email:
            return None
        query = select(Candidate).where(Candidate.email == email)
        if organization_id is not None:
            query = query.where(Candidate.organization_id == organization_id)
        return self.db.exec(query).first()

    def get_name_by_session_id(self, session_id: str) -> str:
        """Get candidate name by interview session ID.

        Args:
            session_id: Interview session UUID

        Returns:
            Candidate name or empty string if not found
        """
        from models.interview_session import InterviewSession
        
        # Join interview_session and candidate tables
        query = (
            select(Candidate.name)
            .join(InterviewSession, InterviewSession.candidate_id == Candidate.id)
            .where(InterviewSession.id == session_id)
        )
        result = self.db.exec(query).first()
        return result or ""

    def get_paginated(self, page: int = 1, page_size: int = 20, organization_id: Optional[int] = None):
        """
        Get paginated candidates.

        Args:
            page: Page number
            page_size: Number of candidates per page
            organization_id: Optional organization filter

        Returns:
            Tuple of (candidates, total_count)
        """
        offset = (page - 1) * page_size
        query = select(Candidate)
        if organization_id:
            query = query.where(Candidate.organization_id == organization_id)
        query = query.offset(offset).limit(page_size)
        candidates = self.db.exec(query).all()
        # Count total records using func.count() - more efficient
        count_query = select(func.count(Candidate.id))
        if organization_id:
            count_query = count_query.where(Candidate.organization_id == organization_id)
        total = self.db.exec(count_query).one()
        return candidates, total
