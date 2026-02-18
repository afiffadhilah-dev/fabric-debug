from typing import Dict, Any
from utils.prompt_loader import PromptLoader
from utils.llm_service import LLMService


class ConversationSkillAgent:
    """Skills-only extractor for conversation content using a dedicated prompt."""

    extract_prompt = "conversation_skills_extract"

    def __init__(self, prompt_loader: PromptLoader = None, llm: LLMService = None):
        self.prompt_loader = prompt_loader or PromptLoader()
        self.llm = llm or LLMService.fast()

    def analyze(self, answers, candidate_id: str = "", target_role: str = "auto") -> Dict[str, Any]:
        if not answers:
            return {"candidate_id": candidate_id or "", "skills": []}

        role_display = "Auto-detect" if not target_role or target_role == "auto" else target_role

        formatted = answers
        system_prompt = self.prompt_loader.load("conversation_system", mode="summarization")
        human_prompt = self.prompt_loader.load(
            self.extract_prompt,
            mode="summarization",
            candidate_id=candidate_id or "",
            target_role=role_display,
            answers=formatted,
        )

        schema = {"candidate_id": "string", "skills": [{"name": "string", "evidence": [{"quote": "string", "timestamp": "string"}]}]}

        try:
            result = self.llm.generate_json(system_prompt=system_prompt, human_prompt=human_prompt, schema=schema)
        except Exception:
            result = None

        if not result:
            return {"candidate_id": candidate_id or "", "skills": []}

        return {"candidate_id": result.get("candidate_id", candidate_id or ""), "skills": result.get("skills", [])}
