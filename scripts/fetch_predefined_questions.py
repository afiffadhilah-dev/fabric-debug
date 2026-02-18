"""
Script to fetch predefined question set from database and save as JSON.
"""

import sys
from pathlib import Path

# Add parent directory to path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

import json
from sqlmodel import Session, create_engine, select
from config.settings import settings
from models.predefined_role import PredefinedRole
from models.predefined_question_set import PredefinedQuestionSet
from models.predefined_question import PredefinedQuestion

# Create database engine
engine = create_engine(settings.DATABASE_URL)


def fetch_question_set(question_set_id: str):
    """Fetch complete question set with role and all questions."""
    with Session(engine) as session:
        # Get question set
        question_set = session.get(PredefinedQuestionSet, question_set_id)
        if not question_set:
            print(f"Question set {question_set_id} not found")
            return None

        # Get role
        role = session.get(PredefinedRole, question_set.role_id)

        # Get all questions
        questions = session.exec(
            select(PredefinedQuestion)
            .where(PredefinedQuestion.question_set_id == question_set_id)
            .order_by(PredefinedQuestion.order)
        ).all()

        # Build data structure
        data = {
            "role": {
                "id": str(role.id),
                "name": role.name,
                "level": role.level,
                "description": role.description,
                "is_active": role.is_active
            },
            "question_set": {
                "id": str(question_set.id),
                "role_id": str(question_set.role_id),
                "name": question_set.name,
                "version": question_set.version,
                "description": question_set.description,
                "is_active": question_set.is_active
            },
            "questions": [
                {
                    "id": str(q.id),
                    "category": q.category,
                    "question_text": q.question_text,
                    "what_assesses": q.what_assesses,
                    "expected_answer_pattern": q.expected_answer_pattern,
                    "order": q.order,
                    "is_required": q.is_required
                }
                for q in questions
            ]
        }

        return data


if __name__ == "__main__":
    question_set_id = "03b84681-2c75-4bbd-89ee-307861ec7b6b"

    print(f"Fetching question set {question_set_id}...")
    data = fetch_question_set(question_set_id)

    if data:
        # Save to JSON file
        output_file = root_dir / "scripts" / "seed_data" / "predefined_questions.json"
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"\n✅ Data saved to: {output_file}")
        print(f"\nSummary:")
        print(f"  Role: {data['role']['name']} ({data['role']['level']})")
        print(f"  Question Set: {data['question_set']['name']} (v{data['question_set']['version']})")
        print(f"  Total Questions: {len(data['questions'])}")

        # Group by category
        from collections import Counter
        categories = Counter(q['category'] for q in data['questions'])
        print(f"\n  Questions by category:")
        for category, count in categories.items():
            print(f"    - {category}: {count}")
