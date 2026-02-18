from __future__ import annotations

from typing import Dict, Any
from sqlmodel import Session
from utils.database import get_engine

from config.settings import settings
from repositories.candidate_profile_data_repository import CandidateProfileDataRepository
from repositories.candidate_profile_repository import CandidateProfileSummaryRepository
from utils.prompt_loader import PromptLoader
from utils.llm_service import LLMService


class ProfileSummaryAgent:
    """
    Summarize a candidate's profile based on all persisted database signals.
    Produces a long-form Markdown summary using an LLM.
    """

    PROMPT_NAME = "profile_summary"  # profile_summary.md

    def __init__(self):
        self.prompt_loader = PromptLoader()
        self.llm = LLMService.deep()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def summarize(self, candidate_id: str) -> str:
        if not candidate_id:
            raise ValueError("candidate_id is required")

        profile = self._load_candidate_profile(candidate_id)

        if not profile or not profile.get("candidate"):
            return self._empty_summary(candidate_id)

        profile_context = self._format_profile(profile)

        system_prompt = self.prompt_loader.load(
            "system",
            mode="summarization",
        )

        human_prompt = self.prompt_loader.load(
            self.PROMPT_NAME,
            mode="summarization",
            candidate_id=candidate_id,
            profile_text=profile_context,
        )

        summary = self.llm.generate(
            prompt=human_prompt,
            system_prompt=system_prompt,
        )

        # Persist summary to database
        self._persist_summary(candidate_id, summary)

        return summary

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_candidate_profile(self, candidate_id: str) -> Dict[str, Any]:
        engine = get_engine()
        with Session(engine) as db:
            repo = CandidateProfileDataRepository(db)
            return repo.get_candidate_profile(candidate_id)

    def _format_profile(self, profile: Dict[str, Any]) -> str:
        """
        Convert structured DB records into a readable, LLM-friendly context.
        """
        parts = []

        candidate = profile.get("candidate")
        if candidate:
            parts.append(
                f"""## Candidate

- ID: {candidate.id}
- Name: {getattr(candidate, "name", "N/A")}
"""
            )

        def section(title: str, items):
            if not items:
                return
            parts.append(f"\n## {title}")
            for item in items:
                parts.append(self._format_item(item))

        section("Skills", profile.get("skills"))
        section("Behavioral Observations", profile.get("behavioral_observations"))
        section("Aspirations", profile.get("aspirations"))
        section("Confirmed Gaps", profile.get("confirmed_gaps"))
        section("Constraints", profile.get("constraints"))
        section("Follow-up Flags", profile.get("followup_flags"))
        section("Potential Indicators", profile.get("potential_indicators"))
        section("Risk Notes", profile.get("risk_notes"))

        present_state = profile.get("present_state")
        if present_state:
            parts.append(
                f"""
## Present State

{present_state.content if hasattr(present_state, "content") else str(present_state)}
"""
            )

        evidence = profile.get("evidence") or []
        if evidence:
            parts.append("\n## Evidence")
            for ev in evidence:
                parts.append(
                    f"""
- **Attribute**: {ev.attribute}
- **Source**: {ev.source_type}
- **Related Entity**: {ev.related_entity}
- **Content**:
  {ev.content}
"""
                )

        return "\n".join(parts).strip()

    def _format_item(self, item: Any) -> str:
        """
        Generic formatter for ORM or dict-like objects.
        """
        if isinstance(item, dict):
            lines = []
            for k, v in item.items():
                if k in {"id", "candidate_id"}:
                    continue
                lines.append(f"- **{k.replace('_', ' ').title()}**: {v}")
            return "\n".join(lines)

        # ORM object fallback
        lines = []
        for attr in dir(item):
            if attr.startswith("_"):
                continue
            if attr in {"id", "candidate_id"}:
                continue
            try:
                value = getattr(item, attr)
            except Exception:
                continue
            if callable(value):
                continue
            if value is not None:
                lines.append(f"- **{attr.replace('_', ' ').title()}**: {value}")
        return "\n".join(lines)

    def _empty_summary(self, candidate_id: str) -> str:
        return f"""# Candidate Profile Summary

**Candidate ID:** {candidate_id}

No profile data is available for this candidate yet.
"""

    def _persist_summary(self, candidate_id: str, summary: str) -> None:
        """
        Save the generated summary to the candidate_profile_summaries table.
        """
        engine = get_engine()
        with Session(engine) as db:
            repo = CandidateProfileSummaryRepository(db)
            repo.save(
                candidate_id=candidate_id,
                summary=summary,
                summary_type="GENERAL",
            )
