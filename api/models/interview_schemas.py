from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any, Union
from uuid import UUID
from datetime import datetime
from enum import Enum

from utils.language_config import SUPPORTED_LANGUAGES


class InterviewMode(str, Enum):
    """Interview mode options"""
    DYNAMIC_GAP = "dynamic_gap"
    PREDEFINED_QUESTIONS = "predefined_questions"


class SSEEventType(str, Enum):
    """Server-Sent Events types for streaming endpoints"""
    SESSION = "session"       # Initial session info
    STATUS = "status"         # Human-readable status message during processing
    NODE = "node"             # Node completion event
    TOKEN = "token"           # LLM token during question generation
    PROGRESS = "progress"     # Custom progress from parse_answer
    COMPLETE = "complete"     # Stream completed
    ERROR = "error"           # Error occurred


# ============ SSE Event Data Schemas ============

class SSESessionData(BaseModel):
    """Data for session event"""
    session_id: UUID


class SSEStatusData(BaseModel):
    """Data for status event - human-readable processing status"""
    message: str
    node: str


class SSENodeData(BaseModel):
    """Data for node completion event"""
    node: str
    status: str = "complete"


class SSETokenData(BaseModel):
    """Data for token streaming event"""
    content: str
    node: Optional[str] = None


class SSEProgressData(BaseModel):
    """Data for progress event from parse_answer"""
    stage: str
    detail: Optional[str] = None


class SSECompleteData(BaseModel):
    """Data for stream completion event"""
    session_id: Optional[UUID] = None
    question: Optional[str] = None
    completed: bool = False
    termination_reason: Optional[str] = None
    completion_message: Optional[str] = None
    completeness_score: float = Field(default=0.0, description="Interview completeness percentage (0-100)")


class SSEErrorData(BaseModel):
    """Data for error event"""
    detail: str


class SSEEvent(BaseModel):
    """Generic SSE event wrapper"""
    event: SSEEventType
    data: Union[SSESessionData, SSENodeData, SSETokenData, SSEProgressData, SSECompleteData, SSEErrorData]


# ============ Request Schemas ============

class StartInterviewRequest(BaseModel):
    """Schema for starting a new interview"""
    candidate_id: str = Field(..., min_length=1,
                              description="Unique identifier for the candidate")
    user: Optional[str] = Field(
        default=None,
        min_length=1,
        description="User name to store on the candidate record"
    )
    resume_text: Optional[str] = Field(default=None,
                             description="Resume text to analyze")
    mode: Optional[InterviewMode] = Field(
        default=InterviewMode.DYNAMIC_GAP, description="Interview mode: dynamic_gap (extract skills from resume) or predefined_questions (use question set)")
    question_set_id: Optional[UUID] = Field(
        default=None, description="UUID of predefined question set (required if mode=predefined_questions)")
    language: Optional[str] = Field(
        default=None, min_length=2, max_length=5,
        description="ISO 639-1 language code (e.g., 'en', 'id'). Defaults to English.")

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.lower()
        if v not in SUPPORTED_LANGUAGES:
            supported = ", ".join(sorted(SUPPORTED_LANGUAGES.keys()))
            raise ValueError(
                f"Unsupported language code '{v}'. "
                f"Supported codes: {supported}"
            )
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "candidate_id": "2eb2aa03-ec75-426f-8db9-8c25901eea2c",
                "user": "John Doe",
                "resume_text": "John Doe\nSenior Software Engineer\n\nEXPERIENCE:\n- Led development of e-commerce platform using Python...",
                "mode": "predefined_questions",
                "question_set_id": "0800bfe1-8d88-4bda-8f42-c70b1f748a42",
                "language": "en"
            }
        }


class ChatRequest(BaseModel):
    """Schema for continuing an interview with candidate answer"""
    answer: str = Field(..., min_length=1,
                        description="Candidate's answer to the previous question")

    class Config:
        json_schema_extra = {
            "example": {
                "answer": "I have worked with Python for 5 years, primarily building REST APIs with FastAPI and Flask..."
            }
        }


# ============ Response Schemas ============

class StartInterviewResponse(BaseModel):
    """Schema for start interview response"""
    session_id: UUID = Field(..., description="Database interview session ID")
    question: str = Field(..., description="First interview question")
    mode: InterviewMode = Field(..., description="Interview mode being used")
    completeness_score: float = Field(default=0.0, description="Interview completeness percentage (0-100)")

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "12345678-1234-1234-1234-123456789abc",
                "question": "How long have you worked with Python in production environments?",
                "mode": "predefined_questions",
                "completeness_score": 0.0
            }
        }


