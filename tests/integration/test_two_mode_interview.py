"""
Integration test for two-mode interview system.

Tests both dynamic_gap and predefined_questions modes end-to-end.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlmodel import Session, create_engine, SQLModel
from agents.conversational.service import ConversationalInterviewService
from utils.llm_service import LLMService
from utils.prompt_loader import PromptLoader
from models.candidate import Candidate
from config.settings import settings
import json


def test_predefined_questions_mode():
    """Test predefined questions mode with resume coverage."""
    print("\n" + "=" * 80)
    print("TEST 1: PREDEFINED QUESTIONS MODE")
    print("=" * 80)

    # Initialize database
    engine = create_engine(settings.DATABASE_URL)
    SQLModel.metadata.create_all(engine)

    with Session(engine) as db_session:
        # Initialize services
        llm_service = LLMService()
        prompt_loader = PromptLoader()
        service = ConversationalInterviewService(llm_service, prompt_loader, db_session)

        # Create test candidate
        candidate_id = "test_predefined_mode"
        candidate = db_session.get(Candidate, candidate_id)
        if not candidate:
            candidate = Candidate(id=candidate_id, name="Test Candidate - Predefined Mode")
            db_session.add(candidate)
            db_session.commit()

        # Comprehensive resume that should answer some questions
        resume_text = """
        Jane Smith
        Senior Software Engineer

        EXPERIENCE:
        - Led development of microservices platform using Python and FastAPI for 5 years
        - Built RESTful APIs serving 100k+ requests/day in production
        - Managed team of 5 developers, conducted code reviews, mentored junior devs
        - Implemented CI/CD pipelines with GitHub Actions and Docker
        - Worked with PostgreSQL, Redis, and MongoDB in high-scale environments
        - Deployed to AWS (EC2, S3, Lambda, RDS) with infrastructure as code (Terraform)

        SKILLS:
        - Python (expert level): FastAPI, Django, async programming, pytest
        - JavaScript/TypeScript: React, Node.js, Express
        - Databases: PostgreSQL (advanced), Redis, MongoDB
        - DevOps: Docker, Kubernetes, AWS, Terraform
        - Team Leadership: Led agile teams, conducted sprint planning and retrospectives
        """

        print("\nResume:")
        print("-" * 80)
        print(resume_text.strip())
        print("-" * 80)

        # Start interview in PREDEFINED_QUESTIONS mode
        print("\n[TEST] Starting interview in PREDEFINED_QUESTIONS mode...")
        result = service.start_interview(
            candidate_id=candidate_id,
            resume_text=resume_text,
            mode="predefined_questions",
            question_set_id="03b84681-2c75-4bbd-89ee-307861ec7b6b"
        )

        session_id = result["session_id"]
        thread_id = result["thread_id"]
        question = result["question"]

        print(f"\n[OK] Session created: {session_id}")
        print(f"[OK] Thread ID: {thread_id}")
        print(f"\nFirst question: {question}\n")

        # Simulate 2 Q&A rounds
        answers = [
            "I worked with Python for 5 years in production environments, primarily building REST APIs with FastAPI.",
            "I led a team of 5 developers, conducted code reviews, and mentored junior developers. I had full autonomy over architecture decisions."
        ]

        for i, answer in enumerate(answers, 1):
            print(f"[TEST] Answering question {i}...")
            result = service.continue_interview(thread_id, answer)

            if result["completed"]:
                print(f"\n[OK] Interview completed after {i} questions")
                print(f"Termination reason: {result['termination_reason']}")
                print(f"Completion message: {result['completion_message']}")
                break
            else:
                print(f"\nNext question: {result['question']}\n")

        # Get extracted skills
        print("\n" + "-" * 80)
        print("EXTRACTED SKILLS (Predefined Mode)")
        print("-" * 80)
        skills = service.get_extracted_skills(session_id)

        if skills:
            for skill in skills:
                print(f"\n{skill['name']} (confidence: {skill['confidence_score']:.2f})")
                print(f"  Duration: {skill['duration'] or 'N/A'}")
                print(f"  Depth: {skill['depth'] or 'N/A'}")
                print(f"  Autonomy: {skill['autonomy'] or 'N/A'}")
        else:
            print("\n[INFO] No skills extracted (may need to complete interview)")

        print("\n[OK] Predefined questions mode test completed\n")


def test_dynamic_gap_mode():
    """Test dynamic gap mode."""
    print("\n" + "=" * 80)
    print("TEST 2: DYNAMIC GAP MODE")
    print("=" * 80)

    # Initialize database
    engine = create_engine(settings.DATABASE_URL)
    SQLModel.metadata.create_all(engine)

    with Session(engine) as db_session:
        # Initialize services
        llm_service = LLMService()
        prompt_loader = PromptLoader()
        service = ConversationalInterviewService(llm_service, prompt_loader, db_session)

        # Create test candidate
        candidate_id = "test_dynamic_gap_mode"
        candidate = db_session.get(Candidate, candidate_id)
        if not candidate:
            candidate = Candidate(id=candidate_id, name="Test Candidate - Dynamic Gap")
            db_session.add(candidate)
            db_session.commit()

        # Minimal resume with gaps
        resume_text = """
        John Doe
        Software Engineer

        EXPERIENCE:
        - Worked with Python and React
        - Built some APIs

        SKILLS:
        - Python, JavaScript
        - PostgreSQL
        """

        print("\nResume:")
        print("-" * 80)
        print(resume_text.strip())
        print("-" * 80)

        # Start interview in DYNAMIC_GAP mode (default)
        print("\n[TEST] Starting interview in DYNAMIC_GAP mode...")
        result = service.start_interview(
            candidate_id=candidate_id,
            resume_text=resume_text
        )

        session_id = result["session_id"]
        thread_id = result["thread_id"]
        question = result["question"]

        print(f"\n[OK] Session created: {session_id}")
        print(f"[OK] Thread ID: {thread_id}")
        print(f"\nFirst question: {question}\n")

        # Simulate 2 Q&A rounds
        answers = [
            "I've been working with Python for about 3 years, mainly building REST APIs with Flask.",
            "I worked mostly solo on small projects, handling everything from design to deployment."
        ]

        for i, answer in enumerate(answers, 1):
            print(f"[TEST] Answering question {i}...")
            result = service.continue_interview(thread_id, answer)

            if result["completed"]:
                print(f"\n[OK] Interview completed after {i} questions")
                print(f"Termination reason: {result['termination_reason']}")
                print(f"Completion message: {result['completion_message']}")
                break
            else:
                print(f"\nNext question: {result['question']}\n")

        # Get extracted skills
        print("\n" + "-" * 80)
        print("EXTRACTED SKILLS (Dynamic Gap Mode)")
        print("-" * 80)
        skills = service.get_extracted_skills(session_id)

        if skills:
            for skill in skills:
                print(f"\n{skill['name']} (confidence: {skill['confidence_score']:.2f})")
                print(f"  Duration: {skill['duration'] or 'N/A'}")
                print(f"  Depth: {skill['depth'] or 'N/A'}")
                print(f"  Autonomy: {skill['autonomy'] or 'N/A'}")
        else:
            print("\n[INFO] No skills extracted (may need to complete interview)")

        print("\n[OK] Dynamic gap mode test completed\n")


def test_edge_case_all_questions_filled():
    """Test edge case: resume fills ALL predefined questions."""
    print("\n" + "=" * 80)
    print("TEST 3: EDGE CASE - All Questions Filled by Resume")
    print("=" * 80)

    engine = create_engine(settings.DATABASE_URL)
    SQLModel.metadata.create_all(engine)

    with Session(engine) as db_session:
        llm_service = LLMService()
        prompt_loader = PromptLoader()
        service = ConversationalInterviewService(llm_service, prompt_loader, db_session)

        candidate_id = "test_edge_all_filled"
        candidate = db_session.get(Candidate, candidate_id)
        if not candidate:
            candidate = Candidate(id=candidate_id, name="Test Edge Case - All Filled")
            db_session.add(candidate)
            db_session.commit()

        # Extremely comprehensive resume
        resume_text = """
        Alice Johnson
        Principal Software Engineer

        EXPERIENCE (10+ years):
        - Led development of enterprise e-commerce platform using Python, FastAPI, and React for 6 years
        - Architected microservices handling 1M+ requests/day in production on AWS
        - Managed cross-functional team of 10 engineers, conducted hiring, mentoring, performance reviews
        - Built real-time data processing pipelines with Kafka and Redis
        - Implemented ML models for recommendation system using scikit-learn and TensorFlow
        - Worked with PostgreSQL (sharding, replication), MongoDB, Elasticsearch
        - Led migration from monolith to microservices under aggressive timelines and resource constraints
        - Deployed containerized applications to Kubernetes on AWS EKS
        - Established CI/CD best practices, code review standards, testing strategies

        TECHNICAL EXPERTISE:
        - Python (10 years): FastAPI, Django, Flask, async programming, multiprocessing, profiling
        - JavaScript/TypeScript (8 years): React, Next.js, Node.js, Express, WebSockets
        - Databases (8 years): PostgreSQL (expert), MongoDB, Redis, Elasticsearch
        - Cloud (6 years): AWS (EC2, S3, Lambda, RDS, EKS, CloudFormation), Docker, Kubernetes
        - Leadership: Agile methodologies, sprint planning, stakeholder management, technical mentoring

        NOTABLE ACHIEVEMENTS:
        - Scaled platform from 10k to 1M daily users while maintaining 99.9% uptime
        - Reduced API latency by 60% through caching and query optimization
        - Led team through successful SOC2 compliance certification
        """

        print("\nResume:")
        print("-" * 80)
        print(resume_text.strip())
        print("-" * 80)

        print("\n[TEST] Starting interview with extremely comprehensive resume...")
        try:
            result = service.start_interview(
                candidate_id=candidate_id,
                resume_text=resume_text,
                mode="predefined_questions",
                question_set_id="03b84681-2c75-4bbd-89ee-307861ec7b6b"
            )

            print(f"\n[OK] Session created: {result['session_id']}")
            print(f"First question: {result['question']}")
            print("\n[INFO] If resume fills all questions, interview should complete quickly or ask minimal follow-ups")

        except Exception as e:
            print(f"\n[ERROR] Failed: {e}")

        print("\n[OK] Edge case test completed\n")


def test_validation_errors():
    """Test validation errors."""
    print("\n" + "=" * 80)
    print("TEST 4: VALIDATION ERRORS")
    print("=" * 80)

    engine = create_engine(settings.DATABASE_URL)
    SQLModel.metadata.create_all(engine)

    with Session(engine) as db_session:
        llm_service = LLMService()
        prompt_loader = PromptLoader()
        service = ConversationalInterviewService(llm_service, prompt_loader, db_session)

        candidate_id = "test_validation"
        candidate = db_session.get(Candidate, candidate_id)
        if not candidate:
            candidate = Candidate(id=candidate_id, name="Test Validation")
            db_session.add(candidate)
            db_session.commit()

        resume_text = "Simple resume"

        # Test 1: Invalid mode
        print("\n[TEST] Testing invalid mode...")
        try:
            service.start_interview(
                candidate_id=candidate_id,
                resume_text=resume_text,
                mode="invalid_mode"
            )
            print("[FAIL] Should have raised ValueError")
        except ValueError as e:
            print(f"[OK] Caught expected error: {e}")

        # Test 2: Missing question_set_id for predefined mode
        print("\n[TEST] Testing missing question_set_id...")
        try:
            service.start_interview(
                candidate_id=candidate_id,
                resume_text=resume_text,
                mode="predefined_questions"
            )
            print("[FAIL] Should have raised ValueError")
        except ValueError as e:
            print(f"[OK] Caught expected error: {e}")

        # Test 3: Invalid question_set_id
        print("\n[TEST] Testing invalid question_set_id...")
        try:
            service.start_interview(
                candidate_id=candidate_id,
                resume_text=resume_text,
                mode="predefined_questions",
                question_set_id="00000000-0000-0000-0000-000000000000"
            )
            print("[FAIL] Should have raised ValueError")
        except ValueError as e:
            print(f"[OK] Caught expected error: {e}")

        print("\n[OK] Validation tests completed\n")


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("TWO-MODE INTERVIEW SYSTEM - INTEGRATION TESTS")
    print("=" * 80)

    # Import all models for SQLAlchemy relationships
    import importlib
    import pkgutil
    import models

    for _, name, _ in pkgutil.iter_modules(models.__path__):
        importlib.import_module(f"models.{name}")

    # Run tests
    test_predefined_questions_mode()
    test_dynamic_gap_mode()
    test_edge_case_all_questions_filled()
    test_validation_errors()

    print("\n" + "=" * 80)
    print("ALL TESTS COMPLETED")
    print("=" * 80)
