"""
MASTER DEMO: Run All Dynamic Conversation Tests

Runs all 5 demo tests in sequence to showcase the conversational agent's capabilities.

Run: python tests/integration/demo_all_dynamic_conversation.py
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import all demo tests
from tests.integration import (
    demo_1_coreference_resolution,
    demo_2_multi_requirement_extraction,
    demo_3_clarification_handling,
    demo_4_partial_with_clarification,
    demo_5_state_persistence
)


def main():
    print("\n" + "🎬" * 50)
    print("DYNAMIC CONVERSATION DEMONSTRATION SUITE")
    print("🎬" * 50)
    print("\nRunning 5 demos to showcase conversational intelligence:\n")
    print("1. Co-reference Resolution - 'Same as Python' → Extracts correctly")
    print("2. Multi-Requirement Extraction - Single answer → Multiple attributes")
    print("3. Clarification Handling - 'What do you mean?' → Provides examples")
    print("4. Partial + Clarification - '3 years. What types?' → Extract then clarify")
    print("5. State Persistence - Resume interviews across restarts")
    print("\n" + "🎬" * 50)

    results = {}

    print("\n\n")
    try:
        demo_1_coreference_resolution.main()
        results["Demo 1: Co-reference"] = "✅ PASSED"
    except Exception as e:
        results["Demo 1: Co-reference"] = f"❌ FAILED: {e}"

    print("\n\n")
    try:
        demo_2_multi_requirement_extraction.main()
        results["Demo 2: Multi-Requirement"] = "✅ PASSED"
    except Exception as e:
        results["Demo 2: Multi-Requirement"] = f"❌ FAILED: {e}"

    print("\n\n")
    try:
        demo_3_clarification_handling.main()
        results["Demo 3: Clarification"] = "✅ PASSED"
    except Exception as e:
        results["Demo 3: Clarification"] = f"❌ FAILED: {e}"

    print("\n\n")
    try:
        demo_4_partial_with_clarification.main()
        results["Demo 4: Partial + Clarification"] = "✅ PASSED"
    except Exception as e:
        results["Demo 4: Partial + Clarification"] = f"❌ FAILED: {e}"

    print("\n\n")
    try:
        demo_5_state_persistence.main()
        results["Demo 5: State Persistence"] = "✅ PASSED"
    except Exception as e:
        results["Demo 5: State Persistence"] = f"❌ FAILED: {e}"

    # Summary
    print("\n" + "=" * 100)
    print("DEMO SUITE SUMMARY")
    print("=" * 100)

    for test_name, result in results.items():
        print(f"{result.split(':')[0]:3s} {test_name}")

    passed = sum(1 for r in results.values() if "PASSED" in r)
    total = len(results)

    print(f"\n📊 Results: {passed}/{total} demos passed")

    if passed == total:
        print("\n🎉 ALL DEMOS PASSED! Conversational intelligence working perfectly.")
    else:
        print(f"\n⚠️  {total - passed} demo(s) failed. Review output above.")

    print("=" * 100 + "\n")


if __name__ == "__main__":
    main()
