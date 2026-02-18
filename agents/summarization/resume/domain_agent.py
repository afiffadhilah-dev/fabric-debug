from utils.prompt_loader import PromptLoader
from utils.llm_service import LLMService


class ResumeDomainAgent:
    extract_prompt = "resume_domain_extract"

    def __init__(self, loader=None, llm=None):
        self.loader = loader or PromptLoader()
        self.llm = llm or LLMService.fast()

    def analyze(self, resume_text, candidate_id=""):
        if not resume_text:
            return {"candidate_id": candidate_id or "", "domain_contexts": []}

        system = self.loader.load("system", mode="summarization")
        human = self.loader.load(
            self.extract_prompt,
            mode="summarization",
            candidate_id=candidate_id or "",
            resume_text=resume_text,
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

        print("ResumeDomainAgent result: \n")
        print(result)

        return {
            "candidate_id": result.get("candidate_id", candidate_id or ""),
            "domain_contexts": result.get("domain_contexts", []),
        }
