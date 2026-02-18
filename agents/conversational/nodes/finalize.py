"""
Finalize node - completes the interview and persists data.
"""

from datetime import datetime
from typing import Dict, Any
from langchain_core.messages import AIMessage
from agents.conversational.state import InterviewState
from utils.prompt_loader import PromptLoader
from utils.llm_service import LLMService


def finalize_node(state: InterviewState) -> Dict[str, Any]:
    """
    Complete the interview and persist results to database.

    Generates a completion message and marks should_continue as False.
    Collects summary statistics including skipped questions for API response.

    Note: Database persistence (InterviewSession and ExtractedSkill updates)
    is handled by the ConversationalInterviewService after the graph completes,
    since nodes don't have direct database access.

    Returns:
        Dictionary with updates:
        - should_continue: False
        - messages: [AIMessage] with completion message
        - interview_summary: Statistics including skipped questions
    """
    termination_reason = state.get("termination_reason", "unknown")
    completeness_score = state.get("completeness_score", 0.0)
    questions_asked = state.get("questions_asked", 0)
    extracted_skills = state.get("extracted_skills", [])
    language = state.get("language")
    mode = state.get("mode", "dynamic_gap")
    
    # Collect skipped questions info (predefined mode only)
    skipped_questions = []
    skipped_categories = []
    
    if mode == "predefined_questions":
        identified_gaps = state.get("identified_gaps", [])
        skipped_questions = [g for g in identified_gaps if g.get("skipped", False)]
        skipped_categories = [g.get("category", "Unknown") for g in skipped_questions]
    
    # Calculate answered questions
    questions_answered = questions_asked - len(skipped_questions)

    # Generate appropriate completion message based on termination reason
    prompt_loader = PromptLoader()

    if termination_reason == "complete":
        message = prompt_loader.load(
            "completion_complete",
            mode="conversational",
            num_skills=len(extracted_skills),
            completeness_score=f"{completeness_score:.0%}"
        )
    elif termination_reason == "disengaged":
        message = prompt_loader.load("completion_disengaged", mode="conversational")
    elif termination_reason == "no_gaps":
        message = prompt_loader.load(
            "completion_no_gaps",
            mode="conversational",
            questions_asked=questions_asked
        )
    else:
        message = prompt_loader.load("completion_default", mode="conversational")

    # Generate completion message in target language (consistent with other nodes)
    if language and language.lower() != "en":
        try:
            llm = LLMService()
            result = llm.generate(
                prompt=f"Deliver this interview completion message to the candidate:\n\n{message}",
                system_prompt="You are a friendly interviewer wrapping up an interview. Output only the message, nothing else.",
                langcode=language
            ).strip()
            if result:
                message = result
        except Exception as e:
            print(f"Warning: Failed to generate completion message in target language: {e}")

    print(f"Interview finalized: {termination_reason}")
    print(f"Final stats: {len(extracted_skills)} skills, {completeness_score:.2%} complete, {questions_asked} questions")
    
    if skipped_questions:
        print(f"Skipped: {len(skipped_questions)} questions ({', '.join(skipped_categories[:3])}{'...' if len(skipped_categories) > 3 else ''})")

    # Create interview summary for API response
    interview_summary = {
        "questions_asked": questions_asked,
        "questions_answered": questions_answered,
        "questions_skipped": len(skipped_questions),
        "skipped_categories": skipped_categories
    }

    return {
        "should_continue": False,
        "messages": [AIMessage(content=message)],
        "interview_summary": interview_summary
    }
