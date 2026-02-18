from datetime import datetime
from uuid import UUID
import uuid

from sqlmodel import SQLModel, Field
from sqlalchemy import Column
from pgvector.sqlalchemy import Vector


class CandidateChunk(SQLModel, table=True):
    """Candidate chunk model for storing chunked content with embeddings."""
    id: UUID = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)

    candidate_id: str = Field(foreign_key="candidate.id")
    chunk_index: int

    content: str
    embedding: list = Field(sa_column=Column(Vector(1536))) # OpenAI embedding dimension
    # embedding: list = Field(sa_column=Column(Vector(1024))) # Alternative dimension like Multilingual E5

    created_at: datetime = Field(default_factory=datetime.utcnow)
