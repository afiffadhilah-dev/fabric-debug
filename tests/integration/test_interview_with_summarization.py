"""
Integration test for interview completion with automatic summarization.

This test verifies that when an interview session ends (using predefined mode),
the summarization agent is automatically triggered and processes the session data.

Run with: python tests/integration/test_interview_with_summarization.py
Requires: Database running (make db-start)
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import all models for SQLAlchemy relationships
import importlib
import pkgutil
import models

for _, name, _ in pkgutil.iter_modules(models.__path__):
    importlib.import_module(f"models.{name}")

from sqlmodel import Session, create_engine, select
from agents.conversational.service import ConversationalInterviewService
from utils.llm_service import LLMService
from utils.prompt_loader import PromptLoader
from models.candidate import Candidate
from models.interview_session import InterviewSession
from models.extracted_skill import ExtractedSkill
from config.settings import settings

# Output path for test results
OUTPUT_DIR = Path(__file__).parent / "output"

# Predefined question set ID (from existing test)
QUESTION_SET_ID = "03b84681-2c75-4bbd-89ee-307861ec7b6b"

# Predefined answers for common question categories
PREDEFINED_ANSWERS = {
    "GENERAL": """I'm a senior software engineer with 6 years of experience building scalable systems.
    Currently leading a team of 5 engineers at a tech startup. I work primarily with Python, FastAPI,
    and PostgreSQL for backend, and React for frontend.""",

    "LEADERSHIP": """I've led a team of 5 engineers for 2 years. My responsibilities include architecture
    decisions, code reviews, mentoring junior developers, and sprint planning. I focus on enabling
    team performance through clear communication and technical guidance.""",

    "BACKEND": """I've worked extensively with Python for 6 years, Node.js for 3 years. Built RESTful APIs,
    GraphQL endpoints, and microservices. Strong experience with FastAPI, Django, and Express.
    I've handled production systems serving 100K+ daily users.""",

    "DATABASE": """Expert in PostgreSQL with 6 years experience. Also worked with MongoDB, Redis for caching.
    Designed schemas, optimized queries, implemented replication. Handled databases with millions of records.""",

    "SCALE": """Our main system handles 100K+ daily active users, 10M API requests per day.
    I've optimized for performance, implemented caching strategies, and designed for horizontal scaling.""",

    "TESTING": """I practice TDD for critical business logic. Use pytest for Python, Jest for JavaScript.
    We have comprehensive unit tests, integration tests, and E2E tests with Cypress.""",

    "DEFAULT": """I have solid experience in that area. I've worked on production systems and delivered
    quality code. I'm comfortable with the technical aspects and collaborate well with teams.""",
}


def get_answer_for_question(question: str) -> str:
    """Get a predefined answer based on question keywords."""
    q_lower = question.lower()

    if any(word in q_lower for word in ["lead", "team", "mentor", "manage"]):
        return PREDEFINED_ANSWERS["LEADERSHIP"]
    elif any(word in q_lower for word in ["backend", "api", "python", "node", "server"]):
        return PREDEFINED_ANSWERS["BACKEND"]
    elif any(word in q_lower for word in ["database", "sql", "postgres", "mongo", "redis"]):
        return PREDEFINED_ANSWERS["DATABASE"]
    elif any(word in q_lower for word in ["scale", "users", "production", "performance"]):
        return PREDEFINED_ANSWERS["SCALE"]
    elif any(word in q_lower for word in ["test", "tdd", "quality", "coverage"]):
        return PREDEFINED_ANSWERS["TESTING"]
    elif any(word in q_lower for word in ["role", "experience", "background", "tell me"]):
        return PREDEFINED_ANSWERS["GENERAL"]
    else:
        return PREDEFINED_ANSWERS["DEFAULT"]


def setup_service(db_session: Session) -> ConversationalInterviewService:
    """Initialize the conversational interview service."""
    llm_service = LLMService()
    prompt_loader = PromptLoader()
    return ConversationalInterviewService(llm_service, prompt_loader, db_session)


def print_header(text: str):
    """Print formatted header."""
    print("\n" + "=" * 80)
    print(text)
    print("=" * 80)


def print_step(step: int, text: str):
    """Print step indicator."""
    print(f"\n[Step {step}] {text}")


