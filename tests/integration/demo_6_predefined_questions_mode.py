"""
DEMO TEST 6: Predefined Questions Mode

Demonstrates: Using predefined question sets instead of dynamic gap-based questions

Scenario:
- Start interview with predefined question set (mode="predefined_questions")
- Questions come from a pre-configured question set (not dynamically generated)
- Answer questions from the predefined list
- System assesses answers against criteria (what_assesses) from each question

Difference from dynamic_gap mode:
- dynamic_gap: Extracts technical skills with 6 attributes (duration, depth, etc.)
- predefined_questions: Assesses answers against predefined criteria (leadership, decision-making, etc.)

Run: python tests/integration/demo_6_predefined_questions_mode.py
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlmodel import Session, create_engine
from agents.conversational.service import ConversationalInterviewService
from utils.llm_service import LLMService
from utils.prompt_loader import PromptLoader
from models.candidate import Candidate
from config.settings import settings


def main():
    print("\n" + "=" * 100)
    print("DEMO 6: PREDEFINED QUESTIONS MODE")
    print("=" * 100)
    print("\nDemonstrates: Questions come from predefined set, not dynamically generated from gaps\n")

    engine = create_engine(settings.DATABASE_URL)

    with Session(engine) as db_session:
        service = ConversationalInterviewService(
            LLMService(),
            PromptLoader(),
            db_session
        )

        # Create test candidate
        candidate_id = "demo_predefined"
        candidate = db_session.get(Candidate, candidate_id)
        if not candidate:
            candidate = Candidate(id=candidate_id, name="Demo - Predefined Questions")
            db_session.add(candidate)
            db_session.commit()

        # Resume mentioning Python, React, and leadership
        resume_text = """
        Alice Johnson - Fullstack Engineer

        EXPERIENCE:
        - Senior Engineer at TechCorp (2020-Present)
        - Led team of 3 developers building web applications
        - Technologies: Python, React, PostgreSQL

        SKILLS:
        - Python (backend development with FastAPI)
        - React (frontend development)
        - Team leadership and mentoring
        """

        print("=" * 100)
        print("STARTING INTERVIEW - PREDEFINED QUESTIONS MODE")
        print("=" * 100)
        print("\nNote: Questions come from a predefined question set, not from gap analysis")

        # Use predefined question set ID
        # This ID should exist in the database (from migrations/seed data)
        question_set_id = "03b84681-2c75-4bbd-89ee-307861ec7b6b"  # Default fullstack set

        result = service.start_interview(
            candidate_id=candidate_id,
            resume_text=resume_text,
            mode="predefined_questions",
            question_set_id=question_set_id
        )

        session_id = result["session_id"]
        thread_id = result["thread_id"]
        question = result["question"]

        print(f"\n[INTERVIEWER Q1]: {question}")

        # Answer 1: Behavioral answer demonstrating leadership and decision-making
        answer1 = """At TechCorp, I led a team of 3 developers on a critical project
        to rebuild our payment system. When we faced a tight deadline, I had to make
        a tough decision to cut some features to ensure we shipped on time. I communicated
        this trade-off clearly to stakeholders and got their buy-in. The project launched
        successfully and we added the remaining features in the next sprint."""

        print(f"[CANDIDATE A1]: {answer1}")

        result = service.continue_interview(thread_id, answer1)
        question = result.get("question")

        if question:
            print(f"\n[INTERVIEWER Q2]: {question}")

            # Answer 2: Behavioral answer about collaboration and problem-solving
            answer2 = """I once had a disagreement with a senior engineer about our
            architecture approach. Instead of escalating, I set up a meeting where we
            both presented our solutions with pros and cons. We ended up combining the
            best parts of both approaches. This taught me the value of collaborative
            problem-solving and keeping an open mind."""

            print(f"[CANDIDATE A2]: {answer2}")

            result = service.continue_interview(thread_id, answer2)

        # Answer a few more questions with behavioral responses
        attempt = 3
        while not result.get("completed") and attempt <= 5:
            question = result.get("question")
            if question:
                print(f"\n[INTERVIEWER Q{attempt}]: {question}")

                # Generic behavioral answer
                answer = """In my experience, I've handled similar situations by first
                understanding all perspectives involved. I then work to find a solution
                that addresses the core concerns. For example, when facing technical debt,
                I proposed a phased approach that balanced new features with cleanup work.
                This got buy-in from both engineering and product teams."""

                print(f"[CANDIDATE A{attempt}]: {answer}")
                result = service.continue_interview(thread_id, answer)
            attempt += 1

        # Check if interview completed
        if result.get("completed"):
            print(f"\n[Interview completed: {result.get('termination_reason')}]")

        # Verify: Check criteria assessments (NOT skill extraction)
        print("\n" + "=" * 100)
        print("VERIFICATION - CRITERIA ASSESSMENT")
        print("=" * 100)

        # Query messages to check criteria assessments
        from sqlmodel import select
        from models.message import Message
        from models.interview_session import InterviewSession

        statement = select(Message).where(
            Message.session_id == session_id,
            Message.role == "user"
        ).order_by(Message.created_at)
        user_messages = db_session.exec(statement).all()

        success = True
        assessed_count = 0
        total_quality = 0

        print(f"\nCriteria Assessments from Answers:")

        for i, msg in enumerate(user_messages, 1):
            meta = msg.meta or {}
            criteria_assessment = meta.get("criteria_assessment")

            if criteria_assessment:
                assessed_count += 1
                quality = criteria_assessment.get("answer_quality", 0)
                total_quality += quality
                criteria_list = criteria_assessment.get("criteria_assessed", [])

                print(f"\n✅ Answer {i} assessed:")
                print(f"   Quality Score: {quality}/5")
                print(f"   Criteria Evaluated: {len(criteria_list)}")
                if criteria_list:
                    for c in criteria_list[:3]:  # Show first 3
                        print(f"   - {c.get('criterion', 'N/A')}: {c.get('demonstrated', 'N/A')}")
            else:
                print(f"\n⚠️  Answer {i}: No criteria assessment found")

        # Check if we got any assessments
        if assessed_count == 0:
            print(f"\n❌ No criteria assessments found!")
            success = False
        else:
            avg_quality = total_quality / assessed_count
            print(f"\n📊 Assessment Summary:")
            print(f"   Answers Assessed: {assessed_count}/{len(user_messages)}")
            print(f"   Average Quality: {avg_quality:.1f}/5")

            if avg_quality >= 2:
                print(f"   ✅ Quality threshold met")
            else:
                print(f"   ⚠️  Quality below threshold")

        # Check session metadata
        session = db_session.get(InterviewSession, session_id)

        print(f"\n📊 Interview Metadata:")
        print(f"   Mode: {session.mode}")
        print(f"   Questions Asked: {session.questions_asked}")
        print(f"   Completeness: {session.completeness_score:.1%}")
        print(f"   Status: {session.status}")

        if session.mode == "predefined_questions":
            print(f"   ✅ Confirmed: Using predefined_questions mode")
        else:
            print(f"   ❌ Mode mismatch: Expected 'predefined_questions', got '{session.mode}'")
            success = False

        print("\n" + "=" * 100)
        if success:
            print("🎉 DEMO 6 PASSED: Predefined questions mode working!")
            print("=" * 100)
            print("\nKey Takeaway:")
            print("- Questions came from a predefined set (not generated from gap analysis)")
            print("- Answers were assessed against criteria (what_assesses) from each question")
            print("- This mode is useful for standardized interviews with consistent evaluation")
        else:
            print("❌ DEMO 6 FAILED: Predefined questions mode not working as expected")
            print("=" * 100)
        print()


if __name__ == "__main__":
    main()
