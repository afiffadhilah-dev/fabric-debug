import sys
from pathlib import Path

# Ensure project root is on sys.path for all test files
sys.path.insert(0, str(Path(__file__).parent.parent))
