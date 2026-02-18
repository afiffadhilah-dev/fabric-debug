"""
Parse answer node - following LangGraph workflow pattern.

NO nested agent! Just direct tool calls with explicit context.
This is the CORRECT pattern from LangGraph docs.

Supports streaming via get_stream_writer() for real-time progress updates.
"""

from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any
from agents.conversational.state import InterviewState
from tools.extraction_tools import (
    extract_all_skills_from_answer,
    assess_answer_engagement,
    assess_criteria,
    analyze_cross_gap_coverage
)
from tools.skip_detector import detect_skip_intent


def _get_stream_writer():
    """
    Get stream writer for custom progress events.

    Returns a callable that emits events to the 'custom' stream mode.
    Falls back to no-op if streaming is not enabled or unavailable.
    """
    try:
        from langgraph.config import get_stream_writer
        return get_stream_writer()
    except Exception:
        # Streaming not available (sync mode or older LangGraph)
        return lambda x: None

CRITERIA_FIELDS = {
    "answer_quality",
    "criteria_assessed"
}

ENGAGEMENT_FIELDS = {
    "answer_type",
    "engagement_level",
    "detail_score",
    "relevance_score",
    "enthusiasm_detected",
    "reasoning"
}

def split_combined_result(combined: dict):
    criteria_result = {k: combined[k] for k in CRITERIA_FIELDS if k in combined}
    engagement_json = {k: combined[k] for k in ENGAGEMENT_FIELDS if k in combined}
    return criteria_result, engagement_json

def run_criteria(question, answer, what_assesses, category):
    return assess_criteria(
        question=question,
        answer=answer,
        what_assesses=what_assesses,
        category=category
    )

def run_engagement(question, answer, current_question, what_assesses, category):
    return assess_answer_engagement(
        question=question,
        answer=answer,
        gap_description=current_question["gap_description"],
        what_assesses=what_assesses,
        category=category,
        mode="dynamic_gap"
    )

executor = ThreadPoolExecutor(max_workers=2)

#Separate 2 LLM calls with async
def run_assessments(
    question: str,
    answer: str,
    current_question: Dict[str, Any],
    what_assesses: list,
    category: str
):
    criteria_future = executor.submit(
        run_criteria,
        question, answer, what_assesses, category
    )

    engagement_future = executor.submit(
        run_engagement,
        question, answer, current_question, what_assesses, category
    )

    criteria_result = criteria_future.result()
    engagement_json = engagement_future.result()

    return criteria_result, engagement_json

# Separate 2 LLM calls without async
def separate_calls(question: str, answer: str, current_question: Dict[str, Any], what_assesses: list, category: str):
    criteria_result = assess_criteria(
        question=question,
        answer=answer,
        what_assesses=what_assesses,
        category=category
    )
    engagement_json = assess_answer_engagement(
        question=question,
        answer=answer,
        gap_description=current_question["gap_description"],
        what_assesses=what_assesses,
        category=category,
        mode="dynamic_gap"
    )
    return criteria_result, engagement_json

# Combined 2 LLM calls into 1
def combined_call(question: str, answer: str, current_question: Dict[str, Any], what_assesses: list, category: str, mode: str):
    engagement_json = assess_answer_engagement(
        question=question,
        answer=answer,
        gap_description=current_question["gap_description"],
        what_assesses=what_assesses,
        category=category,
        mode=mode
    )
    criteria_result, engagement_json = split_combined_result(engagement_json)
    return criteria_result, engagement_json


def _get_last_human_messages(messages, count: int = 3):
    """
    Extract last N human messages from conversation history.
    
    Args:
        messages: List of all messages from state
        count: Number of recent human messages to return (default: 3)
    
    Returns:
        List of last N human messages (or fewer if not available)
    """
    human_messages = [msg for msg in messages if msg.type == "human"]
    return human_messages[-count:] if human_messages else []


