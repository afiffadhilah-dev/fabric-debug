"""
Services module - Business Logic Layer.

Contains application services that orchestrate business logic,
sitting between the API layer (routes) and the data layer (repositories).

Services handle:
- Business rule validation
- Orchestrating multiple repository operations
- Coordinating with external services (LLM, agents)
- Transaction management

Usage:
    from services import InterviewService
    
    service = InterviewService(deps)
    result = service.start_interview(candidate_id, resume_text, mode)
"""

from services.interview_service import InterviewService
from services.summarization_service import SummarizationService

__all__ = [
    "InterviewService",
    "SummarizationService"
]
