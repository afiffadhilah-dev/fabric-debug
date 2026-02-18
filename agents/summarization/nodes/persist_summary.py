from sqlmodel import Session
from utils.database import get_engine

from config.settings import settings
from models.skill import Skill
from models.skill_dimension import SkillDimension
from models.behavioral_observation import BehavioralObservation
from models.evidence import Evidence
from models.domain_context import DomainContext
from models.infrastructure_context import InfrastructureContext


def persist_summary_node(state):
    """
    Persist summarized skills, behaviors, domain contexts, and infrastructure contexts into DB.
    """
    candidate_id = state["candidate_id"]
    skills = state.get("skills", [])
    behaviors = state.get("behavior_observations", [])
    domain_contexts = state.get("domain_contexts", [])
    infra_contexts = state.get("infra_contexts", [])

    engine = get_engine()

    with Session(engine) as db:
        # -----------------------
        # Persist skills + evidence
        # -----------------------
        for skill in skills:
            skill_row = Skill(
                candidate_id=candidate_id,
                name=skill["name"],
                meaningfulness_score=skill.get("meaningfulness"),
                confidence=skill.get("confidence"),
            )
            db.add(skill_row)
            db.flush()  # populate skill_row.id

            # Skill dimensions
            for dim, value in (skill.get("dimensions") or {}).items():
                db.add(
                    SkillDimension(
                        skill_id=skill_row.id,
                        dimension=dim,
                        value=value,
                    )
                )

            # Evidence for skill
            for ev in skill.get("evidence", []):
                db.add(
                    Evidence(
                        candidate_id=candidate_id,
                        related_entity="skill",
                        related_entity_id=skill_row.id,
                        attribute=ev.get("attribute"),
                        content=ev.get("quote", ""),
                        source_type=ev.get("source", "unknown"),
                        source_reference=ev.get("timestamp"),
                    )
                )

        # -----------------------
        # Persist behaviors + evidence
        # -----------------------
        for behavior in behaviors:
            behavior_row = BehavioralObservation(
                candidate_id=candidate_id,
                category=behavior["name"],
                observation=_summarize_behavior(behavior),
                confidence=behavior.get("confidence"),
            )
            db.add(behavior_row)
            db.flush()

            for ev in behavior.get("evidence", []):
                db.add(
                    Evidence(
                        candidate_id=candidate_id,
                        related_entity="behavior",
                        related_entity_id=behavior_row.id,
                        attribute=ev.get("attribute"),
                        content=ev.get("quote", ""),
                        source_type=ev.get("source", "unknown"),
                        source_reference=ev.get("timestamp"),
                    )
                )

        # -----------------------
        # Persist domain contexts
        # -----------------------
        for domain_context in domain_contexts:
            db.add(
                DomainContext(
                    candidate_id=candidate_id,
                    data=domain_context,
                )
            )

        # -----------------------
        # Persist infrastructure contexts
        # -----------------------
        for infra_context in infra_contexts:
            db.add(
                InfrastructureContext(
                    candidate_id=candidate_id,
                    data=infra_context,
                )
            )

        db.commit()

    return {
        **state,
        "persisted": True,
    }


def _summarize_behavior(behavior: dict) -> str:
    """
    Lightweight summary used for BehavioralObservation.observation.
    """
    name = behavior.get("name", "")
    confidence = behavior.get("confidence", "")
    return f"{name} ({confidence})"
