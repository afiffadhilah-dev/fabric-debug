"""
Interview Service - Business Logic Layer.

Owns all application concerns for interview operations:
- Session creation and lifecycle management
- Database persistence (messages, skills, sessions)
- Validation (modes, question sets)
- Streaming event processing
- Summarization triggering

Delegates only graph invocation to ConversationalInterviewService.
"""

from utils.language_config import WARNING_MESSAGES
import uuid
from uuid import UUID
from datetime import datetime
from typing import Dict, Any, Optional, List, AsyncGenerator
from fastapi import BackgroundTasks

from sqlmodel import Session

from models.interview_session import InterviewSession
from models.extracted_skill import ExtractedSkill
from models.candidate import Candidate
from repositories import (
    InterviewSessionRepository,
    MessageRepository,
    CandidateRepository,
    PredefinedQuestionSetRepository,
    ExtractedSkillRepository,
)
from agents.conversational.service import ConversationalInterviewService
from services.summarization_service import SummarizationService
from config.settings import settings
from utils.database import get_engine
from utils.llm_service import LLMService
from utils.prompt_loader import PromptLoader

from langchain_core.messages import AIMessageChunk



class InterviewService:
    """
    Application service for interview operations.

    Responsibilities:
    - Validate business rules (modes, question sets, resume text)
    - Create and manage InterviewSession lifecycle
    - Persist messages, extracted skills, session metrics
    - Process raw graph events into structured SSE events
    - Trigger post-interview summarization
    - Delegate graph invocation to ConversationalInterviewService
    """

    def __init__(
        self,
        db_session: Session,
        llm_service: Optional[LLMService] = None,
        prompt_loader: Optional[PromptLoader] = None
    ):
        self.db = db_session
        self.llm_service = llm_service or LLMService()
        self.prompt_loader = prompt_loader or PromptLoader()

        # Repositories
        self.session_repo = InterviewSessionRepository(db_session)
        self.message_repo = MessageRepository(db_session)
        self.candidate_repo = CandidateRepository(db_session)
        self.predefined_question_set_repo = PredefinedQuestionSetRepository(db_session)
        self.extracted_skill_repo = ExtractedSkillRepository(db_session)

        # Agent service (thin graph wrapper)
        self.agent_service = ConversationalInterviewService(
            self.llm_service,
            self.prompt_loader,
            db_session
        )

    # ============ INTERVIEW LIFECYCLE ============

    def start_interview(
        self,
        candidate_id: str,
        resume_text: str,
        organization_id: int,
        mode: str = "dynamic_gap",
        question_set_id: Optional[str] = None,
        language: Optional[str] = None,
        user_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Start a new interview session.

        Validates inputs, creates session, invokes graph, persists first question.

        Returns:
            Dict with session_id, thread_id, question
        """
        # Validate mode
        if mode not in ["dynamic_gap", "predefined_questions"]:
            raise ValueError(f"Invalid mode: {mode}. Must be 'dynamic_gap' or 'predefined_questions'")

        if mode == "dynamic_gap" and not resume_text:
            raise ValueError("resume_text is required for dynamic_gap mode")

        # Validate predefined mode requirements
        self._validate_predefined_mode(mode, question_set_id)

        # Ensure candidate exists
        self._ensure_candidate_exists(candidate_id, user_name=user_name)

        # Create interview session
        session_id = str(uuid.uuid4())
        thread_id = f"thread_{session_id}"
        session = InterviewSession(
            id=session_id,
            candidate_id=candidate_id,
            resume_text=resume_text,
            thread_id=thread_id,
            status="active",
            mode=mode,
            question_set_id=UUID(question_set_id) if question_set_id else None,
            language=language,
            organization_id=organization_id
        )
        session = self.session_repo.create(session)

        # Invoke graph
        result = self.agent_service.invoke_start(
            session_id=session.id,
            resume_text=resume_text,
            mode=mode,
            question_set_id=question_set_id,
            thread_id=thread_id,
            candidate_id=candidate_id,
            language=language
        )

        # Extract first question from last AI message
        last_message = result["messages"][-1] if result["messages"] else None
        question = last_message.content if last_message else "Tell me about your experience."

        # Save the first question to database
        self.message_repo.create(session.id, "assistant", question)

        # Update session with initial metrics
        session.questions_asked = result.get("questions_asked", 0)
        session.completeness_score = result.get("completeness_score", 0.0)
        self.session_repo.update(session)

        print(f"Started interview session {session.id} for candidate {candidate_id}")

        return {
            "session_id": session.id,
            "thread_id": thread_id,
            "question": question,
            "completeness_score": round(result.get("completeness_score", 0.0) * 100, 2)
        }

    def continue_interview(
        self,
        session_id: str,
        answer: str,
        organization_id: int,
        background_tasks=None
    ) -> Dict[str, Any]:
        """
        Continue an existing interview with a user answer.

        Returns:
            Dict with question, completed, termination_reason, completion_message,
            summarization_status, consecutive_low_quality, warning
        """
        session = self.session_repo.get_by_session_id(session_id=session_id, organization_id=organization_id)
        if not session:
            raise ValueError(f"No interview session found for session_id: {session_id}")

        # Invoke graph
        result = self.agent_service.invoke_continue(
            session_id=session.id,
            answer=answer,
            thread_id=session.thread_id,
            candidate_id=session.candidate_id
        )
        feedback = result.get("feedback")

        # Save user answer to database
        self.message_repo.create(session.id, "user", answer)

        # Update session metrics
        session.questions_asked = result.get("questions_asked", 0)
        session.completeness_score = result.get("completeness_score", 0.0)

        should_continue = result.get("should_continue", True)

        if not should_continue:
            # Interview completed
            session.status = "completed"
            session.termination_reason = result.get("termination_reason", "unknown")
            session.completed_at = datetime.utcnow()

            # Persist interview summary (from finalize_node) - skip tracking
            interview_summary = result.get("interview_summary", {})
            if interview_summary:
                session.questions_answered = interview_summary.get("questions_answered")
                session.questions_skipped = interview_summary.get("questions_skipped")
                # Store skipped_categories as JSON string
                import json
                skipped_categories = interview_summary.get("skipped_categories", [])
                session.skipped_categories = json.dumps(skipped_categories) if skipped_categories else None

            # Persist extracted skills
            self._persist_extracted_skills(session.id, result.get("extracted_skills", []))

            self.session_repo.update(session)

            # Get completion message
            last_message = result["messages"][-1] if result["messages"] else None
            completion_message = last_message.content if last_message else "Thank you!"

            # Save completion message
            self.message_repo.create(session.id, "assistant", completion_message)

            # Trigger background summarization
            task_id = self._trigger_summarization(session.id, background_tasks, session)

            print(f"Interview {session.id} completed: {session.termination_reason}")

            return {
                "question": None,
                "completed": True,
                "termination_reason": session.termination_reason,
                "completion_message": completion_message,
                "summarization_task_id": task_id,
                "consecutive_low_quality": result.get("consecutive_low_quality", 0),
                "completeness_score": round(result.get("completeness_score", 0.0) * 100, 2)
            }
        else:
            # Continue interview
            self.session_repo.update(session)

            last_message = result["messages"][-1] if result["messages"] else None
            question = last_message.content if last_message else "Can you elaborate?"

            self.message_repo.create(session.id, "assistant", question)
            self.db.commit()

            warning = ""
            if result.get("consecutive_low_quality", 0) >= 2:
                language = result.get("language")
                lang_key = (language or "en").lower()
                warning = WARNING_MESSAGES.get(lang_key, WARNING_MESSAGES["en"])

            return {
                "question": question,
                "completed": False,
                "termination_reason": None,
                "warning": warning,
                "feedback": feedback,
                "consecutive_low_quality": result.get("consecutive_low_quality", 0),
                "completeness_score": round(result.get("completeness_score", 0.0) * 100, 2)
            }

    # ============ STREAMING METHODS ============

    # Node status messages for user-friendly feedback
    _NODE_STATUS_MESSAGES = {
        "identify_gaps": "Analyzing resume for skill gaps...",
        "select_gap": "Selecting next topic to explore...",
        "parse_answer": "Processing your answer...",
        "update_state": "Updating interview progress...",
        "generate_question": "Generating question...",
        "generate_follow_up": "Generating follow-up question...",
        "finalize": "Completing interview...",
    }

    # Nodes that generate human-readable questions (stream tokens from these)
    _QUESTION_NODES = {"generate_question", "generate_follow_up"}

    async def start_interview_stream(
        self,
        candidate_id: str,
        resume_text: str,
        mode: str = "dynamic_gap",
        question_set_id: Optional[str] = None,
        language: Optional[str] = None,
        user_name: Optional[str] = None,
        organization_id: int = None,
        background_tasks=None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Start a new interview session with SSE streaming.

        Yields structured events: session, node, token, status, progress, complete, error.
        """
        # Validate mode
        if mode not in ["dynamic_gap", "predefined_questions"]:
            yield {"event": "error", "data": {"detail": f"Invalid mode: {mode}"}}
            return

        # Validate predefined mode
        if mode == "predefined_questions":
            if not question_set_id:
                yield {"event": "error", "data": {"detail": "question_set_id is required for predefined_questions mode"}}
                return
            question_set = self.predefined_question_set_repo.get_by_id(UUID(question_set_id))
            if not question_set:
                yield {"event": "error", "data": {"detail": f"Question set {question_set_id} not found"}}
                return
            if not question_set.questions:
                yield {"event": "error", "data": {"detail": f"Question set {question_set_id} has no questions"}}
                return

        # Ensure candidate exists
        self._ensure_candidate_exists(candidate_id, user_name=user_name)

        # Create interview session
        session_id = str(uuid.uuid4())
        thread_id = f"thread_{session_id}"
        session = InterviewSession(
            id=session_id,
            candidate_id=candidate_id,
            resume_text=resume_text,
            thread_id=thread_id,
            status="active",
            mode=mode,
            question_set_id=UUID(question_set_id) if question_set_id else None,
            language=language,
            organization_id=organization_id
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)

        # Yield session info immediately
        yield {"event": "session", "data": {"session_id": str(session.id)}}

        final_question = None

        try:
            async for event in self.agent_service.astream_start(
                session_id=session.id,
                resume_text=resume_text,
                mode=mode,
                question_set_id=question_set_id,
                thread_id=thread_id,
                candidate_id=candidate_id,
                language=language
            ):
                result = self._process_stream_event(event, background_tasks, session)
                if result:
                    for evt in result["events"]:
                        yield evt
                    if result.get("question"):
                        final_question = result["question"]

            # Get final state for question if not captured during streaming
            if not final_question:
                state = await self.agent_service.aget_state(thread_id)
                if state and state.values:
                    messages = state.values.get("messages", [])
                    if messages:
                        final_question = messages[-1].content if hasattr(messages[-1], 'content') else "Tell me about your experience."

            # Update session with initial metrics (fresh session — original may be stale)
            state = await self.agent_service.aget_state(thread_id)
            if state and state.values:
                with Session(get_engine()) as fresh_db:
                    fresh_session = fresh_db.get(InterviewSession, session.id)
                    if fresh_session:
                        fresh_session.questions_asked = state.values.get("questions_asked", 0)
                        fresh_session.completeness_score = state.values.get("completeness_score", 0.0)
                        fresh_db.commit()

            yield {
                "event": "complete",
                "data": {
                    "session_id": str(session.id),
                    "question": final_question or "Tell me about your experience.",
                    "completed": False,
                    "completeness_score": round(state.values.get("completeness_score", 0.0) * 100, 2) if state and state.values else 0.0
                }
            }

        except Exception as e:
            import traceback
            error_msg = str(e) if str(e) else f"{type(e).__name__}: {traceback.format_exc()}"
            print(f"[STREAM ERROR] {error_msg}")
            yield {"event": "error", "data": {"detail": error_msg}}

    async def continue_interview_stream(
        self,
        session_id: str,
        answer: str,
        organization_id: int = None,
        background_tasks=None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Continue an existing interview with SSE streaming.

        Yields structured events: node, progress, token, status, complete, error.
        """
        session = self.session_repo.get_by_id(session_id)
        if not session:
            yield {"event": "error", "data": {"detail": f"No interview session found for session_id: {session_id}"}}
            return

        if session.organization_id != organization_id:
            yield {"event": "error", "data": {"detail": "Unauthorized access to this interview session"}}
            return

        thread_id = session.thread_id
        final_question = None
        should_continue = True
        termination_reason = None
        completion_message = None

        try:
            async for event in self.agent_service.astream_continue(
                session_id=session.id,
                answer=answer,
                thread_id=thread_id,
                candidate_id=session.candidate_id
            ):
                result = self._process_stream_event(event, background_tasks, session, check_finalize=True)
                if result:
                    for evt in result["events"]:
                        yield evt
                    if result.get("question"):
                        final_question = result["question"]
                    if result.get("finalized"):
                        should_continue = False
                        termination_reason = result.get("termination_reason", "complete")
                        completion_message = result.get("completion_message")

            # Get final state
            state = await self.agent_service.aget_state(thread_id)
            if state and state.values:
                should_continue = state.values.get("should_continue", True)

                if not final_question and should_continue:
                    messages = state.values.get("messages", [])
                    if messages:
                        final_question = messages[-1].content if hasattr(messages[-1], 'content') else "Can you elaborate?"

                if not should_continue:
                    termination_reason = state.values.get("termination_reason", "complete")
                    messages = state.values.get("messages", [])
                    if messages and not completion_message:
                        completion_message = messages[-1].content if hasattr(messages[-1], 'content') else None

            # Update session metrics (fresh session — original may be stale after long SSE stream)
            if state and state.values:
                with Session(get_engine()) as fresh_db:
                    fresh_session = fresh_db.get(InterviewSession, session.id)
                    if fresh_session:
                        fresh_session.questions_asked = state.values.get("questions_asked", 0)
                        fresh_session.completeness_score = state.values.get("completeness_score", 0.0)

                        if not should_continue:
                            fresh_session.status = "completed"
                            fresh_session.termination_reason = termination_reason
                            fresh_session.completed_at = datetime.utcnow()

                            extracted_skills = state.values.get("extracted_skills", []) if state and state.values else []
                            self._persist_extracted_skills_with_session(fresh_db, fresh_session.id, extracted_skills)

                        fresh_db.commit()

            if not should_continue:
                # Queue background summarization
                task_id = self._trigger_summarization(session.id, background_tasks, session)

                yield {
                    "event": "complete",
                    "data": {
                        "session_id": str(session.id),
                        "question": None,
                        "completed": True,
                        "termination_reason": termination_reason,
                        "completion_message": completion_message,
                        "summarization_task_id": task_id,
                        "completeness_score": round(state.values.get("completeness_score", 0.0) * 100, 2) if state and state.values else 0.0
                    }
                }
            else:

                warning = ""
                if state.values.get("consecutive_low_quality", 0) >= 2:
                    language = state.values.get("language")
                    lang_key = (language or "en").lower()
                    warning = WARNING_MESSAGES.get(lang_key, WARNING_MESSAGES["en"])

                yield {
                    "event": "complete",
                    "data": {
                        "question": final_question or "Can you elaborate?",
                        "completed": False,
                        "warning": warning,
                        "completeness_score": round(state.values.get("completeness_score", 0.0) * 100, 2) if state and state.values else 0.0
                    }
                }

        except Exception as e:
            import traceback
            error_msg = str(e) if str(e) else f"{type(e).__name__}: {traceback.format_exc()}"
            print(f"[STREAM ERROR] {error_msg}")
            yield {"event": "error", "data": {"detail": error_msg}}

    # ============ SESSION QUERIES ============

    def get_session(self, session_id: str, organization_id: int) -> Optional[InterviewSession]:
        """Get interview session by ID, verifying organization access."""
        session = self.session_repo.get_by_id(session_id)
        if session and session.organization_id != organization_id:
            raise ValueError("Unauthorized access to this interview session")
        return session

    def get_session_by_thread(self, thread_id: str, organization_id: int) -> Optional[InterviewSession]:
        """Get session by LangGraph thread ID, filtered by organization."""
        return self.session_repo.get_by_thread_id(thread_id, organization_id)

    def list_sessions(
        self,
        organization_id: int,
        candidate_id: Optional[str] = None,
        status: Optional[str] = None,
        mode: Optional[str] = None,
        start: int = 0,
        limit: int = 50
    ) -> List[InterviewSession]:
        """List sessions with optional filters, filtered by organization."""
        return self.session_repo.list_sessions(
            organization_id=organization_id,
            candidate_id=candidate_id,
            status=status,
            mode=mode,
            start=start,
            limit=limit
        )

    # ============ MESSAGE QUERIES ============

    def get_checkpoint_messages(self, thread_id: str) -> List[Dict[str, Any]]:
        """
        Get full conversation from LangGraph checkpoint.

        Returns list of message dicts with role and content.
        """
        try:
            state = self.agent_service.get_state(thread_id)

            if not state or not state.values:
                return []

            messages = state.values.get("messages", [])

            result = []
            for msg in messages:
                if hasattr(msg, 'type'):
                    role = "assistant" if msg.type == "ai" else "user"
                    result.append({
                        "role": role,
                        "content": msg.content,
                    })

            return result

        except Exception as e:
            print(f"Failed to get checkpoint messages: {e}")
            raise

    # ============ SKILL QUERIES ============

    def get_extracted_skills(self, session_id: str) -> List[Dict[str, Any]]:
        """Retrieve all extracted skills for a session."""
        skills = self.extracted_skill_repo.get_by_session(session_id)

        return [
            {
                "name": skill.name,
                "confidence_score": skill.confidence_score,
                "duration": skill.duration,
                "depth": skill.depth,
                "autonomy": skill.autonomy,
                "scale": skill.scale,
                "constraints": skill.constraints,
                "production_vs_prototype": skill.production_vs_prototype,
                "evidence": skill.evidence
            }
            for skill in skills
        ]

    # ============ HELPER METHODS ============

    def _ensure_candidate_exists(
        self,
        candidate_id: str,
        user_name: Optional[str] = None
    ) -> Candidate:
        """Ensure candidate exists, create if not, and update name when provided."""
        candidate = self.candidate_repo.get_by_id(candidate_id)
        if candidate:
            if user_name and candidate.name != user_name:
                candidate.name = user_name
                candidate = self.candidate_repo.update(candidate)
            return candidate

        return self.candidate_repo.get_or_create(candidate_id, name=user_name)

    def _validate_predefined_mode(
        self,
        mode: str,
        question_set_id: Optional[str]
    ) -> None:
        """Validate predefined_questions mode requirements."""
        if mode != "predefined_questions":
            return

        if not question_set_id:
            raise ValueError("question_set_id is required when mode='predefined_questions'")

        question_set = self.predefined_question_set_repo.get_by_id(UUID(question_set_id))
        if not question_set:
            raise ValueError(
                f"Question set {question_set_id} not found. "
                "Please verify the question set ID or create it first."
            )

        if not question_set.questions:
            raise ValueError(
                f"Question set {question_set_id} has no questions. "
                "Please add questions before starting interview."
            )

        print(f"Using question set: {question_set.name} (v{question_set.version}) with {len(question_set.questions)} questions")

    def _persist_extracted_skills_with_session(
        self,
        db: Session,
        session_id: str,
        skills: List[Dict[str, Any]]
    ) -> None:
        """Persist extracted skills using a provided DB session (for streaming endpoints)."""
        for skill_data in skills:
            skill = ExtractedSkill(
                session_id=session_id,
                name=skill_data["name"],
                confidence_score=skill_data.get("confidence_score", 1.0),
                duration=skill_data.get("duration"),
                depth=skill_data.get("depth"),
                autonomy=skill_data.get("autonomy"),
                scale=skill_data.get("scale"),
                constraints=skill_data.get("constraints"),
                production_vs_prototype=skill_data.get("production_vs_prototype"),
                evidence=skill_data.get("evidence", "")
            )
            db.add(skill)
        print(f"Persisted {len(skills)} skills for session {session_id}")

    def _persist_extracted_skills(
        self,
        session_id: str,
        skills: List[Dict[str, Any]]
    ) -> None:
        """Persist extracted skills to database."""
        for skill_data in skills:
            skill = ExtractedSkill(
                session_id=session_id,
                name=skill_data["name"],
                confidence_score=skill_data.get("confidence_score", 1.0),
                duration=skill_data.get("duration"),
                depth=skill_data.get("depth"),
                autonomy=skill_data.get("autonomy"),
                scale=skill_data.get("scale"),
                constraints=skill_data.get("constraints"),
                production_vs_prototype=skill_data.get("production_vs_prototype"),
                evidence=skill_data.get("evidence", "")
            )
            self.extracted_skill_repo.create(skill)

        print(f"Persisted {len(skills)} skills for session {session_id}")

    def _trigger_summarization(self, session_id: str, background_tasks, session=None):
        """Trigger background summarization after interview finalization."""
        if not background_tasks:
            return None
        if not settings.AUTO_SUMMARIZE:
            print(f"[Summarization] Auto-summarize disabled, skipping for session {session_id}")
            return None
        try:
            summarization_service = SummarizationService()
            task_result = summarization_service.analyze_session_async(
                background_tasks=background_tasks,
                session_id=session_id,
                mode="SELF_REPORT"
            )
            return task_result.get("task_id")
        except Exception as e:
            print(f"Failed to queue summarization for session {session_id}: {e}")
            return None

    def _process_stream_event(
        self,
        event: Any,
        background_tasks,
        session,
        check_finalize: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Process a raw LangGraph stream event into structured SSE events.

        Returns dict with:
        - events: list of SSE event dicts to yield
        - question: captured question text (if any)
        - finalized: whether finalize node was hit (if check_finalize)
        - termination_reason: reason (if finalized)
        - completion_message: message (if finalized)
        """
        events = []
        question = None
        finalized = False
        termination_reason = None
        completion_message = None

        if isinstance(event, tuple):
            mode_type, data = event

            if mode_type == "messages":
                if isinstance(data, tuple) and len(data) >= 2:
                    msg_chunk, metadata = data
                    token_node = metadata.get("langgraph_node", "")

                    if (
                        token_node in self._QUESTION_NODES
                        and isinstance(msg_chunk, AIMessageChunk)
                        and msg_chunk.content
                    ):
                        events.append({
                            "event": "token",
                            "data": {"content": msg_chunk.content}
                        })

            elif mode_type == "updates":
                if isinstance(data, dict):
                    for node_name, node_output in data.items():
                        if node_output is None:
                            continue

                        if node_name in self._NODE_STATUS_MESSAGES:
                            events.append({
                                "event": "status",
                                "data": {
                                    "message": self._NODE_STATUS_MESSAGES[node_name],
                                }
                            })

                        events.append({
                            "event": "node",
                            "data": {"node": node_name, "status": "complete"}
                        })

                        if node_name in self._QUESTION_NODES:
                            messages = node_output.get("messages", [])
                            if messages:
                                question = messages[-1].content if hasattr(messages[-1], 'content') else str(messages[-1])

                        if check_finalize and node_name == "finalize":
                            finalized = True
                            termination_reason = node_output.get("termination_reason", "complete")
                            messages = node_output.get("messages", [])
                            if messages:
                                completion_message = messages[-1].content if hasattr(messages[-1], 'content') else None
                            # Trigger summarization when interview is finalized
                            self._trigger_summarization(session.id, background_tasks, session)

            elif mode_type == "custom":
                if isinstance(data, dict):
                    if "feedback" in data:
                        events.append({"event": "feedback", "data": data})
                    else:
                        events.append({"event": "progress", "data": data})

        else:
            # Legacy format
            if isinstance(event, dict):
                for node_name, node_output in event.items():
                    if node_output is None:
                        continue
                    if node_name in self._NODE_STATUS_MESSAGES:
                        events.append({
                            "event": "status",
                            "data": {
                                "message": self._NODE_STATUS_MESSAGES[node_name],
                                "node": node_name
                            }
                        })

                    events.append({
                        "event": "node",
                        "data": {"node": node_name, "status": "complete"}
                    })

                    if node_name in self._QUESTION_NODES:
                        messages = node_output.get("messages", [])
                        if messages:
                            question = messages[-1].content if hasattr(messages[-1], 'content') else str(messages[-1])

                    if check_finalize and node_name == "finalize":
                        finalized = True
                        termination_reason = node_output.get("termination_reason", "complete")
                        # Trigger summarization when interview is finalized
                        self._trigger_summarization(session.id, background_tasks, session)

        if not events and not question and not finalized:
            return None

        result = {"events": events}
        if question:
            result["question"] = question
        if finalized:
            result["finalized"] = True
            result["termination_reason"] = termination_reason
            result["completion_message"] = completion_message
        return result
