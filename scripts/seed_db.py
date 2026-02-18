"""Seed script to insert a minimal Candidate, InterviewSession and Message rows.

This no longer reads JSON files — it creates a small deterministic dataset
useful for local development and tests. It will create a candidate with id
`seed_candidate_1`, an interview session `seed_session_1`, and two messages.

Usage:
  $env:PYTHONPATH = "$PWD"
  python scripts/seed_db.py
"""
from datetime import datetime, timedelta
import sys
from pathlib import Path

# When running the script directly (e.g. `python scripts/seed_db.py`),
# ensure the repository root is on `sys.path` so local package imports
# like `config.settings` resolve correctly without setting `PYTHONPATH`.
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
import uuid
import argparse
import sys

from sqlmodel import Session, create_engine, SQLModel
from sqlalchemy import delete

from config.settings import settings
from models.candidate import Candidate
from models.interview_session import InterviewSession
from models.message import Message


DEFAULT_CANDIDATE_ID = "0c6dec64-5292-4293-859f-700411c57e6c"
DEFAULT_SESSION_ID = "18426303-9f4f-49ec-bb82-bb7820bb7485"


def perform_reset(db: Session, candidate_id: str, session_id: str) -> int:
    """Delete seeded messages, interview session, and candidate if present.

    Returns number of rows deleted (messages + session + candidate where applicable).
    """
    deleted = 0
    # delete messages for the session
    res = db.exec(delete(Message).where(Message.session_id == session_id))
    deleted += res.rowcount if hasattr(res, "rowcount") and res.rowcount is not None else 0

    # delete interview session
    res = db.exec(delete(InterviewSession).where(InterviewSession.id == session_id))
    deleted += res.rowcount if hasattr(res, "rowcount") and res.rowcount is not None else 0

    # delete candidate
    res = db.exec(delete(Candidate).where(Candidate.id == candidate_id))
    deleted += res.rowcount if hasattr(res, "rowcount") and res.rowcount is not None else 0

    db.commit()
    return deleted


