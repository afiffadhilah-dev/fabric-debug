"""
Run `ProfileSummaryAgent.summarize` for `seed_candidate_1` and save output.

Usage:
  python tests/summarization/profile_summary_seed_candidate_1.py

Note: Ensure local DB is seeded (scripts/seed_db.py) and `DATABASE_URL` is set.
"""
import sys
from pathlib import Path
import json

# Ensure project root is importable
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from agents.summarization.profile.profile_summary_agent import ProfileSummaryAgent


def main():
    agent = ProfileSummaryAgent()
    candidate_id = "3f59c85b-a308-4675-a5fc-5b88218340731"

    try:
        summary = agent.summarize(candidate_id)
    except Exception as e:
        print(f"Error generating profile summary: {e}")
        raise

    out_dir = Path(__file__).parent / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"profile_summary_{candidate_id}.md"
    out_path.write_text(summary, encoding="utf-8")

    print(f"Wrote profile summary to {out_path}")


if __name__ == '__main__':
    main()
