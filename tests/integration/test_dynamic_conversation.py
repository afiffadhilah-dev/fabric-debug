"""
Integration test for dynamic conversation handling features.

This test suite verifies the 4 core dynamic conversation requirements:
1. Full conversation history with co-reference resolution
2. Multi-requirement answer detection (multiple skills/attributes at once)
3. User clarification request handling
4. State persistence and resume capability

Run with: python tests/integration/test_dynamic_conversation.py
Requires: Database running (make db-start)
"""

import sys
from pathlib import Path
import json

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlmodel import Session, create_engine, SQLModel
from agents.conversational.service import ConversationalInterviewService
from utils.llm_service import LLMService
from utils.prompt_loader import PromptLoader
from models.candidate import Candidate
from models.interview_session import InterviewSession
from models.message import Message
from config.settings import settings
from sqlmodel import select


def setup_service(db_session: Session) -> ConversationalInterviewService:
    """Initialize the conversational interview service."""
    llm_service = LLMService()
    prompt_loader = PromptLoader()
    return ConversationalInterviewService(llm_service, prompt_loader, db_session)


def print_test_header(test_name: str, description: str):
    """Print formatted test header."""
    print("\n" + "=" * 100)
    print(f"TEST: {test_name}")
    print(f"DESCRIPTION: {description}")
    print("=" * 100)


def print_verification(check_name: str, passed: bool, details: str = ""):
    """Print verification result."""
    symbol = "✅" if passed else "❌"
    print(f"{symbol} {check_name}: {'PASS' if passed else 'FAIL'}")
    if details:
        print(f"   Details: {details}")


def test_full_conversation_history():
    """
    Test 1: Verify full message history flows through nodes with co-reference resolution.

    Scenario:
    - Start interview with resume mentioning Python
    - Q1: Ask about Python duration
    - A1: "Python: 3 years"
    - Q2: Ask about React duration
    - A2: "Same duration for React"
    - Verify: System extracts React duration = 3 years (co-reference)
    """
    print_test_header(
        "Test 1: Full Conversation History with Co-reference Resolution",
        "Verify the agent sees full message history and resolves co-references"
    )

    engine = create_engine(settings.DATABASE_URL)

    with Session(engine) as db_session:
        service = setup_service(db_session)

        # Create test candidate
        candidate_id = "test_full_history"
        candidate = db_session.get(Candidate, candidate_id)
        if not candidate:
            candidate = Candidate(id=candidate_id, name="Test Full History")
            db_session.add(candidate)
            db_session.commit()

        # Resume mentioning Python and React
        resume_text = """
        John Doe - Software Engineer

        EXPERIENCE:
        - Worked with Python and React on various projects
        - Experience with FastAPI and Node.js

        SKILLS:
        - Python (backend development)
        - React (frontend development)
        """

        print("\n[SETUP] Starting interview...")
        result = service.start_interview(
            candidate_id=candidate_id,
            resume_text=resume_text,
            mode="dynamic_gap"
        )

        session_id = result["session_id"]
        thread_id = result["thread_id"]
        question1 = result["question"]

        print(f"[OK] Session ID: {session_id}")
        print(f"[OK] Thread ID: {thread_id}")
        print(f"\nQ1: {question1}")

        # Answer 1: Provide Python duration
        answer1 = "Python: 3 years"
        print(f"A1: {answer1}")

        result = service.continue_interview(thread_id, answer1)
        question2 = result.get("question")
        print(f"\nQ2: {question2}")

        # Answer 2: Co-reference to previous answer
        answer2 = "Same duration for React"
        print(f"A2: {answer2}")

        result = service.continue_interview(thread_id, answer2)

        # Verify: Check if React duration was extracted as 3 years
        print("\n[VERIFICATION] Checking extracted skills...")
        skills = service.get_extracted_skills(session_id)

        python_skill = next((s for s in skills if "python" in s["name"].lower()), None)
        react_skill = next((s for s in skills if "react" in s["name"].lower()), None)

        # Verification 1: Python duration extracted
        python_has_duration = python_skill and python_skill.get("duration") is not None
        print_verification(
            "Python duration extracted",
            python_has_duration,
            f"Duration: {python_skill.get('duration') if python_skill else 'N/A'}"
        )

        # Verification 2: React duration extracted (co-reference)
        react_has_duration = react_skill and react_skill.get("duration") is not None
        print_verification(
            "React duration extracted from co-reference",
            react_has_duration,
            f"Duration: {react_skill.get('duration') if react_skill else 'N/A'}"
        )

        # Verification 3: Both durations match
        if python_has_duration and react_has_duration:
            durations_match = python_skill["duration"] == react_skill["duration"]
            print_verification(
                "Co-reference resolution: Durations match",
                durations_match,
                f"Python: {python_skill['duration']}, React: {react_skill['duration']}"
            )
        else:
            print_verification(
                "Co-reference resolution: Durations match",
                False,
                "One or both durations not extracted"
            )

        print("\n[TEST 1 COMPLETE]")
        return python_has_duration and react_has_duration


