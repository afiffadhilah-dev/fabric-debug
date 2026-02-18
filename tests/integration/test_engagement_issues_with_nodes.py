"""
Integration tests for engagement tracking issues - runs ACTUAL agent nodes.

These tests invoke the real update_state_node, parse_answer_node, and conditions
to demonstrate bugs documented in:
docs/issues/engagement-tracking-predefined-mode.md

Run with: python tests/integration/test_engagement_issues_with_nodes.py
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from typing import Dict, Any, List
from copy import deepcopy


# =============================================================================
# HELPER: Create base state for predefined mode
# =============================================================================

def create_predefined_mode_state(
    tool_results: Dict[str, Any] = None,
    current_gap: Dict[str, Any] = None,
    resolved_gaps: List[Dict] = None,
    consecutive_low_quality: int = 0,
    identified_gaps: List[Dict] = None,
    completeness_score: float = 0.0,
    messages: List = None,
) -> Dict[str, Any]:
    """Create a base state for predefined_questions mode testing."""
    from langchain_core.messages import AIMessage, HumanMessage

    default_gap = {
        "question_id": "test-gap-001",
        "question_text": "Tell me about your leadership experience",
        "category": "LEADERSHIP EXPERIENCE",
        "what_assesses": ["People leadership", "Decision-making skills"],
        "probes_attempted": 0,
        "max_probes": 2,
        "severity": 0.8,
        "resume_filled": False,
        "interview_filled": False,
    }

    default_messages = [
        AIMessage(content="Tell me about your leadership experience."),
        HumanMessage(content="I have led teams before."),
    ]

    return {
        "mode": "predefined_questions",
        "session_id": "test-session-001",
        "messages": messages or default_messages,
        "current_gap": current_gap or default_gap,
        "current_question": {
            "question_id": (current_gap or default_gap)["question_id"],
            "question_text": (current_gap or default_gap)["question_text"],
            "skill_name": "LEADERSHIP",
            "attribute": "People leadership",
            "gap_description": "Leadership experience assessment",
            "category": (current_gap or default_gap).get("category", "LEADERSHIP EXPERIENCE"),
            "what_assesses": (current_gap or default_gap).get("what_assesses", ["People leadership"]),
        },
        "tool_results": tool_results or {},
        "resolved_gaps": resolved_gaps or [],
        "identified_gaps": identified_gaps or [current_gap or default_gap],
        "all_predefined_gaps": identified_gaps or [current_gap or default_gap],
        "extracted_skills": [],
        "engagement_signals": [],
        "consecutive_low_quality": consecutive_low_quality,
        "completeness_score": completeness_score,
        "minimum_completeness": 0.9,
        "questions_asked": 1,
    }


# =============================================================================
# ISSUE 1: Gap Resolution Fallback - ACTUAL NODE TEST
# =============================================================================

def test_issue1_gap_resolution_actual_node():
    """
    ISSUE 1: Run update_state_node with off-topic verbose answer.

    When criteria assessment is skipped (off-topic), the code falls back to
    detail_score but uses answer_quality thresholds.

    Expected: Gap should NOT resolve (off-topic = no criteria demonstrated)
    Actual (BUG): Gap RESOLVES because detail_score >= 3
    """
    print("\n" + "=" * 80)
    print("ISSUE 1: Gap Resolution Fallback - Running ACTUAL update_state_node")
    print("=" * 80)

    from agents.conversational.nodes.update_state import update_state_node

    # Scenario: User gives verbose but off-topic answer
    # - Criteria assessment was SKIPPED (answer_type = off_topic)
    # - So tool_results["criteria"] is empty/missing
    # - But engagement shows detail_score = 4 (verbose answer)

    state = create_predefined_mode_state(
        tool_results={
            "engagement": {
                "answer_type": "off_topic",  # Off-topic answer
                "detail_score": 4,           # But verbose!
                "engagement_level": "engaged",
            },
            # NOTE: No "criteria" key - criteria assessment was skipped for off-topic
            "skills": [],
        },
        current_gap={
            "question_id": "test-gap-001",
            "question_text": "Tell me about your leadership experience",
            "category": "LEADERSHIP EXPERIENCE",
            "what_assesses": ["People leadership", "Decision-making skills"],
            "probes_attempted": 0,
            "max_probes": 2,
            "severity": 0.8,
        },
    )

    print("\nInput state:")
    print(f"  mode: {state['mode']}")
    print(f"  answer_type: off_topic")
    print(f"  detail_score: 4 (verbose)")
    print(f"  criteria assessment: SKIPPED (no 'criteria' in tool_results)")
    print(f"  current_gap: {state['current_gap']['question_text'][:50]}...")
    print(f"  resolved_gaps before: {len(state['resolved_gaps'])}")

    # Run the actual node
    print("\n>>> Running update_state_node()...")
    result = update_state_node(state)

    resolved_gaps = result.get("resolved_gaps", [])
    print(f"\nOutput:")
    print(f"  resolved_gaps after: {len(resolved_gaps)}")

    # Check if gap was incorrectly resolved
    gap_resolved = len(resolved_gaps) > 0

    print("\n" + "-" * 70)
    if gap_resolved:
        print("BUG CONFIRMED: Gap was resolved despite off-topic answer!")
        print("  Root cause: Fallback to detail_score (4) >= 3 triggers resolution")
        print("  Expected: Off-topic answer should NOT resolve gap")
        return False
    else:
        print("PASS: Gap correctly NOT resolved for off-topic answer")
        return True


def test_issue1b_gap_resolution_criteria_zero():
    """
    ISSUE 1b: Run update_state_node when answer_quality = 0.

    Tests the fallback when criteria assessment returns 0.
    """
    print("\n" + "=" * 80)
    print("ISSUE 1b: Gap Resolution - answer_quality=0 fallback")
    print("=" * 80)

    from agents.conversational.nodes.update_state import update_state_node

    state = create_predefined_mode_state(
        tool_results={
            "engagement": {
                "answer_type": "partial_answer",
                "detail_score": 4,
                "engagement_level": "engaged",
            },
            "criteria": {
                "answer_quality": 0,  # Criteria assessment returned 0
                "criteria_assessed": [],
            },
            "skills": [],
        },
        current_gap={
            "question_id": "test-gap-002",
            "question_text": "Describe your system design experience",
            "category": "SYSTEM DESIGN",
            "what_assesses": ["Architecture skills"],
            "probes_attempted": 0,
            "max_probes": 2,
        },
    )

    print("\nInput state:")
    print(f"  answer_type: partial_answer")
    print(f"  detail_score: 4")
    print(f"  answer_quality: 0 (criteria assessment returned 0)")
    print(f"  resolved_gaps before: {len(state['resolved_gaps'])}")

    print("\n>>> Running update_state_node()...")
    result = update_state_node(state)
    resolved_gaps = result.get("resolved_gaps", [])

    print(f"\nOutput:")
    print(f"  resolved_gaps after: {len(resolved_gaps)}")

    gap_resolved = len(resolved_gaps) > 0

    print("\n" + "-" * 70)
    if gap_resolved:
        print("BUG CONFIRMED: Gap resolved with answer_quality=0!")
        print("  Root cause: Fallback to detail_score when answer_quality=0")
        return False
    else:
        print("PASS: Gap correctly NOT resolved when answer_quality=0")
        return True


# =============================================================================
# ISSUE 2: Off-Topic Resets Counter - ACTUAL NODE TEST
# =============================================================================

def test_issue2_off_topic_resets_counter_actual_node():
    """
    ISSUE 2: Run update_state_node repeatedly with off-topic answers.

    Expected: Counter should increment (or at least not reset)
    Actual (BUG): Counter resets to 0 on each off-topic answer
    """
    print("\n" + "=" * 80)
    print("ISSUE 2: Off-Topic Resets Counter - Running ACTUAL update_state_node")
    print("=" * 80)

    from agents.conversational.nodes.update_state import update_state_node

    # Simulate 5 consecutive off-topic answers
    consecutive_low_quality = 0
    gaps = [
        {"question_id": f"gap-{i}", "question_text": f"Question about skill {i}",
         "category": f"CATEGORY_{i}", "what_assesses": [f"Skill {i}"],
         "probes_attempted": 0, "max_probes": 2}
        for i in range(5)
    ]

    print("\nSimulating 5 consecutive off-topic answers with ACTUAL node:")
    print("-" * 70)

    for i, gap in enumerate(gaps):
        state = create_predefined_mode_state(
            tool_results={
                "engagement": {
                    "answer_type": "off_topic",
                    "detail_score": 3,
                    "engagement_level": "engaged",
                },
                "skills": [],
            },
            current_gap=gap,
            consecutive_low_quality=consecutive_low_quality,
            identified_gaps=gaps,
        )

        result = update_state_node(state)
        consecutive_low_quality = result.get("consecutive_low_quality", 0)

        print(f"  {i+1}. Question: {gap['question_text']}")
        print(f"     answer_type=off_topic, counter after={consecutive_low_quality}")

    print("\n" + "-" * 70)

    if consecutive_low_quality >= 3:
        print(f"PASS: Counter is {consecutive_low_quality}, pattern detected")
        return True
    else:
        print(f"BUG CONFIRMED: Counter is {consecutive_low_quality} after 5 off-topic answers!")
        print("  Root cause: Off-topic answers reset counter to 0")
        print("  Expected: Counter >= 3 to detect inability to answer")
        return False


# =============================================================================
# ISSUE 3: Follow-Up Uses Wrong Signal - ACTUAL CONDITIONS TEST
# =============================================================================

def test_issue3_follow_up_actual_conditions():
    """
    ISSUE 3: Run should_follow_up with high quality but low detail_score.

    Expected: No follow-up (answer_quality >= 3 = good answer)
    Actual (BUG): Follow-up triggered (detail_score < 3 = concise)
    """
    print("\n" + "=" * 80)
    print("ISSUE 3: Follow-Up Wrong Signal - Running ACTUAL should_follow_up")
    print("=" * 80)

    from agents.conversational.conditions import should_follow_up
    from agents.conversational.nodes.update_state import update_state_node

    # Scenario: Concise but high-quality answer
    state = create_predefined_mode_state(
        tool_results={
            "engagement": {
                "answer_type": "direct_answer",
                "detail_score": 2,  # Concise
                "engagement_level": "engaged",
            },
            "criteria": {
                "answer_quality": 4,  # High quality!
                "criteria_assessed": [
                    {"criterion": "People leadership", "demonstrated": True, "evidence": "Led team of 5"},
                ],
            },
        },
        current_gap={
            "question_id": "test-gap-003",
            "question_text": "Tell me about leadership",
            "category": "LEADERSHIP",
            "what_assesses": ["People leadership"],
            "probes_attempted": 0,
            "max_probes": 2,
        },
        resolved_gaps=[],  # Gap not yet resolved
    )

    print("\nInput state:")
    print(f"  answer_type: direct_answer")
    print(f"  detail_score: 2 (concise)")
    print(f"  answer_quality: 4 (high quality - from criteria assessment)")
    print(f"  gap_resolved: False")
    print(f"  probes_attempted: 0")

    # Ensure state reflects any gap-resolution logic before making follow-up decision
    update_result = update_state_node(state)
    state.update(update_result)

    print("\n>>> Running should_follow_up()...")
    result = should_follow_up(state)

    print(f"\nOutput:")
    print(f"  should_follow_up returned: '{result}'")

    print("\n" + "-" * 70)

    if result == "generate_follow_up":
        print("BUG CONFIRMED: Follow-up triggered despite high answer_quality!")
        print("  Root cause: Condition uses detail_score < 3, ignores answer_quality")
        print("  Expected: No follow-up needed - answer demonstrates criteria")
        return False
    else:
        print(f"PASS: Correct decision '{result}' based on answer quality")
        return True


def test_issue3b_verbose_poor_quality():
    """
    ISSUE 3b: Verbose but poor quality answer - should trigger follow-up.
    """
    print("\n" + "=" * 80)
    print("ISSUE 3b: Verbose Poor Quality - Running ACTUAL should_follow_up")
    print("=" * 80)

    from agents.conversational.conditions import should_follow_up
    from agents.conversational.nodes.update_state import update_state_node

    state = create_predefined_mode_state(
        tool_results={
            "engagement": {
                "answer_type": "partial_answer",
                "detail_score": 4,  # Verbose
                "engagement_level": "engaged",
            },
            "criteria": {
                "answer_quality": 2,  # Poor quality
                "criteria_assessed": [
                    {"criterion": "People leadership", "demonstrated": False, "evidence": ""},
                ],
            },
        },
        current_gap={
            "question_id": "test-gap-004",
            "question_text": "Tell me about leadership",
            "category": "LEADERSHIP",
            "what_assesses": ["People leadership"],
            "probes_attempted": 0,
            "max_probes": 2,
        },
        resolved_gaps=[],
    )

    print("\nInput state:")
    print(f"  detail_score: 4 (verbose)")
    print(f"  answer_quality: 2 (poor)")
    print(f"  gap_resolved: False")

    # Ensure state reflects any gap-resolution logic before making follow-up decision
    update_result = update_state_node(state)
    state.update(update_result)

    print("\n>>> Running should_follow_up()...")
    result = should_follow_up(state)

    print(f"\nOutput:")
    print(f"  should_follow_up returned: '{result}'")

    print("\n" + "-" * 70)

    if result == "generate_follow_up":
        print("PASS: Follow-up triggered for poor quality answer")
        return True
    else:
        print("BUG CONFIRMED: No follow-up for poor quality (verbose) answer!")
        print("  Root cause: detail_score >= 3 skips follow-up even with poor quality")
        return False


# =============================================================================
# ISSUE 4: Cross-Gap Skipped - ACTUAL NODE TEST
# =============================================================================

def test_issue4_cross_gap_actual_node():
    """
    ISSUE 4: Run parse_answer_node with concise but good answer.

    Expected: Cross-gap analysis should run (answer demonstrates criteria)
    Actual (BUG): Cross-gap skipped (detail_score < 3)
    """
    print("\n" + "=" * 80)
    print("ISSUE 4: Cross-Gap Skipped - Running ACTUAL parse_answer_node")
    print("=" * 80)

    from agents.conversational.nodes.parse_answer import parse_answer_node
    from langchain_core.messages import AIMessage, HumanMessage

    # Create state with concise but comprehensive answer
    state = {
        "mode": "predefined_questions",
        "session_id": "test-session-004",
        "messages": [
            AIMessage(content="Tell me about your leadership experience."),
            # Concise but mentions leadership, productivity improvement, conflict resolution
            HumanMessage(content="Led team of 5, improved productivity 20%, resolved conflicts weekly."),
        ],
        "current_question": {
            "question_id": "test-gap-001",
            "question_text": "Tell me about your leadership experience",
            "skill_name": "LEADERSHIP",
            "attribute": "People leadership",
            "gap_description": "Leadership assessment",
            "category": "LEADERSHIP EXPERIENCE",
            "what_assesses": ["People leadership", "Decision-making", "Conflict resolution"],
        },
        "current_gap": {
            "question_id": "test-gap-001",
            "question_text": "Tell me about your leadership experience",
            "category": "LEADERSHIP EXPERIENCE",
            "what_assesses": ["People leadership", "Decision-making", "Conflict resolution"],
            "probes_attempted": 0,
            "max_probes": 2,
        },
        "identified_gaps": [
            {
                "question_id": "test-gap-002",
                "question_text": "Tell me about conflict resolution",
                "category": "SOFT SKILLS",
                "what_assesses": ["Conflict resolution"],
            },
            {
                "question_id": "test-gap-003",
                "question_text": "Describe a decision you made",
                "category": "DECISION MAKING",
                "what_assesses": ["Decision-making skills"],
            },
        ],
        "extracted_skills": [],
    }

    print("\nInput state:")
    print(f"  mode: {state['mode']}")
    print(f"  answer: '{state['messages'][-1].content}'")
    print(f"  Note: Answer is concise but mentions leadership, productivity, conflicts")
    print(f"  other_gaps: {len(state['identified_gaps'])} (conflict resolution, decision making)")

    # Run the actual node
    print("\n>>> Running parse_answer_node()...")
    print("    (This calls LLM for engagement assessment)\n")

    try:
        result = parse_answer_node(state)

        tool_results = result.get("tool_results", {})
        engagement = tool_results.get("engagement", {})
        cross_coverage = tool_results.get("cross_coverage", [])

        print(f"\nOutput:")
        print(f"  answer_type: {engagement.get('answer_type')}")
        print(f"  detail_score: {engagement.get('detail_score')}")
        print(f"  cross_coverage: {len(cross_coverage)} gaps analyzed")

        if cross_coverage:
            for cov in cross_coverage:
                print(f"    - {cov.get('category', 'unknown')}: covered={cov.get('covered')}")

        print("\n" + "-" * 70)

        # Check if cross-gap analysis was skipped
        detail_score = engagement.get("detail_score", 0)

        if len(cross_coverage) == 0 and detail_score < 3:
            print(f"BUG CONFIRMED: Cross-gap analysis skipped (detail_score={detail_score} < 3)")
            print("  Answer mentions 'conflicts' but gap 'conflict resolution' not checked")
            print("  Root cause: Uses detail_score threshold, ignores answer content")
            return False
        elif len(cross_coverage) == 0:
            print(f"Cross-gap analysis ran but found no coverage (detail_score={detail_score})")
            return True
        else:
            print(f"PASS: Cross-gap analysis ran, found {len(cross_coverage)} potential matches")
            return True

    except Exception as e:
        print(f"\nError running parse_answer_node: {e}")
        import traceback
        traceback.print_exc()
        return False


# =============================================================================
# RUN ALL TESTS
# =============================================================================

def run_all_tests():
    """Run all engagement tracking issue tests using actual nodes."""
    print("\n" + "=" * 80)
    print("ENGAGEMENT TRACKING ISSUES - INTEGRATION TESTS WITH ACTUAL NODES")
    print("Running REAL agent nodes to demonstrate bugs")
    print("Documented in: docs/issues/engagement-tracking-predefined-mode.md")
    print("=" * 80)

    tests = [
        ("Issue 1a: Gap resolution (off-topic)", test_issue1_gap_resolution_actual_node),
        ("Issue 1b: Gap resolution (criteria=0)", test_issue1b_gap_resolution_criteria_zero),
        ("Issue 2: Off-topic resets counter", test_issue2_off_topic_resets_counter_actual_node),
        ("Issue 3a: Follow-up (concise good answer)", test_issue3_follow_up_actual_conditions),
        ("Issue 3b: Follow-up (verbose poor answer)", test_issue3b_verbose_poor_quality),
        ("Issue 4: Cross-gap skips concise", test_issue4_cross_gap_actual_node),
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
    print("\nThese tests run ACTUAL nodes. FAIL = bug confirmed in real code.\n")

    bugs_confirmed = 0
    bugs_fixed = 0
    errors = 0

    for name, passed, error in results:
        if error:
            status = f"ERROR: {error[:50]}..."
            errors += 1
        elif passed:
            status = "PASS (bug may be fixed)"
            bugs_fixed += 1
        else:
            status = "FAIL (BUG CONFIRMED)"
            bugs_confirmed += 1
        print(f"  {status}: {name}")

    print(f"\nBugs confirmed: {bugs_confirmed}")
    print(f"Possibly fixed: {bugs_fixed}")
    print(f"Errors: {errors}")

    if bugs_confirmed > 0:
        print(f"\n{bugs_confirmed} bug(s) confirmed in actual node execution.")
        print("See docs/issues/engagement-tracking-predefined-mode.md for details.")

    return bugs_confirmed == 0 and errors == 0


def setup_test_sessions():
    """Create test interview sessions in the database."""
    from sqlmodel import create_engine, Session
    from config.settings import settings
    from models.interview_session import InterviewSession
    from models.candidate import Candidate

    engine = create_engine(settings.DATABASE_URL)

    test_candidate_id = "test-candidate-engagement"
    test_session_ids = [
        "test-session-001",
        "test-session-004",
    ]

    with Session(engine) as db:
        # Create test candidate first (foreign key requirement)
        existing_candidate = db.get(Candidate, test_candidate_id)
        if not existing_candidate:
            candidate = Candidate(id=test_candidate_id, name="Test Candidate")
            db.add(candidate)
            db.commit()
            print(f"Created test candidate: {test_candidate_id}")

        # Create test sessions
        for session_id in test_session_ids:
            existing = db.get(InterviewSession, session_id)
            if not existing:
                session = InterviewSession(
                    id=session_id,
                    candidate_id=test_candidate_id,
                    resume_text="Test resume for engagement tracking tests",
                    status="in_progress",
                    thread_id=f"thread-{session_id}",
                )
                db.add(session)
        db.commit()
        print(f"Created {len(test_session_ids)} test interview sessions")


def cleanup_test_sessions():
    """Remove test interview sessions from the database."""
    from sqlmodel import create_engine, Session, select
    from config.settings import settings
    from models.interview_session import InterviewSession
    from models.message import Message
    from models.candidate import Candidate

    engine = create_engine(settings.DATABASE_URL)

    test_candidate_id = "test-candidate-engagement"
    test_session_ids = [
        "test-session-001",
        "test-session-004",
    ]

    with Session(engine) as db:
        # Delete messages first (foreign key)
        for session_id in test_session_ids:
            messages = db.exec(
                select(Message).where(Message.session_id == session_id)
            ).all()
            for msg in messages:
                db.delete(msg)

        # Delete sessions
        for session_id in test_session_ids:
            session = db.get(InterviewSession, session_id)
            if session:
                db.delete(session)

        # Delete test candidate
        candidate = db.get(Candidate, test_candidate_id)
        if candidate:
            db.delete(candidate)

        db.commit()
        print(f"Cleaned up {len(test_session_ids)} test interview sessions and candidate")


if __name__ == "__main__":
    # Import all models for SQLAlchemy relationships
    import importlib
    import pkgutil
    import models

    for _, name, _ in pkgutil.iter_modules(models.__path__):
        importlib.import_module(f"models.{name}")

    # Setup: Create test sessions
    setup_test_sessions()

    try:
        success = run_all_tests()
    finally:
        # Cleanup: Remove test sessions
        cleanup_test_sessions()

    sys.exit(0 if success else 1)
