"""
Checkpointer for LangGraph state persistence.

Supports two modes (configured via CHECKPOINTER_TYPE env var):
- "memory": In-memory state, zero DB connections (default, recommended for Supabase free tier)
- "postgres": PostgreSQL-based persistent state (requires more DB connections)

See docs/supabase-502-investigation.md for why memory mode is the default.
"""

import atexit
from config.settings import settings
from langgraph.checkpoint.memory import MemorySaver


# Global singleton instances
_checkpointer_instance = None
_async_checkpointer_instance = None
_connection_pool = None


def get_checkpointer():
    """
    Get or create the singleton checkpointer instance.

    Uses CHECKPOINTER_TYPE from settings:
    - "memory": MemorySaver (no DB connections, state lost on restart)
    - "postgres": PostgresSaver (persistent, uses DB connection pool)

    Returns:
        Checkpointer singleton instance
    """
    global _checkpointer_instance

    if _checkpointer_instance is None:
        if settings.CHECKPOINTER_TYPE == "postgres":
            _checkpointer_instance = _create_postgres_checkpointer()
        else:
            print("[Checkpointer] Using MemorySaver (no DB connections)")
            _checkpointer_instance = MemorySaver()

    return _checkpointer_instance


async def get_async_checkpointer():
    """
    Get or create the singleton async checkpointer instance.

    For MemorySaver, returns the same instance (it supports both sync and async).
    For PostgresSaver, creates an async-specific instance with AsyncConnectionPool.

    Returns:
        Checkpointer singleton instance
    """
    global _async_checkpointer_instance

    if _async_checkpointer_instance is None:
        if settings.CHECKPOINTER_TYPE == "postgres":
            _async_checkpointer_instance = await _create_async_postgres_checkpointer()
        else:
            # MemorySaver works for both sync and async
            _async_checkpointer_instance = get_checkpointer()

    return _async_checkpointer_instance


# ============ POSTGRES CHECKPOINTER (when CHECKPOINTER_TYPE=postgres) ============

def _create_postgres_checkpointer():
    """Create PostgreSQL-based checkpointer for LangGraph."""
    import psycopg
    from psycopg.rows import dict_row
    from psycopg_pool import ConnectionPool
    from langgraph.checkpoint.postgres import PostgresSaver

    connection_string = settings.DATABASE_URL
    print("[Checkpointer] Using PostgresSaver (persistent state)")

    # First, run setup with autocommit=True to create tables
    with psycopg.connect(
        connection_string,
        autocommit=True,
        row_factory=dict_row,
        prepare_threshold=None,
        connect_timeout=10,
    ) as setup_conn:
        setup_checkpointer = PostgresSaver(conn=setup_conn)
        setup_checkpointer.setup()

    global _connection_pool

    _connection_pool = ConnectionPool(
        conninfo=connection_string,
        min_size=1,
        max_size=3,
        max_lifetime=300,
        max_idle=60,
        timeout=10,
        kwargs={
            "autocommit": True,
            "row_factory": dict_row,
            "prepare_threshold": None,
            "connect_timeout": 10,
        }
    )

    atexit.register(_close_sync_pool)
    return PostgresSaver(conn=_connection_pool)


def _close_sync_pool():
    """Close the sync connection pool gracefully at exit."""
    global _connection_pool
    if _connection_pool is not None:
        try:
            _connection_pool.close()
        except Exception:
            pass
        _connection_pool = None


async def _create_async_postgres_checkpointer():
    """Create async PostgreSQL-based checkpointer for LangGraph streaming."""
    from psycopg.rows import dict_row
    from psycopg_pool import AsyncConnectionPool
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

    connection_string = settings.DATABASE_URL

    async_pool = AsyncConnectionPool(
        conninfo=connection_string,
        min_size=1,
        max_size=3,
        timeout=10,
        kwargs={
            "autocommit": True,
            "row_factory": dict_row,
            "prepare_threshold": None,
            "connect_timeout": 10,
        },
        open=False
    )

    await async_pool.open()
    checkpointer = AsyncPostgresSaver(conn=async_pool)
    await checkpointer.setup()
    return checkpointer


# ============ BACKWARDS COMPATIBILITY ============
# Old names still work so nothing else breaks

def get_postgres_checkpointer():
    """Backwards-compatible alias for get_checkpointer()."""
    return get_checkpointer()


async def get_async_postgres_checkpointer():
    """Backwards-compatible alias for get_async_checkpointer()."""
    return await get_async_checkpointer()
