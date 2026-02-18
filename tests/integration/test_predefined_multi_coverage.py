"""
Test: Multi-Question Coverage in Predefined Mode

Scenario:
- User is asked about their role (Question 1)
- User provides VERY detailed answer covering:
  - Their role
  - Frontend experience (React, TypeScript)
  - Backend experience (Python, APIs)
  - Leadership experience
- Later questions about frontend/backend should recognize this was already covered
- Interview should skip or only follow-up for completeness, not re-ask from scratch

Expected Behavior:
- System detects that answer covers multiple question assessments
- Subsequent questions that were "filled" by the answer are marked as covered
- Interview asks follow-up for completeness, not redundant questions

Run: python tests/integration/test_predefined_multi_coverage.py
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
from models.interview_session import InterviewSession
from config.settings import settings


def main():
    print("\n" + "=" * 100)
    print("TEST: MULTI-QUESTION COVERAGE IN PREDEFINED MODE")
    print("=" * 100)
    print("\nScenario: User's detailed answer covers multiple subsequent questions")
    print("Expected: System should not re-ask questions already answered\n")

    engine = create_engine(settings.DATABASE_URL)

    with Session(engine) as db_session:
        service = ConversationalInterviewService(
            LLMService(),
            PromptLoader(),
            db_session
        )

        # Create test candidate
        candidate_id = "test_multi_coverage"
        candidate = db_session.get(Candidate, candidate_id)
        if not candidate:
            candidate = Candidate(id=candidate_id, name="Test - Multi Coverage")
            db_session.add(candidate)
            db_session.commit()

        # Simple resume - intentionally brief
        resume_text = """
        John Smith - Software Engineer

        EXPERIENCE:
        - Software Engineer at TechCorp (2020-Present)

        SKILLS:
        - Programming
        - Team collaboration
        """

        question_set_id = "03b84681-2c75-4bbd-89ee-307861ec7b6b"

        print("=" * 100)
        print("STARTING INTERVIEW")
        print("=" * 100)

        result = service.start_interview(
            candidate_id=candidate_id,
            resume_text=resume_text,
            mode="predefined_questions",
            question_set_id=question_set_id
        )

        session_id = result["session_id"]
        thread_id = result["thread_id"]
        question1 = result["question"]

        print(f"\n[Q1]: {question1}")

        # VERY DETAILED answer that covers multiple topics
        detailed_answer = """
        I'm currently a Senior Fullstack Engineer at TechCorp, where I've been for 4 years.

        On the FRONTEND side, I work extensively with React and TypeScript. I've built
        several large-scale SPAs serving 100k+ users. I handle state management with Redux
        and have experience with Next.js for SSR. I also mentor junior developers on
        React best practices.

        For BACKEND, I primarily use Python with FastAPI. I've designed and built RESTful
        APIs and microservices architecture. Our services handle 50k requests per minute.
        I also work with PostgreSQL, Redis for caching, and have set up CI/CD pipelines.

        In terms of LEADERSHIP, I lead a team of 5 engineers. I conduct code reviews,
        run sprint planning, and make architecture decisions. I've also been involved in
        hiring - I've interviewed over 20 candidates and designed our technical assessment.

        I've also dealt with PRODUCTION INCIDENTS - last month I led the response to a
        database outage that affected 10k users. I coordinated the team, communicated with
        stakeholders, and we resolved it within 2 hours.
        """

        print(f"\n[A1 - DETAILED]: {detailed_answer[:200]}...")
        print("       (Answer covers: role, frontend, backend, leadership, incident response)")

        result = service.continue_interview(thread_id, detailed_answer)

        # Track questions asked
        questions_asked = [question1]
        question_num = 2

        # Continue interview and observe what questions are asked
        print("\n" + "-" * 100)
        print("OBSERVING SUBSEQUENT QUESTIONS")
        print("-" * 100)

        while not result.get("completed") and question_num <= 8:
            question = result.get("question")
            if question:
                questions_asked.append(question)
                print(f"\n[Q{question_num}]: {question}")

                # Check if this is asking about something already covered
                q_lower = question.lower()
                if any(topic in q_lower for topic in ["frontend", "react", "typescript"]):
                    print("       ⚠️  FRONTEND - Already covered in A1!")
                elif any(topic in q_lower for topic in ["backend", "python", "api"]):
                    print("       ⚠️  BACKEND - Already covered in A1!")
                elif any(topic in q_lower for topic in ["lead", "team", "mentor"]):
                    print("       ⚠️  LEADERSHIP - Already covered in A1!")

                # Give a brief answer for subsequent questions
                brief_answer = "As I mentioned earlier, I have experience in this area through my work at TechCorp."
                print(f"[A{question_num}]: {brief_answer}")

                result = service.continue_interview(thread_id, brief_answer)
                question_num += 1

        if result.get("completed"):
            print(f"\n[Interview completed: {result.get('termination_reason')}]")

        # ANALYSIS
        print("\n" + "=" * 100)
        print("ANALYSIS")
        print("=" * 100)

        # Get session details
        session = db_session.get(InterviewSession, session_id)

        print(f"\n📊 Interview Stats:")
        print(f"   Total Questions Asked: {session.questions_asked}")
        print(f"   Completeness: {session.completeness_score:.1%}")

        # Get all messages to analyze criteria assessments
        statement = select(Message).where(
            Message.session_id == session_id,
            Message.role == "user"
        ).order_by(Message.created_at)
        user_messages = db_session.exec(statement).all()

        print(f"\n📝 Answer Analysis:")
        for i, msg in enumerate(user_messages, 1):
            meta = msg.meta or {}
            criteria = meta.get("criteria_assessment", {})
            if criteria:
                quality = criteria.get("answer_quality", 0)
                assessed = criteria.get("criteria_assessed", [])
                print(f"\n   Answer {i}:")
                print(f"   - Quality: {quality}/5")
                print(f"   - Criteria Assessed: {len(assessed)}")

        # Check for redundancy
        print(f"\n🔍 Question Topics Asked:")
        for i, q in enumerate(questions_asked, 1):
            print(f"   Q{i}: {q[:80]}...")

        print("\n" + "=" * 100)
        print("KEY OBSERVATIONS")
        print("=" * 100)
        print("""
        Current Behavior:
        - System asks predefined questions in order
        - Does NOT check if previous answers already covered the topic

        Desired Behavior:
        - After detailed A1, system should detect topics already covered
        - Skip or modify questions about frontend/backend/leadership
        - Only ask follow-up for completeness, not re-ask from scratch

        Implementation Needed:
        - After each answer, analyze if it covers OTHER predefined gaps
        - Mark those gaps as partially/fully filled
        - When generating next question, acknowledge what was covered
        """)
        print("=" * 100)


if __name__ == "__main__":
    # Import all models
    import importlib
    import pkgutil
    import models

    for _, name, _ in pkgutil.iter_modules(models.__path__):
        importlib.import_module(f"models.{name}")

    main()
