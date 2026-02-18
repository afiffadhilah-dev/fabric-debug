import json
import os
import sys
from pathlib import Path
from sqlmodel import create_engine, Session

# Ensure project root is on sys.path
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from agents.summarization.orchestrator import summarize_session
from config.settings import settings

SESSION_ID = "18426303-9f4f-49ec-bb82-bb7820bb7485"
OUTPUT_PATH = Path(__file__).parent / "output" / f"orchestrator_{SESSION_ID}.json"


# -------------------------
# Test-only output writer
# -------------------------

def write_test_output(data, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)


# -------------------------
# Integration test
# -------------------------

def run_integration():
    """Run orchestrator against real DB + LLM and write JSON output."""

    # Ensure all model modules are imported (SQLAlchemy relationship safety)
    import importlib
    import pkgutil
    import models

    try:
        importlib.import_module("models.candidate")
    except Exception:
        pass

    for _, name, _ in pkgutil.iter_modules(models.__path__):
        if name == "candidate":
            continue
        importlib.import_module(f"models.{name}")

    engine = create_engine(settings.DATABASE_URL)

    with Session(engine):
        result = summarize_session(SESSION_ID)

    write_test_output(result, OUTPUT_PATH)

    print(f"Wrote orchestrator output to: {OUTPUT_PATH}")


if __name__ == "__main__":
    run_integration()
