# 03 — Database Models (SQLAlchemy ORM)

How data is structured, stored, and queried in the Customer Support Agent.

---

## 3.1 Why an ORM?

Instead of writing raw SQL:
```sql
INSERT INTO tickets (id, subject, status, priority)
VALUES ('abc-123', 'Help me', 'new', 'medium');
```

We define Python classes that **map to database tables**:
```python
ticket = Ticket(subject="Help me", status="new", priority="medium")
db.add(ticket)
await db.commit()
```

**Benefits:**
- **Type safety** — IDE catches typos, wrong types, missing fields
- **Relationships** — `ticket.messages` auto-loads related messages
- **Migrations** — Alembic compares models vs. database and generates migration scripts
- **Portability** — same code works on PostgreSQL, MySQL, SQLite (for testing)

---

## 3.2 The Base Class

Every model inherits from a shared base:

```python
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass
```

This is SQLAlchemy 2.0's modern approach. The old way was `Base = declarative_base()` — deprecated but still works.

**What `Base` provides:**
- `Base.metadata` — tracks all tables, used by `create_all()` and Alembic
- table creation: `Base.metadata.create_all(engine)` creates all tables
- migration detection: Alembic compares `Base.metadata` to the database

---

## 3.3 Models (Tables)

### Customer

```
Table: customers
Purpose: People who submit support tickets
```

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| `id` | UUID | Primary Key, auto-generated | Unique identifier |
| `email` | String(255) | Unique, Not Null, Indexed | Login identity, ticket lookup |
| `name` | String(255) | Nullable | Display name |
| `metadata_` | JSONB | Default {} | Flexible key-value data (account info, preferences) |
| `created_at` | TIMESTAMPTZ | Auto-set | Account creation time |

**Relationships:** `customer.tickets` → list of all their tickets (one-to-many)

**Why JSONB for metadata?** Relational databases are rigid — every row must have the same columns. JSONB lets us store flexible, schema-less data (like customer preferences or account type) without adding columns for every possible field.

---

### Agent

```
Table: agents
Purpose: AI agents and human support staff
```

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| `id` | UUID | Primary Key | Unique identifier |
| `name` | String(255) | Not Null | Agent name (e.g., "AI Support Agent") |
| `is_ai` | Boolean | Default True | Distinguishes AI from human agents |
| `specialties` | ARRAY(String) | Nullable | Areas of expertise (e.g., ["billing", "technical"]) |
| `metadata_` | JSONB | Default {} | Agent configuration data |
| `created_at` | TIMESTAMPTZ | Auto-set | When the agent was created |

**Relationships:**
- `agent.assigned_tickets` → tickets assigned to this agent
- `agent.actions` → audit trail entries this agent created

---

### Ticket ⭐ (Central Table)

```
Table: tickets
Purpose: The core entity — almost everything relates to it
Lifecycle: new → open → (pending_customer | pending_agent | escalated) → resolved → closed
```

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| `id` | UUID | Primary Key | Unique identifier |
| `customer_id` | UUID | Foreign Key → customers, Not Null | Who created this ticket |
| `assigned_agent_id` | UUID | Foreign Key → agents, Nullable | Which agent handles it |
| `subject` | String(500) | Not Null | Ticket title |
| `status` | String(50) | Default "new", Check Constraint | Current lifecycle stage |
| `priority` | String(20) | Default "medium" | Urgency level (low/medium/high/urgent) |
| `category` | String(100) | Nullable | AI-classified category |
| `sentiment` | String(50) | Nullable | Customer's emotional state |
| `channel` | String(50) | Default "web" | Origin (web, email, api) |
| `ai_confidence` | Float | Nullable | AI's classification confidence (0.0–1.0) |
| `ai_context` | JSONB | Default {} | Full AI classification data (stored for debugging) |
| `resolution_notes` | Text | Nullable | How the ticket was resolved |
| `resolved_at` | TIMESTAMPTZ | Nullable | When resolution happened |
| `resolved_by` | String(50) | Nullable | Who resolved it (customer/admin/ai_agent) |
| `created_at` | TIMESTAMPTZ | Auto-set | Ticket creation time |
| `updated_at` | TIMESTAMPTZ | Auto-updated | Last modification time |

**Relationships:**
- `ticket.customer` → the Customer who created it
- `ticket.assigned_agent` → the Agent handling it
- `ticket.messages` → all messages in this ticket's thread
- `ticket.actions` → all AI agent actions (audit trail)
- `ticket.tags` → categorization labels (many-to-many)

**Check Constraint on status:**
```python
CheckConstraint(
    "status IN ('new', 'open', 'in_progress', 'pending_customer', "
    "'pending_agent', 'escalated', 'resolved', 'closed')",
)
```

---

### Message

