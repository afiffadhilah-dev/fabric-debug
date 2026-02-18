"""
Test runner for skill scoring moved into tests.

Reads `tests/summarization/input/merged_output.json`, runs
`agents.summarization.skill_scoring.score_all(...)`, writes to
`tests/summarization/output/scored_output.json`.
"""
import sys
from pathlib import Path
import json

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from agents.summarization.skill_tools.score_skills import score_all


def main():
    tests_root = Path(__file__).parent
    input_path = tests_root / "input" / "score_skills_input.json"
    output_path = tests_root / "output" / "scored_output.json"

    score_all(input_path, output_path, use_llm=False)
    print(f"Wrote scored output to {output_path}")


if __name__ == '__main__':
    main()
