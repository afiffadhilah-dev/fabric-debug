from utils.prompt_loader import PromptLoader
from utils.llm_service import LLMService


class ConversationDomainAgent:
    extract_prompt = "conversation_domain_extract"

    def __init__(self, prompt_loader=None, llm=None):
        self.prompt_loader = prompt_loader or PromptLoader()
        self.llm = llm or LLMService.fast()

    def analyze(self, answers, candidate_id=""):
        if not answers:
            return {"candidate_id": candidate_id or "", "domain_contexts": []}

        system = self.prompt_loader.load("conversation_system", mode="summarization")
        human = self.prompt_loader.load(
            self.extract_prompt,
            mode="summarization",
            candidate_id=candidate_id or "",
            answers=answers,
        )

        schema = {
            "candidate_id": "string",
            "domain_contexts": [
                {
                    "industry": "string",
                    "product_type": "string",
                    "business_model": "string",
                    "customer_type": "string",
                    "regulatory_or_compliance_context": "string",
                    "business_criticality": "string",
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
            return {"candidate_id": candidate_id or "", "domain_contexts": []}

        if not result:
            return {"candidate_id": candidate_id or "", "domain_contexts": []}

        print("ConversationDomainAgent result: \n")
        print(result)

        return {
            "candidate_id": result.get("candidate_id", candidate_id or ""),
            "domain_contexts": result.get("domain_contexts", []),
        }
