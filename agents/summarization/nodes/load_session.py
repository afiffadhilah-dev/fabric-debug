"""
Load session data node.

Loads interview session, candidate, and messages for a given session ID.
"""

from typing import Dict, Any, Optional
from sqlmodel import Session

from repositories.interview_session_repository import InterviewSessionRepository
from repositories.message_repository import MessageRepository
from repositories.candidate_repository import CandidateRepository


def get_all_data_for_session(session_id: str, db_session: Session, message_limit: Optional[int] = None) -> Dict[str, Any]:
    """
    Convenience helper that returns candidate, interview_session and messages.

    Returned dict keys: `interview_session`, `candidate`, `messages`.
    """
    interview_repo = InterviewSessionRepository(db_session)
    interview = interview_repo.get_by_id(session_id)
    
    if not interview:
        return {"interview_session": None, "candidate": None, "messages": []}

    candidate_repo = CandidateRepository(db_session)
    candidate = candidate_repo.get_by_id(interview.candidate_id)
    
    message_repo = MessageRepository(db_session)
    messages = message_repo.get_by_session(session_id, limit=message_limit)

    return {
        "interview_session": interview,
        "candidate": candidate,
        "messages": messages,
    }


class LoadSessionNode:
    def __init__(self, db_session):
        self.db = db_session

    def run(self, state):
        data = get_all_data_for_session(
            state["session_id"],
            self.db,
        )

        interview = data.get("interview_session")
        if not interview:
            raise ValueError(f"Interview session not found: {state['session_id']}")

        state["interview_session"] = interview
        state["candidate"] = data.get("candidate")
        state["messages"] = data.get("messages", [])
        state["resume_text"] = getattr(interview, "resume_text", None)

        return state
