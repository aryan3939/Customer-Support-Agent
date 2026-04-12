# `src/db/` — Database Layer

This folder handles everything related to data persistence — ORM models,
database connections, and repository functions for CRUD operations.

## Architecture

```
Route Handler → calls → Repository Function → uses → SQLAlchemy ORM → talks to → Supabase PostgreSQL
                              │
                         AsyncSession
                         (from pool)
```

**Key principle:** Routes never write SQL directly. They call repository functions,
which use the SQLAlchemy ORM to construct and execute queries.

## Files

### `models.py` — SQLAlchemy ORM Models (20KB, largest DB file)

Defines all database tables as Python classes using SQLAlchemy's declarative mapping.
Every table in the database has a corresponding class here.

| Model | Table | Purpose | Key Columns |
|-------|-------|---------|-------------|
| `Customer` | `customers` | People who submit tickets | `id`, `email`, `name`, `metadata_`, `created_at` |
| `Ticket` | `tickets` | Support tickets | `id`, `customer_id` (FK), `assigned_agent_id` (FK), `subject`, `status`, `priority`, `category`, `sentiment`, `channel`, `ai_context` (JSONB), `resolved_at`, `resolved_by`, timestamps |
| `Message` | `messages` | Individual messages in a ticket thread | `id`, `ticket_id` (FK), `sender_type` (customer/ai_agent/human_agent/system), `content`, `metadata_` (JSONB), timestamps |
| `Agent` | `agents` | AI and human agents | `id`, `name`, `is_ai`, `specialties` (ARRAY), `metadata_` (JSONB) |
| `AgentAction` | `agent_actions` | Audit trail of AI decisions | `id`, `agent_id` (FK), `ticket_id` (FK), `action_type`, `action_data` (JSONB), `reasoning` (JSONB), `outcome`, timestamps |
| `KnowledgeBaseArticle` | `knowledge_base_articles` | KB articles with vector embeddings | `id`, `title`, `content`, `category`, `tags` (ARRAY), `embedding` (VECTOR(384)), `metadata_` (JSONB) |

**Key design decisions:**
- All IDs are UUIDs (not auto-increment integers) — better for distributed systems
- JSONB columns (`ai_context`, `action_data`, `reasoning`) store flexible, schema-less data
- `embedding` uses pgvector's `VECTOR(384)` type for similarity search
- All timestamps are `TIMESTAMPTZ` (timezone-aware)

---

### `session.py` — Database Connection & Initialization (5.7KB)

Manages the async database connection pool and initialization.

**Key components:**

| Component | Purpose |
|-----------|---------|
| `engine` | Async SQLAlchemy engine — manages the connection pool to Supabase PostgreSQL |
| `async_session_factory` | Creates individual `AsyncSession` objects for each request |
| `get_db_session()` | FastAPI dependency — provides a session to route handlers, auto-commits on success, auto-rollbacks on error |
| `init_db()` | Called once on startup — tests connectivity, enables pgvector extension, creates tables, and runs any schema migrations |

**Connection pool:** The engine maintains a pool of database connections. Instead
of opening a new connection for every request (expensive), it reuses connections
from the pool (fast).

```python
# How routes get a DB session:
async def create_ticket(db: AsyncSession = Depends(get_db_session)):
    # 'db' is an auto-managed session from the pool
    # Commits on success, rolls back on exception
```

---

### `repositories/` Subfolder

Contains the actual CRUD functions. See `repositories/README.md`.

---

### `__init__.py` — Package Init

Exports session utilities for clean imports.
