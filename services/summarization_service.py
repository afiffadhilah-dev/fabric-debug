from typing import Optional, Dict, Any
from sqlmodel import Session
from fastapi import BackgroundTasks
from utils.database import get_engine
import json
from datetime import datetime

from config.settings import settings
from agents.summarization.orchestrator import summarize_session, summarize_session_profile_context
from agents.summarization.profile.profile_summary_agent import ProfileSummaryAgent
from agents.summarization.profile.session_profile_summary_agent import SessionProfileSummaryAgent
from repositories.candidate_profile_repository import CandidateProfileSummaryRepository
from repositories.candidate_profile_data_repository import CandidateProfileDataRepository
from repositories.background_task_repository import BackgroundTaskRepository


class SummarizationService:
    """
    Public summarization service.
    Provides multiple independent summarization entry points.
    """

    def __init__(self):
        self._profile_agent = ProfileSummaryAgent()

    # -------------------------
    # Synchronous methods with internal task tracking
    # -------------------------

    def analyze_session(self, session_id: str, mode: str = "SELF_REPORT", task_id: Optional[str] = None):
        """
        Analyze an interview session and persist results to the database.
        
        If task_id is provided, updates task status in database.
        Can be called directly (task_id=None) or from async context (task_id provided).
        
        Args:
            session_id: Interview session ID
            mode: Interview mode (default: "SELF_REPORT")
            task_id: Optional task ID for tracking (set by async methods)
        """
        engine = get_engine()
        
        try:
            # Update task to PENDING if tracking
            if task_id:
                with Session(engine) as db:
                    task_repo = BackgroundTaskRepository(db)
                    task_repo.update_status(task_id, "PENDING")

            # Execute the actual summarization
            result = summarize_session(session_id=session_id, mode=mode)

            # Mark as SUCCESS if tracking
            if task_id:
                with Session(engine) as db:
                    task_repo = BackgroundTaskRepository(db)
                    task_repo.update_status(
                        task_id,
                        "SUCCESS",
                        result=json.dumps(result or {})
                    )

            return result

        except Exception as e:
            # Mark as FAILED if tracking
            if task_id:
                with Session(engine) as db:
                    task_repo = BackgroundTaskRepository(db)
                    task_repo.update_status(
                        task_id,
                        "FAILED",
                        error_message=str(e)
                    )
            raise

    # -------------------------
    # New behavior
    # -------------------------

    def summarize_candidate_profile(self, candidate_id: str, task_id: Optional[str] = None) -> str:
        """
        Summarize a candidate's profile based on DB data only.
        
        If task_id is provided, updates task status in database.
        Can be called directly (task_id=None) or from async context (task_id provided).
        
        Args:
            candidate_id: Candidate ID
            task_id: Optional task ID for tracking (set by async methods)
        """
        if not candidate_id:
            raise ValueError("candidate_id is required")

        engine = get_engine()
        
        try:
            # Update task to PENDING if tracking
            if task_id:
                with Session(engine) as db:
                    task_repo = BackgroundTaskRepository(db)
                    task_repo.update_status(task_id, "PENDING")

            # Execute the actual summarization
            result = self._profile_agent.summarize(candidate_id)

            # Mark as SUCCESS if tracking
            if task_id:
                with Session(engine) as db:
                    task_repo = BackgroundTaskRepository(db)
                    task_repo.update_status(
                        task_id,
                        "SUCCESS",
                        result=json.dumps({"summary": result} if result else {})
                    )

            return result

        except Exception as e:
            # Mark as FAILED if tracking
            if task_id:
                with Session(engine) as db:
                    task_repo = BackgroundTaskRepository(db)
                    task_repo.update_status(
                        task_id,
                        "FAILED",
                        error_message=str(e)
                    )
            raise

    def get_candidate_profile_summary(
        self,
        candidate_id: str,
        summary_type: str = "GENERAL",
    ) -> str:
        """
        Retrieve a candidate's profile summary from the database.

        If the summary doesn't exist, it will:
        1. Find the most recent interview session for the candidate
        2. Generate a profile summary
        3. Persist and return the summary

        Args:
            candidate_id: The candidate ID
            summary_type: Type of summary to retrieve (default: "GENERAL")

        Returns:
            The profile summary text

        Raises:
            ValueError: If candidate_id is missing, no interview session exists,
                        or summary generation fails
        """
        if not candidate_id:
            raise ValueError("candidate_id is required")

        engine = get_engine()

        # 1. Try to fetch an existing summary
        with Session(engine) as db:
            repo = CandidateProfileSummaryRepository(db)
            existing_summary = repo.get_by_candidate_and_type(
                candidate_id=candidate_id,
                summary_type=summary_type,
            )

            if existing_summary is not None:
                return existing_summary.summary

        # 2. No existing summary → generate one
        generated_summary = self.summarize_candidate_profile(candidate_id)

        if not generated_summary:
            raise ValueError(
                f"Failed to generate profile summary for candidate_id={candidate_id}"
            )

        return generated_summary

    def get_candidate_profile(self, candidate_id: str) -> Dict[str, Any]:
        """
        Retrieve a candidate's complete profile from the database in JSON format.
        
        The profile includes:
        - candidate info
        - skills with dimensions
        - behavioral observations
        - aspirations
        - confirmed gaps
        - constraints
        - evidence
        - followup flags
        - potential indicators
        - present state
        - risk notes
        - domain contexts
        - infrastructure contexts
        
        Args:
            candidate_id: The candidate ID
        
        Returns:
            A dictionary containing the candidate's complete profile
        
        Raises:
            ValueError: If candidate_id is not provided
        """
        if not candidate_id:
            raise ValueError("candidate_id is required")
        
        engine = get_engine()

        with Session(engine) as db:
            repo = CandidateProfileDataRepository(db)
            profile = repo.get_candidate_profile(candidate_id)
        
        return profile

    # -------------------------
    # ASYNC INTENT: Dispatch FastAPI Background Tasks
    # -------------------------
    # These methods dispatch FastAPI background tasks and return immediately.
    # Task creation and tracking is handled internally by the service.

    def analyze_session_async(
        self,
        background_tasks: BackgroundTasks,
        session_id: str,
        mode: str = "SELF_REPORT",
    ) -> Dict[str, str]:
        """
        Dispatch a background task to analyze (summarize) an interview session asynchronously.

        Task creation and status tracking are handled internally.
        
        Called by: API endpoints, conversational agents, schedulers
        Returns: Task ID and confirmation message

        Args:
            background_tasks: FastAPI BackgroundTasks instance
            session_id: Interview session ID
            mode: Interview mode (default: "SELF_REPORT")

        Returns:
            Dictionary with task_id and status message
        """
        if not session_id:
            raise ValueError("session_id is required")

        # Check for existing task for this session
        engine = get_engine()
        with Session(engine) as db:
            task_repo = BackgroundTaskRepository(db)
            existing_tasks = task_repo.get_by_entity(
                related_entity_type="interview_session",
                related_entity_id=session_id
            )
            # Check if there's an existing active task
            for task in existing_tasks:
                if task.status in ["INITIATED", "PENDING"]:
                    return {
                        "task_id": task.id,
                        "status": task.status,
                        "message": f"Session analysis already queued for session {session_id}",
                    }

        # Create task record in database
        with Session(engine) as db:
            task_repo = BackgroundTaskRepository(db)
            task = task_repo.create_task(
                task_type="session_summarization",
                related_entity_type="interview_session",
                related_entity_id=session_id,
            )
            task_id = task.id

        # Queue background task with task tracking
        background_tasks.add_task(
            self.analyze_session,
            session_id=session_id,
            mode=mode,
            task_id=task_id,
        )

        return {
            "task_id": task_id,
            "status": "task_queued",
            "message": f"Session analysis queued for session {session_id}",
        }

    def summarize_profile_async(
        self,
        background_tasks: BackgroundTasks,
        candidate_id: str,
        summary_type: str = "GENERAL",
    ) -> Dict[str, str]:
        """
        Dispatch a background task to summarize a candidate's profile asynchronously.
        
        Task creation and status tracking are handled internally.
        
        Called by: API endpoints, agents, schedulers
        Returns: Task ID and confirmation message
        
        Args:
            background_tasks: FastAPI BackgroundTasks instance
            candidate_id: Candidate ID
            summary_type: Type of summary to generate (default: "GENERAL")
        
        Returns:
            Dictionary with task_id and status message
        """
        if not candidate_id:
            raise ValueError("candidate_id is required")

        # Create task record in database
        engine = get_engine()
        with Session(engine) as db:
            task_repo = BackgroundTaskRepository(db)
            task = task_repo.create_task(
                task_type="profile_summarization",
                related_entity_type="candidate",
                related_entity_id=candidate_id,
            )
            task_id = task.id

        # Queue background task with task tracking
        background_tasks.add_task(
            self.summarize_candidate_profile,
            candidate_id=candidate_id,
            task_id=task_id,
        )
        
        return {
            "task_id": task_id,
            "status": "task_queued",
            "message": f"Profile summarization queued for candidate {candidate_id}",
        }

    def summarize_session_profile(self, session_id: str, mode: str = "SELF_REPORT", task_id: Optional[str] = None) -> str:
        """
        Generate and persist a long-form candidate profile summary using all context from a session (skills, behaviors, infra, domain, resume, conversation).
        Only the final summary is persisted to candidate_profile_summary.
        Supports BackgroundTask tracking.
        """
        try:
            # Update task to PENDING if tracking
            if task_id:
                engine = get_engine()
                with Session(engine) as db:
                    task_repo = BackgroundTaskRepository(db)
                    task_repo.update_status(task_id, "PENDING")

            # Run the graph up to domain_node to get all context
            state = summarize_session_profile_context(session_id=session_id, mode=mode)
            candidate_id = state.get("candidate_id")
            if not candidate_id:
                raise ValueError("candidate_id could not be determined from session")

            agent = SessionProfileSummaryAgent()
            summary = agent.summarize_and_persist(candidate_id, session_id, state)

            # Mark as SUCCESS if tracking
            if task_id:
                engine = get_engine()
                with Session(engine) as db:
                    task_repo = BackgroundTaskRepository(db)
                    task_repo.update_status(
                        task_id,
                        "SUCCESS",
                        result=json.dumps({"summary": summary} if summary else {})
                    )

            return summary

        except Exception as e:
            # Mark as FAILED if tracking
            if task_id:
                engine = get_engine()
                with Session(engine) as db:
                    task_repo = BackgroundTaskRepository(db)
                    task_repo.update_status(
                        task_id,
                        "FAILED",
                        error_message=str(e)
                    )
            raise

    def summarize_session_profile_async(
        self,
        background_tasks: BackgroundTasks,
        session_id: str,
        mode: str = "SELF_REPORT",
    ) -> Dict[str, str]:
        """
        Dispatch a background task to summarize a session profile asynchronously.
        Task creation and status tracking are handled internally.
        """
        if not session_id:
            raise ValueError("session_id is required")

        # Create task record in database
        engine = get_engine()
        with Session(engine) as db:
            task_repo = BackgroundTaskRepository(db)
            task = task_repo.create_task(
                task_type="session_profile_summarization",
                related_entity_type="interview_session",
                related_entity_id=session_id,
            )
            task_id = task.id

        # Queue background task with task tracking
        background_tasks.add_task(
            self.summarize_session_profile,
            session_id=session_id,
            mode=mode,
            task_id=task_id,
        )

        return {
            "task_id": task_id,
            "status": "task_queued",
            "message": f"Session profile summarization queued for session {session_id}",
        }


