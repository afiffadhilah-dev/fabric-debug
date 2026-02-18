"""
Utility to load data files from the data directory.

This keeps data loading logic separated from agent business logic.
"""

import json
from pathlib import Path
from typing import Any, Dict


class DataLoader:
    """Load data files from the data directory"""

    def __init__(self, data_dir: str = "data"):
        """
        Initialize data loader

        Args:
            data_dir: Root directory containing data files
        """
        # Get absolute path to data directory
        self.data_dir = Path(__file__).parent.parent / data_dir

    def load_resume_data(self, filename: str = "input.json") -> Dict[str, Any]:
        """
        Load resume conversation data from JSON file.

        Args:
            filename: Name of the JSON file in data/resume/

        Returns:
            Parsed JSON data containing conversation history

        Raises:
            FileNotFoundError: If the file doesn't exist
        """
        file_path = self.data_dir / "resume" / filename

        if not file_path.exists():
            raise FileNotFoundError(f"Resume data file not found: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def load_conversation_data(self, filename: str = "input.json") -> Dict[str, Any]:
        """
        Load conversation data from JSON file.

        Args:
            filename: Name of the JSON file in data/conversation/

        Returns:
            Parsed JSON data

        Raises:
            FileNotFoundError: If the file doesn't exist
        """
        file_path = self.data_dir / "conversation" / filename

        if not file_path.exists():
            raise FileNotFoundError(f"Conversation data file not found: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