def save_output(data: dict, filename: str):
    """Save test output to JSON file."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / filename
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    print(f"\nOutput saved to: {output_path}")


def test_interview_with_summarization():
    """
    Simulate a complete interview session (predefined mode) and verify summarization.

    This test:
    1. Creates a candidate and starts an interview in predefined mode
    2. Provides answers to reach interview completion
    3. Verifies summarization was triggered
    4. Outputs the final results
    """
    print_header("INTERVIEW WITH SUMMARIZATION INTEGRATION TEST (PREDEFINED MODE)")

    engine = create_engine(settings.DATABASE_URL)

    with Session(engine) as db_session:
        service = setup_service(db_session)

        # Step 1: Create test candidate
        print_step(1, "Creating test candidate...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        candidate_id = f"test_summarization_{timestamp}"

        candidate = Candidate(id=candidate_id, name="Test Summarization Candidate")
        db_session.add(candidate)
        db_session.commit()
        print(f"  Candidate ID: {candidate_id}")

        # Step 2: Start interview with a resume (predefined mode)
        print_step(2, "Starting interview session (predefined mode)...")
        resume_text = """
        Sarah Chen - Senior Software Engineer

        SUMMARY:
        Experienced software engineer with 6+ years building scalable systems.

        EXPERIENCE:

        Tech Lead at StartupXYZ (2021-Present)
        - Led team of 5 engineers building microservices architecture
        - Designed and implemented real-time data pipeline processing 1M events/day
        - Reduced system latency by 40% through optimization

        Senior Developer at BigCorp (2018-2021)
        - Built RESTful APIs using Python/FastAPI serving 100K daily users
        - Implemented CI/CD pipelines with GitHub Actions
        - Mentored 3 junior developers

        SKILLS:
        - Languages: Python, JavaScript, Go
        - Frameworks: FastAPI, React, Node.js
        - Databases: PostgreSQL, Redis, MongoDB
        - Cloud: AWS (EC2, S3, Lambda), Docker, Kubernetes
        """

        result = service.start_interview(
            candidate_id=candidate_id,
            resume_text=resume_text,
            mode="predefined_questions",
            question_set_id=QUESTION_SET_ID
        )

        session_id = result["session_id"]
        thread_id = result["thread_id"]
        question = result["question"]

        print(f"  Session ID: {session_id}")
        print(f"  Thread ID: {thread_id}")
        print(f"\n  Q1: {question[:100]}..." if len(question) > 100 else f"\n  Q1: {question}")

        # Step 3: Simulate interview answers
        print_step(3, "Simulating interview conversation...")

        conversation_log = [{"role": "assistant", "content": question}]
        attempt = 1
        completed = False
        final_result = None
        max_questions = 20  # Limit to prevent infinite loops

        while attempt <= max_questions:
            # Get appropriate answer based on the question
            answer = get_answer_for_question(question)

            print(f"\n  A{attempt}: {answer[:80]}...")
            conversation_log.append({"role": "user", "content": answer})

            result = service.continue_interview(thread_id, answer)

            if result.get("completed"):
                completed = True
                final_result = result
                print(f"\n  Interview completed!")
                print(f"  Termination reason: {result.get('termination_reason')}")
                print(f"  Summarization status: {result.get('summarization_status')}")
                if result.get("completion_message"):
                    msg = result["completion_message"]
                    print(f"  Completion message: {msg[:100]}..." if len(msg) > 100 else f"  Completion message: {msg}")
                break
            else:
                question = result.get("question", "")
                conversation_log.append({"role": "assistant", "content": question})
                print(f"\n  Q{attempt+1}: {question[:80]}..." if len(question) > 80 else f"\n  Q{attempt+1}: {question}")

            attempt += 1

        if not completed:
            print(f"\n  Interview did not complete after {max_questions} questions")

        # Step 4: Verify results
        print_step(4, "Verifying results...")

        # Get session from DB
        statement = select(InterviewSession).where(InterviewSession.id == session_id)
        session = db_session.exec(statement).first()

        # Get extracted skills
        skills = service.get_extracted_skills(session_id)

        print(f"\n  Session Status: {session.status if session else 'N/A'}")
        print(f"  Questions Asked: {session.questions_asked if session else 'N/A'}")
        print(f"  Completeness Score: {session.completeness_score if session else 'N/A'}")
        print(f"  Extracted Skills: {len(skills)}")

        if skills:
            print("\n  Skills Summary:")
            for skill in skills[:5]:  # Show first 5
                print(f"    - {skill['name']}: duration={skill.get('duration')}, depth={skill.get('depth')}")

        # Step 5: Compile and save output
        print_step(5, "Saving test output...")

        output_data = {
            "test_run": {
                "timestamp": datetime.now().isoformat(),
                "candidate_id": candidate_id,
                "session_id": session_id,
                "thread_id": thread_id
            },
            "interview_result": {
                "completed": completed,
                "termination_reason": final_result.get("termination_reason") if final_result else None,
                "summarization_status": final_result.get("summarization_status") if final_result else None,
                "questions_asked": session.questions_asked if session else None,
                "completeness_score": session.completeness_score if session else None
            },
            "extracted_skills": skills,
            "conversation_log": conversation_log
        }

        save_output(output_data, f"interview_summarization_{timestamp}.json")

        # Final verification
        print_header("TEST RESULTS")

        checks = [
            ("Interview completed", completed),
            ("Summarization triggered", final_result.get("summarization_status") == "completed" if final_result else False),
            ("Skills extracted", len(skills) > 0),
            ("Session marked completed", session.status == "completed" if session else False)
        ]

        all_passed = True
        for check_name, passed in checks:
            symbol = "✅" if passed else "❌"
            print(f"  {symbol} {check_name}: {'PASS' if passed else 'FAIL'}")
            if not passed:
                all_passed = False

        print("\n" + "=" * 80)
        if all_passed:
            print("🎉 ALL CHECKS PASSED - Integration working correctly!")
        else:
            print("⚠️  Some checks failed - Review output for details")
        print("=" * 80)

        return all_passed


if __name__ == "__main__":
    try:
        success = test_interview_with_summarization()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ TEST ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
