"""
Test for analyze_resume_coverage node.

Tests the node that analyzes which predefined questions
can be answered from the resume.

Usage:
    python tests/integration/test_analyze_resume_coverage.py
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from agents.conversational.nodes.analyze_resume_coverage import analyze_resume_coverage_node
from agents.conversational.state import InterviewState
import json

# =============================================================================
# CONFIGURATION - Change these values to test different scenarios
# =============================================================================

QUESTION_SET_ID = "03b84681-2c75-4bbd-89ee-307861ec7b6b"

DUMMY_RESUME = """
John Doe
Software Engineer

EXPERIENCE:
- 3 years Python development
- Built REST APIs with FastAPI
- PostgreSQL database management

SKILLS:
- Python, JavaScript
- Docker, AWS
"""

# =============================================================================
# TEST
# =============================================================================

def create_minimal_state(resume_text: str, question_set_id: str) -> InterviewState:
    """Create minimal InterviewState for testing analyze_resume_coverage."""
    return {
        # Required fields for analyze_resume_coverage
        "mode": "predefined_questions",
        "resume_text": resume_text,
        "question_set_id": question_set_id,

        # Other fields (not used by this node but required by TypedDict)
        "session_id": "test-session",
        "messages": [],
        "identified_gaps": [],
        "resolved_gaps": [],
        "current_gap": None,
        "current_question": None,
        "extracted_skills": [],
        "engagement_signals": [],
        "consecutive_low_quality": 0,
        "should_continue": True,
        "termination_reason": None,
        "completeness_score": 0.0,
        "minimum_completeness": 0.9,
        "all_predefined_gaps": None,
        "current_predefined_question": None,
        "gaps_resolved_this_turn": 0,
    }


def test_analyze_resume_coverage():
    """
    Test analyze_resume_coverage node.

    Input: Dummy CV + predefined_question_set_id
    Output: List of gaps (questions not answered by resume)
    """
    print("\n" + "=" * 80)
    print("TEST: analyze_resume_coverage node")
    print("=" * 80)

    # Create minimal state
    state = create_minimal_state(DUMMY_RESUME, QUESTION_SET_ID)

    print(f"\n📄 Resume length: {len(DUMMY_RESUME)} chars")
    print(f"📋 Question Set ID: {QUESTION_SET_ID}")

    print("\n" + "-" * 80)
    print("Running analyze_resume_coverage_node...")
    print("-" * 80)

    # Call the node
    result = analyze_resume_coverage_node(state)

    print("\n" + "-" * 80)
    print("RESULTS")
    print("-" * 80)

    # Extract results
    identified_gaps = result.get("identified_gaps", [])
    all_gaps = result.get("all_predefined_gaps", [])
    completeness = result.get("completeness_score", 0.0)

    print(f"\n📊 Total questions: {len(all_gaps)}")
    print(f"✅ Resume filled: {len(all_gaps) - len(identified_gaps)}")
    print(f"❓ Gaps to ask: {len(identified_gaps)}")
    print(f"📈 Initial completeness: {completeness:.1%}")

    # Show gaps (questions to ask)
    print("\n" + "-" * 80)
    print("GAPS (Questions to ask)")
    print("-" * 80)

    for i, gap in enumerate(identified_gaps, 1):
        print(f"\n{i}. [{gap['category']}]")
        print(f"   Question: {gap['question_text'][:100]}...")
        print(f"   Required: {gap['is_required']}")
        print(f"   Severity: {gap['severity']}")

    # Show filled questions
    filled = [g for g in all_gaps if g.get("resume_filled")]
    if filled:
        print("\n" + "-" * 80)
        print("FILLED BY RESUME")
        print("-" * 80)

        for i, gap in enumerate(filled, 1):
            print(f"\n{i}. [{gap['category']}]")
            print(f"   Question: {gap['question_text'][:80]}...")
            print(f"   Evidence: {gap.get('resume_evidence', 'N/A')[:100]}...")

    # Save output to file
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "analyze_resume_coverage_result.json"

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "input": {
                "resume": DUMMY_RESUME,
                "question_set_id": QUESTION_SET_ID
            },
            "output": {
                "completeness_score": completeness,
                "total_questions": len(all_gaps),
                "gaps_count": len(identified_gaps),
                "filled_count": len(all_gaps) - len(identified_gaps),
                "gaps": identified_gaps,
                "all_gaps": all_gaps
            }
        }, f, indent=2, ensure_ascii=False)

    print(f"\n💾 Full output saved to: {output_file}")

    print("\n" + "=" * 80)
    print("✅ TEST COMPLETED")
    print("=" * 80)

    return result


if __name__ == "__main__":
    # Import all models for SQLAlchemy relationships
    import importlib
    import pkgutil
    import models

    for _, name, _ in pkgutil.iter_modules(models.__path__):
        importlib.import_module(f"models.{name}")

    # Run test
    try:
        test_analyze_resume_coverage()
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
