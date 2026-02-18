import json
import sys
from pathlib import Path
from typing import Dict, Any, List

if __name__ == "__main__":
    project_root = Path(__file__).parent.parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from agents.summarization.utils.scoring import _score_with_llm, _heuristic_score
from utils.llm_service import LLMService


def score_all(input_path: Path, output_path: Path, use_llm: bool = True):
    data = json.loads(input_path.read_text(encoding="utf-8"))
    llm = None
    if use_llm:
        try:
            llm = LLMService.fast()
        except Exception:
            llm = None

    def score_list(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        out = []
        for it in items or []:
            name = it.get("name", "")
            evidence = it.get("evidence", [])
            if llm:
                scores = _score_with_llm(llm, name, evidence)
            else:
                scores = _heuristic_score(evidence)

            new = it.copy()
            new.update(scores)
            out.append(new)
        return out

    scored = {
        "candidate_id": data.get("candidate_id", ""),
        "skills": score_list(data.get("skills", [])),
        "behavior_observations": score_list(data.get("behavior_observations", []))
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(scored, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Scored {len(scored['skills'])} skills and {len(scored['behavior_observations'])} behaviors -> {output_path}")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="Score extracted skills using LLM or heuristics")
    parser.add_argument('--input', '-i', type=str, default='data/extracted_skills_merger/merged_output.json')
    parser.add_argument('--output', '-o', type=str, default='data/skill_scoring/scored_output.json')
    parser.add_argument('--no-llm', dest='use_llm', action='store_false')
    args = parser.parse_args()
    score_all(Path(args.input), Path(args.output), use_llm=args.use_llm)
