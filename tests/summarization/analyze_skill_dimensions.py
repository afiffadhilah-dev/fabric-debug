"""
Test runner for AnalyzeAgent moved into tests.

Loads input from `tests/summarization/input/input.json`, runs
`AnalyzeAgent.analyze(...)` and writes result to
`tests/summarization/output/output.json`.
"""
import json
from pathlib import Path
import sys

# Ensure project root is on sys.path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from agents.summarization.skill_tools.analyze_dimensions import AnalyzeAgent


def main():
    tests_root = Path(__file__).parent
    input_path = tests_root / "input" / "skill_dimensions_input.json"
    output_path = tests_root / "output" / "skill_dimensions_output.json"

    with open(input_path, "r", encoding="utf-8") as f:
        input_data = json.load(f)

    agent = AnalyzeAgent()
    analyzed = agent.analyze(input_data)

    print("Analysis complete!")
    print(f"Analyzed {len(analyzed.get('skills', []))} skills")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(analyzed, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