class ContinueInterviewResponse(BaseModel):
    """Schema for continue interview response"""
    question: Optional[str] = Field(
        None, description="Next interview question (None if interview completed)")
    completed: bool = Field(..., description="Whether interview is complete")
    termination_reason: Optional[str] = Field(
        None, description="Reason interview ended (if completed)")
    completion_message: Optional[str] = Field(
        None, description="Completion message from interviewer (if completed)")
    warning: Optional[str] = Field(
        None, description="Warning message (if any)")
    feedback: Optional[str] = Field(
        None, description="Feedback message for the candidate about their last answer")
    summarization_task_id: Optional[str] = Field(
        None, description="Background task ID for summarization (poll GET /summarization/task-status/{task_id})")
    completeness_score: float = Field(default=0.0, description="Interview completeness percentage (0-100)")

    class Config:
        json_schema_extra = {
            "example": {
                "question": "Can you describe your level of ownership when working with Docker?",
                "completed": False,
                "termination_reason": None,
                "completion_message": None,
                "warning": None,
                "feedback": None,
                "completeness_score": 45.5
            }
        }


class InterviewSessionResponse(BaseModel):
    """Schema for interview session response"""
    id: UUID
    status: str
    mode: str
    completeness_score: float = Field(description="Interview completeness percentage (0-100)")
    created_at: datetime
    completed_at: Optional[datetime]

    @field_validator("completeness_score", mode="before")
    @classmethod
    def convert_to_percentage(cls, v: float) -> float:
        """Convert 0.0-1.0 float from DB to percentage."""
        if v is not None and v <= 1.0:
            return round(v * 100, 2)
        return v

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "12345678-1234-1234-1234-123456789abc",
                "status": "completed",
                "mode": "predefined_questions",
                "completeness_score": 75.0,
                "created_at": "2024-01-15T10:30:00Z",
                "completed_at": "2024-01-15T10:45:00Z"
            }
        }


class DetailInterviewSessionResponse(BaseModel):
    """Schema for detail interview session response"""
    id: UUID
    candidate_id: str
    resume_text: Optional[str]
    status: str
    mode: str
    question_set_id: Optional[UUID]
    questions_asked: int
    questions_answered: Optional[int] = Field(None, description="Number of questions actually answered (excludes skipped)")
    questions_skipped: Optional[int] = Field(None, description="Number of questions skipped by user")
    skipped_categories: Optional[List[str]] = Field(None, description="Categories of skipped questions")
    completeness_score: float = Field(description="Interview completeness percentage (0-100)")
    termination_reason: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]

    @field_validator("completeness_score", mode="before")
    @classmethod
    def convert_to_percentage(cls, v: float) -> float:
        """Convert 0.0-1.0 float from DB to percentage."""
        if v is not None and v <= 1.0:
            return round(v * 100, 2)
        return v

    @field_validator('skipped_categories', mode='before')
    @classmethod
    def parse_skipped_categories(cls, v):
        """Parse skipped_categories from JSON string if needed."""
        if v is None:
            return None
        if isinstance(v, str):
            import json
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return []
        return v

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "12345678-1234-1234-1234-123456789abc",
                "candidate_id": "2eb2aa03-ec75-426f-8db9-8c25901eea2c",
                "resume_text": "John Doe\nSenior Software Engineer...",
                "status": "completed",
                "mode": "predefined_questions",
                "question_set_id": "03b84681-2c75-4bbd-89ee-307861ec7b6b",
                "questions_asked": 8,
                "questions_answered": 6,
                "questions_skipped": 2,
                "skipped_categories": ["LEADERSHIP EXPERIENCE", "BUDGET_MANAGEMENT"],
                "completeness_score": 75.0,
                "termination_reason": "complete",
                "created_at": "2024-01-15T10:30:00Z",
                "completed_at": "2024-01-15T10:45:00Z"
            }
        }

class InterviewSessionMessageResponse(BaseModel):
    """Schema for interview session messages response"""
    id: UUID
    messages: List[Dict[str, Any]]  # Each message can have various fields

    class Config:
        json_schema_extra = {
            "example": {
                "id": "12345678-1234-1234-1234-123456789abc",
                "messages": [
                    {
                        "role": "interviewer",
                        "content": "Can you describe your experience with REST APIs?",
                    },
                    {
                        "role": "candidate",
                        "content": "I have built several REST APIs using FastAPI and Flask...",
                    }
                ]
            }
        }


# ============ Error Response Schema ============

class ErrorResponse(BaseModel):
    """Schema for error responses"""
    detail: str = Field(..., description="Error message")

    class Config:
        json_schema_extra = {
            "example": {
                "detail": "Question set 03b84681-2c75-4bbd-89ee-307861ec7b6b not found"
            }
        }
