"""
Alembic environment configuration for running migrations.

WHY THIS FILE EXISTS:
---------------------
Alembic needs to know:
1. WHERE is the database? (connection URL from our .env)
2. WHAT models exist? (import our SQLAlchemy Base)
3. HOW to run migrations? (async because we use asyncpg)

This file bridges Alembic with our application's config and models.

HOW ALEMBIC WORKS:
------------------
    1. You change a model in models.py (e.g., add a column)
    2. Run: alembic revision --autogenerate -m "add column"
       → Alembic compares models.py vs current database
       → Generates a migration file with the differences
    3. Run: alembic upgrade head
       → Applies the migration to the database

    models.py (Python) → alembic revision → migration file → alembic upgrade → database
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

# ---- Import our application's models and config ----
from src.config import settings
from src.db.models import Base  # This imports ALL models (they register with Base)

# Alembic Config object (reads alembic.ini)
config = context.config

# Set the database URL from our application settings
# This overrides the placeholder in alembic.ini
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Setup logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Tell Alembic about our models' metadata
# Alembic compares this against the actual database to generate migrations
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.
    
    This generates SQL scripts WITHOUT connecting to the database.
    Useful for reviewing migrations before applying them.
    
    Usage: alembic upgrade head --sql
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    """Run migrations with a given database connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """
    Run migrations in 'online' mode with async engine.
    
    We use async because our app uses asyncpg (async PostgreSQL driver).
    Standard sync migrations would fail with our async connection string.
    """
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # Don't pool connections during migrations
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Entry point for online migrations — runs the async version."""
    asyncio.run(run_async_migrations())


# ---- Determine which mode to run ----
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
