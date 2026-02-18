from typing import Dict, Any
from utils.prompt_loader import PromptLoader
from utils.llm_service import LLMService


class ResumeBehaviorAgent:
    """Behavior-only extractor for resume content using a dedicated prompt."""

    extract_prompt = "resume_behavior_extract"

    def __init__(self, prompt_loader: PromptLoader = None, llm: LLMService = None):
        self.prompt_loader = prompt_loader or PromptLoader()
        self.llm = llm or LLMService.fast()

    def analyze(self, resume_text: str, candidate_id: str = "", target_role: str = "auto") -> Dict[str, Any]:
        if not resume_text:
            return {"candidate_id": candidate_id or "", "behavior_observations": []}

        role_display = "Auto-detect" if not target_role or target_role == "auto" else target_role

        system_prompt = self.prompt_loader.load("system", mode="summarization")
        human_prompt = self.prompt_loader.load(
            self.extract_prompt,
            mode="summarization",
            candidate_id=candidate_id or "",
            target_role=role_display,
            resume_text=resume_text,
        )

        schema = {"candidate_id": "string", "behavior_observations": [{"name": "string", "evidence": [{"quote": "string", "timestamp": "string"}]}]}

        try:
            result = self.llm.generate_json(system_prompt=system_prompt, human_prompt=human_prompt, schema=schema)
        except Exception:
            result = None

        if not result:
            return {"candidate_id": candidate_id or "", "behavior_observations": []}

        return {"candidate_id": result.get("candidate_id", candidate_id or ""), "behavior_observations": result.get("behavior_observations", [])}
