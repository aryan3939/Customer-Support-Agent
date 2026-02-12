# Phase 1C: Database Models & Migrations

## Why This Step?

Our app needs to **persist data** — tickets, customers, messages, AI actions. Without a database layer:
- Data disappears when the server restarts
- No relationships between entities (who created which ticket?)
- No audit trail (what did the AI agent do and why?)

This step creates three things:
1. **ORM Models** — Python classes that represent database tables
2. **Session Management** — How the app connects to and talks to the database
3. **Alembic Migrations** — Version control for the database schema

---

## Files Created

```
├── alembic.ini              ← Alembic configuration
├── alembic/
│   ├── env.py               ← Bridges Alembic with our app config
│   ├── script.py.mako       ← Template for migration files
│   └── versions/            ← Migration files go here
└── src/db/
    ├── __init__.py           ← Re-exports all models
    ├── models.py             ← SQLAlchemy ORM models (8 tables)
    └── session.py            ← Async connection pool + session factory
```

---

## The Database Schema

```
Customer ──creates──→ Ticket ──has──→ Message
                        │
                        ├──assigned_to──→ Agent
                        ├──has──→ AgentAction (audit trail)
                        └──tagged_with──→ Tag (many-to-many)

KnowledgeArticle ──has──→ KBEmbedding (vector chunks for RAG)
```

### Tables at a Glance

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `customers` | People submitting tickets | email, name, metadata |
| `agents` | AI + human support staff | name, skills, is_ai |
| `tickets` | Core entity — a support request | status, priority, category, subject |
| `messages` | Conversation thread on a ticket | sender_type, content |
| `agent_actions` | Audit trail — what the AI did and why | action_type, reasoning, outcome |
| `tags` | Labels for categorization | name, category |
| `ticket_tags` | Junction: ticket ↔ tag (many-to-many) | ticket_id, tag_id |
| `knowledge_articles` | KB articles for RAG search | title, content |
| `kb_embeddings` | Vector chunks for similarity search | chunk_text, embedding, chunk_index |

---

## File-by-File Breakdown

### `src/db/models.py` — ORM Models

#### What Is an ORM?

ORM = Object-Relational Mapping. It maps Python → Database:

```
Python Class    ←→  Database Table
Python Instance ←→  Database Row
Python Attribute ←→ Database Column
```

**Without ORM (raw SQL):**
```python
cursor.execute("INSERT INTO tickets (subject, status) VALUES (%s, %s)", 
               ("Help me", "new"))
```
Problems: SQL injection risk, no type safety, no autocomplete.

**With ORM (SQLAlchemy):**
```python
ticket = Ticket(subject="Help me", status="new")
session.add(ticket)
await session.commit()
```
Benefits: safe, typed, readable, database-agnostic.

#### The Base Class

```python
class Base(DeclarativeBase):
    pass
```

Every model inherits from `Base`. This lets SQLAlchemy and Alembic:
- Discover all models (via `Base.metadata`)
- Generate CREATE TABLE statements
- Detect schema differences for migrations

#### UUIDs as Primary Keys

```python
id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
```

Why UUID instead of auto-increment integers?
- **Security** — Can't guess the next ID (no `/tickets/1`, `/tickets/2`)
- **Client-side generation** — No DB round-trip to get an ID
- **Merge-safe** — No collisions when combining databases

#### JSONB Columns

```python
metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, server_default="{}")
```

JSONB = flexible schema-less data inside a relational database. Perfect for:
- Varying customer metadata: `{"company": "...", "plan": "pro"}`
- AI context: `{"intent": "billing", "confidence": 0.92}`
- Action data: `{"tool_name": "send_email", "result": "success"}`

The `_` suffix (`metadata_`) avoids clashing with Python's built-in `metadata`. The `"metadata"` string sets the actual column name in the database.

#### Relationships

```python
# In Customer:
tickets: Mapped[list["Ticket"]] = relationship(back_populates="customer")

# In Ticket:
customer: Mapped["Customer"] = relationship(back_populates="tickets")
```

