from .chunking import ChunkingService
from .embedding import EmbeddingService
from .repository import RepositoryService
from .normalize import NormalizeService
from .scoring import ScoringService
from ..models import StoreRequest, QueryRequest


class RagService:
    def __init__(self):
        self.chunker = ChunkingService()
        self.embedder = EmbeddingService()
        self.repo = RepositoryService()
        self.normalizer = NormalizeService()
        self.scorer = ScoringService()
    
    def store(self, req: StoreRequest) -> list[str]:
        req.content = self.normalizer.normalize_text(req.content)
        chunks = self.chunker.split(req.content)
        embeddings = self.embedder.embed_chunks(chunks)
        self.repo.save_embeddings(req, chunks, embeddings)
        return chunks

    def retrieve(self, req: QueryRequest) -> list[dict]:
        req.query = self.normalizer._clean_noise(req.query)
        query_vec = self.embedder.embed_query(req.query)
        results = self.repo.search(query_vec, req.top_k)
        results = self.scorer.rerank(results)
        return results

