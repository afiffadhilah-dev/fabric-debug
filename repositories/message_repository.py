"""
Message repository for conversation persistence.

Handles CRUD operations for messages table with rich query support.
"""

from typing import List, Optional, Dict, Any
from sqlmodel import Session, select
from models.message import Message
from datetime import datetime


class MessageRepository:
    """Repository for managing conversation messages."""

    def __init__(self, db_session: Session):
        self.db = db_session

    def create(
        self,
        session_id: str,
        role: str,
        content: str,
        meta: Optional[Dict[str, Any]] = None
    ) -> Message:
        """
        Create a new message.

        Args:
            session_id: Interview session ID
            role: "user" or "assistant"
            content: Message text
            meta: Rich metadata dict (optional)

        Returns:
            Created Message instance
        """
        message = Message(
            session_id=session_id,
            role=role,
            content=content,
            meta=meta or {},
            created_at=datetime.utcnow()
        )

        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)

        return message

    def get_by_session(
        self,
        session_id: str,
        role: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Message]:
        """
        Get all messages for a session.

        Args:
            session_id: Interview session ID
            role: Optional filter by role ("user" or "assistant")
            limit: Optional limit number of messages

        Returns:
            List of messages ordered by created_at
        """
        query = select(Message).where(Message.session_id == session_id)

        if role:
            query = query.where(Message.role == role)

        query = query.order_by(Message.created_at)

        if limit:
            query = query.limit(limit)

        messages = self.db.exec(query).all()
        return list(messages)

    def get_recent_conversation(
        self,
        session_id: str,
        limit: int = 10
    ) -> List[Message]:
        """
        Get recent conversation history.

        Args:
            session_id: Interview session ID
            limit: Number of recent messages (default: 10)

        Returns:
            List of recent messages ordered by created_at DESC
        """
        query = (
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )

        messages = self.db.exec(query).all()
        # Reverse to get chronological order
        return list(reversed(messages))

    def get_questions(self, session_id: str) -> List[Message]:
        """
        Get all questions asked in a session.

        Args:
            session_id: Interview session ID

        Returns:
            List of assistant messages
        """
        return self.get_by_session(session_id, role="assistant")

    def get_answers(self, session_id: str) -> List[Message]:
        """
        Get all answers provided in a session.

        Args:
            session_id: Interview session ID

        Returns:
            List of user messages
        """
        return self.get_by_session(session_id, role="user")

    def get_disengaged_answers(self, session_id: str) -> List[Message]:
        """
        Get all disengaged answers in a session.

        Useful for analytics on disengagement patterns.

        Args:
            session_id: Interview session ID

        Returns:
            List of user messages marked as disengaged
        """
        messages = self.get_answers(session_id)
        return [
            msg for msg in messages
            if msg.meta.get("engagement_level") == "disengaged"
        ]

    def get_clarification_requests(self, session_id: str) -> List[Message]:
        """
        Get all clarification requests from user.

        Useful for analytics on question clarity.

        Args:
            session_id: Interview session ID

        Returns:
            List of user messages asking for clarification
        """
        messages = self.get_answers(session_id)
        return [
            msg for msg in messages
            if msg.meta.get("answer_type") == "clarification_request"
        ]

    def count_messages(self, session_id: str, role: Optional[str] = None) -> int:
        """
        Count messages in a session.

        Args:
            session_id: Interview session ID
            role: Optional filter by role

        Returns:
            Number of messages
        """
        query = select(Message).where(Message.session_id == session_id)

        if role:
            query = query.where(Message.role == role)

        return len(self.db.exec(query).all())

    def get_conversation_stats(self, session_id: str) -> Dict[str, Any]:
        """
        Get conversation statistics for analytics.

        Args:
            session_id: Interview session ID

        Returns:
            Dict with stats: total_messages, questions_asked, answers_given,
            disengaged_count, clarification_count, avg_detail_score, etc.
        """
        questions = self.get_questions(session_id)
        answers = self.get_answers(session_id)

        # Calculate detail scores
        detail_scores = [
            msg.meta.get("detail_score", 0)
            for msg in answers
            if msg.meta.get("detail_score")
        ]
        avg_detail_score = sum(detail_scores) / len(detail_scores) if detail_scores else 0

        # Count answer types
        answer_types = {}
        for msg in answers:
            answer_type = msg.meta.get("answer_type", "unknown")
            answer_types[answer_type] = answer_types.get(answer_type, 0) + 1

        return {
            "total_messages": len(questions) + len(answers),
            "questions_asked": len(questions),
            "answers_given": len(answers),
            "disengaged_count": len(self.get_disengaged_answers(session_id)),
            "clarification_count": len(self.get_clarification_requests(session_id)),
            "avg_detail_score": round(avg_detail_score, 2),
            "answer_types": answer_types
        }