These don't create columns! They tell SQLAlchemy how to JOIN tables:
```python
customer = await session.get(Customer, customer_id)
print(customer.tickets)  # → [Ticket1, Ticket2, ...]  (auto-loaded from DB)
```

`back_populates` creates a two-way link: `customer.tickets` and `ticket.customer`.

#### CHECK Constraints

```python
CheckConstraint(
    "status IN ('new', 'open', 'pending_customer', ...)",
    name="valid_status",
)
```

The database itself rejects invalid values. Even if a bug in our code tries to set `status="invalid"`, PostgreSQL says NO. Defense in depth.

#### Indexes

```python
Index("idx_tickets_status", "status"),
Index("idx_tickets_customer", "customer_id"),
```

Indexes speed up queries. Without an index on `status`, finding all open tickets scans EVERY row. With an index, it's nearly instant.

---

### `src/db/session.py` — Connection Management

#### Connection Pooling

```python
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=5,        # 5 connections always ready
    max_overflow=10,    # 10 extra during spikes
    pool_pre_ping=True, # Test before using
)
```

**Without pooling:** Every request opens a new connection (slow — ~50ms each).
**With pooling:** Connections are reused from a pool (fast — ~0.1ms).

```
Request 1 ─→ [Pool: □□□□□] ─→ Take connection ─→ Use ─→ Return to pool
Request 2 ─→ [Pool: □□□□ ] ─→ Take connection ─→ Use ─→ Return to pool
```

#### The Session Dependency

```python
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session           # Give session to route
            await session.commit()  # Success → save changes
        except Exception:
            await session.rollback()  # Error → undo everything
        finally:
            await session.close()     # Always return to pool
```

Used in FastAPI routes via dependency injection:
```python
@app.get("/tickets")
async def list_tickets(db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(Ticket))
    return result.scalars().all()
```

This implements the **Unit of Work** pattern: all database operations within one request are a single atomic transaction. Either everything succeeds, or nothing does.

---

### Alembic — Database Migrations

#### What Are Migrations?

Migrations = version control for your database schema.

```
v1: CREATE TABLE tickets (id, subject)
v2: ALTER TABLE tickets ADD COLUMN priority
v3: ALTER TABLE tickets ADD COLUMN category
```

Without migrations: you'd manually run SQL on every environment. With Alembic: one command applies all pending changes.

#### `alembic.ini`

Configuration file. Key settings:
```ini
script_location = alembic          # Where migration scripts live
file_template = %%(year)d_...      # Date-based naming
```

#### `alembic/env.py`

Bridges Alembic with our app:
```python
from src.config import settings
from src.db.models import Base

config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
target_metadata = Base.metadata
```

It reads our `.env` for the database URL and our models to know what the schema should look like.

**Async support:** Since we use `asyncpg`, migrations must also run async. The `run_async_migrations()` function handles this.

---

## How to Use

### Generate the First Migration

```bash
# Make sure .env has your Supabase DATABASE_URL
# Then generate migration from models
alembic revision --autogenerate -m "initial tables"
```

This compares `models.py` against the actual database and generates a migration file in `alembic/versions/`.

### Apply Migrations

```bash
# Apply all pending migrations to the database
alembic upgrade head
```

### Other Useful Commands

```bash
alembic history            # Show migration history
alembic current            # Show current database version
alembic downgrade -1       # Undo last migration
alembic revision --autogenerate -m "add new column"  # New migration
```

---

## What Supabase Gives You

Since we're using Supabase, you can also:
1. **View tables** in the Supabase Dashboard → Table Editor
2. **Run SQL** in the SQL Editor
3. **See data** visually without any CLI tools

After running `alembic upgrade head`, check your Supabase dashboard to see all tables created!

---

## What's Next?

With the database ready, Phase 2 begins: **Core Agent**
1. `src/agents/state.py` — LangGraph state schema
2. `src/agents/nodes/classifier.py` — Ticket classification
3. `src/tools/knowledge_base.py` — RAG search tool
4. `src/agents/graph.py` — Main agent workflow