```
Table: messages
Purpose: Individual messages in a ticket's conversation thread
```

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| `id` | UUID | Primary Key | Unique identifier |
| `ticket_id` | UUID | Foreign Key → tickets, Not Null, Indexed | Which ticket this belongs to |
| `sender_type` | String(50) | Check Constraint, Not Null | Who sent it: "customer", "ai_agent", "human_agent", "system" |
| `content` | Text | Not Null | The message body |
| `metadata_` | JSONB | Default {} | Additional data (e.g., AI model used, processing time) |
| `created_at` | TIMESTAMPTZ | Auto-set | When the message was sent |

---

### AgentAction

```
Table: agent_actions
Purpose: Audit trail — records every decision the AI makes
```

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| `id` | UUID | Primary Key | Unique identifier |
| `agent_id` | UUID | Foreign Key → agents, Not Null | Which agent performed this |
| `ticket_id` | UUID | Foreign Key → tickets, Not Null, Indexed | Which ticket this is about |
| `action_type` | String(100) | Not Null, Indexed | What was done: "classify_ticket", "search_kb", "generate_response", "escalate" |
| `action_data` | JSONB | Default {} | Input/output data for this action |
| `reasoning` | JSONB | Default {} | LLM's chain-of-thought explanation |
| `outcome` | String(50) | Nullable | Result: "success", "escalated", "error" |
| `created_at` | TIMESTAMPTZ | Auto-set | When the action happened |

**Why JSONB for action_data and reasoning?** Each action type has different data. A classification action stores intent/priority/sentiment. A KB search stores query and results. JSONB accommodates this without separate tables.

---

### KnowledgeBaseArticle

```
Table: knowledge_base_articles
Purpose: Support articles with vector embeddings for RAG search
```

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| `id` | UUID | Primary Key | Unique identifier |
| `title` | String(500) | Not Null | Article title (e.g., "How to Reset Your Password") |
| `content` | Text | Not Null | Full article body |
| `category` | String(100) | Nullable | Article category (e.g., "account", "billing") |
| `tags` | ARRAY(String) | Nullable | Search tags |
| `embedding` | VECTOR(384) | Nullable | 384-dimensional vector from sentence-transformers |
| `metadata_` | JSONB | Default {} | Additional article data |
| `created_at` | TIMESTAMPTZ | Auto-set | When the article was created |
| `updated_at` | TIMESTAMPTZ | Auto-updated | Last modification time |

**The `embedding` column:** This is a pgvector `VECTOR(384)` type. It stores the semantic meaning of the article as 384 floating-point numbers. When a customer asks a question, we embed their question and find the most similar article embeddings using cosine distance.

---

## 3.4 Database Connection (`src/db/session.py`)

### Async Engine & Connection Pool

```python
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,          # Print SQL queries in debug mode
    pool_size=5,                  # Keep 5 connections open
    max_overflow=10,              # Allow 10 more during spikes
    pool_recycle=3600,            # Replace connections after 1 hour
)
```

**Why connection pooling?** Opening a database connection takes ~50-100ms. For a web app handling 100 requests/second, that's 5-10 seconds of wasted time. The pool keeps connections open and reusable.

### Session Management

```python
async def get_db_session():
    """FastAPI dependency — provides a session per request."""
    async with async_session_factory() as session:
        try:
            yield session       # Route uses the session
            await session.commit()   # Auto-commit on success
        except Exception:
            await session.rollback() # Auto-rollback on error
            raise
```

### Database Initialization (`init_db()`)

Called once on startup via the FastAPI lifespan:

```python
async def init_db():
    # 1. Test connectivity
    # 2. Enable pgvector extension: CREATE EXTENSION IF NOT EXISTS vector
    # 3. Create all tables: Base.metadata.create_all()
    # 4. Run schema migrations (add missing columns, etc.)
    # 5. Ensure AI agent record exists in the agents table
```

---

## 3.5 Repository Pattern (`src/db/repositories/`)

Repositories encapsulate all SQL queries:

```python
# ❌ BAD — SQL in route handler
@router.get("/tickets")
async def list_tickets(db: AsyncSession):
    result = await db.execute(select(Ticket).where(Ticket.status == "open"))
    return result.scalars().all()

# ✅ GOOD — Repository abstracts it
@router.get("/tickets")
async def list_tickets(db: AsyncSession):
    return await ticket_repo.get_tickets_by_status(db, "open")
```

**Eager loading** prevents N+1 query problems:
```python
stmt = select(Ticket).options(
    selectinload(Ticket.messages),      # Load messages in ONE query
    selectinload(Ticket.agent_actions), # Load actions in ONE query
    joinedload(Ticket.customer),        # Load customer via JOIN
)
# Without eager loading: accessing ticket.messages triggers a SEPARATE query
# With it: everything loads in the initial query
```
