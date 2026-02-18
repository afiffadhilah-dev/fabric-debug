"""
Candidate Profile Summary repository for profile summary persistence.

Handles CRUD operations for candidate_profile_summary table with rich query support.
"""

from typing import Optional
from sqlmodel import Session, select

from models.candidate_profile_summary import CandidateProfileSummary
from repositories.base_repository import BaseRepository


class CandidateProfileSummaryRepository(BaseRepository[CandidateProfileSummary]):
    """Repository for managing candidate profile summaries."""

    def __init__(self, db_session: Session):
        super().__init__(db_session, CandidateProfileSummary)

    def save(
        self,
        candidate_id: str,
        summary: str,
        summary_type: str,
        session_id: Optional[str] = None,
    ) -> CandidateProfileSummary:
        """
        Save a candidate profile summary to the database.

        Args:
            candidate_id: The candidate ID
            summary: The summary text
            summary_type: Type of summary (e.g., "GENERAL", "SKILLS", "INFRA", "DOMAIN")
            session_id: Session ID for session-based summaries

        Returns:
            The created CandidateProfileSummary record
        """
        profile_summary = CandidateProfileSummary(
            candidate_id=candidate_id,
            session_id=session_id,
            summary_type=summary_type,
            summary=summary,
        )
        return self.create(profile_summary)

    def get_by_candidate_and_type(
        self,
        candidate_id: str,
        summary_type: str,
    ) -> Optional[CandidateProfileSummary]:
        """
        Retrieve a candidate profile summary from the database.

        Args:
            candidate_id: The candidate ID
            summary_type: Type of summary to retrieve (e.g., "GENERAL", "SKILLS", "INFRA", "DOMAIN")

        Returns:
            CandidateProfileSummary record or None if not found
        """
        query = select(CandidateProfileSummary).where(
            (CandidateProfileSummary.candidate_id == candidate_id) &
            (CandidateProfileSummary.summary_type == summary_type)
        ).order_by(CandidateProfileSummary.id.desc())
        return self.db.exec(query).first()
