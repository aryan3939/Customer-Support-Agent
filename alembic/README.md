# `alembic/` — Database Migrations

Alembic is a database migration tool for SQLAlchemy. It tracks changes to
your database schema over time, letting you apply and roll back changes
safely.

## Why Use Migrations?

Without migrations, changing the database schema (adding a column, creating a table)
requires manual SQL or dropping/recreating tables (losing all data). Migrations
provide a **versioned, repeatable** way to evolve the schema:

```
Version 1: Initial tables (customers, tickets, messages)
    ↓
Version 2: Add 'resolved_by' column to tickets table
    ↓
Version 3: Add 'embedding' column to knowledge_base_articles
```

Each migration can be applied (upgrade) or reversed (downgrade).

## Folder Structure

| File/Folder | Purpose |
|-------------|---------|
| `env.py` | **Alembic configuration** — sets up the database connection (reads `DATABASE_URL` from `.env`), configures the migration engine, and defines how migrations run. Uses async SQLAlchemy for compatibility with our async app. |
| `script.py.mako` | **Template** for new migration files. Mako is a Python templating engine. When you run `alembic revision`, it uses this template to create the migration file. |
| `versions/` | **Migration scripts** — each file in here is one migration. Files are ordered by timestamp and linked together (each knows its parent revision). |

## Key Commands

```bash
# Create a new migration (auto-generates based on model changes)
alembic revision --autogenerate -m "add_resolved_by_column"

# Apply all pending migrations
alembic upgrade head

# Roll back the last migration
alembic downgrade -1

# Show migration history
alembic history

# Show current database migration version
alembic current
```

## How `env.py` Works

The env.py file is Alembic's brain — it:
1. Reads `DATABASE_URL` from environment variables (via `config.py`)
2. Replaces the sync driver with async driver (`postgresql+asyncpg://`)
3. Imports all SQLAlchemy models (so Alembic knows the target schema)
4. Compares current DB schema vs. model definitions → generates migration steps

## Auto-Generate vs. Manual Migrations

**Auto-generate** (recommended for most changes):
```bash
alembic revision --autogenerate -m "description"
```
Alembic compares your SQLAlchemy models to the actual database and generates
the migration automatically. Works for: adding columns, creating tables,
changing types.

**Manual** (for complex operations):
```bash
alembic revision -m "description"
```
Creates an empty migration file. You write the upgrade/downgrade SQL yourself.
Needed for: data migrations, complex constraints, custom SQL.

> **Note:** In this project, most schema changes are also applied automatically
> by `init_db()` on startup. Alembic migrations are kept as a formal record
> and for production deployments where you can't just recreate tables.
