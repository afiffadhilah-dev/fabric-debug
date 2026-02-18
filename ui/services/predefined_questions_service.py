"""
Service class for predefined questions database operations.

Provides direct database access for the Streamlit UI, eliminating
the need for REST API calls.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from sqlmodel import Session, select

from models.predefined_role import PredefinedRole, SeniorityLevel
from models.predefined_question_set import PredefinedQuestionSet
from models.predefined_question import PredefinedQuestion
from utils.document_extractor import DocumentExtractor
from utils.predefined_question_parser import PredefinedQuestionParser


class PredefinedQuestionsService:
    """
    Service for managing predefined questions, question sets, and roles.

    Provides CRUD operations and document import functionality.
    """

    def __init__(self, db_session: Session):
        """
        Initialize the service with a database session.

        Args:
            db_session: SQLModel database session
        """
        self.db = db_session

    # ============ ROLE OPERATIONS ============

    def list_roles(self, is_active: Optional[bool] = None) -> List[Dict[str, Any]]:
        """
        List all predefined roles with optional filtering.

        Args:
            is_active: Optional filter for active/inactive roles

        Returns:
            List of role dictionaries
        """
        query = select(PredefinedRole)
        if is_active is not None:
            query = query.where(PredefinedRole.is_active == is_active)

        roles = self.db.exec(query).all()
        return [self._role_to_dict(role) for role in roles]

    def create_role(
        self,
        name: str,
        level: str,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new predefined role.

        Args:
            name: Role name (e.g., "Fullstack Developer")
            level: Seniority level (Junior, Mid, Senior, Lead, Principal)
            description: Optional role description

        Returns:
            Created role as dictionary

        Raises:
            ValueError: If level is invalid
        """
        try:
            seniority_level = SeniorityLevel(level)
        except ValueError:
            raise ValueError(
                f"Invalid role level. Must be one of: {', '.join([e.value for e in SeniorityLevel])}"
            )

        db_role = PredefinedRole(
            name=name,
            level=seniority_level,
            description=description,
            is_active=True
        )
        self.db.add(db_role)
        self.db.commit()
        self.db.refresh(db_role)
        return self._role_to_dict(db_role)

    def _role_to_dict(self, role: PredefinedRole) -> Dict[str, Any]:
        """Convert PredefinedRole model to dictionary."""
        return {
            "id": str(role.id),
            "name": role.name,
            "level": role.level.value if isinstance(role.level, SeniorityLevel) else role.level,
            "description": role.description,
            "is_active": role.is_active,
            "created_at": role.created_at.isoformat() if role.created_at else None,
            "updated_at": role.updated_at.isoformat() if role.updated_at else None,
        }

    # ============ QUESTION SET OPERATIONS ============

    def list_question_sets(
        self,
        role_id: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """
        List all question sets with optional filtering.

        Args:
            role_id: Optional filter by role ID
            is_active: Optional filter for active/inactive sets

        Returns:
            List of question set dictionaries
        """
        query = select(PredefinedQuestionSet)

        if role_id:
            query = query.where(PredefinedQuestionSet.role_id == UUID(role_id))
        if is_active is not None:
            query = query.where(PredefinedQuestionSet.is_active == is_active)

        question_sets = self.db.exec(query).all()
        return [self._question_set_to_dict(qs) for qs in question_sets]

    def create_question_set(
        self,
        role_id: str,
        name: str,
        version: str,
        description: Optional[str] = None,
        is_active: bool = False
    ) -> Dict[str, Any]:
        """
        Create a new question set.

        Args:
            role_id: ID of the role this set belongs to
            name: Question set name
            version: Version identifier (e.g., "v1.0")
            description: Optional description
            is_active: Whether to set as active

        Returns:
            Created question set as dictionary

        Raises:
            ValueError: If role not found
        """
        # Verify role exists
        role = self.db.get(PredefinedRole, UUID(role_id))
        if not role:
            raise ValueError("Role not found")

        db_question_set = PredefinedQuestionSet(
            role_id=UUID(role_id),
            name=name,
            version=version,
            description=description,
            is_active=is_active
        )
        self.db.add(db_question_set)
        self.db.commit()
        self.db.refresh(db_question_set)
        return self._question_set_to_dict(db_question_set)

    def activate_question_set(self, question_set_id: str) -> Dict[str, Any]:
        """
        Activate a question set and deactivate all other sets for the same role.

        Only one question set can be active per role at a time.

        Args:
            question_set_id: ID of the question set to activate

        Returns:
            Updated question set as dictionary

        Raises:
            ValueError: If question set not found
        """
        db_question_set = self.db.get(PredefinedQuestionSet, UUID(question_set_id))
        if not db_question_set:
            raise ValueError("Question set not found")

        # Deactivate all other question sets for this role
        other_sets = self.db.exec(
            select(PredefinedQuestionSet).where(
                PredefinedQuestionSet.role_id == db_question_set.role_id,
                PredefinedQuestionSet.id != UUID(question_set_id)
            )
        ).all()

        for other_set in other_sets:
            other_set.is_active = False
            self.db.add(other_set)

        # Activate this question set
        db_question_set.is_active = True
        db_question_set.updated_at = datetime.utcnow()
        self.db.add(db_question_set)
        self.db.commit()
        self.db.refresh(db_question_set)
        return self._question_set_to_dict(db_question_set)

    def _question_set_to_dict(self, qs: PredefinedQuestionSet) -> Dict[str, Any]:
        """Convert PredefinedQuestionSet model to dictionary."""
        return {
            "id": str(qs.id),
            "role_id": str(qs.role_id),
            "name": qs.name,
            "version": qs.version,
            "description": qs.description,
            "is_active": qs.is_active,
            "created_at": qs.created_at.isoformat() if qs.created_at else None,
            "updated_at": qs.updated_at.isoformat() if qs.updated_at else None,
        }

    # ============ QUESTION OPERATIONS ============

    def list_questions(self, question_set_id: str) -> List[Dict[str, Any]]:
        """
        List all questions for a specific question set.

        Args:
            question_set_id: ID of the question set

        Returns:
            List of question dictionaries, ordered by sequence
        """
        query = (
            select(PredefinedQuestion)
            .where(PredefinedQuestion.question_set_id == UUID(question_set_id))
            .order_by(PredefinedQuestion.order)
        )
        questions = self.db.exec(query).all()
        return [self._question_to_dict(q) for q in questions]

    def _question_to_dict(self, q: PredefinedQuestion) -> Dict[str, Any]:
        """Convert PredefinedQuestion model to dictionary."""
        return {
            "id": str(q.id),
            "question_set_id": str(q.question_set_id),
            "category": q.category,
            "question_text": q.question_text,
            "what_assesses": q.what_assesses,
            "expected_answer_pattern": q.expected_answer_pattern,
            "order": q.order,
            "is_required": q.is_required,
            "created_at": q.created_at.isoformat() if q.created_at else None,
            "updated_at": q.updated_at.isoformat() if q.updated_at else None,
        }

    # ============ DOCUMENT IMPORT ============

    def import_from_document(
        self,
        file_content: bytes,
        filename: str,
        role_name: str,
        role_level: str,
        role_description: Optional[str],
        question_set_name: str,
        question_set_version: str,
        question_set_description: Optional[str],
        is_active: bool = False
    ) -> Dict[str, Any]:
        """
        Import questions from a document file.

        This method:
        1. Extracts text from the uploaded document
        2. Uses LLM to parse the text into structured questions
        3. Creates or finds the role
        4. Creates the question set with all questions

        Args:
            file_content: Raw bytes of the file
            filename: Name of the file (used for extension detection)
            role_name: Name of the role (e.g., "Fullstack Developer")
            role_level: Level of the role (Junior, Mid, Senior, Lead, Principal)
            role_description: Optional description of the role
            question_set_name: Name for this question set
            question_set_version: Version identifier (e.g., "v1.0")
            question_set_description: Optional description
            is_active: Whether to set this as the active question set

        Returns:
            Created question set with questions as dictionary

        Raises:
            ValueError: If file format is not supported or role level is invalid
        """
        # Validate file extension
        allowed_extensions = ['.md', '.txt', '.docx', '.pdf']
        file_extension = '.' + filename.split('.')[-1].lower()

        if file_extension not in allowed_extensions:
            raise ValueError(
                f"Unsupported file format. Allowed: {', '.join(allowed_extensions)}"
            )

        # Validate role level
        try:
            seniority_level = SeniorityLevel(role_level)
        except ValueError:
            raise ValueError(
                f"Invalid role level. Must be one of: {', '.join([e.value for e in SeniorityLevel])}"
            )

        # Step 1: Extract text from document
        document_text = DocumentExtractor.extract_text(file_content, filename)

        # Step 2: Parse text into structured questions using LLM
        parser = PredefinedQuestionParser()
        parsed_data = parser.parse_document(document_text, role_name, role_level)

        # Step 3: Find or create the role
        role = self.db.exec(
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
            self.db.add(role)
            self.db.commit()
            self.db.refresh(role)

        # Step 4: Create the question set
        question_set = PredefinedQuestionSet(
            role_id=role.id,
            name=question_set_name,
            version=question_set_version,
            description=question_set_description,
            is_active=is_active
        )
        self.db.add(question_set)
        self.db.commit()
        self.db.refresh(question_set)

        # Step 5: If this should be active, deactivate others
        if is_active:
            other_sets = self.db.exec(
                select(PredefinedQuestionSet).where(
                    PredefinedQuestionSet.role_id == role.id,
                    PredefinedQuestionSet.id != question_set.id
                )
            ).all()

            for other_set in other_sets:
                other_set.is_active = False
                self.db.add(other_set)

            self.db.commit()

        # Step 6: Create all questions
        created_questions = []
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
            self.db.add(question)
            created_questions.append(question)

        self.db.commit()
        self.db.refresh(question_set)

        # Return question set with questions
        result = self._question_set_to_dict(question_set)
        result["questions"] = [self._question_to_dict(q) for q in created_questions]
        return result
