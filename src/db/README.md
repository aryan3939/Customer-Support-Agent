# `db/` — Database Layer (Supabase + SQLAlchemy)

This folder handles **all database interactions** — models, sessions, and
repository functions. Data is persisted to **Supabase** (managed PostgreSQL)
via **SQLAlchemy** with async support (`asyncpg` driver).

## Architecture

```
FastAPI Route
    │
    ▼  Depends(get_db_session)
AsyncSession (from session.py)
    │
    ▼  Repository functions
ticket_repo.py / customer_repo.py
    │
    ▼  SQLAlchemy ORM queries
Supabase PostgreSQL (via asyncpg)
```

## Files

| File | What It Does |
|------|-------------|
| `models.py` | SQLAlchemy ORM models — Python classes that map to database tables |
| `session.py` | Engine creation, session factory, `get_db_session()` dependency, `init_db()`/`close_db()` lifecycle |
| `repositories/` | Query functions organized by entity (tickets, customers) |
| `__init__.py` | Re-exports models and `get_db_session` for convenient imports |

## Database Tables

| Table | Model | Purpose |
|-------|-------|---------|
| `customers` | `Customer` | People who submit tickets |
| `agents` | `Agent` | AI and human support agents |
| `tickets` | `Ticket` | Core entity — the support ticket |
| `messages` | `Message` | Conversation thread within a ticket |
| `agent_actions` | `AgentAction` | Audit trail of every AI decision |
| `tags` | `Tag` | Labels for categorization |
| `ticket_tags` | (junction table) | Many-to-many: tickets ↔ tags |
| `knowledge_articles` | `KnowledgeArticle` | KB articles for RAG |
| `kb_embeddings` | `KBEmbedding` | Vector chunks for similarity search |

## PgBouncer Compatibility

Supabase uses **PgBouncer** (connection pooler) in transaction mode. This
requires special SQLAlchemy settings:
```python
connect_args={"statement_cache_size": 0, "prepared_statement_cache_size": 0}
```
Without this, `asyncpg` tries to use prepared statements, which PgBouncer
doesn't support.

## How to Explain This

> "I used the **Repository Pattern** to isolate database queries from business
> logic. Routes never write SQL directly — they call repository functions like
> `create_ticket()` or `get_ticket_by_id()`. This means if we switch databases,
> we only change the repository layer. SQLAlchemy's async engine with
> `asyncpg` gives non-blocking database access, and PgBouncer compatibility
> ensures it works with Supabase's connection pooling."
