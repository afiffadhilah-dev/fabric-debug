from typing import Any, Dict
from utils.prompt_loader import PromptLoader
from utils.llm_service import LLMService
from repositories.candidate_profile_repository import CandidateProfileSummaryRepository
from sqlmodel import Session
from utils.database import get_engine

class SessionProfileSummaryAgent:
    """
    Generates a long-form candidate profile summary using all extracted context from a session (skills, behaviors, infra, domain, resume, conversation).
    Persists only the final summary to the candidate_profile_summary table.
    """
    PROMPT_NAME = "session_profile_summary"  # session_profile_summary.md

    def __init__(self):
        self.prompt_loader = PromptLoader()
        self.llm = LLMService.deep()

    def summarize_and_persist(self, candidate_id: str, session_id: str, context: Dict[str, Any]) -> str:
        """
        Generate and persist a long-form professional profile summary for a candidate/session.
        The summary is a detailed, readable Markdown text (not JSON), suitable for hiring managers.
        """
        profile_context = self._format_context(context)

        # Use a prompt that instructs the LLM to write a professional, detailed summary
        human_prompt = self.prompt_loader.load(
            self.PROMPT_NAME,
            mode="summarization",
            candidate_id=candidate_id,
            session_id=session_id,
            profile_text=profile_context,
        )
        # Optionally, you can add a system prompt for style/role
        summary = self.llm.generate(
            prompt=human_prompt,
            system_prompt=None,  # or use a system prompt if you want
        )
        # Persist summary as plain text
        self._persist_summary(candidate_id, session_id, summary)
        return summary

    def _format_context(self, context: Dict[str, Any]) -> str:
        parts = []
        # Resume
        resume = context.get('resume_text', '')
        if resume:
            parts.append("## Resume\n" + resume)
        # Conversation (Q/A)
        answers = context.get('answers', [])
        if answers:
            parts.append("\n## Conversation (Q/A)")
            for qa in answers:
                question = qa.get("question", "")
                answer = qa.get("answer", "")
                parts.append(f"- **Q:** {question}\n  **A:** {answer}")
        # Skills
        skills = context.get('skills', [])
        if skills:
            parts.append("\n## Skills")
            for skill in skills:
                parts.append(self._format_item(skill))
        # Behaviors
        behaviors = context.get('behavior_observations', [])
        if behaviors:
            parts.append("\n## Behavioral Observations")
            for behavior in behaviors:
                parts.append(self._format_item(behavior))
        # Infra Contexts
        infra = context.get('infra_contexts', [])
        if infra:
            parts.append("\n## Infrastructure Contexts")
            for item in infra:
                parts.append(self._format_item(item))
        # Domain Contexts
        domain = context.get('domain_contexts', [])
        if domain:
            parts.append("\n## Domain Contexts")
            for item in domain:
                parts.append(self._format_item(item))
        return "\n".join(parts).strip()

    def _format_item(self, item: Any) -> str:
        if isinstance(item, dict):
            lines = []
            for k, v in item.items():
                if k in {"id", "candidate_id"}:
                    continue
                lines.append(f"- **{k.replace('_', ' ').title()}**: {v}")
            return "\n".join(lines)
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

    def _persist_summary(self, candidate_id: str, session_id: str, summary: str):
        engine = get_engine()
        with Session(engine) as db:
            repo = CandidateProfileSummaryRepository(db)
            repo.save(
                candidate_id=candidate_id,
                session_id=session_id,
                summary=summary,
                summary_type="SESSION_PROFILE",
            )
            db.commit()
