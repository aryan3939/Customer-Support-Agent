# `alembic/` — Database Migrations

**Alembic** is SQLAlchemy's migration tool — it tracks schema changes
(add column, create table, drop index) as versioned Python scripts,
so you can upgrade/rollback the database reliably.

## Current Status

> **Not actively used yet.** Tables are auto-created at startup via
> `Base.metadata.create_all()` in `session.py`. Alembic is set up for
> when the schema stabilizes and you need versioned migrations.

## Files

| File | What It Does |
|------|-------------|
| `env.py` | Alembic's runtime config — connects to the database, imports models, runs migrations |
| `script.py.mako` | Template for auto-generated migration files |
| `versions/` | Migration scripts (currently empty) |

The root `alembic.ini` file contains the database URL and logging config.

## How to Use (When Needed)

```bash
# 1. Generate a migration after changing models.py
alembic revision --autogenerate -m "add priority column to tickets"

# 2. Review the generated file in alembic/versions/
# 3. Apply the migration
alembic upgrade head

# 4. Rollback if something goes wrong
alembic downgrade -1
```

## Why Both `create_all` and Alembic?

| | `create_all` | Alembic |
|---|---|---|
| **Purpose** | Quick development setup | Production schema management |
| **Creates tables** | ✅ | ✅ |
| **Adds columns** | ❌ (only creates, never alters) | ✅ |
| **Drops columns** | ❌ | ✅ |
| **Rollback** | ❌ | ✅ |
| **Version history** | ❌ | ✅ |

During development, `create_all` is faster. In production, Alembic ensures
safe, versioned schema changes.

## How to Explain This

> "I use `create_all` for rapid development — it auto-creates tables at
> startup. For production, Alembic provides versioned, reviewable, and
> reversible database migrations. It auto-detects differences between my
> SQLAlchemy models and the actual database schema, generates migration
> scripts, and lets me upgrade or rollback safely."
