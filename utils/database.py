"""
Database utilities and engine management.

This module provides the core database engine that can be used by any layer:
- API routes
- Services
- Agents
- Repositories
- Scripts

No dependencies on higher-level modules (api, services, agents).
"""

from functools import lru_cache
from typing import Generator

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlmodel import create_engine, Session, text

from config.settings import settings


@lru_cache()
def get_engine() -> Engine:
    """
    Get cached database engine.

    Returns:
        SQLAlchemy engine singleton

    Note:
        Uses psycopg (v3) driver for compatibility with PgBouncer/connection poolers.
        prepare_threshold=0 disables client-side prepared statements.
    """
    # Convert postgresql:// to postgresql+psycopg:// for psycopg3 driver
    db_url = settings.DATABASE_URL
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)

    engine = create_engine(
        db_url,
        connect_args={
            "prepare_threshold": None,  # Disable prepared statements for pooler compatibility
            "connect_timeout": 10,      # Fail fast if Supabase pooler is slow
        },
        pool_pre_ping=True,  # Verify connection before use
        pool_recycle=300,
        pool_size=3,         # Supabase free tier: keep low (checkpointer uses MemorySaver)
        max_overflow=2,      # Max 5 connections total (within Supabase free tier limit of 15)
        pool_timeout=30,     # Wait up to 30s for a connection from pool
    )

    # Set statement_timeout after connection is established (compatible with Supavisor)
    @event.listens_for(engine, "connect")
    def set_statement_timeout(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("SET statement_timeout = '15000'")
        cursor.close()

    return engine


def get_db() -> Generator[Session, None, None]:
    """
    Database session dependency for FastAPI.
    
    Yields:
        SQLModel Session that auto-closes after request
    
    Usage:
        @router.get("/example")
        def example(db: Session = Depends(get_db)):
            ...
    """
    engine = get_engine()
    with Session(engine) as session:
        yield session
