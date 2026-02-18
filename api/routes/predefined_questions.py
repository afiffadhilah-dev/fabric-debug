from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File, Form
from sqlmodel import Session, select
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from config.settings import settings
from sqlmodel import create_engine
from models.predefined_role import PredefinedRole, SeniorityLevel
from models.predefined_question_set import PredefinedQuestionSet
from models.predefined_question import PredefinedQuestion
from api.models.predefined_questions_schemas import (
    PredefinedRoleCreate,
    PredefinedRoleUpdate,
    PredefinedRoleResponse,
    PredefinedRoleWithQuestionSets,
    PredefinedQuestionSetCreate,
    PredefinedQuestionSetUpdate,
    PredefinedQuestionSetResponse,
    PredefinedQuestionSetWithQuestions,
    PredefinedQuestionCreate,
    PredefinedQuestionUpdate,
    PredefinedQuestionResponse,
    BulkQuestionSetCreate,
)
from utils.document_extractor import DocumentExtractor
from utils.predefined_question_parser import PredefinedQuestionParser
from api.auth import verify_api_key

router = APIRouter(
    prefix="/predefined",
    tags=["Predefined Questions"],
    dependencies=[Depends(verify_api_key)]
)

# Database dependency
engine = create_engine(settings.DATABASE_URL)


def get_session():
    with Session(engine) as session:
        yield session


# ============ ROLE ENDPOINTS ============

@router.post("/roles", response_model=PredefinedRoleResponse, status_code=status.HTTP_201_CREATED)
def create_role(role: PredefinedRoleCreate, db: Session = Depends(get_session)):
    """
    Create a new predefined role for interviews.

    Roles represent job positions (e.g., "Backend Developer", "Data Scientist")
    with a seniority level. Question sets are associated with roles.

    **Seniority Levels:** Junior, Mid, Senior, Lead, Principal
    """
    db_role = PredefinedRole(**role.model_dump())
    db.add(db_role)
    db.commit()
    db.refresh(db_role)
    return db_role


@router.get("/roles", response_model=List[PredefinedRoleResponse])
def list_roles(
    skip: int = 0,
    limit: int = 100,
    is_active: bool = None,
    db: Session = Depends(get_session)
):
    """
    List all predefined roles.

    **Filters:**
    - `is_active`: Filter by active status (true/false)
    - `skip/limit`: Pagination
    """
    query = select(PredefinedRole)
    if is_active is not None:
        query = query.where(PredefinedRole.is_active == is_active)

    roles = db.exec(query.offset(skip).limit(limit)).all()
    return roles


@router.get("/roles/{role_id}", response_model=PredefinedRoleWithQuestionSets)
def get_role(role_id: UUID, db: Session = Depends(get_session)):
    """Get a specific role with its question sets"""
    role = db.get(PredefinedRole, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    return role


@router.patch("/roles/{role_id}", response_model=PredefinedRoleResponse)
def update_role(
    role_id: UUID,
    role_update: PredefinedRoleUpdate,
    db: Session = Depends(get_session)
):
    """Update a predefined role"""
    db_role = db.get(PredefinedRole, role_id)
    if not db_role:
        raise HTTPException(status_code=404, detail="Role not found")

    update_data = role_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_role, key, value)

    db_role.updated_at = datetime.utcnow()
    db.add(db_role)
    db.commit()
    db.refresh(db_role)
    return db_role


@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_role(role_id: UUID, db: Session = Depends(get_session)):
    """Delete a predefined role"""
    db_role = db.get(PredefinedRole, role_id)
    if not db_role:
        raise HTTPException(status_code=404, detail="Role not found")

    db.delete(db_role)
    db.commit()
    return None


# ============ QUESTION SET ENDPOINTS ============

