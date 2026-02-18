"""
Conditional routing logic for the interview graph.

Determines which path the graph should take based on state.
"""

from typing import Literal, Dict, Any
from agents.conversational.state import InterviewState


def get_gap_identifier(gap: Dict[str, Any]) -> str:
    """
    Get unique identifier for a gap (handles both Gap and PredefinedGap types).

    Args:
        gap: Either Gap (has "description") or PredefinedGap (has "question_text")

    Returns:
        Unique identifier string for the gap
    """
    # PredefinedGap uses question_text
    if "question_text" in gap:
        return gap["question_text"]
    # Gap uses description
    return gap.get("description", "")


def should_continue_interview(state: InterviewState) -> Literal["select_gap", "finalize"]:
    """
    Determine whether to continue the interview or finalize.

    For predefined_questions mode:
    - Try to cover all questions while user is engaged
    - Only stop when: disengaged OR no more questions remaining
    - Completeness is tracked but NOT used as a stop condition

    For dynamic_gap mode:
    - Stop when completeness threshold reached OR disengaged OR no gaps

    Args:
        state: Current interview state

    Returns:
        "select_gap" to continue, "finalize" to end
    """
    mode = state.get("mode", "dynamic_gap")
    consecutive_low_quality = state.get("consecutive_low_quality", 0)
    completeness_score = state.get("completeness_score", 0.0)
    minimum_completeness = state.get("minimum_completeness", 0.6)
    identified_gaps = state.get("identified_gaps", [])
    resolved_gaps = state.get("resolved_gaps", [])

    # Check disengagement (applies to all modes)
    if consecutive_low_quality >= 3:
        print("Terminating: User disengaged (3+ consecutive low-quality answers)")
        state["termination_reason"] = "disengaged"
        return "finalize"

    # Check if there are unresolved gaps with probes remaining
    # IMPORTANT: Must use same filtering logic as select_gap_node!
    resolved_identifiers = {get_gap_identifier(gap) for gap in resolved_gaps}
    available_gaps = []
    low_confidence_gaps = []

    for gap in identified_gaps:
        gap_id = get_gap_identifier(gap)

        # Skip resolved gaps
        if gap_id in resolved_identifiers:
            continue

        # Skip exhausted gaps
        if gap.get("probes_attempted", 0) >= gap.get("max_probes", 2):
            continue

        # For predefined mode: additional filtering
        if mode == "predefined_questions":
            # Skip gaps that user explicitly skipped
            if gap.get("skipped"):
                continue

            # Skip resume-filled gaps
            if gap.get("resume_filled"):
                continue

            # Handle interview-filled gaps (from cross-gap detection)
            if gap.get("interview_filled"):
                confidence = gap.get("coverage_confidence", 0.0)
                if confidence >= 0.9:
                    # High confidence: skip entirely
                    continue
                else:
                    # Low confidence: may ask follow-up
                    low_confidence_gaps.append(gap)
                    continue

        available_gaps.append(gap)

    # Include low-confidence gaps as available (select_gap will pick from them)
    total_available = len(available_gaps) + len(low_confidence_gaps)

    if total_available == 0:
        print(f"Terminating: No more gaps to explore (completeness: {completeness_score:.2%})")
        state["termination_reason"] = "no_gaps"
        return "finalize"

    # Mode-specific completeness check
    if mode == "predefined_questions":
        # Predefined mode: Continue as long as user is engaged and questions remain
        # Don't stop just because we hit a completeness threshold
        print(f"Continuing interview (predefined): {total_available} questions remaining ({len(available_gaps)} regular, {len(low_confidence_gaps)} low-confidence), completeness: {completeness_score:.2%}")
        return "select_gap"
    else:
        # Dynamic mode: Use completeness threshold as stop condition
        if completeness_score >= minimum_completeness:
            print(f"Terminating: Completeness threshold reached ({completeness_score:.2%} >= {minimum_completeness:.2%})")
            state["termination_reason"] = "complete"
            return "finalize"

        print(f"Continuing interview (dynamic): {len(available_gaps)} gaps remaining, completeness: {completeness_score:.2%}")
        return "select_gap"


