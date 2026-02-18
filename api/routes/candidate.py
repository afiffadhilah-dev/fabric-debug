from fastapi import APIRouter, Depends, Query, HTTPException, status, Response
from sqlmodel import Session
from typing import List, Optional
from repositories.candidate_repository import CandidateRepository
from repositories.interview_session_repository import InterviewSessionRepository
from utils.database import get_engine, get_db
from api.auth import verify_api_key, get_current_organization
from api.models.candidate_schemas import (
    CandidateDetailResponse, 
    CandidateListResponse, 
    SessionListResponse, 
    CandidateBase, 
    SessionBase,
    CandidateUpsertRequest,
    ResumeRequest,
    ResumeResponse
)
from api.models.candidate_summarization_schemas import ErrorResponse
from models.candidate import Candidate
from uuid import uuid4

router = APIRouter(
    prefix="/candidates",
    tags=["Candidates"],
    dependencies=[Depends(verify_api_key)]
)

@router.post("/", response_model=CandidateBase)
def upsert_candidate(
    request: CandidateUpsertRequest,
    response: Response,
    organization_id: int = Depends(get_current_organization),
    db: Session = Depends(get_db)
):
    """
    Create or update a candidate.
    
    Args:
        request: CandidateUpsertRequest with id, name, and optional email
        response: FastAPI Response object for setting status code
        organization_id: Organization ID from API key context
        db: Database session
    
    Returns:
        CandidateDetailResponse with the created/updated candidate
    """
    try:
        repo = CandidateRepository(db)

        # Organization ID comes from the X-API-Key header (via get_current_organization)
        # No user input needed - this ensures data isolation per organization
        target_org_id = organization_id

        # Try to find existing candidate by email + org (if email provided)
        existing = None
        if request.email:
            existing = repo.get_by_email_and_org(email=request.email, organization_id=target_org_id)

        if existing:
            # Update existing candidate - return 200 OK
            existing.name = request.name
            existing.email = request.email
            candidate = repo.update(existing)
            response.status_code = status.HTTP_200_OK
        else:
            # Create new candidate - return 201 Created
            candidate = Candidate(
                id=str(uuid4()),
                name=request.name,
                email=request.email,
                organization_id=target_org_id
            )
            candidate = repo.create(candidate)
            response.status_code = status.HTTP_201_CREATED
        
        # Convert to Pydantic model for response
        return CandidateBase(
            id=candidate.id,
            name=candidate.name,
            email=candidate.email
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upsert candidate: {str(e)}"
        )

@router.get("/", response_model=CandidateListResponse)
def get_candidates(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    organization_id: int = Depends(get_current_organization),
    db: Session = Depends(get_db)
):
    repo = CandidateRepository(db)
    candidates, total = repo.get_paginated(page=page, page_size=page_size, organization_id=organization_id)
    # Convert SQLModel objects to Pydantic models
    candidate_models = [
        CandidateBase(
            id=c.id, 
            name=c.name,
            email=c.email,
            organization_id=c.organization_id
        ) 
        for c in candidates
    ]
    return CandidateListResponse(candidates=candidate_models, total=total, page=page, page_size=page_size)

@router.get("/{candidate_id}", response_model=CandidateDetailResponse)
def get_candidate_detail(
    candidate_id: str,
    organization_id: int = Depends(get_current_organization),
    db: Session = Depends(get_db)
):
    repo = CandidateRepository(db)
    candidate = repo.get_by_id(candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    # Verify candidate belongs to this organization
    if candidate.organization_id != organization_id:
        raise HTTPException(status_code=403, detail="Unauthorized access to this candidate")
    # Convert SQLModel object to Pydantic model
    candidate_model = CandidateBase(
        id=candidate.id, 
        name=candidate.name,
        email=candidate.email,
        organization_id=candidate.organization_id
    )
    return CandidateDetailResponse(candidate=candidate_model)

@router.get("/{candidate_id}/sessions", response_model=SessionListResponse)
def get_candidate_sessions(
    candidate_id: str,
    organization_id: int = Depends(get_current_organization),
    db: Session = Depends(get_db)
):
    repo = CandidateRepository(db)
    candidate = repo.get_by_id(candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    # Verify candidate belongs to this organization
    if candidate.organization_id != organization_id:
        raise HTTPException(status_code=403, detail="Unauthorized access to this candidate")
    
    session_repo = InterviewSessionRepository(db)
    sessions = session_repo.get_by_candidate(candidate_id, organization_id)
    # Convert SQLModel objects to Pydantic models
    session_models = [
        SessionBase(
            id=s.id,
            candidate_id=s.candidate_id,
            created_at=s.created_at.isoformat() if s.created_at else None,
            completed_at=s.completed_at.isoformat() if s.completed_at else None,
        )
        for s in sessions
    ]
    return SessionListResponse(sessions=session_models)

def get_candidate_repo(db: Session = Depends(get_db)) -> CandidateRepository:
    return CandidateRepository(db)


@router.post("/{candidate_id}/resume", response_model=ResumeResponse, status_code=status.HTTP_201_CREATED,
             responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
def upload_resume(candidate_id: str, request: ResumeRequest, repo: CandidateRepository = Depends(get_candidate_repo)):
    try:
        candidate = repo.get_or_create(candidate_id)
        candidate.resume = request.resume
        updated = repo.update(candidate)

        return ResumeResponse(candidate_id=updated.id, resume=updated.resume, status="success")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload resume: {str(e)}")


@router.get("/{candidate_id}/resume", response_model=ResumeResponse, responses={404: {"model": ErrorResponse}})
def get_resume(candidate_id: str, repo: CandidateRepository = Depends(get_candidate_repo)):
    candidate = repo.get_by_id(candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail=f"Candidate not found: {candidate_id}")

    return ResumeResponse(candidate_id=candidate.id, resume=getattr(candidate, "resume", None), status="success")

