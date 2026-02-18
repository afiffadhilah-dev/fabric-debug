import sys
from pathlib import Path
import json

# Ensure project root is importable
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from services.summarization_service import SummarizationService

CANDIDATE_ID = "0c6dec64-5292-4293-859f-700411c57e6c"
OUTPUT_PATH = Path(__file__).parent / "output" / f"get_candidate_profile_{CANDIDATE_ID}.json"


def write_output(data: dict, path: Path) -> None:
    """Write JSON output to file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)


def run_integration():
    """Run get_candidate_profile and write JSON output."""
    service = SummarizationService()

    try:
        profile = service.get_candidate_profile(CANDIDATE_ID)
    except Exception as e:
        profile = {"error": str(e)}

    write_output(profile, OUTPUT_PATH)

    print(f"Wrote output to: {OUTPUT_PATH}")


if __name__ == "__main__":
    run_integration()
