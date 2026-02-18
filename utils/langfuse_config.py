"""
Global Langfuse configuration.

Auto-initializes Langfuse when this module is imported.
Works across ALL entry points (main.py, ui/app.py, api/main.py).

How it works:
1. config/settings.py loads .env into os.environ via load_dotenv()
2. Langfuse SDK auto-discovers credentials from os.environ
3. CallbackHandler() can be used anywhere without passing credentials!

Usage:
    # Just import CallbackHandler anywhere you need it
    from langfuse.langchain import CallbackHandler

    # It automatically reads from os.environ (no args needed!)
    handler = CallbackHandler()
"""

from langfuse import Langfuse
from config.settings import settings


def is_langfuse_enabled() -> bool:
    """
    Check if Langfuse observability is enabled.

    Returns:
        bool: True if enabled and configured, False otherwise
    """
    if not settings.LANGFUSE_ENABLED:
        return False

    if not settings.LANGFUSE_PUBLIC_KEY or not settings.LANGFUSE_SECRET_KEY:
        print("WARNING: LANGFUSE_ENABLED=true but credentials missing in .env")
        return False

    return True


# Auto-initialize Langfuse singleton on module import
# This runs once per Python process (main.py, ui/app.py, api/main.py)
if is_langfuse_enabled():
    try:
        # Initialize singleton (credentials auto-discovered from os.environ)
        Langfuse()
        print(f"[OK] Langfuse initialized (host: {settings.LANGFUSE_HOST})")
    except Exception as e:
        print(f"[ERROR] Failed to initialize Langfuse: {e}")
else:
    print("[INFO] Langfuse observability disabled")
