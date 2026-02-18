from typing import Dict, Any, List

from utils.llm_service import LLMService
from utils.prompt_loader import PromptLoader


LEVELS = ["Low", "Low-Medium", "Medium", "Medium-High", "High"]


def _heuristic_score(evidence: List[Dict[str, Any]]) -> Dict[str, str]:
    text_blob = " ".join([e.get("quote", "") for e in evidence or []]).lower()
    count = len([e for e in evidence or [] if e.get("quote", "").strip()])

    if count >= 3:
        meaningful = "High"
    elif count == 2:
        meaningful = "Medium-High"
    elif count == 1:
        meaningful = "Medium"
    else:
        meaningful = "Low"

    confidence = "Medium"
    if any(k in text_blob for k in ["designed", "implemented", "led", "reduced", "%", "improved", "optimized", "achieved"]):
        confidence = "High"
    elif any(k in text_blob for k in ["used", "familiar", "dabbled", "basic"]):
        confidence = "Low-Medium"
    elif count == 0:
        confidence = "Low"

    explanation = {
        "High": "High (specific example demonstrates understanding beyond surface level)",
        "Medium-High": "Medium-High (multiple concrete examples or integrations shown)",
        "Medium": "Medium (mentions usage but limited depth)",
        "Low-Medium": "Low-Medium (mentions familiarity without depth)",
        "Low": "Low (no concrete evidence provided)"
    }

    return {"meaningfulness": meaningful, "confidence": explanation[confidence]}


def _score_with_llm(llm: LLMService, name: str, evidence: List[Dict[str, Any]]) -> Dict[str, str]:
    loader = PromptLoader()
    system_prompt = loader.load("skill_scoring_system", mode="summarization")

    evidence_text = "\n".join([f"- {e.get('quote','')}" for e in evidence or []]) or "(no evidence)"
    human_prompt = loader.load("skill_scoring", mode="summarization", skill_name=name, evidence_text=evidence_text)

    schema = {"meaningfulness": "string", "confidence": "string"}

    try:
        result = llm.generate_json(system_prompt=system_prompt, human_prompt=human_prompt, schema=schema)
        if not result:
            return _heuristic_score(evidence)

        m = result.get("meaningfulness", "").strip()
        c = result.get("confidence", "").strip()
        if m not in LEVELS or not c:
            return _heuristic_score(evidence)
        return {"meaningfulness": m, "confidence": c}
    except Exception:
        return _heuristic_score(evidence)