def seed(dry_run: bool = False, reset_flag: bool = False) -> bool:
    db_url = settings.DATABASE_URL
    if not db_url:
        print("ERROR: DATABASE_URL not set in environment/.env", file=sys.stderr)
        return False

    engine = create_engine(db_url)
    # ensure tables exist for local/dev seeding
    SQLModel.metadata.create_all(engine)

    candidate_id = DEFAULT_CANDIDATE_ID
    session_id = DEFAULT_SESSION_ID

    # Rich resume text to support profile extraction tests
    resume_text = (
        "Miguel Santos — Senior Data Platform Engineer\n\n"
        "SUMMARY:\n"
        "Data engineer with 8 years of experience building production-grade analytics and data platforms for healthcare and regulated industries.\n\n"
        "TECHNICAL SKILLS:\n"
        "Languages: Python, SQL\n"
        "Frameworks & Tools: Apache Airflow, Spark, dbt\n"
        "Datastores: PostgreSQL, Snowflake, S3\n"
        "Infrastructure: Docker, Kubernetes, GitHub Actions\n\n"
        "BUSINESS & DOMAIN CONTEXT:\n"
        "Worked on healthcare analytics platforms used by hospitals and insurance providers. Systems processed patient records, "
        "billing data, and operational metrics used for compliance reporting and financial forecasting.\n\n"
        "INFRASTRUCTURE & OPERATIONS:\n"
        "Data pipelines ran in Kubernetes with scheduled and streaming workloads. The platform supported nightly reporting "
        "deadlines for hospitals and was monitored for data freshness, pipeline failures, and SLA breaches.\n\n"
        "EXPERIENCE HIGHLIGHTS:\n"
        "- Built and maintained data pipelines ingesting millions of patient and billing records per day.\n"
        "- Led a migration from on-premise data warehouse to Snowflake, improving query performance and reducing infrastructure costs.\n"
        "- Implemented data quality checks and alerting to catch missing or corrupted healthcare records.\n\n"
        "PROJECTS:\n"
        "- Compliance reporting pipelines for hospital finance teams.\n"
        "- Analytics dashboards used by executives to track operational efficiency and reimbursement rates."
    )


    if dry_run:
        print("DRY RUN: would seed the following:")
        print(f" Candidate: id={candidate_id}, name=Jane Doe")
        print(f" InterviewSession: id={session_id}, resume_text=(len={len(resume_text)})")
        print(" Conversation: multi-message assistant<->user exchange (~12 messages)")
        return True

    try:
        with Session(engine) as db:
            if reset_flag:
                deleted = perform_reset(db, candidate_id, session_id)
                print(f"Reset removed {deleted} rows")

            # Create or reuse candidate
            candidate = db.get(Candidate, candidate_id)
            if not candidate:
                candidate = Candidate(id=candidate_id, name="Jane Doe")
                db.add(candidate)
                db.commit()
                db.refresh(candidate)

            # Create or reuse interview session
            interview = db.get(InterviewSession, session_id)
            if not interview:
                interview = InterviewSession(
                    id=session_id,
                    candidate_id=candidate.id,
                    resume_text=resume_text,
                    status="completed",
                    questions_asked=1,
                    completeness_score=1.0,
                    thread_id=str(uuid.uuid4()),
                )
                db.add(interview)
                db.commit()
                db.refresh(interview)

            # Add a richer realistic conversation between assistant (chatbot) and user
            now = datetime.utcnow()
            convo = [
                {
                    "role": "assistant",
                    "content": "Hi Miguel — I’d like to understand the context you worked in. What was your team responsible for?",
                    "meta": {"source": "seed", "question_number": 1},
                },
                {
                    "role": "user",
                    "content": "My team built and ran the data platform that hospitals used to analyze patient, billing, and operational data. These systems supported compliance and financial reporting.",
                    "meta": {"source": "seed", "answer_type": "domain_context"},
                },
                {
                    "role": "assistant",
                    "content": "How important were those systems to the business?",
                    "meta": {"source": "seed", "question_number": 2},
                },
                {
                    "role": "user",
                    "content": "They were mission critical. If our pipelines failed, hospitals couldn’t submit reports or get reimbursed properly, which directly impacted revenue.",
                    "meta": {"source": "seed", "answer_type": "business_impact"},
                },
                {
                    "role": "assistant",
                    "content": "What kind of production environment did this platform run in?",
                    "meta": {"source": "seed", "question_number": 3},
                },
                {
                    "role": "user",
                    "content": "We ran Airflow and Spark jobs in Kubernetes. Data was stored in Snowflake and S3, and we used GitHub Actions for deploying pipeline changes.",
                    "meta": {"source": "seed", "answer_type": "infrastructure"},
                },
                {
                    "role": "assistant",
                    "content": "Did you have operational responsibilities?",
                    "meta": {"source": "seed", "question_number": 4},
                },
                {
                    "role": "user",
                    "content": "Yes — I was responsible for keeping data pipelines within SLA. I investigated failures, fixed broken jobs, and added alerts when data freshness dropped.",
                    "meta": {"source": "seed", "answer_type": "operations"},
                },
                {
                    "role": "assistant",
                    "content": "What were your main technical contributions?",
                    "meta": {"source": "seed", "question_number": 5},
                },
                {
                    "role": "user",
                    "content": "I designed batch and streaming pipelines using Spark and Airflow, and built data models with dbt so analysts could trust the data.",
                    "meta": {"source": "seed", "answer_type": "technical_details"},
                },
                {
                    "role": "assistant",
                    "content": "Can you quantify the impact of your work?",
                    "meta": {"source": "seed", "question_number": 6},
                },
                {
                    "role": "user",
                    "content": "We cut reporting delays from days to hours and reduced data errors by over 50%, which improved hospital billing accuracy.",
                    "meta": {"source": "seed", "answer_type": "metrics"},
                },
                {
                    "role": "assistant",
                    "content": "Did you have to make any trade-offs?",
                    "meta": {"source": "seed", "question_number": 7},
                },
                {
                    "role": "user",
                    "content": "We chose slower but more reliable batch processing for critical compliance reports instead of real-time pipelines, because accuracy mattered more than speed.",
                    "meta": {"source": "seed", "answer_type": "tradeoff"},
                },
                {
                    "role": "assistant",
                    "content": "Thanks — that gives me a full picture of both your technical and business environment.",
                    "meta": {"source": "seed", "question_number": 8},
                },
            ]


            msg_count = 0
            for i, item in enumerate(convo):
                msg = Message(
                    session_id=interview.id,
                    role=item["role"],
                    content=item["content"],
                    meta=item.get("meta", {}),
                    created_at=now + timedelta(seconds=i * 30),
                )
                db.add(msg)
                msg_count += 1

            db.commit()

            # update interview with accurate question count
            assistant_questions = sum(1 for m in convo if m["role"] == "assistant")
            interview.questions_asked = assistant_questions
            db.add(interview)
            db.commit()

        print(f"Seeded candidate={candidate_id}, interview_session={session_id}, messages={msg_count}")
        return True
    except Exception as exc:
        print(f"ERROR: seeding failed: {exc}", file=sys.stderr)
        return False


def _cli():
    parser = argparse.ArgumentParser(description="Seed the local database with example candidate/session/messages")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without writing to DB")
    parser.add_argument("--reset", action="store_true", help="Remove existing seeded rows before seeding")
    args = parser.parse_args()

    ok = seed(dry_run=args.dry_run, reset_flag=args.reset)
    sys.exit(0 if ok else 2)


if __name__ == '__main__':
    _cli()
