
from typing import Dict, Any
from agents.conversational.state import InterviewState, Gap
from agents.conversational.conditions import get_gap_identifier


def calculate_effective_max_probes(gap: Gap) -> int:
    """
    Calculate effective max_probes based on probe history patterns.

    Adjusts the limit intelligently:
    - If last 3 probes are "clarification_request" → User is engaged, give +2 more chances
    - If last 2 probes are "off_topic" → User doesn't have this info, stop immediately
    - Otherwise → Use base max_probes

    Args:
        gap: The gap to calculate effective limit for

    Returns:
        Effective max_probes (adjusted based on history)
    """
    base_max = gap.get("max_probes", 3)
    history = gap.get("probe_history", [])

    if len(history) < 2:
        # Not enough history, use base limit
        return base_max

    # Pattern 1: Last 3 are ALL clarification requests → User is trying hard, increase limit
    if len(history) >= 3 and history[-3:] == ["clarification_request"] * 3:
        adjusted_max = base_max + 2
        print(f"     📈 Intelligent limit: User asking for clarification 3x → Increased limit to {adjusted_max} (base: {base_max})")
        return adjusted_max

    # Pattern 2: Last 2 are ALL off-topic → User doesn't have this info, stop now
    if len(history) >= 2 and history[-2:] == ["off_topic"] * 2:
        # Stop immediately by setting effective max to current attempts
        adjusted_max = gap.get("probes_attempted", 0)
        print(f"     📉 Intelligent limit: User off-topic 2x → Stop asking (limit: {adjusted_max})")
        return adjusted_max

    # Pattern 3: Last 2 are "partial_answer" + "partial_answer" (disengaged) → Reduce by 1
    if len(history) >= 2 and history[-2:] == ["partial_answer", "partial_answer"]:
        adjusted_max = max(base_max - 1, 2)  # At least give 2 chances
        print(f"     ⚖️  Intelligent limit: 2 partial answers → Reduced to {adjusted_max} (base: {base_max})")
        return adjusted_max

    # Default: Use base max
    return base_max


def select_gap_node(state: InterviewState) -> Dict[str, Any]:
    """
    Select the next gap to address.

    Selects the highest-severity unresolved gap that hasn't been
    probed too many times.

    For predefined_questions mode, also handles:
    - resume_filled gaps: Skip entirely
    - interview_filled gaps (high confidence >= 0.9): Skip
    - interview_filled gaps (low confidence < 0.9): May ask follow-up

    Returns:
        Dictionary with current_gap update
    """
    identified_gaps = state.get("identified_gaps", [])
    resolved_gaps = state.get("resolved_gaps", [])
    mode = state.get("mode", "dynamic_gap")

    # Get IDs of resolved gaps for filtering
    resolved_identifiers = {get_gap_identifier(gap) for gap in resolved_gaps}

    # Filter to unresolved gaps that can still be probed (with intelligent limits)
    available_gaps = []
    low_confidence_gaps = []  # interview_filled with low confidence (may need follow-up)

    for gap in identified_gaps:
        gap_id = get_gap_identifier(gap)

        # Skip resolved gaps
        if gap_id in resolved_identifiers:
            continue

        # For predefined mode: handle resume_filled, interview_filled, and skipped
        if mode == "predefined_questions":
            # Skip gaps that user explicitly skipped
            if gap.get("skipped"):
                skip_reason = gap.get("skip_reason", "unknown")
                print(f"🚫 Skipping gap (user skipped: {skip_reason}): {gap.get('category')}")
                continue

            # Skip resume-filled gaps
            if gap.get("resume_filled"):
                continue

            # Handle interview-filled gaps (from cross-gap detection)
            if gap.get("interview_filled"):
                confidence = gap.get("coverage_confidence", 0.0)
                if confidence >= 0.9:
                    # High confidence: skip entirely
                    print(f"   ⏭️  Skipping gap (interview_filled, confidence={confidence:.2f}): {gap.get('category')}")
                    continue
                else:
                    # Low confidence: may ask follow-up later
                    low_confidence_gaps.append(gap)
                    print(f"   📝 Gap pre-filled with low confidence ({confidence:.2f}): {gap.get('category')}")
                    continue

        # Calculate effective max_probes based on probe history
        effective_max = calculate_effective_max_probes(gap)

        # Check if gap can still be probed
        if gap["probes_attempted"] < effective_max:
            available_gaps.append(gap)
        elif gap["probes_attempted"] >= gap["max_probes"]:
            # Gap exhausted its base limit
            continue
        else:
            # Intelligently stopped early
            print(f"   ⏭️  Skipping gap (intelligent limit reached): {gap_id}")

    if not available_gaps:
        # No regular gaps available - check if we have low-confidence pre-filled gaps
        if low_confidence_gaps and mode == "predefined_questions":
            # Sort by confidence (lowest first - ask about least certain ones)
            low_confidence_gaps.sort(key=lambda g: g.get("coverage_confidence", 0.0))
            selected_gap = low_confidence_gaps[0]
            print(f"   🔄 Selecting low-confidence gap for follow-up: {selected_gap.get('category')}")
            return {"current_gap": selected_gap}

        # No gaps available at all
        return {"current_gap": None}

    # Sort by severity (highest first)
    available_gaps.sort(key=lambda g: g["severity"], reverse=True)

    # Select highest severity gap
    selected_gap = available_gaps[0]

    return {"current_gap": selected_gap}
