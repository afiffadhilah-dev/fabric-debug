"""
DEMO TEST 1: Co-reference Resolution

Demonstrates: Agent understands "same as" references by looking at full conversation history

Scenario:
- Q1: "How long with Python?"
- A1: "Python: 3 years"
- Q2: "How long with React?"
- A2: "Same duration for React"
- Result: System correctly extracts React duration = 3 years

Run: python tests/integration/demo_1_coreference_resolution.py
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
    print("DEMO 1: CO-REFERENCE RESOLUTION")
    print("=" * 100)
    print("\nDemonstrates: Agent sees full conversation history and resolves 'same as' references\n")

    engine = create_engine(settings.DATABASE_URL)

    with Session(engine) as db_session:
        service = ConversationalInterviewService(
            LLMService(),
            PromptLoader(),
            db_session
        )

        # Create test candidate
        candidate_id = "demo_coreference"
        candidate = db_session.get(Candidate, candidate_id)
        if not candidate:
            candidate = Candidate(id=candidate_id, name="Demo - Co-reference")
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

        # Answer 1: Provide Python duration
        answer1 = "Python: 3 years"
        print(f"[CANDIDATE]: {answer1}")

        result = service.continue_interview(thread_id, answer1)
        question = result.get("question")

        if question:
            print(f"\n[INTERVIEWER]: {question}")

            # Answer 2: Co-reference to previous answer
            answer2 = "Same duration for React"
            print(f"[CANDIDATE]: {answer2}")

            service.continue_interview(thread_id, answer2)

        # Verify: Check extracted skills
        print("\n" + "=" * 100)
        print("VERIFICATION")
        print("=" * 100)

        skills = service.get_extracted_skills(session_id)

        python_skill = next((s for s in skills if "python" in s["name"].lower()), None)
        react_skill = next((s for s in skills if "react" in s["name"].lower()), None)

        print(f"\nExtracted Skills:")
        print(f"  Python: duration = {python_skill.get('duration') if python_skill else 'NOT FOUND'}")
        print(f"  React:  duration = {react_skill.get('duration') if react_skill else 'NOT FOUND'}")

        # Check results
        success = True
        if python_skill and python_skill.get("duration"):
            print(f"\n✅ Python duration extracted: {python_skill['duration']}")
        else:
            print(f"\n❌ Python duration NOT extracted")
            success = False

        if react_skill and react_skill.get("duration"):
            print(f"✅ React duration extracted from co-reference: {react_skill['duration']}")
        else:
            print(f"❌ React duration NOT extracted from co-reference")
            success = False

        if python_skill and react_skill and python_skill.get("duration") == react_skill.get("duration"):
            print(f"✅ Co-reference resolved correctly: Both = {python_skill['duration']}")
        else:
            print(f"❌ Co-reference resolution failed: Durations don't match")
            success = False

        print("\n" + "=" * 100)
        if success:
            print("🎉 DEMO 1 PASSED: Co-reference resolution working!")
        else:
            print("❌ DEMO 1 FAILED: Co-reference resolution not working")
        print("=" * 100 + "\n")


if __name__ == "__main__":
    main()
