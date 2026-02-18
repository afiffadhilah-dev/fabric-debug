"""
Interview Session repository for interview session persistence.

Handles CRUD operations for interview_sessions table with rich query support.
"""

from typing import List, Optional, Dict, Any
from sqlmodel import Session, select
from datetime import datetime

from models.interview_session import InterviewSession
from repositories.base_repository import BaseRepository


class InterviewSessionRepository(BaseRepository[InterviewSession]):
    """Repository for managing interview sessions."""

    def __init__(self, db_session: Session):
        super().__init__(db_session, InterviewSession)

    def get_latest_by_session_id(self, session_id: str, organization_id: int) -> Optional[str]:
        """
        Get the latest interview session ID for a candidate, filtered by organization.

        Args:
            session_id: Session identifier
            organization_id: Organization to filter by

        Returns:
            Latest session_id if found, None otherwise
        """
        statement = (
            select(InterviewSession)
            .where(InterviewSession.id == session_id)
            .where(InterviewSession.organization_id == organization_id)
            .order_by(InterviewSession.created_at.desc())
            .limit(1)
        )
        session = self.db.exec(statement).first()
        return session.id if session else None

    def get_last_by_candidate(self, candidate_id: str) -> Optional[InterviewSession]:
        """
        Get the most recent interview session for a candidate.

        Args:
            candidate_id: The candidate ID

        Returns:
            The most recent InterviewSession or None if not found
        """
        query = select(InterviewSession).where(
            InterviewSession.candidate_id == candidate_id
        ).order_by(InterviewSession.created_at.desc())
        return self.db.exec(query).first()

    def get_by_session_id(self, session_id: str, organization_id: int) -> Optional[InterviewSession]:
        """
        Get session by session ID, filtered by organization.

        Args:
            session_id: Session identifier
            organization_id: Organization to filter by

        Returns:
            InterviewSession if found, None otherwise
        """
        statement = select(InterviewSession).where(
            InterviewSession.id == session_id,
            InterviewSession.organization_id == organization_id
        )
        return self.db.exec(statement).first()

    def get_by_thread_id(self, thread_id: str, organization_id: int) -> Optional[InterviewSession]:
        """
        Get session by LangGraph thread ID, filtered by organization.

        Args:
            thread_id: LangGraph thread identifier
            organization_id: Organization to filter by

        Returns:
            InterviewSession if found, None otherwise
        """
        statement = select(InterviewSession).where(
            InterviewSession.thread_id == thread_id,
            InterviewSession.organization_id == organization_id
        )
        return self.db.exec(statement).first()

    def get_by_candidate(
        self,
        candidate_id: str,
        organization_id: int,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[InterviewSession]:
        """
        Get all sessions for a candidate, filtered by organization.

        Args:
            candidate_id: Candidate identifier
            organization_id: Organization to filter by
            status: Optional filter by status
            limit: Maximum number of results

        Returns:
            List of sessions ordered by created_at DESC
        """
        statement = select(InterviewSession).where(
            InterviewSession.candidate_id == candidate_id,
            InterviewSession.organization_id == organization_id
        )

        if status:
            statement = statement.where(InterviewSession.status == status)

        statement = statement.order_by(
            InterviewSession.created_at.desc()).limit(limit)

        return list(self.db.exec(statement).all())

    def get_active_sessions(self, organization_id: int, limit: int = 100) -> List[InterviewSession]:
        """
        Get all active interview sessions for organization.

        Args:
            organization_id: Organization to filter by
            limit: Maximum number of results

        Returns:
            List of active sessions
        """
        statement = (
            select(InterviewSession)
            .where(
                InterviewSession.status == "active",
                InterviewSession.organization_id == organization_id
            )
            .order_by(InterviewSession.created_at.desc())
            .limit(limit)
        )
        return list(self.db.exec(statement).all())

    def get_completed_sessions(
        self,
        organization_id: int,
        candidate_id: Optional[str] = None,
        limit: int = 100
    ) -> List[InterviewSession]:
        """
        Get completed interview sessions for organization.

        Args:
            organization_id: Organization to filter by
            candidate_id: Optional filter by candidate
            limit: Maximum number of results

        Returns:
            List of completed sessions
        """
        statement = select(InterviewSession).where(
            InterviewSession.status == "completed",
            InterviewSession.organization_id == organization_id
        )

        if candidate_id:
            statement = statement.where(
                InterviewSession.candidate_id == candidate_id)

        statement = statement.order_by(
            InterviewSession.completed_at.desc()).limit(limit)

        return list(self.db.exec(statement).all())

    def list_sessions(
        self,
        organization_id: int,
        candidate_id: Optional[str] = None,
        status: Optional[str] = None,
        mode: Optional[str] = None,
        start: int = 0,
        limit: int = 50
    ) -> List[InterviewSession]:
        """
        List sessions with optional filters, filtered by organization.

        Args:
            organization_id: Organization to filter by
            candidate_id: Filter by candidate
            status: Filter by status
            mode: Filter by interview mode
            start: Offset for pagination
            limit: Maximum results (max 100)

        Returns:
            List of sessions matching filters
        """
        if limit > 100:
            limit = 100

        statement = select(InterviewSession).where(
            InterviewSession.organization_id == organization_id
        )

        if candidate_id:
            statement = statement.where(
                InterviewSession.candidate_id == candidate_id)
        if status:
            statement = statement.where(InterviewSession.status == status)
        if mode:
            statement = statement.where(InterviewSession.mode == mode)

        statement = statement.order_by(
            InterviewSession.created_at.desc()).offset(start).limit(limit)

        return list(self.db.exec(statement).all())

    def mark_completed(
        self,
        session_id: str,
        termination_reason: str,
        completeness_score: float
    ) -> Optional[InterviewSession]:
        """
        Mark a session as completed.

        Args:
            session_id: Session to complete
            termination_reason: Why it ended (complete, disengaged, no_gaps)
            completeness_score: Final completeness score

        Returns:
            Updated session, None if not found
        """
        session = self.get_by_id(session_id)
        if not session:
            return None

        session.status = "completed"
        session.termination_reason = termination_reason
        session.completeness_score = completeness_score
        session.completed_at = datetime.utcnow()

        return self.update(session)

    def increment_questions_asked(self, session_id: str) -> Optional[InterviewSession]:
        """
        Increment the questions_asked counter.

        Args:
            session_id: Session to update

        Returns:
            Updated session, None if not found
        """
        session = self.get_by_id(session_id)
        if not session:
            return None

        session.questions_asked += 1
        return self.update(session)

    def update_completeness_score(
        self,
        session_id: str,
        score: float
    ) -> Optional[InterviewSession]:
        """
        Update completeness score.

        Args:
            session_id: Session to update
            score: New completeness score (0.0 - 1.0)

        Returns:
            Updated session, None if not found
        """
        session = self.get_by_id(session_id)
        if not session:
            return None

        session.completeness_score = score
        return self.update(session)
