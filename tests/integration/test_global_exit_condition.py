"""
Integration tests for global exit condition logic.

Tests the should_continue_interview() function to verify:
1. Predefined mode: Continues until all questions asked or user disengages
2. Dynamic mode: Stops at completeness threshold
3. Disengagement detection works correctly in both modes

Run with: python tests/integration/test_global_exit_condition.py
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from typing import Dict, Any, List


# =============================================================================
# HELPER: Create test states
# =============================================================================

def create_test_state(
    mode: str = "predefined_questions",
    completeness_score: float = 0.0,
    minimum_completeness: float = 0.6,
    consecutive_low_quality: int = 0,
    identified_gaps: List[Dict] = None,
    resolved_gaps: List[Dict] = None,
) -> Dict[str, Any]:
    """Create a test state for global exit condition testing."""

    if identified_gaps is None:
        # Default: 5 gaps, none resolved
        identified_gaps = [
            {
                "question_id": f"gap-{i}",
                "question_text": f"Question {i}",
                "category": f"CATEGORY_{i}",
                "what_assesses": [f"Skill {i}"],
                "probes_attempted": 0,
                "max_probes": 2,
            }
            for i in range(5)
        ]

    return {
        "mode": mode,
        "completeness_score": completeness_score,
        "minimum_completeness": minimum_completeness,
        "consecutive_low_quality": consecutive_low_quality,
        "identified_gaps": identified_gaps,
        "resolved_gaps": resolved_gaps or [],
        "termination_reason": None,
    }


# =============================================================================
# TEST 1: Predefined mode does NOT stop at completeness threshold
# =============================================================================

def test_predefined_mode_continues_past_threshold():
    """
    PREDEFINED MODE: Should continue even when completeness >= minimum.

    The interview should only stop when:
    - User disengages (3+ consecutive low quality)
    - No more questions remaining
    """
    print("\n" + "=" * 80)
    print("TEST 1: Predefined mode continues past completeness threshold")
    print("=" * 80)

    from agents.conversational.conditions import should_continue_interview

    # Scenario: 65% complete, user engaged, 3 gaps remaining
    state = create_test_state(
        mode="predefined_questions",
        completeness_score=0.65,  # Above 60% threshold
        minimum_completeness=0.6,
        consecutive_low_quality=0,  # User is engaged
        identified_gaps=[
            {"question_id": f"gap-{i}", "question_text": f"Q{i}", "category": "CAT",
             "what_assesses": ["Skill"], "probes_attempted": 0, "max_probes": 2}
            for i in range(5)
        ],
        resolved_gaps=[
            {"question_id": "gap-0", "question_text": "Q0", "category": "CAT",
             "what_assesses": ["Skill"], "probes_attempted": 1, "max_probes": 2},
            {"question_id": "gap-1", "question_text": "Q1", "category": "CAT",
             "what_assesses": ["Skill"], "probes_attempted": 1, "max_probes": 2},
        ],  # 2 resolved, 3 remaining
    )

    print(f"\nInput state:")
    print(f"  mode: {state['mode']}")
    print(f"  completeness: {state['completeness_score']:.0%} (threshold: {state['minimum_completeness']:.0%})")
    print(f"  consecutive_low_quality: {state['consecutive_low_quality']}")
    print(f"  gaps: {len(state['identified_gaps'])} total, {len(state['resolved_gaps'])} resolved")

    result = should_continue_interview(state)

    print(f"\nResult: {result}")
    print(f"Termination reason: {state.get('termination_reason')}")

    print("\n" + "-" * 70)
    if result == "select_gap":
        print("✅ PASS: Predefined mode correctly continues past completeness threshold")
        return True
    else:
        print("❌ FAIL: Predefined mode incorrectly stopped at completeness threshold")
        print("  Expected: select_gap (continue)")
        print(f"  Actual: {result}")
        return False


# =============================================================================
# TEST 2: Predefined mode stops when user disengaged
# =============================================================================

def test_predefined_mode_stops_on_disengagement():
    """
    PREDEFINED MODE: Should stop when user shows disengagement.

    3+ consecutive low quality answers = disengaged
    """
    print("\n" + "=" * 80)
    print("TEST 2: Predefined mode stops on disengagement")
    print("=" * 80)

    from agents.conversational.conditions import should_continue_interview

    # Scenario: 30% complete, user disengaged, gaps remaining
    state = create_test_state(
        mode="predefined_questions",
        completeness_score=0.30,
        consecutive_low_quality=3,  # DISENGAGED
        identified_gaps=[
            {"question_id": f"gap-{i}", "question_text": f"Q{i}", "category": "CAT",
             "what_assesses": ["Skill"], "probes_attempted": 0, "max_probes": 2}
            for i in range(5)
        ],
        resolved_gaps=[],
    )

    print(f"\nInput state:")
    print(f"  mode: {state['mode']}")
    print(f"  completeness: {state['completeness_score']:.0%}")
    print(f"  consecutive_low_quality: {state['consecutive_low_quality']} (DISENGAGED)")
    print(f"  gaps remaining: {len(state['identified_gaps'])}")

    result = should_continue_interview(state)

    print(f"\nResult: {result}")
    print(f"Termination reason: {state.get('termination_reason')}")

    print("\n" + "-" * 70)
    if result == "finalize" and state.get("termination_reason") == "disengaged":
        print("✅ PASS: Predefined mode correctly stops on disengagement")
        return True
    else:
        print("❌ FAIL: Predefined mode did not stop on disengagement")
        return False


# =============================================================================
# TEST 3: Predefined mode stops when no gaps remaining
# =============================================================================

def test_predefined_mode_stops_when_no_gaps():
    """
    PREDEFINED MODE: Should stop when all questions have been asked.
    """
    print("\n" + "=" * 80)
    print("TEST 3: Predefined mode stops when no gaps remaining")
    print("=" * 80)

    from agents.conversational.conditions import should_continue_interview

    gaps = [
        {"question_id": f"gap-{i}", "question_text": f"Q{i}", "category": "CAT",
         "what_assesses": ["Skill"], "probes_attempted": 2, "max_probes": 2}
        for i in range(3)
    ]

    # Scenario: All gaps resolved
    state = create_test_state(
        mode="predefined_questions",
        completeness_score=0.85,
        consecutive_low_quality=0,
        identified_gaps=gaps,
        resolved_gaps=gaps.copy(),  # All resolved
    )

    print(f"\nInput state:")
    print(f"  mode: {state['mode']}")
    print(f"  completeness: {state['completeness_score']:.0%}")
    print(f"  gaps: {len(state['identified_gaps'])} total, ALL resolved")

    result = should_continue_interview(state)

    print(f"\nResult: {result}")
    print(f"Termination reason: {state.get('termination_reason')}")

    print("\n" + "-" * 70)
    if result == "finalize" and state.get("termination_reason") == "no_gaps":
        print("✅ PASS: Predefined mode correctly stops when no gaps remaining")
        return True
    else:
        print("❌ FAIL: Predefined mode did not stop when no gaps remaining")
        return False


# =============================================================================
# TEST 4: Dynamic mode stops at completeness threshold
# =============================================================================

def test_dynamic_mode_stops_at_threshold():
    """
    DYNAMIC MODE: Should stop when completeness >= minimum_completeness.
    """
    print("\n" + "=" * 80)
    print("TEST 4: Dynamic mode stops at completeness threshold")
    print("=" * 80)

    from agents.conversational.conditions import should_continue_interview

    # Scenario: 65% complete, user engaged, gaps remaining
    state = create_test_state(
        mode="dynamic_gap",  # Dynamic mode
        completeness_score=0.65,
        minimum_completeness=0.6,
        consecutive_low_quality=0,
        identified_gaps=[
            {"question_id": f"gap-{i}", "question_text": f"Q{i}", "category": "CAT",
             "what_assesses": ["Skill"], "probes_attempted": 0, "max_probes": 2}
            for i in range(5)
        ],
        resolved_gaps=[],
    )

    print(f"\nInput state:")
    print(f"  mode: {state['mode']}")
    print(f"  completeness: {state['completeness_score']:.0%} (threshold: {state['minimum_completeness']:.0%})")
    print(f"  user engaged: yes")
    print(f"  gaps remaining: {len(state['identified_gaps'])}")

    result = should_continue_interview(state)

    print(f"\nResult: {result}")
    print(f"Termination reason: {state.get('termination_reason')}")

    print("\n" + "-" * 70)
    if result == "finalize" and state.get("termination_reason") == "complete":
        print("✅ PASS: Dynamic mode correctly stops at completeness threshold")
        return True
    else:
        print("❌ FAIL: Dynamic mode did not stop at completeness threshold")
        return False


# =============================================================================
# TEST 5: Dynamic mode continues below threshold
# =============================================================================

def test_dynamic_mode_continues_below_threshold():
    """
    DYNAMIC MODE: Should continue when completeness < minimum_completeness.
    """
    print("\n" + "=" * 80)
    print("TEST 5: Dynamic mode continues below threshold")
    print("=" * 80)

    from agents.conversational.conditions import should_continue_interview

    # Scenario: 45% complete, user engaged, gaps remaining
    state = create_test_state(
        mode="dynamic_gap",
        completeness_score=0.45,  # Below threshold
        minimum_completeness=0.6,
        consecutive_low_quality=0,
        identified_gaps=[
            {"question_id": f"gap-{i}", "question_text": f"Q{i}", "category": "CAT",
             "what_assesses": ["Skill"], "probes_attempted": 0, "max_probes": 2}
            for i in range(5)
        ],
        resolved_gaps=[],
    )

    print(f"\nInput state:")
    print(f"  mode: {state['mode']}")
    print(f"  completeness: {state['completeness_score']:.0%} (threshold: {state['minimum_completeness']:.0%})")
    print(f"  user engaged: yes")

    result = should_continue_interview(state)

    print(f"\nResult: {result}")

    print("\n" + "-" * 70)
    if result == "select_gap":
        print("✅ PASS: Dynamic mode correctly continues below threshold")
        return True
    else:
        print("❌ FAIL: Dynamic mode incorrectly stopped below threshold")
        return False


# =============================================================================
# RUN ALL TESTS
# =============================================================================

def run_all_tests():
    """Run all global exit condition tests."""
    print("\n" + "=" * 80)
    print("GLOBAL EXIT CONDITION - INTEGRATION TESTS")
    print("=" * 80)

    tests = [
        ("Predefined: continues past threshold", test_predefined_mode_continues_past_threshold),
        ("Predefined: stops on disengagement", test_predefined_mode_stops_on_disengagement),
        ("Predefined: stops when no gaps", test_predefined_mode_stops_when_no_gaps),
        ("Dynamic: stops at threshold", test_dynamic_mode_stops_at_threshold),
        ("Dynamic: continues below threshold", test_dynamic_mode_continues_below_threshold),
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

    passed = sum(1 for _, p, _ in results if p)
    failed = sum(1 for _, p, e in results if not p and e is None)
    errors = sum(1 for _, _, e in results if e is not None)

    for name, p, error in results:
        if error:
            status = f"❌ ERROR: {error[:40]}..."
        elif p:
            status = "✅ PASS"
        else:
            status = "❌ FAIL"
        print(f"  {status}: {name}")

    print(f"\nPassed: {passed}/{len(results)}")
    print(f"Failed: {failed}")
    print(f"Errors: {errors}")

    return failed == 0 and errors == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
