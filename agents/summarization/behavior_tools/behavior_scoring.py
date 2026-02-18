from utils.llm_service import LLMService
from agents.summarization.utils.scoring import _score_with_llm, _heuristic_score


def score_behaviors(behaviors, use_llm: bool = True):
    llm = None
    if use_llm:
        try:
            llm = LLMService.fast()
        except Exception:
            llm = None

    scored = []
    for b in behaviors or []:
        evidence = b.get("evidence", [])
        if llm:
            scores = _score_with_llm(llm, b.get("name", ""), evidence)
        else:
            scores = _heuristic_score(evidence)
        item = {**b, **scores}
        scored.append(item)
    return scored
