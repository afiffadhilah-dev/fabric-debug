"""
Introduce node - Warm introduction conversation to personalize the interview.

Handles opening conversation with candidate to make the interview feel personal
and friendly before transitioning to main interview questions.
"""

from typing import Dict, Any
from agents.conversational.state import InterviewState
from utils.language_config import GREETINGS
from utils.database import get_db
from repositories.candidate_repository import CandidateRepository


# Cosmetic node to handle introduction phase
def introduce_node(state: InterviewState) -> Dict[str, Any]:
    """
    Initialize warm introduction phase.

    Prepares opening message for first interaction to build rapport before
    main interview begins.

    Args:
        state: Current interview state

    Returns:
        State updates with introduction_text
    """
    language = state.get("language")
    lang_key = (language or "en").lower()
    greeting_template = GREETINGS.get(lang_key, GREETINGS["en"])
    
    # Extra safety: ensure template is never None
    if not greeting_template:
        greeting_template = GREETINGS["en"]

    # Get candidate name from database
    session_id = state.get("session_id")
    candidate_name = ""

    if session_id:
        try:
            db_session = next(get_db())
            candidate_repo = CandidateRepository(db_session)
            # Ensure session_id is string for query
            candidate_name = candidate_repo.get_name_by_session_id(str(session_id))
            db_session.close()
        except Exception as e:
            print(f"Warning: Could not fetch candidate name: {e}")
            import traceback
            traceback.print_exc()

    # Ensure name is never None for string formatting
    candidate_name = f" {candidate_name}" if candidate_name else ""
    introduction = greeting_template.format(name=candidate_name)

    print(f"\n=== INTRODUCE NODE ===")
    print(f"Language: {lang_key}")
    print(f"Candidate name: {candidate_name}")
    print(f"Introduction prepared: {introduction}\n")

    return {
        "introduction_text": introduction
    }
