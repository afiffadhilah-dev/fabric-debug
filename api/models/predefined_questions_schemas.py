from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from models.predefined_role import SeniorityLevel


# ============ Role Schemas ============

class PredefinedRoleCreate(BaseModel):
    """Schema for creating a new role"""
    name: str = Field(..., min_length=1, max_length=100, description="Role name")
    level: SeniorityLevel = Field(..., description="Seniority level: Junior, Mid, Senior, Lead, Principal")
    description: Optional[str] = Field(None, description="Role description")
    is_active: bool = Field(True, description="Whether the role is active")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Backend Developer",
                "level": "Senior",
                "description": "Server-side development with APIs and databases",
                "is_active": True
            }
        }


class PredefinedRoleUpdate(BaseModel):
    """Schema for updating a role"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Role name")
    level: Optional[SeniorityLevel] = Field(None, description="Seniority level")
    description: Optional[str] = Field(None, description="Role description")
    is_active: Optional[bool] = Field(None, description="Whether the role is active")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Senior Backend Developer",
                "description": "Updated description for the role"
            }
        }


class PredefinedRoleResponse(BaseModel):
    """Schema for role response"""
    id: UUID
    name: str
    level: SeniorityLevel
    description: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "Backend Developer",
                "level": "Senior",
                "description": "Server-side development with APIs and databases",
                "is_active": True,
                "created_at": "2024-01-15T10:00:00Z",
                "updated_at": "2024-01-15T10:00:00Z"
            }
        }


# ============ Question Set Schemas ============

class PredefinedQuestionSetCreate(BaseModel):
    """Schema for creating a new question set"""
    role_id: UUID = Field(..., description="UUID of the role this question set belongs to")
    name: str = Field(..., min_length=1, max_length=200, description="Question set name")
    version: str = Field(..., min_length=1, max_length=50, description="Version identifier")
    description: Optional[str] = Field(None, description="Question set description")
    is_active: bool = Field(False, description="Whether the question set is active (only one active per role)")

    class Config:
        json_schema_extra = {
            "example": {
                "role_id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "Backend Technical Screen",
                "version": "v1.0",
                "description": "Standard technical interview questions for backend developers",
                "is_active": True
            }
        }


class PredefinedQuestionSetUpdate(BaseModel):
    """Schema for updating a question set"""
    name: Optional[str] = Field(None, min_length=1, max_length=200, description="Question set name")
    version: Optional[str] = Field(None, min_length=1, max_length=50, description="Version identifier")
    description: Optional[str] = Field(None, description="Question set description")
    is_active: Optional[bool] = Field(None, description="Whether the question set is active")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Backend Technical Screen v2",
                "version": "v2.0"
            }
        }


class PredefinedQuestionSetResponse(BaseModel):
    """Schema for question set response"""
    id: UUID
    role_id: UUID
    name: str
    version: str
    description: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "661e8400-e29b-41d4-a716-446655440001",
                "role_id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "Backend Technical Screen",
                "version": "v1.0",
                "description": "Standard technical interview questions",
                "is_active": True,
                "created_at": "2024-01-15T10:00:00Z",
                "updated_at": "2024-01-15T10:00:00Z"
            }
        }


# ============ Question Schemas ============

class PredefinedQuestionCreate(BaseModel):
    """Schema for creating a new question"""
    question_set_id: UUID = Field(..., description="UUID of the question set this question belongs to")
    category: str = Field(..., min_length=1, max_length=100, description="Question category (e.g., System Design, Databases)")
    question_text: str = Field(..., min_length=1, description="The interview question text")
    what_assesses: List[str] = Field(..., min_items=1, description="Skills/competencies this question evaluates")
    expected_answer_pattern: Optional[str] = Field(None, description="Expected answer pattern or key points")
    order: int = Field(default=0, ge=0, description="Question order (lower = asked first)")
    is_required: bool = Field(True, description="Whether this question must be asked")

    class Config:
        json_schema_extra = {
            "example": {
                "question_set_id": "661e8400-e29b-41d4-a716-446655440001",
                "category": "System Design",
                "question_text": "How would you design a rate limiter?",
                "what_assesses": ["system design", "scalability", "distributed systems"],
                "expected_answer_pattern": "Should mention token bucket or sliding window algorithms",
                "order": 1,
                "is_required": True
            }
        }


class PredefinedQuestionUpdate(BaseModel):
    """Schema for updating a question"""
    category: Optional[str] = Field(None, min_length=1, max_length=100, description="Question category")
    question_text: Optional[str] = Field(None, min_length=1, description="The interview question text")
    what_assesses: Optional[List[str]] = Field(None, min_items=1, description="Skills this question evaluates")
    expected_answer_pattern: Optional[str] = Field(None, description="Expected answer pattern")
    order: Optional[int] = Field(None, ge=0, description="Question order")
    is_required: Optional[bool] = Field(None, description="Whether this question is required")

    class Config:
        json_schema_extra = {
            "example": {
                "question_text": "How would you design a distributed rate limiter?",
                "order": 2
            }
        }


class PredefinedQuestionResponse(BaseModel):
    """Schema for question response"""
    id: UUID
    question_set_id: UUID
    category: str
    question_text: str
    what_assesses: List[str]
    expected_answer_pattern: Optional[str]
    order: int
    is_required: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "772e8400-e29b-41d4-a716-446655440002",
                "question_set_id": "661e8400-e29b-41d4-a716-446655440001",
                "category": "System Design",
                "question_text": "How would you design a rate limiter?",
                "what_assesses": ["system design", "scalability", "distributed systems"],
                "expected_answer_pattern": "Should mention token bucket or sliding window algorithms",
                "order": 1,
                "is_required": True,
                "created_at": "2024-01-15T10:00:00Z",
                "updated_at": "2024-01-15T10:00:00Z"
            }
        }


# ============ Composite Schemas ============

class PredefinedQuestionSetWithQuestions(PredefinedQuestionSetResponse):
    """Question set with nested questions"""
    questions: List[PredefinedQuestionResponse] = []

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "661e8400-e29b-41d4-a716-446655440001",
                "role_id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "Backend Technical Screen",
                "version": "v1.0",
                "description": "Standard technical interview questions",
                "is_active": True,
                "created_at": "2024-01-15T10:00:00Z",
                "updated_at": "2024-01-15T10:00:00Z",
                "questions": [
                    {
                        "id": "772e8400-e29b-41d4-a716-446655440002",
                        "question_set_id": "661e8400-e29b-41d4-a716-446655440001",
                        "category": "System Design",
                        "question_text": "How would you design a rate limiter?",
                        "what_assesses": ["system design", "scalability"],
                        "expected_answer_pattern": None,
                        "order": 1,
                        "is_required": True,
                        "created_at": "2024-01-15T10:00:00Z",
                        "updated_at": "2024-01-15T10:00:00Z"
                    }
                ]
            }
        }


class PredefinedRoleWithQuestionSets(PredefinedRoleResponse):
    """Role with nested question sets"""
    question_sets: List[PredefinedQuestionSetResponse] = []

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "Backend Developer",
                "level": "Senior",
                "description": "Server-side development with APIs and databases",
                "is_active": True,
                "created_at": "2024-01-15T10:00:00Z",
                "updated_at": "2024-01-15T10:00:00Z",
                "question_sets": [
                    {
                        "id": "661e8400-e29b-41d4-a716-446655440001",
                        "role_id": "550e8400-e29b-41d4-a716-446655440000",
                        "name": "Backend Technical Screen",
                        "version": "v1.0",
                        "description": "Standard technical interview questions",
                        "is_active": True,
                        "created_at": "2024-01-15T10:00:00Z",
                        "updated_at": "2024-01-15T10:00:00Z"
                    }
                ]
            }
        }


# ============ Bulk Creation Schema ============

class BulkQuestionSetCreate(BaseModel):
    """Schema for creating a question set with all questions in one request"""
    role_id: UUID = Field(..., description="UUID of the role this question set belongs to")
    name: str = Field(..., min_length=1, max_length=200, description="Question set name")
    version: str = Field(..., min_length=1, max_length=50, description="Version identifier")
    description: Optional[str] = Field(None, description="Question set description")
    is_active: bool = Field(False, description="Whether the question set is active")
    questions: List[PredefinedQuestionCreate] = Field(..., description="List of questions to create")

    class Config:
        json_schema_extra = {
            "example": {
                "role_id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "Backend Technical Screen",
                "version": "v1.0",
                "description": "Standard technical interview questions for backend developers",
                "is_active": True,
                "questions": [
                    {
                        "question_set_id": "661e8400-e29b-41d4-a716-446655440001",
                        "category": "System Design",
                        "question_text": "How would you design a rate limiter?",
                        "what_assesses": ["system design", "scalability"],
                        "order": 1,
                        "is_required": True
                    },
                    {
                        "question_set_id": "661e8400-e29b-41d4-a716-446655440001",
                        "category": "Databases",
                        "question_text": "Explain the difference between SQL and NoSQL databases.",
                        "what_assesses": ["database knowledge", "technical depth"],
                        "order": 2,
                        "is_required": True
                    }
                ]
            }
        }
