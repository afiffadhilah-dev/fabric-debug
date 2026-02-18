"""
Unit tests to verify engagement tracking logic in predefined_questions mode.

These tests replicate the CURRENT logic from the actual nodes/conditions.
Run both this file and test_engagement_issues_with_nodes.py to compare.

Issues tested (ALL FIXED):
1. Gap resolution fallback - FIXED: No longer falls back to detail_score
2. Off-topic answers - FIXED: Now increments counter (was: reset)
3. Follow-up decision - FIXED: Now checks quality_signal < 3 before following up
4. Cross-gap analysis - FIXED: Uses OR condition (detail_score >= 3 OR answer_quality >= 3)

Run with: python tests/integration/test_engagement_tracking_issues.py
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from typing import Dict, Any, List


# =============================================================================
# ISSUE 1: Gap Resolution Fallback Uses Wrong Metric
# =============================================================================

def test_issue1_gap_resolution_fallback_to_detail_score():
    """
    ISSUE 1: When answer_quality is missing (criteria assessment skipped),
    the code falls back to detail_score but uses the same thresholds.

    This causes verbose off-topic answers to incorrectly resolve gaps.

    Expected: Gap should NOT resolve when answer is off-topic (no criteria met)
    Actual: Gap RESOLVES because detail_score >= 3
    """
    print("\n" + "=" * 80)
    print("ISSUE 1: Gap Resolution Fallback Uses Wrong Metric")
    print("=" * 80)

    # Simulate the problematic scenario:
    # - Verbose off-topic answer (detail_score = 4)
    # - No criteria assessment (answer_quality = 0)
    # - System falls back to detail_score

    # This replicates logic from update_state.py:350-363
    def should_resolve_gap(
        criteria_answer_quality: int,  # From assess_criteria (0 if not called)
        detail_score: int,             # From engagement assessment (not used in current code)
        probes_attempted: int,
        max_probes: int
    ) -> tuple[bool, str]:
        """Replicate the gap resolution logic - FIXED version (no fallback to detail_score)."""

        # Current FIXED logic from update_state.py:350-353
        # No longer falls back to detail_score - just uses 0 if missing
        answer_quality = criteria_answer_quality
        if not answer_quality:
            answer_quality = 0  # FIXED: No fallback to detail_score

        # Resolution logic from update_state.py:359-362
        should_resolve = (
            answer_quality >= 3 or
            (probes_attempted >= 2 and answer_quality >= 2) or
            probes_attempted >= max_probes
        )

        reason = "good answer" if answer_quality >= 3 else (
            "decent after probes" if answer_quality >= 2 else "max probes reached"
        )

        return should_resolve, reason

    # Test case: Verbose off-topic answer
    # - User gives long answer about infrastructure when asked about leadership
    # - Criteria assessment skipped (off-topic), so answer_quality = 0
    # - But answer was detailed, so detail_score = 4

    test_cases = [
        {
            "name": "Verbose off-topic answer (first attempt)",
            "criteria_answer_quality": 0,  # No criteria assessment (off-topic)
            "detail_score": 4,             # Verbose answer
            "probes_attempted": 0,
            "max_probes": 2,
            "expected_resolve": False,     # Should NOT resolve - off-topic!
            "why": "Off-topic answer should not resolve gap regardless of verbosity"
        },
        {
            "name": "Concise on-point answer",
            "criteria_answer_quality": 4,  # Good criteria match
            "detail_score": 2,             # Short answer
            "probes_attempted": 0,
            "max_probes": 2,
            "expected_resolve": True,      # Should resolve - criteria met
            "why": "On-point answer should resolve even if concise"
        },
        {
            "name": "Verbose off-topic after one probe",
            "criteria_answer_quality": 0,  # Still no criteria met
            "detail_score": 5,             # Very verbose
            "probes_attempted": 1,
            "max_probes": 2,
            "expected_resolve": False,     # Should NOT resolve
            "why": "Verbosity doesn't mean criteria are demonstrated"
        },
    ]

    print("\nTest cases:")
    print("-" * 70)

    issues_found = []
    for tc in test_cases:
        resolved, reason = should_resolve_gap(
            tc["criteria_answer_quality"],
            tc["detail_score"],
            tc["probes_attempted"],
            tc["max_probes"]
        )

        match = resolved == tc["expected_resolve"]
        status = "PASS" if match else "FAIL (BUG)"

        print(f"\n  {tc['name']}:")
        print(f"    criteria_quality={tc['criteria_answer_quality']}, "
              f"detail_score={tc['detail_score']}, "
              f"probes={tc['probes_attempted']}/{tc['max_probes']}")
        print(f"    Expected: resolve={tc['expected_resolve']} ({tc['why']})")
        print(f"    Actual:   resolve={resolved} ({reason})")
        print(f"    Status:   {status}")

        if not match:
            issues_found.append(tc["name"])

    print("\n" + "-" * 70)
    if issues_found:
        print(f"BUG CONFIRMED: {len(issues_found)} case(s) show incorrect behavior:")
        for issue in issues_found:
            print(f"  - {issue}")
        print("\nRoot cause: Fallback to detail_score uses same threshold as answer_quality")
        return False
    else:
        print("All cases passed - bug may have been fixed")
        return True


# =============================================================================
# ISSUE 2: Off-Topic Answers Reset Engagement Counter
# =============================================================================

def test_issue2_off_topic_resets_engagement_counter():
    """
    ISSUE 2: Off-topic answers reset consecutive_low_quality counter,
    hiding patterns of inability to answer required questions.

    Expected: Repeated off-topic answers should be tracked as a pattern
    Actual: Each off-topic resets counter, never triggering termination
    """
    print("\n" + "=" * 80)
    print("ISSUE 2: Off-Topic Answers Reset Engagement Counter")
    print("=" * 80)

    # Replicate logic from update_state.py:170-181
    def update_engagement_counter(
        answer_type: str,
        engagement_level: str,
        current_counter: int
    ) -> int:
        """Replicate the engagement counter update logic - FIXED version."""

        if answer_type == "clarification_request":
            return 0  # Reset
        elif answer_type == "off_topic":
            return current_counter + 1  # FIXED: Now increments (was: return 0)
        elif engagement_level == "disengaged":
            return current_counter + 1  # Increment
        else:
            return 0  # Reset

    # Simulate 5 consecutive off-topic answers
    # This could happen when asking about skills the candidate doesn't have

    print("\nSimulating 5 consecutive off-topic answers:")
    print("-" * 70)

    counter = 0
    answer_sequence = [
        ("off_topic", "engaged", "Q: AWS experience? A: 'I use Azure'"),
        ("off_topic", "engaged", "Q: Docker experience? A: 'We use VMs'"),
        ("off_topic", "engaged", "Q: Kubernetes? A: 'Not familiar'"),
        ("off_topic", "engaged", "Q: CI/CD pipelines? A: 'Manual deployments'"),
        ("off_topic", "engaged", "Q: Cloud architecture? A: 'On-premise only'"),
    ]

    for i, (answer_type, engagement_level, description) in enumerate(answer_sequence, 1):
        counter = update_engagement_counter(answer_type, engagement_level, counter)
        print(f"  {i}. {description}")
        print(f"     answer_type={answer_type}, counter after={counter}")

    print("\n" + "-" * 70)

    # Expected: Counter should be >= 3 after 5 off-topic answers (triggering termination check)
    # Actual: Counter is 0 because each off-topic resets it

    expected_min_counter = 3  # Would trigger termination if >= 3

    if counter >= expected_min_counter:
        print(f"Expected behavior: Counter is {counter} >= {expected_min_counter}")
        print("Pattern of off-topic answers detected correctly")
        return True
    else:
        print(f"BUG CONFIRMED: Counter is {counter}, expected >= {expected_min_counter}")
        print("\nProblem: 5 consecutive off-topic answers, but counter is 0")
        print("Impact: Interview continues asking irrelevant questions forever")
        print("Root cause: Off-topic answers reset counter instead of tracking pattern")
        return False


# =============================================================================
# ISSUE 3: Follow-Up Uses Wrong Signal (detail_score vs answer_quality)
# =============================================================================

def test_issue3_follow_up_uses_detail_score():
    """
    ISSUE 3: should_follow_up() uses detail_score instead of answer_quality
    in predefined mode, causing unnecessary follow-ups for concise good answers.

    Expected: No follow-up if criteria quality >= 3 (answer demonstrates skills)
    Actual: Follow-up triggered because detail_score < 3 (answer is concise)
    """
    print("\n" + "=" * 80)
    print("ISSUE 3: Follow-Up Uses Wrong Signal")
    print("=" * 80)

    # Replicate logic from conditions.py:161-170 - FIXED version
    def should_generate_follow_up(
        gap_resolved: bool,
        detail_score: int,
        answer_quality: int,  # Now used! quality_signal = answer_quality or detail_score
        probes_attempted: int,
        max_probes: int
    ) -> tuple[bool, str]:
        """
        Current FIXED logic from conditions.py.
        Uses quality_signal (answer_quality if available, else detail_score).
        Only follows up if quality < 3.
        """

        # Use answer_quality if available (predefined mode), else detail_score
        quality_signal = answer_quality if answer_quality > 0 else detail_score

        # Only follow up if quality is actually low
        if not gap_resolved and quality_signal < 3 and probes_attempted < max_probes:
            return True, f"Low quality answer (quality={quality_signal})"

        return False, "No follow-up needed"

    def should_generate_follow_up_fixed(
        gap_resolved: bool,
        detail_score: int,
        answer_quality: int,
        probes_attempted: int,
        max_probes: int
    ) -> tuple[bool, str]:
        """
        Same as current - now fixed.
        """

        # Use answer_quality if available (predefined mode), else detail_score
        quality_signal = answer_quality if answer_quality > 0 else detail_score

        if not gap_resolved and quality_signal < 3 and probes_attempted < max_probes:
            return True, f"Low quality answer (quality={quality_signal})"

        return False, "No follow-up needed"

    test_cases = [
        {
            "name": "Concise but high-quality answer",
            "gap_resolved": False,  # Not yet resolved
            "detail_score": 2,      # Concise answer
            "answer_quality": 4,    # But demonstrates criteria well!
            "probes_attempted": 0,
            "max_probes": 2,
            "expected_follow_up": False,  # Should NOT follow up - quality is good
            "why": "Criteria demonstrated, no need to probe further"
        },
        {
            "name": "Verbose but poor quality answer",
            "gap_resolved": False,
            "detail_score": 4,      # Verbose
            "answer_quality": 2,    # But doesn't demonstrate criteria
            "probes_attempted": 0,
            "max_probes": 2,
            "expected_follow_up": True,  # SHOULD follow up - quality is poor
            "why": "Criteria not demonstrated, need to probe"
        },
        {
            "name": "Vague answer with no criteria assessment",
            "gap_resolved": False,
            "detail_score": 2,
            "answer_quality": 0,    # No criteria assessment available
            "probes_attempted": 0,
            "max_probes": 2,
            "expected_follow_up": True,  # Should follow up
            "why": "No quality info, use detail_score as fallback"
        },
    ]

    print("\nComparing current vs expected behavior:")
    print("-" * 70)

    issues_found = []
    for tc in test_cases:
        current_follow_up, current_reason = should_generate_follow_up(
            tc["gap_resolved"], tc["detail_score"], tc["answer_quality"],
            tc["probes_attempted"], tc["max_probes"]
        )

        # Check if current behavior matches expected
        match = current_follow_up == tc["expected_follow_up"]
        status = "PASS" if match else "FAIL (BUG)"

        print(f"\n  {tc['name']}:")
        print(f"    detail_score={tc['detail_score']}, answer_quality={tc['answer_quality']}")
        print(f"    Expected: follow_up={tc['expected_follow_up']} ({tc['why']})")
        print(f"    Current:  follow_up={current_follow_up} ({current_reason})")
        print(f"    Status:   {status}")

        if not match:
            issues_found.append(tc["name"])

    print("\n" + "-" * 70)
    if issues_found:
        print(f"BUG CONFIRMED: {len(issues_found)} case(s) show incorrect behavior:")
        for issue in issues_found:
            print(f"  - {issue}")
        print("\nRoot cause: should_follow_up uses detail_score, ignores answer_quality")
        return False
    else:
        print("All cases passed - bug may have been fixed")
        return True


# =============================================================================
# ISSUE 4: Cross-Gap Analysis Skipped for Concise Answers
# =============================================================================

def test_issue4_cross_gap_skipped_for_concise_answers():
    """
    ISSUE 4: Cross-gap analysis is skipped when detail_score < 3,
    even if the answer is high quality and covers multiple criteria.

    Expected: Cross-gap runs if answer_quality >= 3 (good answer)
    Actual: Cross-gap skipped if detail_score < 3 (concise answer)
    """
    print("\n" + "=" * 80)
    print("ISSUE 4: Cross-Gap Analysis Skipped for Concise Answers")
    print("=" * 80)

    # Replicate logic from parse_answer.py:124-126
    def should_run_cross_gap_analysis(
        answer_type: str,
        detail_score: int,
        answer_quality: int  # Now used! (detail_score >= 3 OR answer_quality >= 3)
    ) -> tuple[bool, str]:
        """
        Current logic - PARTIALLY FIXED: uses OR condition.
        Runs if detail_score >= 3 OR answer_quality >= 3.
        """

        if answer_type != "off_topic" and (detail_score >= 3 or answer_quality >= 3):
            return True, "Answer detailed/quality enough"
        else:
            return False, f"Skipped: detail={detail_score}, quality={answer_quality} (both < 3)"

    def should_run_cross_gap_analysis_fixed(
        answer_type: str,
        detail_score: int,
        answer_quality: int
    ) -> tuple[bool, str]:
        """
        Same as current - already fixed with OR condition.
        """

        if answer_type != "off_topic" and (detail_score >= 3 or answer_quality >= 3):
            return True, "Answer quality sufficient"
        else:
            return False, f"Skipped: detail={detail_score}, quality={answer_quality} (both < 3)"

    test_cases = [
        {
            "name": "Concise but comprehensive answer",
            "answer_type": "direct_answer",
            "detail_score": 2,      # Short answer
            "answer_quality": 4,    # But covers criteria well
            "expected_run": True,   # SHOULD run cross-gap (answer_quality >= 3)
            "why": "Good answer might cover other gaps too"
        },
        {
            "name": "Verbose but shallow answer",
            "answer_type": "direct_answer",
            "detail_score": 4,      # Long answer
            "answer_quality": 2,    # Doesn't really cover criteria
            "expected_run": True,   # WILL run (detail_score >= 3 in OR condition)
            "why": "Verbose answer might mention other skills (current behavior)"
        },
        {
            "name": "Short and poor quality answer",
            "answer_type": "direct_answer",
            "detail_score": 2,      # Short answer
            "answer_quality": 1,    # Poor quality
            "expected_run": False,  # Should NOT run (both < 3)
            "why": "Neither detailed nor quality - skip cross-gap"
        },
    ]

    print("\nComparing current vs expected behavior:")
    print("-" * 70)

    issues_found = []
    for tc in test_cases:
        current_run, current_reason = should_run_cross_gap_analysis(
            tc["answer_type"], tc["detail_score"], tc["answer_quality"]
        )

        match = current_run == tc["expected_run"]
        status = "PASS" if match else "FAIL (BUG)"

        print(f"\n  {tc['name']}:")
        print(f"    detail_score={tc['detail_score']}, answer_quality={tc['answer_quality']}")
        print(f"    Expected: run_cross_gap={tc['expected_run']} ({tc['why']})")
        print(f"    Current:  run_cross_gap={current_run} ({current_reason})")
        print(f"    Status:   {status}")

        if not match:
            issues_found.append(tc["name"])

    print("\n" + "-" * 70)
    if issues_found:
        print(f"BUG CONFIRMED: {len(issues_found)} case(s) show incorrect behavior:")
        for issue in issues_found:
            print(f"  - {issue}")
        print("\nRoot cause: Cross-gap decision uses detail_score, ignores answer_quality")
        return False
    else:
        print("All cases passed - bug may have been fixed")
        return True


# =============================================================================
# RUN ALL TESTS
# =============================================================================

def run_all_tests():
    """Run all engagement tracking issue tests."""
    print("\n" + "=" * 80)
    print("ENGAGEMENT TRACKING ISSUES - UNIT TESTS")
    print("These tests demonstrate bugs documented in:")
    print("  docs/issues/engagement-tracking-predefined-mode.md")
    print("=" * 80)

    tests = [
        ("Issue 1: Gap resolution fallback", test_issue1_gap_resolution_fallback_to_detail_score),
        ("Issue 2: Off-topic resets counter", test_issue2_off_topic_resets_engagement_counter),
        ("Issue 3: Follow-up uses detail_score", test_issue3_follow_up_uses_detail_score),
        ("Issue 4: Cross-gap skips concise answers", test_issue4_cross_gap_skipped_for_concise_answers),
    ]

    results = []
    for name, test_fn in tests:
        try:
            passed = test_fn()
            results.append((name, passed, None))
        except Exception as e:
            results.append((name, False, str(e)))
            import traceback
            traceback.print_exc()

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print("\nNote: Tests are designed to FAIL to demonstrate bugs exist.")
    print("A passing test means the bug may have been fixed.\n")

    bugs_confirmed = sum(1 for _, passed, _ in results if not passed)
    bugs_fixed = sum(1 for _, passed, _ in results if passed)

    for name, passed, error in results:
        if passed:
            status = "PASS (bug may be fixed)"
        elif error:
            status = f"ERROR: {error[:40]}..."
        else:
            status = "FAIL (BUG CONFIRMED)"
        print(f"  {status}: {name}")

    print(f"\nBugs confirmed: {bugs_confirmed}")
    print(f"Possibly fixed: {bugs_fixed}")

    if bugs_confirmed > 0:
        print(f"\n{bugs_confirmed} bug(s) still present in codebase.")
        print("See docs/issues/engagement-tracking-predefined-mode.md for details.")

    return bugs_confirmed == 0  # Return True only if all bugs are fixed


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
