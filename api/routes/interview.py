"""
Interview API Routes - Thin Controller Layer.

Handles HTTP concerns (request/response, validation, status codes)
and delegates business logic to InterviewService.

Endpoints:
- POST /interview/start - Start new interview
- POST /interview/start/stream - Start new interview with SSE streaming
- POST /interview/chat/{session_id} - Continue with answer
- POST /interview/chat/{session_id}/stream - Continue with answer using SSE streaming
- GET /interview/sessions/{candidate_id} - Get all interview sessions for a candidate
- GET /interview/session/{id} - Get session details
- GET /interview/session/{id}/messages - Get session conversation messages
"""

import json
from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends, status, Query
from sqlmodel import Session
from typing import List, Optional, Literal

from sse_starlette.sse import EventSourceResponse
from api.models.interview_schemas import (
    StartInterviewRequest,
    StartInterviewResponse,
    ChatRequest,
    ContinueInterviewResponse,
    InterviewSessionResponse,
    DetailInterviewSessionResponse,
    InterviewSessionMessageResponse,
    ErrorResponse,
)
from api.auth import verify_api_key, get_current_organization
from services import InterviewService
from services.summarization_service import SummarizationService
from repositories.background_task_repository import BackgroundTaskRepository
from utils.database import get_db

router = APIRouter(
    prefix="/interview",
    tags=["Interview"],
    dependencies=[Depends(verify_api_key)]
)

# ============ DEPENDENCY INJECTION ============


def get_interview_service(db: Session = Depends(get_db)) -> InterviewService:
    """Get InterviewService instance with injected dependencies."""
    return InterviewService(db)


# ============ INTERVIEW ENDPOINTS ============

@router.post(
    "/start",
    response_model=StartInterviewResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request (e.g., missing question_set_id for predefined mode)"},
        404: {"model": ErrorResponse, "description": "Question set not found"},
    }
)
def start_interview(
    request: StartInterviewRequest,
    service: InterviewService = Depends(get_interview_service),
    organization_id: int = Depends(get_current_organization)
):
    """
    Start a new interview session.

    Supports two modes:
    - **dynamic_gap**: Extracts skills from resume, identifies unknown attributes, asks adaptive questions
    - **predefined_questions**: Uses predefined question set, skips questions already answered in resume

    **For predefined_questions mode:**
    - `question_set_id` is required
    - System analyzes resume to determine which questions it already answers
    - Only asks questions where resume cannot provide sufficient information

    **Returns:**
    - `session_id`: Database session ID for retrieving results later
    - `question`: First interview question
    - `mode`: Interview mode being used
    """
    try:
        result = service.start_interview(
            candidate_id=request.candidate_id,
            resume_text=request.resume_text,
            mode=request.mode.value,
            question_set_id=str(
                request.question_set_id) if request.question_set_id else None,
            language=request.language,
            user_name=request.user,
            organization_id=organization_id
        )

        return StartInterviewResponse(
            session_id=result["session_id"],
            question=result["question"],
            mode=request.mode,
            completeness_score=result.get("completeness_score", 0.0)
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to start interview: {str(e)}")


@router.post(
    "/start/stream",
    response_class=EventSourceResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        404: {"model": ErrorResponse, "description": "Question set not found"},
    }
)
async def start_interview_stream(
    request: StartInterviewRequest,
    service: InterviewService = Depends(get_interview_service),
    organization_id: int = Depends(get_current_organization)
):
    """
    Start a new interview session with Server-Sent Events (SSE) streaming.

    Returns a stream of events as the interview initializes:
    - **session**: Initial session info (session_id, thread_id)
    - **node**: Node completion events (identify_gaps, select_gap, etc.)
    - **token**: LLM tokens during question generation
    - **progress**: Progress updates during answer processing
    - **complete**: Final result with first question
    - **error**: Error details if something fails

    **Example event stream:**
    ```
    event: session
    data: {"session_id": "abc-123", "thread_id": "thread_xyz"}

    event: node
    data: {"node": "identify_gaps", "status": "complete"}

    event: token
    data: {"content": "How"}

    event: complete
    data: {"session_id": "abc-123", "question": "How long have you worked with Python?", "completed": false}
    ```
    """
    async def event_generator():
        try:
            async for event in service.start_interview_stream(
                candidate_id=request.candidate_id,
                resume_text=request.resume_text,
                mode=request.mode.value,
                question_set_id=str(request.question_set_id) if request.question_set_id else None,
                language=request.language,
                user_name=request.user,
                organization_id=organization_id
            ):
                yield {
                    "event": event["event"],
                    "data": json.dumps(event["data"])
                }
        except Exception as e:
            yield {
                "event": "error",
                "data": json.dumps({"detail": str(e)})
            }

    return EventSourceResponse(event_generator(), ping=15)


@router.post(
    "/chat/{session_id}",
    response_model=ContinueInterviewResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Interview session not found"},
    }
)
def chat(
    session_id: str,
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    service: InterviewService = Depends(get_interview_service),
    organization_id: int = Depends(get_current_organization)
):
    """
    Continue an existing interview with user's answer.

    **Process:**
    1. Adds user's answer to conversation history
    2. Analyzes answer for skill extraction and engagement
    3. Updates interview state (completeness, gaps resolved, etc.)
    4. Either asks next question or completes interview

    **Interview termination:**
    - Completeness threshold reached (≥60%)
    - User disengaged (3+ consecutive low-quality answers)
    - No more gaps to explore

    **Returns:**
    - `question`: Next question (None if completed)
    - `completed`: Whether interview ended
    - `termination_reason`: Why it ended (if completed): "complete", "disengaged", or "no_gaps"
    - `completion_message`: Interviewer's closing message (if completed)
    """
    try:
        result = service.continue_interview(
            session_id=session_id,
            answer=request.answer,
            organization_id=organization_id,
            background_tasks=background_tasks
        )

        return ContinueInterviewResponse(**result)

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to continue interview: {str(e)}")