def _detect_skip_intent(state: InterviewState, messages: Dict) -> Dict[str, Any]:
    """
    Detect if user intends to skip the current question.

    Delegates to the detect_skip_intent tool (see tools/skip_detector.py)
    which handles the LLM logic. This function is the orchestrator that:
    1. Extracts context from state and messages
    2. Calls the tool
    3. Returns result dict (state update happens in update_state.py)

    Args:
        state: Current interview state
        messages: Message history

    Returns:
        Dict with skip_detected (bool) and skip_reason (str)
        Returns {"skip_detected": False} if not applicable or error
    """
    mode = state.get("mode", "dynamic_gap")

    # Only applies to predefined questions mode
    if mode != "predefined_questions":
        return {"skip_detected": False}

    count = 3
    last_messages = _get_last_human_messages(messages, count=count)

    if not last_messages:
        return {"skip_detected": False}

    # Get the most recent message text
    recent_text = last_messages[-1].content

    # Get the 1-2 previous message texts (if available)
    previous_texts = [msg.content for msg in last_messages[:-1]]

    # Get current question
    current_question = state.get("current_question", {})
    question_text = current_question.get("question_text", "")

    # Call the tool (LLM logic is encapsulated here)
    try:
        result = detect_skip_intent(
            question=question_text,
            recent_message=recent_text,
            previous_messages=previous_texts
        )
        
        # Return result dict - let update_state.py handle state mutation
        return result

    except Exception as e:
        print(f"⚠️  Error in skip intent detection: {e}")
        return {"skip_detected": False, "skip_reason": "detection_error"}


