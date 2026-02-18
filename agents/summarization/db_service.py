from typing import List, Optional, Dict, Any
from sqlmodel import Session, select

from models.candidate import Candidate
from models.interview_session import InterviewSession
from models.message import Message
from repositories.message_repository import MessageRepository
from models.skill import Skill
from models.skill_dimension import SkillDimension
from models.behavioral_observation import BehavioralObservation
from models.aspiration import Aspiration
from models.confirmed_gap import ConfirmedGap
from models.constraint import Constraint
from models.evidence import Evidence
from models.followup_flag import FollowupFlag
from models.potential_Indicator import PotentialIndicator
from models.present_state import PresentState
from models.risk_note import RiskNote
from models.candidate_profile_summary import CandidateProfileSummary
from models.domain_context import DomainContext
from models.infrastructure_context import InfrastructureContext

__all__ = [
    "get_interview_session",
    "get_candidate_for_session",
    "get_messages_for_session",
    "get_all_data_for_session",
    "save_candidate_profile_summary",
    "get_candidate_profile_summary",
    "get_last_interview_session_for_candidate",
]


def get_interview_session(session_id: str, db_session: Session) -> Optional[InterviewSession]:
    """Retrieve an InterviewSession by id.

    Returns None if not found.
    """
    query = select(InterviewSession).where(InterviewSession.id == session_id)
    return db_session.exec(query).first()


def get_candidate_by_id(candidate_id: str, db_session: Session) -> Optional[Candidate]:
    query = select(Candidate).where(Candidate.id == candidate_id)
    return db_session.exec(query).first()


def get_candidate_for_session(session_id: str, db_session: Session) -> Optional[Candidate]:
    """Get the Candidate related to a given interview session id.

    Returns None if interview session or candidate is not found.
    """
    interview = get_interview_session(session_id, db_session)
    if not interview:
        return None
    return get_candidate_by_id(interview.candidate_id, db_session)


def get_messages_for_session(session_id: str, db_session: Session, limit: Optional[int] = None) -> List[Message]:
    """Return messages for a session using the existing MessageRepository.

    Messages are ordered chronologically by default.
    """
    repo = MessageRepository(db_session)
    return repo.get_by_session(session_id, limit=limit)


def get_skills_for_candidate(candidate_id: str, db_session: Session) -> List[Dict[str, Any]]:
    """Return skills for a candidate, including dimension records."""
    query = select(Skill).where(Skill.candidate_id == candidate_id).order_by(Skill.created_at)
    skills = db_session.exec(query).all()
    out = []
    for s in skills:
        dims_q = select(SkillDimension).where(SkillDimension.skill_id == s.id).order_by(SkillDimension.created_at)
        dims = db_session.exec(dims_q).all()
        out.append({
            "id": s.id,
            "name": s.name,
            "meaningfulness_score": s.meaningfulness_score,
            "confidence": s.confidence,
            "created_at": s.created_at,
            "dimensions": [
                {"id": d.id, "dimension": d.dimension, "value": d.value, "created_at": d.created_at}
                for d in dims
            ]
        })
    return out


def get_behavioral_observations_for_candidate(candidate_id: str, db_session: Session) -> List[Dict[str, Any]]:
    query = select(BehavioralObservation).where(BehavioralObservation.candidate_id == candidate_id).order_by(BehavioralObservation.created_at)
    observations = db_session.exec(query).all()
    return [
        {
            "id": obs.id,
            "category": obs.category,
            "observation": obs.observation,
            "confidence": obs.confidence,
            "created_at": obs.created_at,
        }
        for obs in observations
    ]


def get_aspirations_for_candidate(candidate_id: str, db_session: Session) -> List[Aspiration]:
    query = select(Aspiration).where(Aspiration.candidate_id == candidate_id).order_by(Aspiration.created_at)
    return db_session.exec(query).all()


def get_confirmed_gaps_for_candidate(candidate_id: str, db_session: Session) -> List[ConfirmedGap]:
    query = select(ConfirmedGap).where(ConfirmedGap.candidate_id == candidate_id).order_by(ConfirmedGap.created_at)
    return db_session.exec(query).all()


def get_constraints_for_candidate(candidate_id: str, db_session: Session) -> List[Constraint]:
    query = select(Constraint).where(Constraint.candidate_id == candidate_id).order_by(Constraint.created_at)
    return db_session.exec(query).all()


def get_evidence_for_candidate(candidate_id: str, db_session: Session) -> List[Evidence]:
    query = select(Evidence).where(Evidence.candidate_id == candidate_id).order_by(Evidence.created_at)
    return db_session.exec(query).all()


def get_followup_flags_for_candidate(candidate_id: str, db_session: Session) -> List[FollowupFlag]:
    query = select(FollowupFlag).where(FollowupFlag.candidate_id == candidate_id).order_by(FollowupFlag.created_at)
    return db_session.exec(query).all()


def get_potential_indicators_for_candidate(candidate_id: str, db_session: Session) -> List[PotentialIndicator]:
    query = select(PotentialIndicator).where(PotentialIndicator.candidate_id == candidate_id).order_by(PotentialIndicator.created_at)
    return db_session.exec(query).all()


def get_present_state_for_candidate(candidate_id: str, db_session: Session) -> Optional[PresentState]:
    query = select(PresentState).where(PresentState.candidate_id == candidate_id)
    return db_session.exec(query).first()


def get_risk_notes_for_candidate(candidate_id: str, db_session: Session) -> List[RiskNote]:
    query = select(RiskNote).where(RiskNote.candidate_id == candidate_id).order_by(RiskNote.created_at)
    return db_session.exec(query).all()


