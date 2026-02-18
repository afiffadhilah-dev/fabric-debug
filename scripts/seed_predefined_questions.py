"""
Seeder script for predefined questions.

This script seeds the database with predefined question sets from JSON files.
Useful for setting up development environments with consistent data.

Usage:
    python scripts/seed_predefined_questions.py
"""

import sys
from pathlib import Path

# Add parent directory to path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

import json
from uuid import UUID
from sqlmodel import Session, create_engine, select
from config.settings import settings
from models.predefined_role import PredefinedRole, SeniorityLevel
from models.predefined_question_set import PredefinedQuestionSet
from models.predefined_question import PredefinedQuestion

# Create database engine
engine = create_engine(settings.DATABASE_URL)


def seed_from_json(json_file_path: Path):
    """
    Seed database from JSON file.

    Args:
        json_file_path: Path to the JSON file containing seed data
    """
    print(f"Loading data from: {json_file_path}")

    with open(json_file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    with Session(engine) as session:
        # 1. Create or update role
        role_data = data["role"]
        role_id = UUID(role_data["id"])

        existing_role = session.get(PredefinedRole, role_id)

        if existing_role:
            print(f"  Role '{role_data['name']}' already exists (updating)")
            existing_role.name = role_data["name"]
            existing_role.level = SeniorityLevel(role_data["level"])
            existing_role.description = role_data["description"]
            existing_role.is_active = role_data["is_active"]
            session.add(existing_role)
            role = existing_role
        else:
            print(f"  Creating role: {role_data['name']} ({role_data['level']})")
            role = PredefinedRole(
                id=role_id,
                name=role_data["name"],
                level=SeniorityLevel(role_data["level"]),
                description=role_data["description"],
                is_active=role_data["is_active"]
            )
            session.add(role)

        session.commit()

        # 2. Create or update question set
        qs_data = data["question_set"]
        qs_id = UUID(qs_data["id"])

        existing_qs = session.get(PredefinedQuestionSet, qs_id)

        if existing_qs:
            print(f"  Question set '{qs_data['name']}' already exists (updating)")
            existing_qs.name = qs_data["name"]
            existing_qs.version = qs_data["version"]
            existing_qs.description = qs_data["description"]
            existing_qs.is_active = qs_data["is_active"]
            session.add(existing_qs)
            question_set = existing_qs
        else:
            print(f"  Creating question set: {qs_data['name']} (v{qs_data['version']})")
            question_set = PredefinedQuestionSet(
                id=qs_id,
                role_id=role_id,
                name=qs_data["name"],
                version=qs_data["version"],
                description=qs_data["description"],
                is_active=qs_data["is_active"]
            )
            session.add(question_set)

        session.commit()

        # 3. Create or update questions
        questions_data = data["questions"]
        print(f"  Processing {len(questions_data)} questions...")

        created = 0
        updated = 0

        for q_data in questions_data:
            q_id = UUID(q_data["id"])
            existing_q = session.get(PredefinedQuestion, q_id)

            if existing_q:
                # Update existing question
                existing_q.category = q_data["category"]
                existing_q.question_text = q_data["question_text"]
                existing_q.what_assesses = q_data["what_assesses"]
                existing_q.expected_answer_pattern = q_data["expected_answer_pattern"]
                existing_q.order = q_data["order"]
                existing_q.is_required = q_data["is_required"]
                session.add(existing_q)
                updated += 1
            else:
                # Create new question
                question = PredefinedQuestion(
                    id=q_id,
                    question_set_id=qs_id,
                    category=q_data["category"],
                    question_text=q_data["question_text"],
                    what_assesses=q_data["what_assesses"],
                    expected_answer_pattern=q_data["expected_answer_pattern"],
                    order=q_data["order"],
                    is_required=q_data["is_required"]
                )
                session.add(question)
                created += 1

        session.commit()

        print(f"\n[SUCCESS] Seeding completed!")
        print(f"  Questions created: {created}")
        print(f"  Questions updated: {updated}")
        print(f"  Total questions: {len(questions_data)}")

        # Show category breakdown
        from collections import Counter
        categories = Counter(q["category"] for q in questions_data)
        print(f"\n  Questions by category:")
        for category, count in sorted(categories.items()):
            print(f"    - {category}: {count}")


def main():
    """Main seeder function."""
    print("=" * 60)
    print("Predefined Questions Seeder")
    print("=" * 60)
    print()

    # Seed from the default JSON file
    seed_file = root_dir / "scripts" / "seed_data" / "predefined_questions.json"

    if not seed_file.exists():
        print(f"[ERROR] Seed file not found: {seed_file}")
        print("Please run scripts/fetch_predefined_questions.py first.")
        sys.exit(1)

    seed_from_json(seed_file)

    # Also attempt to seed the DevOps predefined questions if present
    devops_seed = root_dir / "scripts" / "seed_data" / "predefined_questions_devops.json"
    if devops_seed.exists():
        print()
        print("Found DevOps seed file — seeding it now.")
        seed_from_json(devops_seed)
    else:
        print()
        print("No DevOps seed file found at expected path; skipping.")

    print()
    print("=" * 60)
    print("You can now use these predefined questions in the UI!")
    print("=" * 60)


if __name__ == "__main__":
    main()
