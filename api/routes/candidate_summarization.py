from fastapi import APIRouter, HTTPException, Depends, status, Query, BackgroundTasks
from typing import Optional
from sqlmodel import Session

from services.summarization_service import SummarizationService
from api.models.candidate_summarization_schemas import (
    SummarizeSessionRequest,
    SummarizeProfileRequest,
    CandidateProfileResponse,
    ProfileSummaryResponse,
    ErrorResponse,
    TaskStatusResponse,
    SummarizeSessionProfileRequest,
)
from api.models.background_task_schemas import BackgroundTaskStatusResponse
from repositories.background_task_repository import BackgroundTaskRepository
from utils.database import get_engine
from api.auth import verify_api_key

router = APIRouter(
    prefix="/summarization",
    tags=["Summarization"],
    dependencies=[Depends(verify_api_key)]
)


def get_service() -> SummarizationService:
    """
    Dependency provider for SummarizationService.

    FastAPI will cache this dependency per process, making it:
    - Thread-safe
    - Singleton-like per worker
    - Idiomatic FastAPI
    """
    return SummarizationService()


# ============ BACKGROUND TASK ENDPOINTS ============

@router.post(
    "/analyze-session",
    response_model=TaskStatusResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        500: {"model": ErrorResponse, "description": "Error creating task"}
    }
)
def analyze_session(
    request: SummarizeSessionRequest,
    background_tasks: BackgroundTasks,
    service: SummarizationService = Depends(get_service)
) -> TaskStatusResponse:
    """
    Enqueue a background task to summarize an interview session.
    
    Returns immediately with a confirmation message.
    
    **Parameters:**
    - `session_id`: Interview session ID
    - `mode`: Interview mode (default: "SELF_REPORT")
    
    **Returns:**
    - status: Task status (task_queued)
    - message: Status message
    """
    try:
        result = service.analyze_session_async(
            background_tasks=background_tasks,
            session_id=request.session_id,
            mode=request.mode
        )
        return TaskStatusResponse(
            task_id=result["task_id"],
            status=result["status"],
            message=result["message"]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating task: {str(e)}")


@router.post(
    "/summarize-profile",
    response_model=TaskStatusResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        500: {"model": ErrorResponse, "description": "Error creating task"}
    }
)
def summarize_profile(
    request: SummarizeProfileRequest,
    background_tasks: BackgroundTasks,
    service: SummarizationService = Depends(get_service)
) -> TaskStatusResponse:
    """
    Enqueue a background task to summarize a candidate's profile.
    
    Returns immediately with a confirmation message.
    
    **Parameters:**
    - `candidate_id`: Candidate ID
    
    **Returns:**
    - status: Task status (task_queued)
    - message: Status message
    """
    try:
        result = service.summarize_profile_async(
            background_tasks=background_tasks,
            candidate_id=request.candidate_id
        )
        return TaskStatusResponse(
            task_id=result["task_id"],
            status=result["status"],
            message=result["message"]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating task: {str(e)}")


@router.post(
    "/summarize-session-profile",
    response_model=TaskStatusResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        500: {"model": ErrorResponse, "description": "Error creating task"}
    }
)
def summarize_session_profile(
    request: SummarizeSessionProfileRequest,
    background_tasks: BackgroundTasks,
    service: SummarizationService = Depends(get_service)
) -> TaskStatusResponse:
    """
    Enqueue a background task to summarize a candidate profile from a session.
    Returns immediately with a confirmation message.
    **Parameters:**
    - `session_id`: Interview session ID
    - `mode`: Interview mode (default: "SELF_REPORT")
    **Returns:**
    - status: Task status (task_queued)
    - message: Status message
    """
    try:
        result = service.summarize_session_profile_async(
            background_tasks=background_tasks,
            session_id=request.session_id,
            mode=request.mode
        )
        return TaskStatusResponse(
            task_id=result["task_id"],
            status=result["status"],
            message=result["message"]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating task: {str(e)}")


@router.get(
    "/task-status/{task_id}",
    response_model=BackgroundTaskStatusResponse,
    status_code=status.HTTP_200_OK,
    responses={
        404: {"model": ErrorResponse, "description": "Task not found"},
        500: {"model": ErrorResponse, "description": "Error retrieving task"}
    }
)
def get_task_status(
    task_id: str,
) -> BackgroundTaskStatusResponse:
    """
    Get the status of a background task by task ID.
    
    **Path Parameters:**
    - `task_id`: Background task ID returned from async endpoints
    
    **Returns:**
    - task_id: ID of the task
    - task_type: Type of task (session_summarization, profile_summarization)
    - status: Current status (INITIATED, PENDING, SUCCESS, FAILED)
    - related_entity_type: Type of related entity
    - related_entity_id: ID of related entity
    - result: JSON result if succeeded
    - error_message: Error message if failed
    - started_at: When task started
    - completed_at: When task completed
    - created_at: When task was created
    """
    try:
        engine = get_engine()
        with Session(engine) as db:
            repo = BackgroundTaskRepository(db)
            task = repo.get_by_id(task_id)
        
        if not task:
            raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
        
        return BackgroundTaskStatusResponse(
            task_id=task.id,
            task_type=task.task_type,
            status=task.status,
            related_entity_type=task.related_entity_type,
            related_entity_id=task.related_entity_id,
            result=task.result,
            error_message=task.error_message,
            started_at=task.started_at,
            completed_at=task.completed_at,
            created_at=task.created_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving task: {str(e)}")


@router.get(
    "/profile",
    response_model=CandidateProfileResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request (missing candidate_id)"},
        500: {"model": ErrorResponse, "description": "Error retrieving profile"}
    }
)
def get_profile(
    candidate_id: str = Query(..., min_length=1, description="Unique identifier for the candidate"),
    service: SummarizationService = Depends(get_service)
) -> CandidateProfileResponse:
    """
    Retrieve a candidate's complete profile from the database.
    
    Returns the candidate's full profile in JSON format including:
    - Candidate information
    - Skills with dimensions and evidence
    - Behavioral observations with evidence
    - Aspirations, gaps, constraints
    - Present state and risk notes
    - Domain contexts and infrastructure contexts
    
    **Query Parameters:**
    - `candidate_id`: Unique identifier for the candidate
    
    **Returns:**
    - Complete candidate profile as JSON
    - Success status
    """
    try:
        profile = service.get_candidate_profile(candidate_id)
        
        if not profile or not profile.get("candidate"):
            raise HTTPException(status_code=404, detail=f"Candidate not found: {candidate_id}")
        
        return CandidateProfileResponse(
            candidate_id=candidate_id,
            profile=profile,
            status="success"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving profile: {str(e)}")


@router.get(
    "/profile-summary",
    response_model=ProfileSummaryResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request (missing candidate_id)"},
        404: {"model": ErrorResponse, "description": "Profile summary or interview session not found"},
        500: {"model": ErrorResponse, "description": "Error retrieving profile summary"}
    }
)
def get_profile_summary(
    candidate_id: str = Query(..., min_length=1, description="Unique identifier for the candidate"),
    summary_type: str = Query(default="GENERAL", description="Type of summary (e.g., GENERAL, SKILLS, INFRA, DOMAIN)"),
    service: SummarizationService = Depends(get_service)
) -> ProfileSummaryResponse:
    """
    Retrieve or generate a candidate's profile summary.
    
    If the summary already exists in the database, returns it immediately.
    Otherwise, generates a new summary from the candidate's most recent interview session
    and stores it in the database.
    
    **Query Parameters:**
    - `candidate_id`: Unique identifier for the candidate
    - `summary_type`: Type of summary to retrieve or generate (default: "GENERAL")
    
    **Returns:**
    - Profile summary text
    - Candidate ID
    - Summary type
    - Success status
    """
    try:
        summary = service.get_candidate_profile_summary(
            candidate_id=candidate_id,
            summary_type=summary_type
        )
        
        return ProfileSummaryResponse(
            candidate_id=candidate_id,
            summary=summary,
            summary_type=summary_type,
            status="success"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving profile summary: {str(e)}")
