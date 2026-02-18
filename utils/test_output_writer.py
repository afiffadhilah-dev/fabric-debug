import json
from pathlib import Path
from typing import Any, Dict


def write_test_output(
    data: Dict[str, Any],
    output_path: str,
) -> None:
    """
    Write orchestrator test output to a JSON file.

    - Creates parent directories if needed
    - Safely serializes datetimes / UUIDs via default=str
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
