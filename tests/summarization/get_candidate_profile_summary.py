import sys
from pathlib import Path

# Ensure project root is importable
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from services.summarization_service import SummarizationService

CANDIDATE_ID = "0c6dec64-5292-4293-859f-700411c57e6c"
OUTPUT_PATH = Path(__file__).parent / "output" / f"get_candidate_profile_summary_{CANDIDATE_ID}.md"


def write_output(data: str, path: Path) -> None:
    """Write markdown output to file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        f.write(data)


def run_integration():
    """Run get_candidate_profile_summary and write markdown output."""
    service = SummarizationService()

    try:
        summary = service.get_candidate_profile_summary(CANDIDATE_ID)
    except Exception as e:
        summary = f"Error retrieving summary: {str(e)}"

    write_output(summary, OUTPUT_PATH)

    print(f"Wrote output to: {OUTPUT_PATH}")


if __name__ == "__main__":
    run_integration()