@router.post("/question-sets", response_model=PredefinedQuestionSetResponse, status_code=status.HTTP_201_CREATED)
def create_question_set(
    question_set: PredefinedQuestionSetCreate,
    db: Session = Depends(get_session)
):
    """
    Create a new question set for a role.

    Question sets contain interview questions for a specific role.
    Each role can have multiple question sets (e.g., different versions),
    but only one can be active at a time.

    **Note:** New question sets are inactive by default. Use `/activate` to enable.
    """
    # Verify role exists
    role = db.get(PredefinedRole, question_set.role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    db_question_set = PredefinedQuestionSet(**question_set.model_dump())
    db.add(db_question_set)
    db.commit()
    db.refresh(db_question_set)
    return db_question_set


@router.get("/question-sets", response_model=List[PredefinedQuestionSetResponse])
def list_question_sets(
    skip: int = 0,
    limit: int = 100,
    role_id: UUID = None,
    is_active: bool = None,
    db: Session = Depends(get_session)
):
    """List all question sets with optional filtering"""
    query = select(PredefinedQuestionSet)

    if role_id:
        query = query.where(PredefinedQuestionSet.role_id == role_id)
    if is_active is not None:
        query = query.where(PredefinedQuestionSet.is_active == is_active)

    question_sets = db.exec(query.offset(skip).limit(limit)).all()
    return question_sets


@router.get("/question-sets/{question_set_id}", response_model=PredefinedQuestionSetWithQuestions)
def get_question_set(question_set_id: UUID, db: Session = Depends(get_session)):
    """Get a specific question set with all its questions"""
    question_set = db.get(PredefinedQuestionSet, question_set_id)
    if not question_set:
        raise HTTPException(status_code=404, detail="Question set not found")
    return question_set


@router.get("/question-sets/{question_set_id}/full-details")
def get_question_set_full_details(question_set_id: UUID, db: Session = Depends(get_session)):
    """
    Get complete details: role + question set + all questions in one call.
    Returns everything needed to display full information without additional API calls.
    """
    # Get question set
    question_set = db.get(PredefinedQuestionSet, question_set_id)
    if not question_set:
        raise HTTPException(status_code=404, detail="Question set not found")

    # Get role
    role = db.get(PredefinedRole, question_set.role_id)

    # Get all questions
    questions = db.exec(
        select(PredefinedQuestion)
        .where(PredefinedQuestion.question_set_id == question_set_id)
        .order_by(PredefinedQuestion.order)
    ).all()

    return {
        "role": {
            "id": role.id,
            "name": role.name,
            "level": role.level,
            "description": role.description,
            "is_active": role.is_active
        } if role else None,
        "question_set": {
            "id": question_set.id,
            "role_id": question_set.role_id,
            "name": question_set.name,
            "version": question_set.version,
            "description": question_set.description,
            "is_active": question_set.is_active,
            "created_at": question_set.created_at,
            "updated_at": question_set.updated_at
        },
        "questions": [
            {
                "id": q.id,
                "category": q.category,
                "question_text": q.question_text,
                "what_assesses": q.what_assesses,
                "expected_answer_pattern": q.expected_answer_pattern,
                "order": q.order,
                "is_required": q.is_required
            }
            for q in questions
        ],
        "total_questions": len(questions)
    }


@router.patch("/question-sets/{question_set_id}", response_model=PredefinedQuestionSetResponse)
def update_question_set(
    question_set_id: UUID,
    question_set_update: PredefinedQuestionSetUpdate,
    db: Session = Depends(get_session)
):
    """Update a question set"""
    db_question_set = db.get(PredefinedQuestionSet, question_set_id)
    if not db_question_set:
        raise HTTPException(status_code=404, detail="Question set not found")

    update_data = question_set_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_question_set, key, value)

    db_question_set.updated_at = datetime.utcnow()
    db.add(db_question_set)
    db.commit()
    db.refresh(db_question_set)
    return db_question_set


