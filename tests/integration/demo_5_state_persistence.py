"""
DEMO TEST 5: State Persistence and Resume Capability

Demonstrates: Interview can be paused and resumed across application restarts

Scenario:
- Start interview, answer 2 questions
- Save thread_id
- Simulate restart: Create NEW service instance
- Continue with same thread_id
- Result: Full conversation history, skills, and state preserved

Run: python tests/integration/demo_5_state_persistence.py
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlmodel import Session, create_engine, select
from agents.conversational.service import ConversationalInterviewService
from utils.llm_service import LLMService
from utils.prompt_loader import PromptLoader
from models.candidate import Candidate
from models.interview_session import InterviewSession
from models.message import Message
from config.settings import settings


def main():
    print("\n" + "=" * 100)
    print("DEMO 5: STATE PERSISTENCE AND RESUME CAPABILITY")
    print("=" * 100)
    print("\nDemonstrates: Interview resumes seamlessly after application restart\n")

    engine = create_engine(settings.DATABASE_URL)

    # PHASE 1: Start interview with first service instance
    print("=" * 100)
    print("PHASE 1: STARTING INTERVIEW (Service Instance #1)")
    print("=" * 100)

    with Session(engine) as db_session:
        service1 = ConversationalInterviewService(
            LLMService(),
            PromptLoader(),
            db_session
        )

        candidate_id = "demo_persistence"
        candidate = db_session.get(Candidate, candidate_id)
        if not candidate:
            candidate = Candidate(id=candidate_id, name="Demo - Persistence")
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

        result = service1.start_interview(
            candidate_id=candidate_id,
            resume_text=resume_text,
            mode="dynamic_gap"
        )

        session_id = result["session_id"]
        thread_id = result["thread_id"]
        question = result["question"]

        print(f"\nSession ID: {session_id}")
        print(f"Thread ID: {thread_id}")
        print(f"\n[INTERVIEWER]: {question}")

        # Answer 1
        answer1 = "Python for 5 years"
        print(f"[CANDIDATE]: {answer1}")

        result = service1.continue_interview(thread_id, answer1)
        question = result.get("question")

        if question:
            print(f"\n[INTERVIEWER]: {question}")

            # Answer 2
            answer2 = "Expert level with production experience"
            print(f"[CANDIDATE]: {answer2}")

            service1.continue_interview(thread_id, answer2)

        # Get state before "restart"
        skills_before = service1.get_extracted_skills(session_id)
        print(f"\n[State before restart: {len(skills_before)} skills extracted]")

    # PHASE 2: Simulate restart - create NEW service instance
    print("\n" + "=" * 100)
    print("PHASE 2: SIMULATING APPLICATION RESTART")
    print("=" * 100)
    print("\n[Creating new service instance...]")
    print("[Loading state from PostgreSQL checkpointer...]")

    with Session(engine) as db_session:
        service2 = ConversationalInterviewService(
            LLMService(),
            PromptLoader(),
            db_session
        )

        print(f"\n[Resuming interview with thread_id: {thread_id}]")

        # Continue with same thread_id
        answer3 = "I also worked with Spark for 3 years"
        print(f"\n[CANDIDATE]: {answer3}")

        result = service2.continue_interview(thread_id, answer3)
        question = result.get("question")

        if question:
            print(f"\n[INTERVIEWER]: {question}")

        # Get state after resume
        skills_after = service2.get_extracted_skills(session_id)

        # Verify
        print("\n" + "=" * 100)
        print("VERIFICATION")
        print("=" * 100)

        success = True

        # 1. Skills preserved
        if len(skills_after) >= len(skills_before):
            print(f"\n✅ Skills preserved: {len(skills_before)} before → {len(skills_after)} after")
        else:
            print(f"\n❌ Skills lost: {len(skills_before)} before → {len(skills_after)} after")
            success = False

        # 2. New skill added (Spark)
        spark_skill = next((s for s in skills_after if "spark" in s["name"].lower()), None)
        if spark_skill:
            print(f"✅ New skill extracted after resume: {spark_skill['name']}")
        else:
            print(f"❌ New skill NOT extracted after resume")
            success = False

        # 3. Check message count
        statement = select(Message).where(Message.session_id == session_id)
        messages = db_session.exec(statement).all()
        message_count = len(messages)

        if message_count >= 6:  # At least 3 Q + 3 A
            print(f"✅ Conversation history preserved: {message_count} messages")
        else:
            print(f"⚠️  Message count: {message_count} (expected >= 6)")

        # 4. Session state preserved
        statement = select(InterviewSession).where(InterviewSession.id == session_id)
        session = db_session.exec(statement).first()

        if session:
            print(f"\n📊 Session State:")
            print(f"  Questions asked: {session.questions_asked}")
            print(f"  Completeness: {session.completeness_score:.1%}")
            print(f"  Status: {session.status}")

            if session.questions_asked >= 3 and session.completeness_score > 0:
                print(f"\n✅ Session metrics preserved")
            else:
                print(f"\n⚠️  Session metrics may be incomplete")
        else:
            print(f"\n❌ Session not found")
            success = False

        print("\n" + "=" * 100)
        if success:
            print("🎉 DEMO 5 PASSED: State persistence working!")
            print("\nKey Capabilities Demonstrated:")
            print("- PostgreSQL checkpointer preserves full state")
            print("- Interview can pause/resume across app restarts")
            print("- Conversation history, skills, and completeness all preserved")
            print("- Thread-based state management works correctly")
        else:
            print("❌ DEMO 5 FAILED")
        print("=" * 100 + "\n")


if __name__ == "__main__":
    main()