def parse_answer_node(state: InterviewState) -> Dict[str, Any]:
    """
    Parse user answer using direct tool calls with EXPLICIT context.

    This replaces the old agent_node which incorrectly used create_agent()
    inside a LangGraph node.

    From LangGraph docs: "Nodes are simple functions that call tools directly"
    NOT: "Nodes create agents that call tools"

    Emits progress events via stream writer for real-time updates:
    - extraction_start: Beginning answer processing
    - engagement_assessed: Engagement analysis complete
    - extraction_skipped: Answer was off-topic, skipping extraction
    - skills_extracted / criteria_assessed: Main extraction complete
    - cross_gap_analyzed: Cross-gap analysis complete (predefined mode)

    Args:
        state: Current interview state

    Returns:
        State updates with tool results
    """
    # Get stream writer for progress events
    writer = _get_stream_writer()

    # Get explicit question context (saved when we asked the question)
    current_question = state.get("current_question")
    if not current_question:
        print("WARNING: No current_question in state!")
        return {}

    # Get the answer
    messages = state.get("messages", [])
    if not messages or messages[-1].type != "human":
        print("WARNING: Last message is not from human!")
        return {}

    answer = messages[-1].content
    question = current_question["question_text"]

    mode = state.get("mode", "dynamic_gap")

    # Emit start event
    writer({"stage": "extraction_start", "detail": f"Processing answer for {mode} mode"})

    print(f"\n=== PARSE ANSWER NODE ({mode}) ===")
    print(f"Question: {question}")
    print(f"Answer: {answer}")

    # Log target based on mode
    if mode == "predefined_questions":
        category = current_question.get("category", "General")
        what_assesses = current_question.get("what_assesses", [])
        print(f"Target: {category} - {what_assesses}")
    else:
        print(f"Target: {current_question.get('skill_name')} - {current_question.get('attribute')}")

    # Step 1: Assess answer type FIRST (to detect clarification requests)
    # Get criteria from current_question context (populated in generate_question)
    what_assesses = current_question.get("what_assesses", [])
    category = current_question.get("category", "General")
    current_gap = state.get("current_gap", {})
    current_gap_id = current_gap.get("question_id", "")

    criteria_result = None
    engagement = None
    feedback = ""
    
    try:
        if mode == "predefined_questions":
            criteria_result, engagement = run_assessments(
                question, answer, current_question, what_assesses, category)
        else:
            engagement = assess_answer_engagement(
                question=question,
                answer=answer,
                gap_description=current_question["gap_description"],
                what_assesses=what_assesses,
                category=category,
                mode=mode
            )
        # criteria_result, engagement = separate_calls(question, answer, current_question, what_assesses, category)
        # criteria_result, engagement = combined_call(question, answer, current_question, what_assesses, category, mode)
        print(f"✅ Answer type: {engagement.get('answer_type')}, Engagement: {engagement.get('engagement_level')}")
        writer({"stage": "engagement_assessed", "detail": f"Type: {engagement.get('answer_type')}"})
        feedback = ""

        if criteria_result and criteria_result.get("answer_quality", 0) <= 3:
            feedback = criteria_result.get("reasoning")
            if feedback:
                writer({"feedback": feedback.strip()})
    except Exception as e:
        print(f"❌ Error assessing engagement: {e}")
        engagement = {"answer_type": "partial_answer", "engagement_level": "engaged"}
        feedback = ""
        criteria_result = None
        writer({"stage": "engagement_assessed", "detail": "fallback"})

    # Step 2: Mode-specific extraction
    # - Dynamic gap mode: Extract technical skills with 6 attributes
    # - Predefined questions mode: Assess criteria (leadership, design, etc.)
    answer_type = engagement.get("answer_type", "partial_answer")

    # Process based on mode
    if mode == "predefined_questions":
        # Check for skip intent FIRST (before off-topic check)
        # Answers like "I don't have experience" should be treated as skip, not off-topic
        print(f"🔍 Checking skip intent for answer: '{answer}'")
        skip_result = _detect_skip_intent(state, messages)
        print(f"🔍 Skip detection result: {skip_result}")
        
        if skip_result.get("skip_detected"):
            # User wants to skip this question - return early with skip flag
            skip_reason = skip_result.get("skip_reason", "pass")
            
            print(f"🚫 SKIP DETECTED: User wants to skip this question (reason: {skip_reason})")
            writer({"stage": "skip_detected", "detail": skip_reason})
            
            return {
                "answer_text": answer,
                "feedback": feedback,
                "tool_results": {
                    "engagement": engagement,
                    "skip_detected": True,
                    "skip_reason": skip_reason
                }
            }

    # Check off-topic (for both modes, but AFTER skip check for predefined mode)
    if answer_type == "off_topic":
        print(f"⏭️  Skipping extraction: off-topic")
        writer({"stage": "extraction_skipped", "detail": "off-topic answer"})
        return {
            "answer_text": answer,
            "feedback": feedback,
            "tool_results": {"engagement": engagement}
        }

    # Continue processing based on mode
    if mode == "predefined_questions":
        cross_coverage = []
        # CROSS-GAP ANALYSIS - Check if this answer covers OTHER questions
        # Only do this for engaged, detailed answers
        detail_score = engagement.get("detail_score", 0)
        answer_quality = criteria_result.get("answer_quality", 0) if criteria_result else 0
        if detail_score >= 3 or answer_quality >= 3:
            try:
                identified_gaps = state.get("identified_gaps", [])
                cross_coverage = analyze_cross_gap_coverage(
                    answer=answer,
                    remaining_gaps=identified_gaps,
                    current_gap_id=current_gap_id
                )
                writer({"stage": "cross_gap_analyzed", "detail": f"{len(cross_coverage)} gaps covered"})
            except Exception as e:
                print(f"⚠️  Cross-gap analysis failed: {e}")
                cross_coverage = []
                writer({"stage": "cross_gap_analyzed", "detail": "error"})
        else:
            print(f"⏭️  Skipping cross-gap analysis: answer not detailed enough (detail={detail_score})")
            writer({"stage": "cross_gap_analyzed", "detail": "skipped"})

        tool_results = {"engagement": engagement}
        if criteria_result is not None:
            tool_results["criteria"] = criteria_result
        if cross_coverage:
            tool_results["cross_coverage"] = cross_coverage

        return {
            "answer_text": answer,
            "feedback": feedback,
            "tool_results": tool_results
        }

    # DYNAMIC GAP MODE: Extract ALL information - even if they also asked for clarification!
    # This handles: "3 years. what types task do you mean?"
    #   → Extract "3 years" AND note clarification request
    skills_list = []
    try:
        extracted_skills = state.get("extracted_skills", [])

        skills_list = extract_all_skills_from_answer(
            answer=answer,
            question=question,
            known_skills=extracted_skills,
            current_context={
                "skill_name": current_question["skill_name"],
                "attribute": current_question["attribute"]
            },
            conversation_messages=messages  # ✅ Pass full conversation for co-reference resolution
        )

        if skills_list:
            print(f"✅ Extracted {len(skills_list)} skill(s)")
            writer({"stage": "skills_extracted", "detail": f"{len(skills_list)} skill(s)"})
        else:
            print(f"⚠️  No specific information extracted")
            writer({"stage": "skills_extracted", "detail": "none"})

    except Exception as e:
        print(f"❌ Error extracting skills: {e}")
        skills_list = []
        writer({"stage": "skills_extracted", "detail": "error"})

    return {
        "answer_text": answer,
        "feedback": feedback,
        "tool_results": {
            "skills": skills_list,
            "engagement": engagement
        }
    }