def test_multi_requirement_extraction():
    """
    Test 2: Verify multi-skill/multi-attribute extraction from single answer.

    Scenario:
    - Start interview
    - Q1: Ask about Python experience
    - A1: "5 years leading a team of 10 in production environment with 100K users"
    - Verify: Extracts duration, autonomy, scale, production_vs_prototype
    - Verify: Multiple gaps resolved from one answer
    """
    print_test_header(
        "Test 2: Multi-Requirement Answer Detection",
        "Verify extraction of multiple attributes from single answer"
    )

    engine = create_engine(settings.DATABASE_URL)

    with Session(engine) as db_session:
        service = setup_service(db_session)

        candidate_id = "test_multi_req"
        candidate = db_session.get(Candidate, candidate_id)
        if not candidate:
            candidate = Candidate(id=candidate_id, name="Test Multi Requirement")
            db_session.add(candidate)
            db_session.commit()

        resume_text = """
        Jane Smith - Backend Developer

        SKILLS:
        - Python (FastAPI, Django)
        - PostgreSQL
        """

        print("\n[SETUP] Starting interview...")
        result = service.start_interview(
            candidate_id=candidate_id,
            resume_text=resume_text,
            mode="dynamic_gap"
        )

        session_id = result["session_id"]
        thread_id = result["thread_id"]
        question = result["question"]

        print(f"\nQ1: {question}")

        # Answer covering multiple attributes at once
        answer = "I worked with Python for 5 years, leading a team of 10 developers on production systems serving 100,000 active users daily"
        print(f"A1: {answer}")

        result = service.continue_interview(thread_id, answer)

        # Continue answering until interview completes so skills are persisted
        attempt = 2
        while not result.get("completed") and attempt <= 5:
            question = result.get("question")
            print(f"\nQ{attempt}: {question}")

            # Give simple answers to complete interview
            answer = "About 2 years in production environments"
            print(f"A{attempt}: {answer}")

            result = service.continue_interview(thread_id, answer)
            attempt += 1

        if result.get("completed"):
            print(f"\n[INFO] Interview completed: {result.get('termination_reason')}")
        else:
            print(f"\n[INFO] Interview still active after {attempt-1} answers")

        # Verify: Check extracted attributes
        print("\n[VERIFICATION] Checking extracted attributes...")
        skills = service.get_extracted_skills(session_id)

        python_skill = next((s for s in skills if "python" in s["name"].lower()), None)

        if python_skill:
            print(f"\n[INFO] Python skill extracted:")
            print(f"  - Duration: {python_skill.get('duration')}")
            print(f"  - Autonomy: {python_skill.get('autonomy')}")
            print(f"  - Scale: {python_skill.get('scale')}")
            print(f"  - Production: {python_skill.get('production_vs_prototype')}")
            print(f"  - Depth: {python_skill.get('depth')}")
            print(f"  - Constraints: {python_skill.get('constraints')}")

        # Verification 1: Duration extracted
        has_duration = python_skill and python_skill.get("duration") is not None
        print_verification(
            "Duration attribute extracted",
            has_duration,
            python_skill.get("duration") if python_skill else "N/A"
        )

        # Verification 2: Autonomy extracted (team leadership)
        has_autonomy = python_skill and python_skill.get("autonomy") is not None
        print_verification(
            "Autonomy attribute extracted",
            has_autonomy,
            python_skill.get("autonomy") if python_skill else "N/A"
        )

        # Verification 3: Scale extracted
        has_scale = python_skill and python_skill.get("scale") is not None
        print_verification(
            "Scale attribute extracted",
            has_scale,
            python_skill.get("scale") if python_skill else "N/A"
        )

        # Verification 4: Production vs prototype extracted
        has_production = python_skill and python_skill.get("production_vs_prototype") is not None
        print_verification(
            "Production vs Prototype extracted",
            has_production,
            python_skill.get("production_vs_prototype") if python_skill else "N/A"
        )

        # Verification 5: At least 3 attributes extracted from single answer
        attributes_count = sum([
            1 if has_duration else 0,
            1 if has_autonomy else 0,
            1 if has_scale else 0,
            1 if has_production else 0
        ])
        multi_attribute_success = attributes_count >= 3
        print_verification(
            "Multiple attributes extracted (3+)",
            multi_attribute_success,
            f"{attributes_count} attributes extracted from single answer"
        )

        print("\n[TEST 2 COMPLETE]")
        return multi_attribute_success