def get_domain_contexts_for_candidate(candidate_id: str, db_session: Session) -> List[Dict[str, Any]]:
    """Return domain contexts for a candidate."""
    query = select(DomainContext).where(DomainContext.candidate_id == candidate_id).order_by(DomainContext.id)
    contexts = db_session.exec(query).all()
    return [ctx.data or {} for ctx in contexts if ctx.data]


def get_infrastructure_contexts_for_candidate(candidate_id: str, db_session: Session) -> List[Dict[str, Any]]:
    """Return infrastructure contexts for a candidate."""
    query = select(InfrastructureContext).where(InfrastructureContext.candidate_id == candidate_id).order_by(InfrastructureContext.id)
    contexts = db_session.exec(query).all()
    return [ctx.data or {} for ctx in contexts if ctx.data]


def get_candidate_profile(candidate_id: str, db_session: Session) -> Dict[str, Any]:
    """Return a consolidated candidate profile without loading interview sessions or candidate chunks.

    The returned dict includes keys:
      - candidate: Candidate or None
      - skills: list of skills with dimensions
      - behavioral_observations
      - aspirations
      - confirmed_gaps
      - constraints
      - evidence
      - followup_flags
      - potential_indicators
      - present_state
      - risk_notes
      - domain_contexts
      - infrastructure_contexts
    """
    candidate = get_candidate_by_id(candidate_id, db_session)
    if not candidate:
        return {"candidate": None}

    # Get all evidence for the candidate
    all_evidence = get_evidence_for_candidate(candidate_id, db_session)
    evidence_by_entity = {}
    for ev in all_evidence:
        key = (ev.related_entity, ev.related_entity_id)
        if key not in evidence_by_entity:
            evidence_by_entity[key] = []
        evidence_by_entity[key].append({
            "id": ev.id,
            "attribute": ev.attribute,
            "content": ev.content,
            "source_type": ev.source_type,
            "source_reference": ev.source_reference,
            "created_at": ev.created_at,
        })

    # Get skills and attach evidence
    skills = get_skills_for_candidate(candidate_id, db_session)
    for skill in skills:
        skill["evidence"] = evidence_by_entity.get(("skill", skill["id"]), [])

    # Get behavioral observations and attach evidence
    observations = get_behavioral_observations_for_candidate(candidate_id, db_session)
    for obs in observations:
        obs["evidence"] = evidence_by_entity.get(("behavior", obs["id"]), [])

    profile = {
        "candidate": candidate,
        "skills": skills,
        "behavioral_observations": observations,
        "aspirations": get_aspirations_for_candidate(candidate_id, db_session),
        "confirmed_gaps": get_confirmed_gaps_for_candidate(candidate_id, db_session),
        "constraints": get_constraints_for_candidate(candidate_id, db_session),
        "followup_flags": get_followup_flags_for_candidate(candidate_id, db_session),
        "potential_indicators": get_potential_indicators_for_candidate(candidate_id, db_session),
        "present_state": get_present_state_for_candidate(candidate_id, db_session),
        "risk_notes": get_risk_notes_for_candidate(candidate_id, db_session),
        "domain_contexts": get_domain_contexts_for_candidate(candidate_id, db_session),
        "infrastructure_contexts": get_infrastructure_contexts_for_candidate(candidate_id, db_session),
    }
    return profile


def get_all_data_for_session(session_id: str, db_session: Session, message_limit: Optional[int] = None) -> Dict[str, Any]:
    """Convenience helper that returns candidate, interview_session and messages.

    Returned dict keys: `interview_session`, `candidate`, `messages`.
    """
    interview = get_interview_session(session_id, db_session)
    if not interview:
        return {"interview_session": None, "candidate": None, "messages": []}

    candidate = get_candidate_by_id(interview.candidate_id, db_session)
    messages = get_messages_for_session(session_id, db_session, limit=message_limit)

    return {
        "interview_session": interview,
        "candidate": candidate,
        "messages": messages,
    }


def save_candidate_profile_summary(candidate_id: str, summary: str, summary_type: str, db_session: Session) -> CandidateProfileSummary:
    """
    Save a candidate profile summary to the database.

    Args:
        candidate_id: The candidate ID
        summary: The summary text
        summary_type: Type of summary (e.g., "GENERAL", "SKILLS", "INFRA", "DOMAIN")
        db_session: SQLModel database session

    Returns:
        The created CandidateProfileSummary record
    """
    profile_summary = CandidateProfileSummary(
        candidate_id=candidate_id,
        summary_type=summary_type,
        summary=summary,
    )
    db_session.add(profile_summary)
    db_session.commit()
    return profile_summary


def get_candidate_profile_summary(candidate_id: str, summary_type: str, db_session: Session) -> Optional[CandidateProfileSummary]:
    """
    Retrieve a candidate profile summary from the database.

    Args:
        candidate_id: The candidate ID
        summary_type: Type of summary to retrieve (e.g., "GENERAL", "SKILLS", "INFRA", "DOMAIN")
        db_session: SQLModel database session

    Returns:
        CandidateProfileSummary record or None if not found
    """
    query = select(CandidateProfileSummary).where(
        (CandidateProfileSummary.candidate_id == candidate_id) &
        (CandidateProfileSummary.summary_type == summary_type)
    ).order_by(CandidateProfileSummary.id.desc())
    return db_session.exec(query).first()


def get_last_interview_session_for_candidate(candidate_id: str, db_session: Session) -> Optional[InterviewSession]:
    """
    Get the most recent interview session for a candidate.

    Args:
        candidate_id: The candidate ID
        db_session: SQLModel database session

    Returns:
        The most recent InterviewSession or None if not found
    """
    query = select(InterviewSession).where(
        InterviewSession.candidate_id == candidate_id
    ).order_by(InterviewSession.created_at.desc())
    return db_session.exec(query).first()
