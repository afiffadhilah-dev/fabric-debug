"""
Repositories module - Data Access Layer.

Provides repository classes for database operations following the Repository pattern.
Each repository handles CRUD operations for a specific domain entity.

Usage:
    from repositories import (
        MessageRepository,
        InterviewSessionRepository,
        APIKeyRepository
    )
    
    # Initialize with a database session
    session_repo = InterviewSessionRepository(db_session)
    message_repo = MessageRepository(db_session)
    
    # Use repository methods
    session = session_repo.get_by_id(session_id)
    messages = message_repo.get_by_session(session_id)
    skills = skill_repo.get_by_session(session_id)
"""

from repositories.base_repository import BaseRepository
from repositories.message_repository import MessageRepository
from repositories.interview_session_repository import InterviewSessionRepository
from repositories.api_key_repository import APIKeyRepository
from repositories.candidate_repository import CandidateRepository
from repositories.predefined_question_set_repository import PredefinedQuestionSetRepository
from repositories.extracted_skill_repository import ExtractedSkillRepository
from repositories.predefined_question_repository import PredefinedQuestionRepository

__all__ = [
    "BaseRepository",
    "MessageRepository",
    "InterviewSessionRepository",
    "APIKeyRepository",
    "CandidateRepository",
    "PredefinedQuestionSetRepository",
    "ExtractedSkillRepository"
    ,"PredefinedQuestionRepository"
]