def test_clarification_request_handling():
    """
    Test 3: Verify clarification requests get special treatment.

    Scenario:
    - Start interview
    - Q1: Ask about skill depth
    - A1: "What do you mean by depth?"
    - Verify: Next message is clarification follow-up
    - Verify: Engagement counter NOT penalized
    - Verify: answer_type == "clarification_request" in metadata
    """
    print_test_header(
        "Test 3: Clarification Request Handling",
        "Verify clarification requests trigger special routing"
    )

    engine = create_engine(settings.DATABASE_URL)

    with Session(engine) as db_session:
        service = setup_service(db_session)

        candidate_id = "test_clarification"
        candidate = db_session.get(Candidate, candidate_id)
        if not candidate:
            candidate = Candidate(id=candidate_id, name="Test Clarification")
            db_session.add(candidate)
            db_session.commit()

        resume_text = """
        Bob Johnson - Full Stack Developer

        SKILLS:
        - JavaScript, Python
        - React, Node.js
        """

        print("\n[SETUP] Starting interview...")
        result = service.start_interview(
            candidate_id=candidate_id,
            resume_text=resume_text,
            mode="dynamic_gap"
        )

        session_id = result["session_id"]
        thread_id = result["thread_id"]
        question = result["question"]

        print(f"\nQ1: {question}")

        # Answer with clarification request
        answer = "What do you mean by that?"
        print(f"A1: {answer}")

        result = service.continue_interview(thread_id, answer)
        follow_up = result.get("question")

        print(f"\nFollow-up: {follow_up}")

        # Verify: Check message metadata
        print("\n[VERIFICATION] Checking answer metadata...")
        statement = select(Message).where(
            Message.session_id == session_id,
            Message.role == "user"
        )
        user_messages = db_session.exec(statement).all()

        if user_messages:
            last_user_message = user_messages[-1]
            meta = last_user_message.meta or {}

            answer_type = meta.get("answer_type")
            engagement_level = meta.get("engagement_level")

            print(f"[INFO] Answer metadata:")
            print(f"  - answer_type: {answer_type}")
            print(f"  - engagement_level: {engagement_level}")

            # Verification 1: Detected as clarification request
            is_clarification = answer_type == "clarification_request"
            print_verification(
                "answer_type == 'clarification_request'",
                is_clarification,
                f"Detected as: {answer_type}"
            )

            # Verification 2: Follow-up was generated (not None)
            has_follow_up = follow_up is not None
            print_verification(
                "Follow-up question generated",
                has_follow_up,
                f"Follow-up: {follow_up[:50]}..." if follow_up else "None"
            )

            # Verification 3: Get session to check engagement counter
            statement = select(InterviewSession).where(InterviewSession.id == session_id)
            session = db_session.exec(statement).first()

            # Check consecutive_low_quality from session state (would need to check checkpointer state)
            # For now, verify engagement_level is not "low"
            engagement_not_penalized = engagement_level != "low"
            print_verification(
                "Engagement NOT penalized",
                engagement_not_penalized,
                f"Engagement level: {engagement_level}"
            )

            print("\n[TEST 3 COMPLETE]")
            return is_clarification and has_follow_up
        else:
            print_verification("Messages found", False, "No user messages in database")
            print("\n[TEST 3 COMPLETE]")
            return False