@router.post(
    "/chat/{session_id}/stream",
    response_class=EventSourceResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Interview session not found"},
    }
)
async def chat_stream(
    session_id: str,
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    service: InterviewService = Depends(get_interview_service),
    organization_id: int = Depends(get_current_organization)
):
    """
    Continue an existing interview with Server-Sent Events (SSE) streaming.

    Returns a stream of events as the answer is processed:
    - **node**: Node completion events (parse_answer, update_state, etc.)
    - **progress**: Progress updates during answer analysis
    - **token**: LLM tokens during question generation
    - **complete**: Final result with next question or completion info
    - **error**: Error details if something fails

    **Progress stages during answer processing:**
    - extraction_start: Beginning answer processing
    - engagement_assessed: Engagement analysis complete
    - skills_extracted / criteria_assessed: Main extraction complete
    - cross_gap_analyzed: Cross-gap analysis complete (predefined mode)

    **Example event stream:**
    ```
    event: node
    data: {"node": "parse_answer", "status": "complete"}

    event: progress
    data: {"stage": "engagement_assessed", "detail": "Type: detailed_answer"}

    event: token
    data: {"content": "Can"}

    event: complete
    data: {"question": "Can you describe your experience with Docker?", "completed": false}
    ```
    """
    async def event_generator():
        try:
            async for event in service.continue_interview_stream(
                session_id=session_id,
                answer=request.answer,
                organization_id=organization_id,
                background_tasks=background_tasks
            ):
                yield {
                    "event": event["event"],
                    "data": json.dumps(event["data"])
                }
        except Exception as e:
            yield {
                "event": "error",
                "data": json.dumps({"detail": str(e)})
            }

    return EventSourceResponse(event_generator(), ping=15)


@router.get(
    "/sessions/{candidate_id}",
    response_model=List[InterviewSessionResponse]
)
def get_user_interview_sessions(
    candidate_id: str,
    status: Optional[Literal["active", "completed"]] = Query(
        None, description="Filter by session status"),
    start: int = Query(0, ge=0, description="Pagination start index"),
    limit: int = Query(
        50, ge=1, le=100, description="Maximum number of sessions to return"),
    service: InterviewService = Depends(get_interview_service),
    organization_id: int = Depends(get_current_organization)
):
    """
    Get all interview sessions for a specific candidate.

    **Filters:**
    - `status`: Filter by status ("active", "completed")
    - `start`: Pagination offset (default 0)
    - `limit`: Maximum results (default 50, max 100)

    **Returns:** List of interview sessions for the candidate ordered by creation date (newest first)
    """

    try:
        sessions = service.list_sessions(
            candidate_id=candidate_id,
            status=status,
            start=start,
            limit=limit,
            organization_id=organization_id
        )

        return [InterviewSessionResponse.model_validate(s) for s in sessions]

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to list interview sessions: {str(e)}")


@router.get(
    "/session/{id}",
    response_model=DetailInterviewSessionResponse
)
def get_interview_session(
    id: str,
    service: InterviewService = Depends(get_interview_service),
    organization_id: int = Depends(get_current_organization)
):
    """Get detail for a specific interview session by ID."""

    try:
        session = service.get_session(session_id=id, organization_id=organization_id)
        if not session:
            raise HTTPException(
                status_code=404, detail=f"Interview session {id} not found")

        return DetailInterviewSessionResponse.model_validate(session)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        # re-raise explicit HTTP exceptions
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get interview session: {str(e)}")


@router.get(
    "/session/{id}/messages",
    response_model=InterviewSessionMessageResponse
)
def get_interview_messages(
    id: str,
    service: InterviewService = Depends(get_interview_service),
    organization_id: int = Depends(get_current_organization)
):
    """Get conversation messages for a specific interview session."""

    try:
        session = service.get_session(session_id=id, organization_id=organization_id)
        if not session:
            raise HTTPException(
                status_code=404, detail=f"Interview session {id} not found")

        # Get messages from LangGraph checkpoint instead of database
        messages = service.get_checkpoint_messages(thread_id=session.thread_id)

        return InterviewSessionMessageResponse(
            id=session.id,
            messages=messages
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        # re-raise explicit HTTP exceptions
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get interview messages: {str(e)}")


# ============ TEST ENDPOINTS ============


@router.post(
    "/test/trigger-summarization/{session_id}",
    status_code=202,
    tags=["Testing"]
)
def test_trigger_summarization(
    session_id: str,
    background_tasks: BackgroundTasks,
    service: InterviewService = Depends(get_interview_service),
    db: Session = Depends(get_db),
    organization_id: int = Depends(get_current_organization)
):
    """
    Test endpoint to trigger summarization for a session without completing full interview.
    
    Returns 202 Accepted - the summarization task is queued and will execute in background.
    
    Usage:
        POST /interview/test/trigger-summarization/{session_id}
    """
    try:
        # Verify session exists
        session = service.get_session(session_id=session_id, organization_id=organization_id)
        if not session:
            raise HTTPException(
                status_code=404, 
                detail=f"Interview session {session_id} not found"
            )
        
        candidate_id = session.candidate_id
        
        # Queue summarization via analyze_session_async (creates task record internally)
        summarization_service = SummarizationService()
        result = summarization_service.analyze_session_async(
            background_tasks=background_tasks,
            session_id=session_id,
            mode="SELF_REPORT"
        )
        
        return {
            "status": "queued",
            "task_id": result.get("task_id"),
            "session_id": session_id,
            "candidate_id": candidate_id,
            "message": result.get("message")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to trigger summarization: {str(e)}")
