from utils.prompt_loader import PromptLoader
from utils.llm_service import LLMService


class ConversationInfraAgent:
    extract_prompt = "conversation_infra_extract"

    def __init__(self, prompt_loader=None, llm=None):
        self.prompt_loader = prompt_loader or PromptLoader()
        self.llm = llm or LLMService.fast()

    def analyze(self, answers, candidate_id=""):
        if not answers:
            return {"candidate_id": candidate_id or "", "infra_contexts": []}

        system = self.prompt_loader.load("conversation_system", mode="summarization")
        human = self.prompt_loader.load(
            self.extract_prompt,
            mode="summarization",
            candidate_id=candidate_id or "",
            answers=answers,
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
