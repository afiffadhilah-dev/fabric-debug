"""
Main entry point for the AI Agents Interview System.

Demonstrates the interview graph agent conducting a technical skill interview.
"""

from sqlmodel import Session, create_engine, SQLModel
from services import InterviewService
from models.candidate import Candidate
from config.settings import settings


def main():
    print("=" * 80)
    print("AI Interview Agent - Technical Skill Assessment")
    print("=" * 80)
    print()

    # Initialize database
    engine = create_engine(settings.DATABASE_URL)
    SQLModel.metadata.create_all(engine)

    with Session(engine) as db_session:
        # Initialize interview service
        service = InterviewService(db_session)

        # Create or get test candidate
        candidate = db_session.get(Candidate, "test_candidate_1")
        if not candidate:
            candidate = Candidate(id="test_candidate_1", name="user_test")
            db_session.add(candidate)
            db_session.commit()

        # Sample resume for testing
        resume_text = """
        John Doe
        Senior Software Engineer

        EXPERIENCE:
        - Led development of e-commerce platform using Python and React
        - Built RESTful APIs with FastAPI
        - Worked with PostgreSQL databases
        - Implemented CI/CD pipelines with GitHub Actions
        - Managed cloud infrastructure on AWS

        SKILLS:
        - Python, JavaScript, TypeScript
        - React, FastAPI, Django
        - PostgreSQL, Redis
        - Docker, Kubernetes
        - AWS (EC2, S3, Lambda)
        """

        print("Resume:")
        print("-" * 80)
        print(resume_text.strip())
        print("-" * 80)
        print()

        # Start interview - PREDEFINED QUESTIONS MODE
        print("Starting interview in PREDEFINED QUESTIONS mode...\n")
        result = service.start_interview(
            candidate_id=candidate.id,
            resume_text=resume_text,
            mode="predefined_questions",
            question_set_id="03b84681-2c75-4bbd-89ee-307861ec7b6b"
        )

        # To use DYNAMIC GAP MODE instead, use:
        # result = service.start_interview(candidate.id, resume_text)

        session_id = result["session_id"]
        thread_id = result["thread_id"]
        question = result["question"]

        print(f"Interviewer: {question}\n")

        # Interview loop
        while True:
            # Get user input
            answer = input("You: ").strip()

            if not answer:
                print("Please provide an answer, or type 'quit' to exit.\n")
                continue

            if answer.lower() in ['quit', 'exit', 'q']:
                print("\nExiting interview early.")
                break

            # Continue interview
            result = service.continue_interview(session_id, answer)

            if result["completed"]:
                # Interview completed
                print(f"\n{result['completion_message']}\n")
                print("=" * 80)
                print(f"Interview completed: {result['termination_reason']}")
                print("=" * 80)
                break
            else:
                # Next question
                question = result["question"]
                print(f"\nInterviewer: {question}\n")

        # Show extracted skills
        print("\n" + "=" * 80)
        print("EXTRACTED SKILLS")
        print("=" * 80)

        skills = service.get_extracted_skills(session_id)

        if skills:
            for i, skill in enumerate(skills, 1):
                print(f"\n{i}. {skill['name']} (confidence: {skill['confidence_score']:.2f})")
                print(f"   Duration: {skill['duration'] or 'unknown'}")
                print(f"   Depth: {skill['depth'] or 'unknown'}")
                print(f"   Autonomy: {skill['autonomy'] or 'unknown'}")
                print(f"   Scale: {skill['scale'] or 'unknown'}")
                print(f"   Constraints: {skill['constraints'] or 'unknown'}")
                print(f"   Production/Prototype: {skill['production_vs_prototype'] or 'unknown'}")
                if skill['evidence']:
                    print(f"   Evidence: {skill['evidence'][:100]}...")
        else:
            print("\nNo skills extracted yet.")

        print("\n" + "=" * 80)
        print("Interview session complete!")
        print("=" * 80)


if __name__ == "__main__":
    main()
