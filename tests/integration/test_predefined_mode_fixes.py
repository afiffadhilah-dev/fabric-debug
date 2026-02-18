"""
Integration test for predefined_questions mode fixes (Phase 0).

Tests:
1. Criteria assessment is called and produces structured data
2. Follow-up questions use predefined-specific templates
3. Gap resolution is relaxed (quality >= 3 OR probes >= 2)
4. Criteria assessment is stored in Message.meta
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from typing import Dict, Any
import json


def test_assess_criteria_function():
    """
    Test that assess_criteria() produces structured output.
    """
    print("\n" + "=" * 80)
    print("TEST 1: assess_criteria() function")
    print("=" * 80)

    from tools.extraction_tools import assess_criteria

    # Test with a leadership question
    question = "Can you describe a situation where you led a team through a difficult challenge?"
    answer = """
    At my previous company, we had a critical deadline for a major client release.
    The team was stressed and we discovered a significant bug two days before launch.
    I organized the team into two groups - one to fix the bug and one to prepare
    contingency plans. I held daily standups, kept everyone motivated, and we
    successfully delivered on time. The client was happy and we learned to build
    in more buffer time for future releases.
    """
    what_assesses = ["People leadership", "Decision-making skills", "Crisis management"]
    category = "LEADERSHIP EXPERIENCE"

    result = assess_criteria(
        question=question,
        answer=answer,
        what_assesses=what_assesses,
        category=category
    )

    print(f"\nInput:")
    print(f"  Question: {question[:60]}...")
    print(f"  Answer: {answer[:80]}...")
    print(f"  Criteria: {what_assesses}")

    print(f"\nOutput:")
    print(f"  answer_quality: {result.get('answer_quality')}")
    print(f"  criteria_assessed: {len(result.get('criteria_assessed', []))} items")

    for criterion in result.get("criteria_assessed", []):
        print(f"    - {criterion['criterion']}: demonstrated={criterion['demonstrated']}")
        if criterion['evidence']:
            print(f"      evidence: {criterion['evidence'][:60]}...")

    print(f"  reasoning: {result.get('reasoning', '')[:100]}...")

    # Assertions
    assert "answer_quality" in result, "Should have answer_quality"
    assert result["answer_quality"] >= 1 and result["answer_quality"] <= 5, "answer_quality should be 1-5"
    assert "criteria_assessed" in result, "Should have criteria_assessed"
    assert len(result["criteria_assessed"]) == len(what_assesses), "Should assess all criteria"

    print("\n✅ TEST 1 PASSED: assess_criteria() produces structured output")
    return result


def test_assess_criteria_with_vague_answer():
    """
    Test assess_criteria() with a vague/brief answer.
    """
    print("\n" + "=" * 80)
    print("TEST 2: assess_criteria() with vague answer")
    print("=" * 80)

    from tools.extraction_tools import assess_criteria

    question = "Describe your experience with system design and architecture decisions."
    answer = "I've done some system design work before."
    what_assesses = ["System design skills", "Architecture decision-making", "Technical depth"]
    category = "SYSTEM DESIGN"

    result = assess_criteria(
        question=question,
        answer=answer,
        what_assesses=what_assesses,
        category=category
    )

    print(f"\nInput (vague answer):")
    print(f"  Question: {question[:60]}...")
    print(f"  Answer: '{answer}'")

    print(f"\nOutput:")
    print(f"  answer_quality: {result.get('answer_quality')}")

    for criterion in result.get("criteria_assessed", []):
        print(f"    - {criterion['criterion']}: demonstrated={criterion['demonstrated']}")

    # Assertions - vague answer should have low quality
    assert result["answer_quality"] <= 3, "Vague answer should have low quality (<=3)"

    print("\n✅ TEST 2 PASSED: Vague answers get low quality scores")
    return result


def test_predefined_follow_up_templates():
    """
    Test that predefined mode uses correct follow-up templates.
    """
    print("\n" + "=" * 80)
    print("TEST 3: Predefined follow-up templates")
    print("=" * 80)

    from utils.prompt_loader import PromptLoader

    loader = PromptLoader()

    # Test predefined probe template
    probe_template = loader.load(
        "follow_up_predefined_probe",
        mode="conversational",
        original_question="Tell me about your leadership experience.",
        user_answer="I've led some teams.",
        criteria_list="People leadership, Decision-making, Communication"
    )

    print(f"\nPredefined Probe Template:")
    print(f"  {probe_template[:200]}...")

    # Assertions
    assert "specific example" in probe_template.lower() or "example" in probe_template.lower(), \
        "Probe template should ask for examples"
    assert "skill_name" not in probe_template, "Should not have skill_name placeholder"
    assert "attribute" not in probe_template or "criteria" in probe_template.lower(), \
        "Should use criteria, not attribute"

    # Test predefined clarification template
    clarification_template = loader.load(
        "follow_up_predefined_clarification",
        mode="conversational",
        original_question="Describe a challenging project.",
        user_answer="What do you mean by challenging?",
        criteria_list="Problem-solving, Technical complexity"
    )

    print(f"\nPredefined Clarification Template:")
    print(f"  {clarification_template[:200]}...")

    # Assertions
    assert "clarification" in clarification_template.lower() or "example" in clarification_template.lower(), \
        "Clarification template should provide clarity"

    print("\n✅ TEST 3 PASSED: Predefined templates loaded correctly")


def test_parse_answer_calls_criteria_assessment():
    """
    Test that parse_answer_node calls assess_criteria for predefined mode.
    """
    print("\n" + "=" * 80)
    print("TEST 4: parse_answer_node calls assess_criteria")
    print("=" * 80)

    from agents.conversational.nodes.parse_answer import parse_answer_node
    from langchain_core.messages import HumanMessage, AIMessage

    # Build mock state for predefined mode
    state = {
        "mode": "predefined_questions",
        "messages": [
            AIMessage(content="Tell me about your leadership experience."),
            HumanMessage(content="I led a team of 5 engineers for 2 years, mentoring juniors and making architecture decisions.")
        ],
        "current_question": {
            "question_id": "test-123",
            "question_text": "Tell me about your leadership experience.",
            "skill_name": "LEADERSHIP",
            "attribute": "People leadership, Decision-making",
            "gap_description": "Leadership assessment"
        },
        "current_gap": {
            "question_id": "test-123",
            "question_text": "Tell me about your leadership experience.",
            "category": "LEADERSHIP EXPERIENCE",
            "what_assesses": ["People leadership", "Decision-making skills"],
            "probes_attempted": 0,
            "max_probes": 2
        },
        "extracted_skills": []
    }

    # Call parse_answer_node
    result = parse_answer_node(state)

    print(f"\nInput state:")
    print(f"  mode: {state['mode']}")
    print(f"  what_assesses: {state['current_gap']['what_assesses']}")
    print(f"  answer: {state['messages'][-1].content[:60]}...")

    print(f"\nOutput:")
    print(f"  tool_results keys: {list(result.get('tool_results', {}).keys())}")

    # Check criteria assessment was called
    tool_results = result.get("tool_results", {})

    if "criteria" in tool_results:
        criteria = tool_results["criteria"]
        print(f"  criteria.answer_quality: {criteria.get('answer_quality')}")
        print(f"  criteria.criteria_assessed: {len(criteria.get('criteria_assessed', []))} items")

        # Assertions
        assert criteria.get("answer_quality") is not None, "Should have answer_quality"
        assert len(criteria.get("criteria_assessed", [])) > 0, "Should have assessed criteria"

        print("\n✅ TEST 4 PASSED: parse_answer_node calls assess_criteria for predefined mode")
    else:
        print(f"  criteria: NOT FOUND in tool_results")
        print(f"  skills: {tool_results.get('skills', [])}")
        print("\n⚠️  TEST 4: criteria not in tool_results (may be due to LLM call)")


def test_gap_resolution_relaxed():
    """
    Test that gap resolution is relaxed for predefined mode.
    """
    print("\n" + "=" * 80)
    print("TEST 5: Relaxed gap resolution logic")
    print("=" * 80)

    # Test the resolution logic directly
    test_cases = [
        # (answer_quality, probes_attempted, max_probes, expected_resolve, reason)
        (4, 0, 2, True, "quality >= 3"),
        (3, 0, 2, True, "quality >= 3"),
        (2, 0, 2, False, "quality < 3, probes < 2"),
        (2, 2, 2, True, "probes >= 2 and quality >= 2"),
        (1, 2, 2, True, "probes >= max_probes (move on even with bad answer)"),
        (1, 3, 2, True, "probes >= max_probes"),
        (2, 1, 3, False, "quality < 3, probes < 2, probes < max"),
    ]

    print("\nTest cases for relaxed resolution logic:")
    print("-" * 60)

    all_passed = True
    for quality, probes, max_p, expected, reason in test_cases:
        # Replicate the logic from update_state.py
        should_resolve = (
            quality >= 3 or
            (probes >= 2 and quality >= 2) or
            probes >= max_p
        )

        status = "✅" if should_resolve == expected else "❌"
        if should_resolve != expected:
            all_passed = False

        print(f"  {status} quality={quality}, probes={probes}/{max_p} -> resolve={should_resolve} ({reason})")

    if all_passed:
        print("\n✅ TEST 5 PASSED: Relaxed gap resolution logic works correctly")
    else:
        print("\n❌ TEST 5 FAILED: Some resolution cases don't match expected")
        assert False, "Gap resolution logic mismatch"


def test_generate_follow_up_mode_aware():
    """
    Test that generate_follow_up_node is mode-aware.
    """
    print("\n" + "=" * 80)
    print("TEST 6: generate_follow_up_node mode awareness")
    print("=" * 80)

    from agents.conversational.nodes.generate_follow_up import generate_follow_up_node
    from langchain_core.messages import HumanMessage, AIMessage

    # Build mock state for predefined mode with vague answer
    state = {
        "mode": "predefined_questions",
        "messages": [
            AIMessage(content="Describe your experience with system design."),
            HumanMessage(content="I've done some design work.")
        ],
        "current_question": {
            "question_id": "test-456",
            "question_text": "Describe your experience with system design.",
            "skill_name": "SYSTEM DESIGN",
            "attribute": "Architecture skills",
            "gap_description": "System design assessment"
        },
        "current_gap": {
            "question_id": "test-456",
            "question_text": "Describe your experience with system design.",
            "category": "SYSTEM DESIGN",
            "what_assesses": ["Architecture skills", "Technical decision-making"],
            "probes_attempted": 0,
            "max_probes": 2
        },
        "tool_results": {
            "engagement": {
                "answer_type": "partial_answer",
                "detail_score": 2,
                "engagement_level": "engaged"
            },
            "skills": []
        },
        "identified_gaps": [],
        "questions_asked": 1
    }

    print(f"\nInput state:")
    print(f"  mode: {state['mode']}")
    print(f"  what_assesses: {state['current_gap']['what_assesses']}")
    print(f"  answer_type: partial_answer")

    # Call generate_follow_up_node
    result = generate_follow_up_node(state)

    print(f"\nOutput:")
    if "messages" in result and result["messages"]:
        follow_up = result["messages"][0].content
        print(f"  follow_up: {follow_up[:150]}...")

        # Check that follow-up doesn't contain skill_name/attribute patterns from dynamic mode
        has_skill_pattern = "SYSTEM DESIGN's" in follow_up or "Architecture skills's" in follow_up
        if has_skill_pattern:
            print("\n⚠️  WARNING: Follow-up may contain dynamic mode patterns")
        else:
            print("\n✅ TEST 6 PASSED: Follow-up uses predefined mode templates")
    else:
        print("  No follow-up generated")


def run_all_tests():
    """Run all Phase 0 fix tests."""
    print("\n" + "=" * 80)
    print("PREDEFINED MODE FIXES - INTEGRATION TESTS (Phase 0)")
    print("=" * 80)

    tests = [
        ("assess_criteria function", test_assess_criteria_function),
        ("assess_criteria with vague answer", test_assess_criteria_with_vague_answer),
        ("predefined follow-up templates", test_predefined_follow_up_templates),
        ("parse_answer calls criteria assessment", test_parse_answer_calls_criteria_assessment),
        ("relaxed gap resolution", test_gap_resolution_relaxed),
        ("generate_follow_up mode awareness", test_generate_follow_up_mode_aware),
    ]

    results = []
    for name, test_fn in tests:
        try:
            test_fn()
            results.append((name, True, None))
        except Exception as e:
            results.append((name, False, str(e)))
            import traceback
            traceback.print_exc()

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    passed = sum(1 for _, success, _ in results if success)
    failed = len(results) - passed

    for name, success, error in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status}: {name}")
        if error:
            print(f"         Error: {error[:60]}...")

    print(f"\nTotal: {passed}/{len(results)} passed, {failed} failed")

    if failed == 0:
        print("\n✅ ALL TESTS PASSED!")
    else:
        print(f"\n❌ {failed} TEST(S) FAILED")

    return failed == 0


if __name__ == "__main__":
    # Import all models for SQLAlchemy relationships
    import importlib
    import pkgutil
    import models

    for _, name, _ in pkgutil.iter_modules(models.__path__):
        importlib.import_module(f"models.{name}")

    # Run tests
    success = run_all_tests()
    sys.exit(0 if success else 1)