@router.delete("/question-sets/{question_set_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_question_set(question_set_id: UUID, db: Session = Depends(get_session)):
    """Delete a question set (and all its questions due to cascade)"""
    db_question_set = db.get(PredefinedQuestionSet, question_set_id)
    if not db_question_set:
        raise HTTPException(status_code=404, detail="Question set not found")

    db.delete(db_question_set)
    db.commit()
    return None


@router.post("/question-sets/{question_set_id}/activate", response_model=PredefinedQuestionSetResponse)
def activate_question_set(question_set_id: UUID, db: Session = Depends(get_session)):
    """
    Activate a question set and deactivate all other question sets for the same role.
    Only one question set can be active per role at a time.
    """
    db_question_set = db.get(PredefinedQuestionSet, question_set_id)
    if not db_question_set:
        raise HTTPException(status_code=404, detail="Question set not found")

    # Deactivate all other question sets for this role
    other_sets = db.exec(
        select(PredefinedQuestionSet).where(
            PredefinedQuestionSet.role_id == db_question_set.role_id,
            PredefinedQuestionSet.id != question_set_id
        )
    ).all()

    for other_set in other_sets:
        other_set.is_active = False
        db.add(other_set)

    # Activate this question set
    db_question_set.is_active = True
    db_question_set.updated_at = datetime.utcnow()
    db.add(db_question_set)
    db.commit()
    db.refresh(db_question_set)
    return db_question_set


# ============ QUESTION ENDPOINTS ============

@router.post("/questions", response_model=PredefinedQuestionResponse, status_code=status.HTTP_201_CREATED)
def create_question(question: PredefinedQuestionCreate, db: Session = Depends(get_session)):
    """
    Create a new question in a question set.

    **Fields:**
    - `category`: Group questions (e.g., "Technical", "Behavioral")
    - `what_assesses`: Skills/competencies this question evaluates
    - `order`: Question sequence (lower = asked first)
    - `is_required`: If true, question is always asked
    """
    # Verify question set exists
    question_set = db.get(PredefinedQuestionSet, question.question_set_id)
    if not question_set:
        raise HTTPException(status_code=404, detail="Question set not found")

    db_question = PredefinedQuestion(**question.model_dump())
    db.add(db_question)
    db.commit()
    db.refresh(db_question)
    return db_question


@router.get("/questions", response_model=List[PredefinedQuestionResponse])
def list_questions(
    skip: int = 0,
    limit: int = 100,
    question_set_id: UUID = None,
    category: str = None,
    db: Session = Depends(get_session)
):
    """List all questions with optional filtering"""
    query = select(PredefinedQuestion).order_by(PredefinedQuestion.order)

    if question_set_id:
        query = query.where(PredefinedQuestion.question_set_id == question_set_id)
    if category:
        query = query.where(PredefinedQuestion.category == category)

    questions = db.exec(query.offset(skip).limit(limit)).all()
    return questions


@router.get("/questions/{question_id}", response_model=PredefinedQuestionResponse)
def get_question(question_id: UUID, db: Session = Depends(get_session)):
    """Get a specific question"""
    question = db.get(PredefinedQuestion, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    return question


@router.patch("/questions/{question_id}", response_model=PredefinedQuestionResponse)
def update_question(
    question_id: UUID,
    question_update: PredefinedQuestionUpdate,
    db: Session = Depends(get_session)
):
    """Update a question"""
    db_question = db.get(PredefinedQuestion, question_id)
    if not db_question:
        raise HTTPException(status_code=404, detail="Question not found")

    update_data = question_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_question, key, value)

    db_question.updated_at = datetime.utcnow()
    db.add(db_question)
    db.commit()
    db.refresh(db_question)
    return db_question


@router.delete("/questions/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_question(question_id: UUID, db: Session = Depends(get_session)):
    """Delete a question"""
    db_question = db.get(PredefinedQuestion, question_id)
    if not db_question:
        raise HTTPException(status_code=404, detail="Question not found")

    db.delete(db_question)
    db.commit()
    return None


# ============ BULK OPERATIONS ============

@router.post("/question-sets/bulk", response_model=PredefinedQuestionSetWithQuestions, status_code=status.HTTP_201_CREATED)
def bulk_create_question_set(
    bulk_data: BulkQuestionSetCreate,
    db: Session = Depends(get_session)
):
    """
    Create a question set with all its questions in a single request.
    This is useful for importing question sets from documents.
    """
    # Verify role exists
    role = db.get(PredefinedRole, bulk_data.role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    # Create question set
    question_set_data = bulk_data.model_dump(exclude={"questions"})
    db_question_set = PredefinedQuestionSet(**question_set_data)
    db.add(db_question_set)
    db.commit()
    db.refresh(db_question_set)

    # Create all questions
    for question_data in bulk_data.questions:
        question_dict = question_data.model_dump()
        question_dict["question_set_id"] = db_question_set.id
        db_question = PredefinedQuestion(**question_dict)
        db.add(db_question)

    db.commit()
    db.refresh(db_question_set)
    return db_question_set


# ============ DOCUMENT IMPORT ============

@router.post("/import-from-document", response_model=PredefinedQuestionSetWithQuestions, status_code=status.HTTP_201_CREATED)
async def import_predefined_questions_from_document(
    file: UploadFile = File(...),
    role_name: str = Form(...),
    role_level: str = Form(...),
    role_description: Optional[str] = Form(None),
    question_set_name: str = Form(...),
    question_set_version: str = Form(...),
    question_set_description: Optional[str] = Form(None),
    is_active: bool = Form(False),
    db: Session = Depends(get_session)
):
    """
    Import predefined questions from a document file (.md, .docx, .txt, .pdf).

    This endpoint:
    1. Extracts text from the uploaded document
    2. Uses LLM to parse the text into structured questions
    3. Creates or finds the role
    4. Creates the question set with all questions

    Args:
        file: The document file to import
        role_name: Name of the role (e.g., "Fullstack Developer")
        role_level: Level of the role (Junior, Mid, Senior, Lead, Principal)
        role_description: Optional description of the role
        question_set_name: Name for this question set
        question_set_version: Version identifier (e.g., "v1.0")
        question_set_description: Optional description
        is_active: Whether to set this as the active question set for the role

    Returns:
        The created question set with all imported questions
    """

    # Validate file extension
    allowed_extensions = ['.md', '.txt', '.docx', '.pdf']
    file_extension = '.' + file.filename.split('.')[-1].lower()

    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format. Allowed: {', '.join(allowed_extensions)}"
        )

    # Validate role level
    try:
        seniority_level = SeniorityLevel(role_level)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role level. Must be one of: {', '.join([e.value for e in SeniorityLevel])}"
        )

    try:
        # Step 1: Extract text from document
        file_content = await file.read()
        extractor = DocumentExtractor()
        document_text = extractor.extract_text(file_content, file.filename)

        # Step 2: Parse text into structured questions using LLM
        parser = PredefinedQuestionParser()
        parsed_data = parser.parse_document(document_text, role_name, role_level)

        # Step 3: Find or create the role
        role = db.exec(
            select(PredefinedRole).where(
                PredefinedRole.name == role_name,
                PredefinedRole.level == seniority_level
            )
        ).first()

        if not role:
            role = PredefinedRole(
                name=role_name,
                level=seniority_level,
                description=role_description,
                is_active=True
            )
            db.add(role)
            db.commit()
            db.refresh(role)

        # Step 4: Create the question set
        question_set = PredefinedQuestionSet(
            role_id=role.id,
            name=question_set_name,
            version=question_set_version,
            description=question_set_description,
            is_active=is_active
        )
        db.add(question_set)
        db.commit()
        db.refresh(question_set)

        # Step 5: If this should be active, deactivate others
        if is_active:
            other_sets = db.exec(
                select(PredefinedQuestionSet).where(
                    PredefinedQuestionSet.role_id == role.id,
                    PredefinedQuestionSet.id != question_set.id
                )
            ).all()

            for other_set in other_sets:
                other_set.is_active = False
                db.add(other_set)

            db.commit()

        # Step 6: Create all questions
        for question_data in parsed_data["questions"]:
            question = PredefinedQuestion(
                question_set_id=question_set.id,
                category=question_data["category"],
                question_text=question_data["question_text"],
                what_assesses=question_data["what_assesses"],
                expected_answer_pattern=question_data.get("expected_answer_pattern"),
                order=question_data["order"],
                is_required=question_data.get("is_required", True)
            )
            db.add(question)

        db.commit()
        db.refresh(question_set)

        return question_set

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")