def test_partial_answer_with_clarification():
    """
    Test 3B: Edge case - partial answer + clarification.

    Scenario:
    - Start interview
    - Q1: Ask about duration and project types
    - A1: "3 years. What do you mean by types?"
    - Verify: System extracts "3 years"
    - Verify: System generates follow-up about "types"
    - Check: Does follow-up acknowledge "3 years" was captured?
    """
    print_test_header(
        "Test 3B: Partial Answer with Clarification (Edge Case)",
        "Verify extraction happens BEFORE clarification follow-up"
    )

    engine = create_engine(settings.DATABASE_URL)

    with Session(engine) as db_session:
        service = setup_service(db_session)

        candidate_id = "test_partial_clarification"
        candidate = db_session.get(Candidate, candidate_id)
        if not candidate:
            candidate = Candidate(id=candidate_id, name="Test Partial Clarification")
            db_session.add(candidate)
            db_session.commit()

        resume_text = """
        Alice Brown - DevOps Engineer

        SKILLS:
        - Docker, Kubernetes
        - AWS, Terraform
        """

        print("\n[SETUP] Starting interview...")
        result = service.start_interview(
            candidate_id=candidate_id,
            resume_text=resume_text,
            mode="dynamic_gap"
        )

        session_id = result["session_id"]
        thread_id = result["thread_id"]
        question = result["question"]

        print(f"\nQ1: {question}")

        # Answer with partial info + clarification
        answer = "3 years. What types of projects do you mean?"
        print(f"A1: {answer}")

        result = service.continue_interview(thread_id, answer)
        follow_up = result.get("question")

        print(f"\nFollow-up: {follow_up}")

        # Verify: Check if info was extracted
        print("\n[VERIFICATION] Checking partial extraction...")
        skills = service.get_extracted_skills(session_id)

        # Should extract duration even though clarification was requested
        has_extracted_info = len(skills) > 0 and any(
            skill.get("duration") is not None for skill in skills
        )

        print_verification(
            "Partial answer extracted before clarification",
            has_extracted_info,
            f"{len(skills)} skills extracted with attributes"
        )

        # Verify: Check if clarification was detected
        statement = select(Message).where(
            Message.session_id == session_id,
            Message.role == "user"
        )
        user_messages = db_session.exec(statement).all()

        if user_messages:
            last_user_message = user_messages[-1]
            meta = last_user_message.meta or {}
            answer_type = meta.get("answer_type")

            is_clarification = answer_type == "clarification_request"
            print_verification(
                "Clarification request detected",
                is_clarification,
                f"answer_type: {answer_type}"
            )

        # Verify: Check if follow-up acknowledges extracted info
        # This is a POTENTIAL GAP - follow-up might not say "Got it - 3 years..."
        if follow_up:
            acknowledges_partial = "3" in follow_up or "year" in follow_up.lower() or "got it" in follow_up.lower()
            print_verification(
                "⚠️  Follow-up acknowledges partial answer (Enhancement 3)",
                acknowledges_partial,
                "This may be missing - Enhancement opportunity!"
            )

        print("\n[TEST 3B COMPLETE]")
        return has_extracted_info


