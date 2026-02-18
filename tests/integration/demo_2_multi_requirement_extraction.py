"""
DEMO TEST 2: Multi-Requirement Extraction

Demonstrates: Agent extracts multiple attributes from a single answer

Scenario:
- Q: "Tell me about your Python experience"
- A: "5 years leading a team of 10 developers on production systems serving 100,000 users"
- Result: Extracts duration (5 years), autonomy (leading), scale (100K users), production (production systems)

Run: python tests/integration/demo_2_multi_requirement_extraction.py
"""

import sys
from pathlib import Path

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
    print("DEMO 2: MULTI-REQUIREMENT EXTRACTION")
    print("=" * 100)
    print("\nDemonstrates: Single answer covers multiple requirements at once\n")

    engine = create_engine(settings.DATABASE_URL)

    with Session(engine) as db_session:
        service = ConversationalInterviewService(
            LLMService(),
            PromptLoader(),
            db_session
        )

        candidate_id = "demo_multi_req"
        candidate = db_session.get(Candidate, candidate_id)
        if not candidate:
            candidate = Candidate(id=candidate_id, name="Demo - Multi Requirement")
            db_session.add(candidate)
            db_session.commit()

        resume_text = """
        Jane Smith - Backend Developer

        SKILLS:
        - Python (FastAPI, Django)
        - PostgreSQL
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

        # Rich answer covering multiple attributes
        answer = "I worked with Python for 5 years, leading a team of 10 developers on production systems serving 100,000 active users daily"
        print(f"[CANDIDATE]: {answer}")

        result = service.continue_interview(thread_id, answer)

        # Continue until interview completes (to persist skills)
        attempt = 2
        while not result.get("completed") and attempt <= 5:
            question = result.get("question")
            if question:
                print(f"\n[INTERVIEWER]: {question}")
                answer = "About 2 years in production"
                print(f"[CANDIDATE]: {answer}")
                result = service.continue_interview(thread_id, answer)
            attempt += 1

        if result.get("completed"):
            print(f"\n[Interview completed: {result.get('termination_reason')}]")

        # Verify: Check extracted attributes
        print("\n" + "=" * 100)
        print("VERIFICATION")
        print("=" * 100)

        skills = service.get_extracted_skills(session_id)
        python_skill = next((s for s in skills if "python" in s["name"].lower()), None)

        if python_skill:
            print(f"\nExtracted from single answer:")
            print(f"  Duration: {python_skill.get('duration')}")
            print(f"  Autonomy: {python_skill.get('autonomy')}")
            print(f"  Scale: {python_skill.get('scale')}")
            print(f"  Production: {python_skill.get('production_vs_prototype')}")
            print(f"  Depth: {python_skill.get('depth')}")
            print(f"  Constraints: {python_skill.get('constraints')}")

            # Count extracted attributes
            attrs = [
                python_skill.get("duration"),
                python_skill.get("autonomy"),
                python_skill.get("scale"),
                python_skill.get("production_vs_prototype")
            ]
            count = sum(1 for attr in attrs if attr is not None)

            print(f"\n📊 Attributes extracted: {count}/4 from single answer")

            if count >= 3:
                print(f"\n✅ Multi-requirement extraction working: {count} attributes from one answer")
                print("\n" + "=" * 100)
                print("🎉 DEMO 2 PASSED: Multi-requirement extraction working!")
                print("=" * 100 + "\n")
            else:
                print(f"\n❌ Only {count} attributes extracted (expected 3+)")
                print("\n" + "=" * 100)
                print("❌ DEMO 2 FAILED")
                print("=" * 100 + "\n")
        else:
            print("\n❌ Python skill not found")
            print("\n" + "=" * 100)
            print("❌ DEMO 2 FAILED")
            print("=" * 100 + "\n")


if __name__ == "__main__":
    main()
