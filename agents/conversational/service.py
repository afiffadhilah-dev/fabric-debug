"""
Conversational Agent - Thin Graph Wrapper.

Provides a minimal interface to the LangGraph interview workflow.
All application concerns (session management, persistence, streaming
event processing, summarization) live in services/interview_service.py.

This service handles:
- Graph creation and checkpointer management
- Langfuse observability integration
- Sync/async graph invocation and streaming
- Graph state retrieval
"""

from typing import Dict, Any, Optional, List, AsyncGenerator
from sqlmodel import Session
from langchain_core.messages import HumanMessage
from langfuse.langchain import CallbackHandler

from utils.llm_service import LLMService
from utils.prompt_loader import PromptLoader
from utils.langfuse_config import is_langfuse_enabled
from agents.conversational.graph import create_interview_graph
from agents.conversational.checkpointer import get_postgres_checkpointer, get_async_postgres_checkpointer
from agents.conversational.state import create_initial_state
from repositories import PredefinedQuestionRepository


class ConversationalInterviewService:
    """
    Thin wrapper around the LangGraph interview graph.

    Manages graph lifecycle (creation, checkpointing, observability)
    and exposes invoke/stream/state methods. Does not own any
    application logic (sessions, persistence, validation).
    """

    def __init__(
        self,
        llm_service: LLMService,
        prompt_loader: PromptLoader,
        db_session: Session
    ):
        self.llm_service = llm_service
        self.prompt_loader = prompt_loader
        self.db_session = db_session
        self.predefined_question_repo = PredefinedQuestionRepository(db_session)

        # Create graph with PostgreSQL checkpointer (singleton)
        self.checkpointer = get_postgres_checkpointer()
        self.graph = create_interview_graph(
            checkpointer=self.checkpointer,
            predefined_question_repo=self.predefined_question_repo,
        )

        # Async graph will be lazily initialized for streaming
        self._async_graph = None

    async def _get_async_graph(self):
        """
        Get or create the async graph for streaming operations.

        Uses AsyncPostgresSaver which supports graph.astream().
        Lazily initialized on first streaming call.
        """
        if self._async_graph is None:
            async_checkpointer = await get_async_postgres_checkpointer()
            self._async_graph = create_interview_graph(
                checkpointer=async_checkpointer,
                predefined_question_repo=self.predefined_question_repo,
            )
        return self._async_graph

    def _get_langfuse_handler(self) -> Optional[CallbackHandler]:
        """Get Langfuse callback handler if observability is enabled."""
        if not is_langfuse_enabled():
            return None

        try:
            return CallbackHandler()
        except Exception as e:
            print(f"Failed to create Langfuse handler: {e}")
            return None

    # ============ CONFIG ============

    def _build_config(
        self,
        thread_id: str,
        session_id: str,
        candidate_id: str,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Build LangGraph config dict with Langfuse tracing."""
        langfuse_handler = self._get_langfuse_handler()
        return {
            "configurable": {"thread_id": thread_id},
            "callbacks": [langfuse_handler] if langfuse_handler else [],
            "metadata": {
                "langfuse_session_id": session_id,
                "langfuse_user_id": candidate_id,
                "langfuse_tags": tags or []
            }
        }

    # ============ SYNC INVOCATION ============

    def invoke_start(
        self,
        session_id: str,
        resume_text: str,
        mode: str,
        question_set_id: Optional[str],
        thread_id: str,
        candidate_id: str,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Invoke graph for the first iteration (resume analysis + first question).

        Returns raw graph result state dict.
        """
        initial_state = create_initial_state(
            session_id, resume_text, mode=mode, question_set_id=question_set_id,
            language=language
        )
        config = self._build_config(
            thread_id, session_id, candidate_id,
            tags=["conversational", "interview", "start"]
        )
        return self.graph.invoke(initial_state, config)

    def invoke_continue(
        self,
        session_id: str,
        answer: str,
        thread_id: str,
        candidate_id: str
    ) -> Dict[str, Any]:
        """
        Invoke graph with a user answer.

        Returns raw graph result state dict.
        """
        config = self._build_config(
            thread_id, session_id, candidate_id,
            tags=["conversational", "interview", "continue"]
        )
        return self.graph.invoke(
            {"messages": [HumanMessage(content=answer)]},
            config
        )

    # ============ ASYNC STREAMING ============

    async def astream_start(
        self,
        session_id: str,
        resume_text: str,
        mode: str,
        question_set_id: Optional[str],
        thread_id: str,
        candidate_id: str,
        language: Optional[str] = None
    ) -> AsyncGenerator:
        """
        Async-stream graph for the first iteration.

        Yields raw LangGraph events from astream with multiple modes.
        """
        initial_state = create_initial_state(
            session_id, resume_text, mode=mode, question_set_id=question_set_id,
            language=language
        )
        config = self._build_config(
            thread_id, session_id, candidate_id,
            tags=["conversational", "interview", "start", "streaming"]
        )
        async_graph = await self._get_async_graph()
        async for event in async_graph.astream(
            initial_state, config, stream_mode=["messages", "updates", "custom"]
        ):
            yield event

    async def astream_continue(
        self,
        session_id: str,
        answer: str,
        thread_id: str,
        candidate_id: str
    ) -> AsyncGenerator:
        """
        Async-stream graph with a user answer.

        Yields raw LangGraph events from astream with multiple modes.
        """
        config = self._build_config(
            thread_id, session_id, candidate_id,
            tags=["conversational", "interview", "continue", "streaming"]
        )
        async_graph = await self._get_async_graph()
        async for event in async_graph.astream(
            {"messages": [HumanMessage(content=answer)]},
            config, stream_mode=["messages", "updates", "custom"]
        ):
            yield event

    # ============ STATE ACCESS ============

    def get_state(self, thread_id: str):
        """Get graph state for a thread (sync)."""
        config = {"configurable": {"thread_id": thread_id}}
        return self.graph.get_state(config)

    async def aget_state(self, thread_id: str):
        """Get graph state for a thread (async)."""
        async_graph = await self._get_async_graph()
        config = {"configurable": {"thread_id": thread_id}}
        return await async_graph.aget_state(config)