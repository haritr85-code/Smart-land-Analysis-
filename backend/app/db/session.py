"""
db/session.py
-------------
Sets up the async SQLAlchemy engine and session factory used
throughout the application, plus the FastAPI dependency
`get_db` that yields a request-scoped AsyncSession.

Configured for high reliability across local PostgreSQL,
Render deployments, and Supabase (specifically port 6543
PgBouncer / Supavisor transaction pooler).
"""

import ssl
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool, QueuePool

from app.core.config import settings


def _build_engine() -> AsyncEngine:
    db_url = settings.DATABASE_URL
    is_remote = not any(loc in db_url for loc in ["localhost", "127.0.0.1", "host.docker.internal"])
    is_supabase_pooler = ":6543" in db_url or "pooler.supabase.com" in db_url

    # Prepared statements MUST be disabled for PgBouncer / Supabase port 6543 transaction pooling
    connect_args: dict = {
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
    }

    # Only attach explicit SSL context if required by connection string or Supabase pooler
    if "sslmode=require" in settings.DATABASE_URL_RAW.lower() or "ssl=true" in settings.DATABASE_URL_RAW.lower() or "supabase.com" in db_url or "pooler.supabase.com" in db_url:
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE
        connect_args["ssl"] = ssl_ctx

    engine_kwargs: dict = {
        "echo": settings.DEBUG,
        "future": True,
        "connect_args": connect_args,
    }

    # For transaction poolers (port 6543), use NullPool to avoid double connection pooling.
    # For local/direct connections, use pre-ping and connection recycling.
    if is_supabase_pooler:
        engine_kwargs["poolclass"] = NullPool
    else:
        engine_kwargs["pool_pre_ping"] = True
        engine_kwargs["pool_recycle"] = 300

    return create_async_engine(db_url, **engine_kwargs)


engine: AsyncEngine = _build_engine()

# Provide both SessionLocal and AsyncSessionLocal aliases
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)
SessionLocal = AsyncSessionLocal


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields a database session for the
    lifetime of a single request, and guarantees it is closed
    (and rolled back on error) afterwards.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
