"""
Candidate Profile Data repository for accessing candidate-related data.

Handles retrieval of candidate-related data including skills, observations,
aspirations, gaps, constraints, evidence, flags, indicators, state, risk notes,
domain contexts, and infrastructure contexts.
"""

from typing import List, Dict, Any, Optional
from sqlmodel import Session, select

from models.candidate import Candidate
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
from models.domain_context import DomainContext
from models.infrastructure_context import InfrastructureContext


class CandidateProfileDataRepository:
    """Repository for accessing candidate profile data."""

    def __init__(self, db_session: Session):
        self.db = db_session

    def get_candidate_by_id(self, candidate_id: str) -> Optional[Candidate]:
        """Get a candidate by ID."""
        query = select(Candidate).where(Candidate.id == candidate_id)
        return self.db.exec(query).first()

    def get_skills_for_candidate(self, candidate_id: str) -> List[Dict[str, Any]]:
        """Return skills for a candidate, including dimension records."""
        query = select(Skill).where(Skill.candidate_id == candidate_id).order_by(Skill.created_at)
        skills = self.db.exec(query).all()
        out = []
        for s in skills:
            dims_q = select(SkillDimension).where(SkillDimension.skill_id == s.id).order_by(SkillDimension.created_at)
            dims = self.db.exec(dims_q).all()
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

    def get_behavioral_observations_for_candidate(self, candidate_id: str) -> List[Dict[str, Any]]:
        """Get behavioral observations for a candidate."""
        query = select(BehavioralObservation).where(BehavioralObservation.candidate_id == candidate_id).order_by(BehavioralObservation.created_at)
        observations = self.db.exec(query).all()
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

    def get_aspirations_for_candidate(self, candidate_id: str) -> List[Aspiration]:
        """Get aspirations for a candidate."""
        query = select(Aspiration).where(Aspiration.candidate_id == candidate_id).order_by(Aspiration.created_at)
        return self.db.exec(query).all()

    def get_confirmed_gaps_for_candidate(self, candidate_id: str) -> List[ConfirmedGap]:
        """Get confirmed gaps for a candidate."""
        query = select(ConfirmedGap).where(ConfirmedGap.candidate_id == candidate_id).order_by(ConfirmedGap.created_at)
        return self.db.exec(query).all()

    def get_constraints_for_candidate(self, candidate_id: str) -> List[Constraint]:
        """Get constraints for a candidate."""
        query = select(Constraint).where(Constraint.candidate_id == candidate_id).order_by(Constraint.created_at)
        return self.db.exec(query).all()

    def get_evidence_for_candidate(self, candidate_id: str) -> List[Evidence]:
        """Get evidence for a candidate."""
        query = select(Evidence).where(Evidence.candidate_id == candidate_id).order_by(Evidence.created_at)
        return self.db.exec(query).all()

    def get_followup_flags_for_candidate(self, candidate_id: str) -> List[FollowupFlag]:
        """Get followup flags for a candidate."""
        query = select(FollowupFlag).where(FollowupFlag.candidate_id == candidate_id).order_by(FollowupFlag.created_at)
        return self.db.exec(query).all()

    def get_potential_indicators_for_candidate(self, candidate_id: str) -> List[PotentialIndicator]:
        """Get potential indicators for a candidate."""
        query = select(PotentialIndicator).where(PotentialIndicator.candidate_id == candidate_id).order_by(PotentialIndicator.created_at)
        return self.db.exec(query).all()

    def get_present_state_for_candidate(self, candidate_id: str) -> Optional[PresentState]:
        """Get present state for a candidate."""
        query = select(PresentState).where(PresentState.candidate_id == candidate_id)
        return self.db.exec(query).first()

    def get_risk_notes_for_candidate(self, candidate_id: str) -> List[RiskNote]:
        """Get risk notes for a candidate."""
        query = select(RiskNote).where(RiskNote.candidate_id == candidate_id).order_by(RiskNote.created_at)
        return self.db.exec(query).all()

    def get_domain_contexts_for_candidate(self, candidate_id: str) -> List[Dict[str, Any]]:
        """Return domain contexts for a candidate."""
        query = select(DomainContext).where(DomainContext.candidate_id == candidate_id).order_by(DomainContext.id)
        contexts = self.db.exec(query).all()
        return [ctx.data or {} for ctx in contexts if ctx.data]

    def get_infrastructure_contexts_for_candidate(self, candidate_id: str) -> List[Dict[str, Any]]:
        """Return infrastructure contexts for a candidate."""
        query = select(InfrastructureContext).where(InfrastructureContext.candidate_id == candidate_id).order_by(InfrastructureContext.id)
        contexts = self.db.exec(query).all()
        return [ctx.data or {} for ctx in contexts if ctx.data]

    def get_candidate_profile(self, candidate_id: str) -> Dict[str, Any]:
        """
        Return a consolidated candidate profile.

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
        candidate = self.get_candidate_by_id(candidate_id)
        if not candidate:
            return {"candidate": None}

        # Get all evidence for the candidate
        all_evidence = self.get_evidence_for_candidate(candidate_id)
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
        skills = self.get_skills_for_candidate(candidate_id)
        for skill in skills:
            skill["evidence"] = evidence_by_entity.get(("skill", skill["id"]), [])

        # Get behavioral observations and attach evidence
        observations = self.get_behavioral_observations_for_candidate(candidate_id)
        for obs in observations:
            obs["evidence"] = evidence_by_entity.get(("behavior", obs["id"]), [])

        profile = {
            "candidate": candidate,
            "skills": skills,
            "behavioral_observations": observations,
            "aspirations": self.get_aspirations_for_candidate(candidate_id),
            "confirmed_gaps": self.get_confirmed_gaps_for_candidate(candidate_id),
            "constraints": self.get_constraints_for_candidate(candidate_id),
            "followup_flags": self.get_followup_flags_for_candidate(candidate_id),
            "potential_indicators": self.get_potential_indicators_for_candidate(candidate_id),
            "present_state": self.get_present_state_for_candidate(candidate_id),
            "risk_notes": self.get_risk_notes_for_candidate(candidate_id),
            "domain_contexts": self.get_domain_contexts_for_candidate(candidate_id),
            "infrastructure_contexts": self.get_infrastructure_contexts_for_candidate(candidate_id),
        }
        return profile
