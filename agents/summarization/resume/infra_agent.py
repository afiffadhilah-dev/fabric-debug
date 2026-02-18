from utils.prompt_loader import PromptLoader
from utils.llm_service import LLMService


class ResumeInfraAgent:
    extract_prompt = "resume_infra_extract"

    def __init__(self, loader=None, llm=None):
        self.loader = loader or PromptLoader()
        self.llm = llm or LLMService.fast()

    def analyze(self, resume_text, candidate_id=""):
        if not resume_text:
            return {"candidate_id": candidate_id or "", "infra_contexts": []}

        system = self.loader.load("system", mode="summarization")
        human = self.loader.load(
            self.extract_prompt,
            mode="summarization",
            candidate_id=candidate_id or "",
            resume_text=resume_text,
        )

        schema = {
            "candidate_id": "string",
            "infra_contexts": [
                {
                    "environment_type": "string",
                    "scale": "string",
                    "reliability_expectation": "string",
                    "operational_constraints": "string",
                    "evidence": "string",
                    "confidence": "string",
                }
            ],
        }

        try:
            result = self.llm.generate_json(
                system_prompt=system,
                human_prompt=human,
                schema=schema,
            )
        except Exception:
            return {"candidate_id": candidate_id or "", "infra_contexts": []}

        if not result:
            return {"candidate_id": candidate_id or "", "infra_contexts": []}

        return {
            "candidate_id": result.get("candidate_id", candidate_id or ""),
            "infra_contexts": result.get("infra_contexts", []),
        }
