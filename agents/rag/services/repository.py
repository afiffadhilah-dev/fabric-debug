from config import settings
from sqlmodel import Session, create_engine, select
from models import Candidate, CandidateChunk
from ..models import StoreRequest
import uuid


class RepositoryService:
    def __init__(self):
        if not settings.DATABASE_URL:
            raise ValueError("DATABASE_URL is required to save embeddings")
        self.engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)

    def save_embeddings(self, req: StoreRequest, chunks: list[str], embeddings: list[list[float]]):
        if len(chunks) != len(embeddings):
            raise ValueError("Chunks and embeddings length must match")

        with Session(self.engine) as session:
            new_uuid = uuid.uuid4()
            candidate = Candidate(id=str(new_uuid), name=req.name)
            session.add(candidate)
            session.flush()  # Ensure candidate.id is available

            for idx, (content, embedding) in enumerate(zip(chunks, embeddings)):
                chunk = CandidateChunk(
                    candidate_id=candidate.id,
                    chunk_index=idx,
                    content=content,
                    embedding=embedding,
                )
                session.add(chunk)

            session.commit()

    def search(self, query_vec: list[float], top_k: int):
        with Session(self.engine) as session:
            # Use pgvector's cosine distance operator (<=>)
            # Cast the parameter to vector type explicitly
            from sqlalchemy import text

            query = text("""
                SELECT 
                    cc.id,
                    cc.candidate_id,
                    cc.chunk_index,
                    cc.content,
                    cc.embedding,
                    c.name,
                    (1 - (cc.embedding <=> CAST(:query_embedding AS vector))) as similarity
                FROM candidatechunk cc
                JOIN candidate c ON cc.candidate_id = c.id
                ORDER BY cc.embedding <=> CAST(:query_embedding AS vector)
                LIMIT :top_k
            """)

            result = session.execute(
                query,
                {"query_embedding": str(query_vec), "top_k": top_k}
            )

            # Group results by candidate_id
            results = []
            candidate_chunks = {}
            for row in result:
                if row.candidate_id not in candidate_chunks:
                    candidate_chunks[row.candidate_id] = self.get_chunks_by_candidate(row.candidate_id)
                    
                results.append({
                    "id": row.id,
                    "name": row.name,
                    "candidate_id": row.candidate_id,
                    "chunk_index": row.chunk_index,
                    "chunk_match": row.content,
                    "embedding": row.embedding,
                    "similarity": row.similarity,
                    "chunks": candidate_chunks[row.candidate_id]
                    })

            return results

    def get_chunks_by_candidate(self, candidate_id: str):
        with Session(self.engine) as session:
            statement = select(CandidateChunk).where(CandidateChunk.candidate_id == candidate_id)
            result = session.exec(statement).all()

            result_text = ""
            for row in result:
                result_text += f"{row.content}\n"

            return result_text