def should_follow_up(state: InterviewState) -> Literal["generate_follow_up", "select_gap", "finalize"]:
    """
    Determine if we should ask a follow-up question on the SAME gap.

    Natural conversation flow - follow up if:
    - User requested clarification (needs examples)
    - Answer was vague/minimal (detail_score < 3)
    - Gap still unresolved AND haven't exceeded max probes

    Otherwise: Apply should_continue_interview logic (select_gap or finalize)

    Args:
        state: Current interview state

    Returns:
        "generate_follow_up" to probe further, "select_gap" or "finalize" to move on
    """
    tool_results = state.get("tool_results", {})
    engagement_data = tool_results.get("engagement", {})
    criteria_data = tool_results.get("criteria", {})
    current_gap = state.get("current_gap")
    resolved_gaps = state.get("resolved_gaps", [])

    answer_type = engagement_data.get("answer_type", "")
    detail_score = engagement_data.get("detail_score", 5)
    answer_quality = criteria_data.get("answer_quality", 5)
    print(f"Answer assessment: type={answer_type}, detail={detail_score}, quality={answer_quality}")
    engagement_level = engagement_data.get("engagement_level", "engaged")

    # PRIORITY CHECK: If user skipped this gap, move to next gap immediately
    skip_detected = tool_results.get("skip_detected", False)
    if skip_detected:
        skip_reason = tool_results.get("skip_reason", "user_skip")
        print(f"  → 🚫 Skip detected ({skip_reason}): Moving to next gap")
        # User explicitly skipped - don't follow up, move to select_gap
        return should_continue_interview(state)

    # Check if gap was resolved
    gap_resolved = False
    if current_gap:
        current_identifier = get_gap_identifier(current_gap)
        gap_resolved = any(
            get_gap_identifier(g) == current_identifier
            for g in resolved_gaps
        )

    # Check probe attempts
    probes_attempted = current_gap.get("probes_attempted", 0) if current_gap else 999
    max_probes = current_gap.get("max_probes", 3) if current_gap else 3

    # Follow up if user requested clarification
    if answer_type == "clarification_request":
        print(f"  → Follow-up: User requested clarification")
        return "generate_follow_up"

    # Determine quality signal: use answer_quality if available, otherwise detail_score
    # In predefined mode, answer_quality comes from criteria assessment
    # In dynamic mode, detail_score is the primary signal
    # Default of 5 means "assume good quality if unknown"
    quality_signal = answer_quality if answer_quality > 0 else detail_score

    # Follow up if gap not resolved, answer was actually low quality, and we have probes left
    if not gap_resolved and quality_signal < 3 and probes_attempted < max_probes:
        print(f"  → Follow-up: Low quality answer (quality={quality_signal}, detail={detail_score}), probes={probes_attempted}/{max_probes}")
        return "generate_follow_up"

    # No follow-up needed - apply should_continue_interview logic
    if gap_resolved:
        print(f"  → No follow-up: Gap resolved, checking if should continue...")
    elif probes_attempted >= max_probes:
        print(f"  → No follow-up: Max probes reached ({probes_attempted}/{max_probes}), checking if should continue...")
    elif quality_signal >= 3:
        print(f"  → No follow-up: Good answer (quality={quality_signal}), checking if should continue...")
    else:
        print(f"  → No follow-up: Gap not resolved but moving on (quality={quality_signal}, probes={probes_attempted}/{max_probes})")

    # Use should_continue_interview logic
    return should_continue_interview(state)


def route_entry_point(state: InterviewState) -> Literal["introduce", "identify_gaps", "analyze_resume_coverage", "parse_answer"]:
    """
    Route entry point based on interview state.

    Flow:
    1. First turn (no messages, questions_asked == 0): Route to introduce
    2. Resume after user answer (messages exist): Route to parse_answer
    3. After introduction (questions_asked > 0, no user messages yet): Route to mode-specific gap identification

    Args:
        state: Current interview state

    Returns:
        Node name to route to: "introduce", "identify_gaps", "analyze_resume_coverage", or "parse_answer"
    """
    messages = state.get("messages", [])
    questions_asked = state.get("questions_asked", 0)
    mode = state.get("mode", "dynamic_gap")

    # First turn: show introduction
    if not messages and questions_asked == 0:
        return "introduce"

    # Resume from user answer
    if messages:
        return "parse_answer"

    # After introduction, route to mode-specific gap identification
    if mode == "predefined_questions":
        return "analyze_resume_coverage"
    else:
        return "identify_gaps"


def route_after_greet(state: InterviewState) -> Literal["identify_gaps", "analyze_resume_coverage"]:
    """
    Route from introduce node to mode-specific gap identification.

    Args:
        state: Current interview state

    Returns:
        Node name: "identify_gaps" or "analyze_resume_coverage"
    """
    mode = state.get("mode", "dynamic_gap")
    if mode == "predefined_questions":
        return "analyze_resume_coverage"
    else:
        return "identify_gaps"
