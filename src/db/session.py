"""
Database session management for async PostgreSQL connections.

WHY THIS FILE EXISTS:
---------------------
Every database operation needs a "session" — a connection to the database
that tracks your changes and commits them atomically.

This file provides:
    ✅ Connection POOLING — reuse connections instead of creating new ones
    ✅ Async sessions — non-blocking database operations
    ✅ Automatic cleanup — sessions are closed even if errors occur
    ✅ FastAPI integration — dependency injection for request-scoped sessions
    ✅ PgBouncer compatibility — works with Supabase's connection pooler

HOW IT WORKS:
-------------
    1. Engine = the connection POOL (manages multiple connections)
    2. SessionMaker = a factory that creates session objects
    3. get_db_session = FastAPI dependency that:
       - Gets a session from the pool
       - Hands it to your route function
       - Commits if successful, rolls back if error
       - Returns the session to the pool
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.config import settings

# =============================================================================
# Create the async engine (connection pool)
# =============================================================================

engine = create_async_engine(
    settings.DATABASE_URL,
    
    # --- Connection Pool Settings ---
    pool_size=5,           # Keep 5 connections always open
    max_overflow=10,       # Allow up to 10 extra connections during spikes
    pool_timeout=30,       # Wait max 30s for a connection before erroring
    pool_recycle=1800,     # Recycle connections after 30 min (prevents stale)
    pool_pre_ping=True,    # Test connection before using (handles disconnects)
    
    # --- PgBouncer Compatibility (Supabase) ---
    # Supabase uses PgBouncer/Supavisor (port 6543) in transaction mode,
    # which doesn't support prepared statements. Disable asyncpg's
    # statement cache to avoid "prepared statement does not exist" errors.
    connect_args={
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
    },
    
    # --- Logging ---
    echo=False,  # Set True to log all SQL queries (very verbose)
)


# =============================================================================
# Create the session factory
# =============================================================================

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# =============================================================================
# FastAPI Dependency — provides a session per request
# =============================================================================

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides a database session.
    
    Usage in routes:
        @app.get("/tickets")
        async def list_tickets(db: AsyncSession = Depends(get_db_session)):
            result = await db.execute(select(Ticket))
            return result.scalars().all()
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# =============================================================================
# Startup / Shutdown
# =============================================================================

async def init_db() -> None:
    """
    Initialize the database: test connection and create tables if needed.
    Called during application startup (in main.py lifespan).
    """
    from sqlalchemy import text
    from src.db.models import Base
    from src.utils.logging import get_logger
    logger = get_logger(__name__)
    
    try:
        # 1. Test connectivity
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("database_connected", url=settings.DATABASE_URL[:40] + "...")
        
        # 2. Create all tables that don't exist yet
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("database_tables_ready", message="All tables created/verified ✓")
        
    except Exception as e:
        logger.error("database_connection_failed", error=str(e))
        raise


async def close_db() -> None:
    """Close all database connections. Called during shutdown."""
    await engine.dispose()
