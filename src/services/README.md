# `src/services/` — Business Logic Layer

Services contain **complex business logic** that spans multiple layers. They're
called by route handlers and coordinate between the database, AI agent, and
external services.

## When to Use a Service vs. Doing It in the Route

- **Route handler** — simple CRUD, direct API-to-DB operations
- **Service** — complex operations that involve multiple steps, external calls, or computations

## Files

### `ticket_service.py` — Ticket Processing Orchestration (3.2KB)

Orchestrates the full ticket lifecycle — from creation through AI processing
to resolution.

**Key function: `process_new_ticket()`**

This is the main function called by the `POST /tickets` route. It:
1. Creates the customer record (if not exists)
2. Creates the ticket in the database
3. Saves the customer's initial message
4. Calls the LangGraph AI agent to process the ticket
5. Saves the AI's response as a new message
6. Updates the ticket with classification data and status
7. Returns the complete ticket with all messages and actions

```python
# Called by the route handler:
result = await process_new_ticket(
    db=session,
    email="user@example.com",
    subject="Can't login",
    message="I've been locked out of my account",
    channel="web",
)
```

---

### `embedding_service.py` — Vector Embedding Singleton (5.1KB)

Manages the `sentence-transformers` model that generates vector embeddings
for knowledge base search (RAG).

**Why a singleton?** The embedding model is ~90MB. Loading it for every request
would be extremely slow. Instead, we load it **once** on startup and reuse it.

**Key function: `get_embedding(text: str) → list[float]`**

Takes a text string, runs it through the `all-MiniLM-L6-v2` model, and returns
a 384-dimensional float vector. This vector represents the **semantic meaning**
of the text — similar texts produce similar vectors.

```python
# "How do I reset my password?" → [0.023, -0.156, 0.089, ..., 0.041] (384 floats)
# "I forgot my login"           → [0.025, -0.149, 0.092, ..., 0.038] (similar!)
# "What is your refund policy?" → [-0.112, 0.234, -0.067, ..., 0.198] (different!)
```

**Used by:**
- `tools/knowledge_base.py` — to embed the customer's question for similarity search
- `scripts/seed_kb.py` — to embed knowledge base articles during seeding

---

### `analytics_service.py` — Dashboard Metrics (2.2KB)

Computes aggregated statistics for the analytics dashboard.

**Key function: `get_dashboard_metrics(db)`**

Returns:
- Total ticket count
- Breakdown by status (open, resolved, escalated, etc.)
- Breakdown by priority (low, medium, high, urgent)
- Breakdown by category (billing, technical, account, etc.)
- Average resolution time in minutes

---

### `__init__.py` — Package Init

Makes the folder importable.
