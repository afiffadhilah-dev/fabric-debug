from pydantic import validate_call
from .models import StoreRequest, QueryRequest
from .services.rag_service import RagService
from .models import StoreResult, RetrieveResult


class RAGAgent:
    """Retrieval-Augmented Generation Agent. It can retrieve and store candidate data."""

    def __init__(self):
        self.rag_service = RagService()

    @validate_call
    def store(self, req: StoreRequest):
        try:
            chunks = self.rag_service.store(req)
            return StoreResult(success=True, stored_chunks=len(chunks))
        except Exception as e:
            return StoreResult(success=False, message=f"Error during storing data: {e}")

    @validate_call
    def retrieve(self, req: QueryRequest):
        try:
            results = self.rag_service.retrieve(req)
            return RetrieveResult(success=True, results=results)
        except Exception as e:
            return RetrieveResult(success=False, message=f"Error during retrieving data: {e}")
