"""
Database utilities.

Provides shared database engine and connection utilities.
"""

from functools import lru_cache
from sqlalchemy.engine import Engine
from sqlmodel import create_engine

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
    
    return create_engine(
        db_url,
        connect_args={
            "prepare_threshold": None,  # Disable prepared statements for pooler compatibility
            "connect_timeout": 10,      # Fail fast if Supabase pooler is slow
        },
        pool_pre_ping=True,  # Verify connection before use
        pool_recycle=300,
        pool_size=3,         # Supabase free tier: keep low
        max_overflow=2,      # Max 5 connections total
        pool_timeout=30,
    )
