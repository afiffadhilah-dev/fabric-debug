"""
Test runner for merge_extracted moved into tests.

Reads `tests/summarization/input/input_from_resume.json` and
`tests/summarization/input/input_from_conversation.json`, writes
`tests/summarization/input/merged_output.json`.
"""
from pathlib import Path
import sys

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from agents.summarization.merger.merge_extracted import main


def run():
    tests_root = Path(__file__).parent
    resume = tests_root / "input" / "input_from_resume.json"
    convo = tests_root / "input" / "input_from_conversation.json"
    out = tests_root / "output" / "merged_output.json"

    main(resume, convo, out)


if __name__ == '__main__':
    run()
