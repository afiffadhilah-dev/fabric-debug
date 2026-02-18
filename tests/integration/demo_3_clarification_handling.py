"""
DEMO TEST 3: Clarification Request Handling

Demonstrates: Agent recognizes when user needs clarification and provides helpful examples

Scenario:
- Q: "What depth of JavaScript knowledge do you have?"
- A: "What do you mean by that?"
- Result: System detects clarification_request, provides examples, treats as high engagement

Run: python tests/integration/demo_3_clarification_handling.py
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
from models.message import Message
from config.settings import settings


def main():
    print("\n" + "=" * 100)
    print("DEMO 3: CLARIFICATION REQUEST HANDLING")
    print("=" * 100)
    print("\nDemonstrates: Agent provides examples when user asks for clarification\n")

    engine = create_engine(settings.DATABASE_URL)

    with Session(engine) as db_session:
        service = ConversationalInterviewService(
            LLMService(),
            PromptLoader(),
            db_session
        )

        candidate_id = "demo_clarification"
        candidate = db_session.get(Candidate, candidate_id)
        if not candidate:
            candidate = Candidate(id=candidate_id, name="Demo - Clarification")
            db_session.add(candidate)
            db_session.commit()

        resume_text = """
        Bob Johnson - Full Stack Developer

        SKILLS:
        - JavaScript, Python
        - React, Node.js
        """

        print("=" * 100)
        print("STARTING INTERVIEW")
        print("=" * 100)

        result = service.start_interview(
            candidate_id=candidate_id,
            resume_text=resume_text,
            mode="dynamic_gap"
        )

        session_id = result["session_id"]
        thread_id = result["thread_id"]
        question = result["question"]

        print(f"\n[INTERVIEWER]: {question}")

        # User asks for clarification
        answer = "What do you mean by that?"
        print(f"[CANDIDATE]: {answer}")
        print("\n[Agent processing...]")

        result = service.continue_interview(thread_id, answer)
        follow_up = result.get("question")

        print(f"\n[INTERVIEWER]: {follow_up}")

        # Verify: Check message metadata
        print("\n" + "=" * 100)
        print("VERIFICATION")
        print("=" * 100)

        statement = select(Message).where(
            Message.session_id == session_id,
            Message.role == "user"
        )
        user_messages = db_session.exec(statement).all()

        if user_messages:
            last_message = user_messages[-1]
            meta = last_message.meta or {}

            answer_type = meta.get("answer_type")
            engagement_level = meta.get("engagement_level")

            print(f"\nMessage Metadata:")
            print(f"  answer_type: {answer_type}")
            print(f"  engagement_level: {engagement_level}")

            success = True

            if answer_type == "clarification_request":
                print(f"\n✅ Clarification request detected correctly")
            else:
                print(f"\n❌ Failed to detect clarification (detected as: {answer_type})")
                success = False

            if engagement_level == "engaged":
                print(f"✅ Engagement level correct (engaged)")
            else:
                print(f"❌ Wrong engagement level: {engagement_level} (expected: engaged)")
                success = False

            if follow_up:
                print(f"✅ Follow-up question generated")
                if "example" in follow_up.lower() or "like" in follow_up.lower():
                    print(f"✅ Follow-up contains examples/clarification")
                else:
                    print(f"⚠️  Follow-up may not contain examples")
            else:
                print(f"❌ No follow-up question generated")
                success = False

            print("\n" + "=" * 100)
            if success:
                print("🎉 DEMO 3 PASSED: Clarification handling working!")
            else:
                print("❌ DEMO 3 FAILED")
            print("=" * 100 + "\n")
        else:
            print("\n❌ No messages found in database")
            print("\n" + "=" * 100)
            print("❌ DEMO 3 FAILED")
            print("=" * 100 + "\n")


if __name__ == "__main__":
    main()
