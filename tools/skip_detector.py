"""
Skip intent detector for interview questions.

Determines if a user intends to skip the current question based on
conversational context and message history.
"""

from typing import List, Dict, Any
from utils.llm_service import LLMService
from utils.prompt_loader import PromptLoader


def detect_skip_intent(
    question: str,
    recent_message: str,
    previous_messages: List[str] = None
) -> Dict[str, Any]:
    """
    Detect if user intends to skip the current question (predefined_questions mode).

    Analyzes recent conversation to determine if user wants to skip answering
    the current question. Uses LLM with context of previous messages for
    better understanding of user intent.

    Args:
        question: The current question being asked
        recent_message: User's most recent message
        previous_messages: List of 1-2 previous user messages for context (optional)

    Returns:
        Dictionary with:
        {
            "skip_detected": bool,  # Whether skip intent was detected
            "skip_reason": str      # Reason for skip (e.g., "user_requested_skip")
        }
    """
    if not previous_messages:
        previous_messages = []

    # Format previous messages for prompt
    previous_messages_formatted = "\n".join(
        [f"Message {i+1}: {text}" for i, text in enumerate(previous_messages)]
    ) if previous_messages else "(No previous messages)"

    # Load prompt template
    try:
        prompt_loader = PromptLoader()
        system_prompt = prompt_loader.load(
            template_name="detect_skip_intent",
            mode="conversational",
            question=question,
            previous_messages=previous_messages_formatted,
            recent_message=recent_message
        )
    except Exception as e:
        print(f"⚠️  Error loading skip intent prompt: {e}")
        return {
            "skip_detected": False,
            "skip_reason": "prompt_load_error"
        }

    schema = {
        "type": "object",
        "properties": {
            "skip_detected": {
                "type": "boolean"
            },
            "skip_reason": {
                "type": "string"
            }
        },
        "required": ["skip_detected", "skip_reason"]
    }

    llm = LLMService()

    try:
        result = llm.generate_json(
            system_prompt=system_prompt,
            human_prompt="",
            schema=schema
        )

        skip_detected = result.get("skip_detected", False)
        skip_reason = result.get("skip_reason", "unknown")

        # Truncate reason for storage
        skip_reason_short = skip_reason[:50] if skip_reason else None

        return {
            "skip_detected": skip_detected,
            "skip_reason": skip_reason_short
        }

    except Exception as e:
        print(f"⚠️  Error detecting skip intent: {e}")
        return {
            "skip_detected": False,
            "skip_reason": "llm_error"
        }