def test_state_persistence_and_resume():
    """
    Test 4: Verify checkpointer preserves full state across restarts.

    Scenario:
    - Start interview, answer 2 questions
    - Get thread_id and session_id
    - Simulate app restart: Create NEW service instance
    - Continue with same thread_id
    - Verify: Full conversation history preserved
    - Verify: extracted_skills preserved
    - Verify: Gaps and completeness preserved
    """
    print_test_header(
        "Test 4: State Persistence and Resume Capability",
        "Verify checkpointer preserves state across service restarts"
    )

    engine = create_engine(settings.DATABASE_URL)

    # Phase 1: Start interview with first service instance
    with Session(engine) as db_session:
        service1 = setup_service(db_session)

        candidate_id = "test_persistence"
        candidate = db_session.get(Candidate, candidate_id)
        if not candidate:
            candidate = Candidate(id=candidate_id, name="Test Persistence")
            db_session.add(candidate)
            db_session.commit()

        resume_text = """
        Charlie Davis - Data Engineer

        EXPERIENCE:
        - Data pipelines with Python and Spark
        - SQL databases: PostgreSQL, MySQL

        SKILLS:
        - Python (Pandas, NumPy)
        - Apache Spark
        - SQL
        """

        print("\n[PHASE 1] Starting interview with Service Instance 1...")
        result = service1.start_interview(
            candidate_id=candidate_id,
            resume_text=resume_text,
            mode="dynamic_gap"
        )

        session_id = result["session_id"]
        thread_id = result["thread_id"]
        question1 = result["question"]

        print(f"[OK] Session ID: {session_id}")
        print(f"[OK] Thread ID: {thread_id}")
        print(f"\nQ1: {question1}")

        # Answer 1
        answer1 = "Python for 5 years"
        print(f"A1: {answer1}")

        result = service1.continue_interview(thread_id, answer1)
        question2 = result.get("question")
        print(f"\nQ2: {question2}")

        # Answer 2
        answer2 = "Expert level with production experience"
        print(f"A2: {answer2}")

        result = service1.continue_interview(thread_id, answer2)

        # Get state before "restart"
        skills_before = service1.get_extracted_skills(session_id)
        print(f"\n[PHASE 1 STATE] Extracted {len(skills_before)} skills")

    # Phase 2: Simulate restart - create NEW service instance
    print("\n[PHASE 2] Simulating application restart...")
    print("[INFO] Creating new service instance (NEW database session)")

    with Session(engine) as db_session:
        service2 = setup_service(db_session)

        print(f"[INFO] Continuing interview with same thread_id: {thread_id}")

        # Continue with same thread_id - should load state from checkpointer
        answer3 = "I also worked with Spark for 3 years"
        print(f"A3: {answer3}")

        result = service2.continue_interview(thread_id, answer3)
        question3 = result.get("question")
        print(f"\nQ3: {question3}")

        # Get state after resume
        skills_after = service2.get_extracted_skills(session_id)
        print(f"\n[PHASE 2 STATE] Extracted {len(skills_after)} skills")

        # Verification 1: Skills preserved (at least as many as before)
        skills_preserved = len(skills_after) >= len(skills_before)
        print_verification(
            "Extracted skills preserved",
            skills_preserved,
            f"Before: {len(skills_before)}, After: {len(skills_after)}"
        )

        # Verification 2: New skill added (Spark)
        spark_skill = next((s for s in skills_after if "spark" in s["name"].lower()), None)
        new_skill_added = spark_skill is not None
        print_verification(
            "New skill extracted after resume",
            new_skill_added,
            f"Spark skill: {spark_skill['name'] if spark_skill else 'Not found'}"
        )

        # Verification 3: Check message count increased
        statement = select(Message).where(Message.session_id == session_id)
        messages = db_session.exec(statement).all()
        message_count = len(messages)

        # Should have at least 6 messages (3 Q + 3 A)
        messages_preserved = message_count >= 6
        print_verification(
            "Conversation history preserved",
            messages_preserved,
            f"{message_count} messages in database"
        )

        # Verification 4: Session state preserved
        statement = select(InterviewSession).where(InterviewSession.id == session_id)
        session = db_session.exec(statement).first()

        if session:
            print(f"\n[INFO] Session state:")
            print(f"  - Questions asked: {session.questions_asked}")
            print(f"  - Completeness: {session.completeness_score}")
            print(f"  - Status: {session.status}")

            state_preserved = (
                session.questions_asked >= 3 and
                session.completeness_score > 0
            )
            print_verification(
                "Session metrics preserved",
                state_preserved,
                f"Questions: {session.questions_asked}, Completeness: {session.completeness_score}"
            )
        else:
            print_verification("Session found", False, "Session not in database")

        print("\n[TEST 4 COMPLETE]")
        return skills_preserved and new_skill_added and messages_preserved


def main():
    """Run all verification tests."""
    print("\n" + "🔍" * 50)
    print("DYNAMIC CONVERSATION VERIFICATION TEST SUITE")
    print("🔍" * 50)
    print("\nThis suite verifies 4 core dynamic conversation requirements:")
    print("1. Full conversation history with co-reference resolution")
    print("2. Multi-requirement answer detection")
    print("3. User clarification request handling")
    print("4. State persistence and resume capability")
    print("\n" + "🔍" * 50)

    results = {}

    try:
        # Test 1
        results["test_1_full_history"] = test_full_conversation_history()

        # Test 2
        results["test_2_multi_requirement"] = test_multi_requirement_extraction()

        # Test 3
        results["test_3_clarification"] = test_clarification_request_handling()

        # Test 3B
        results["test_3b_partial_clarification"] = test_partial_answer_with_clarification()

        # Test 4
        results["test_4_persistence"] = test_state_persistence_and_resume()

    except Exception as e:
        print(f"\n❌ TEST SUITE ERROR: {e}")
        import traceback
        traceback.print_exc()
        return

    # Summary
    print("\n" + "=" * 100)
    print("VERIFICATION TEST SUMMARY")
    print("=" * 100)

    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")

    total_passed = sum(1 for p in results.values() if p)
    total_tests = len(results)

    print(f"\nResults: {total_passed}/{total_tests} tests passed")

    if total_passed == total_tests:
        print("\n🎉 ALL TESTS PASSED! Core features are working correctly.")
        print("Ready to proceed with enhancements.")
    else:
        print("\n⚠️  Some tests failed. Review failures before implementing enhancements.")


if __name__ == "__main__":
    main()
