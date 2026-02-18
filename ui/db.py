"""
Database utilities for Streamlit UI.

Provides cached database engine and session management for direct database access.
"""

from contextlib import contextmanager
import streamlit as st
from sqlmodel import Session, create_engine, SQLModel
from config.settings import settings


@st.cache_resource
def get_database_engine():
    """
    Create and cache database engine.

    Uses Streamlit's cache_resource to ensure a single engine instance
    is shared across all sessions and reruns.
    """
    engine = create_engine(settings.DATABASE_URL)
    SQLModel.metadata.create_all(engine)
    return engine


@contextmanager
def get_db_session():
    """
    Context manager for database sessions.

    Usage:
        with get_db_session() as db:
            roles = db.exec(select(PredefinedRole)).all()

    Ensures proper session cleanup after use.
    """
    engine = get_database_engine()
    with Session(engine) as session:
        yield session
