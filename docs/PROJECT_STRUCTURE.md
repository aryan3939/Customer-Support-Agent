# 🏗️ Project Structure — Complete Reference

> **Customer Support Agent** — an AI-powered support ticket system built with
> FastAPI, LangGraph, Supabase, and Next.js.

This document explains **every file and folder** in the repository, how they
connect, and why they exist.

---

## High-Level Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      FRONTEND (Next.js)                      │
│  page.tsx → api.ts → /api/v1/tickets (proxy to backend)      │
└─────────────────────────┬────────────────────────────────────┘
                          │  HTTP / JSON
┌─────────────────────────▼────────────────────────────────────┐
│                   BACKEND (FastAPI + LangGraph)               │
│                                                               │
│  Routes (tickets.py, analytics.py, webhooks.py)               │
│     ↓                                                         │
│  AI Agent Graph (classify → search KB → resolve → validate)   │
│     ↓                                                         │
│  Repositories (ticket_repo.py, customer_repo.py)              │
│     ↓                                                         │
│  Supabase PostgreSQL (via SQLAlchemy asyncpg)                 │
│                                                               │
│  Observability: LangSmith tracing + structlog logging         │
└──────────────────────────────────────────────────────────────┘
```

---

## Root Directory

```
Customer Support Agent/
├── .env                  # Environment variables (API keys, DB URL) — NEVER commit
├── .env.example          # Template showing all required/optional env vars
├── .gitignore            # Git ignore rules
├── README.md             # Quick-start README
├── requirements.txt      # Python dependencies (pip install -r requirements.txt)
├── pyproject.toml        # Project metadata, linting config, tool settings
├── docker-compose.yml    # Docker setup for local Postgres + Redis (optional)
├── alembic.ini           # Alembic migration config (references alembic/ folder)
│
├── src/                  # ★ Backend application code
├── frontend/             # ★ Next.js frontend
├── scripts/              # Utility scripts (testing)
├── docs/                 # Documentation
├── tests/                # Test directory (unit, integration, e2e)
├── alembic/              # Database migration files
└── venv/                 # Python virtual environment (not committed)
```

---

## `src/` — Backend Application

### `src/main.py`
**The entry point.** Run with `uvicorn src.main:app --reload`.

- Creates the FastAPI app with metadata (title, version, description)
- Configures CORS middleware (allows frontend at `localhost:3000`)
- Registers all route modules (tickets, analytics, webhooks)
- **Lifespan**: connects to Supabase at startup (`init_db`), closes on shutdown (`close_db`)
- Mounts the health check endpoint at `/health`

### `src/config.py`
**Centralized settings** loaded from `.env` via Pydantic Settings.

- Validates all env vars at import time — app crashes immediately if required vars are missing
- Calls `load_dotenv()` so `LANGCHAIN_*` env vars are available in `os.environ` (LangSmith needs this)
- Exposes a singleton `settings` object used everywhere
- Key settings: `DATABASE_URL`, `LLM_PROVIDER`, `GOOGLE_API_KEY`/`GROQ_API_KEY`, `LANGCHAIN_*`

### `src/__init__.py`
Package marker. Contains version string.

---

## `src/agents/` — AI Agent (LangGraph)

This is the **brain** of the application — a LangGraph state machine that
processes each ticket through a multi-step AI workflow.

### `src/agents/graph.py`
**The workflow definition.** Builds and compiles the LangGraph state machine.

```
START → classify_ticket → [escalate?] → search_knowledge_base
                                              ↓
                             generate_response → validate_response → [retry?] → finalize → END
                                                        ↓
                                                    escalate_ticket → END
```

- `build_graph()` — creates the `StateGraph` with nodes and conditional edges
- `compiled_graph` — singleton compiled graph (built once at import time)
- `process_ticket()` — **public API** called by routes; creates initial state,
  passes `RunnableConfig` with LangSmith thread_id/tags/metadata, invokes the graph

### `src/agents/state.py`
**TypedDict** defining `TicketState` — the data structure that flows through the graph.

Fields include: `ticket_id`, `subject`, `message`, `intent`, `category`,
`priority`, `sentiment`, `confidence`, `kb_results`, `draft_response`,
`final_response`, `needs_escalation`, `actions_taken`, etc.

### `src/agents/llm.py`
**LLM factory** — creates the right LangChain chat model based on `LLM_PROVIDER` setting.

- `google` → `ChatGoogleGenerativeAI` (Gemini)
- `groq` → `ChatGroq` (Llama, Mixtral, etc.)
- Caches the instance after first creation

### `src/agents/nodes/` — Graph Node Functions

Each file is a single node in the LangGraph workflow:

| File | Node | What It Does |
|------|------|-------------|
| `classifier.py` | `classify_ticket` | Sends ticket to LLM with classification prompt; extracts intent, category, priority, sentiment, confidence |
| `resolver.py` | `generate_response` | Sends ticket + classification + KB results to LLM; generates customer-facing response |
| `validator.py` | `validate_response` | Checks response quality (length, relevance, tone); approves or flags for retry |
| `escalator.py` | `escalate_ticket` | Handles tickets that need human intervention; generates escalation reason and handoff message |

### `src/agents/edges/`

| File | What It Does |
|------|-------------|
| `conditions.py` | Conditional routing functions: `should_escalate_after_classify` (urgent+angry → escalate), `should_escalate_after_validate` (failed validation → retry or escalate) |

---

## `src/api/` — REST API Layer

### `src/api/routes/tickets.py`
**The main API** — 6 endpoints for ticket CRUD, all persisted to Supabase:

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/tickets` | Create ticket → run AI agent → persist to DB |
| `GET` | `/api/v1/tickets` | List tickets with filters (status, priority, category, email) |
| `GET` | `/api/v1/tickets/{id}` | Get ticket details with messages + actions |
| `POST` | `/api/v1/tickets/{id}/messages` | Add follow-up message → AI re-processes |
| `PATCH` | `/api/v1/tickets/{id}/status` | Update ticket status (resolve, close, etc.) |
| `GET` | `/api/v1/tickets/{id}/actions` | Get AI audit trail for a ticket |

Every route uses `Depends(get_db_session)` for async DB access.

### `src/api/routes/analytics.py`
Dashboard metrics endpoint (`GET /api/v1/analytics/dashboard`).
Queries all tickets from Supabase and computes: total/open/resolved/escalated counts,
resolution rate, priority/category/sentiment breakdowns.

### `src/api/routes/webhooks.py`
Incoming email webhook endpoint (`POST /api/v1/webhooks/email`).
Receives email data from external services (SendGrid, SES), maps it to a ticket,
and reuses the `create_ticket()` function.

### `src/api/schemas/ticket.py`
**Pydantic models** for request/response validation:
`CreateTicketRequest`, `CreateTicketResponse`, `TicketResponse`,
`TicketDetailResponse`, `TicketListResponse`, `MessageResponse`,
`ActionResponse`, `AgentInfo`, `AddMessageRequest`, `UpdateTicketStatusRequest`.

### `src/api/schemas/responses.py`
Generic API response wrappers (`SuccessResponse`, `ErrorResponse`).

### `src/api/middleware/`

| File | What It Does |
|------|-------------|
| `auth.py` | API key authentication middleware (placeholder — checks header) |
| `rate_limit.py` | Simple in-memory rate limiter (placeholder — tracks requests per IP) |

---

## `src/db/` — Database Layer

### `src/db/models.py`
**SQLAlchemy ORM models** — Python classes that map to Supabase tables:

| Model | Table | Purpose |
|-------|-------|---------|
| `Customer` | `customers` | People who submit tickets (email, name, metadata) |
| `Agent` | `agents` | AI and human support agents (name, email, is_ai, skills) |
| `Ticket` | `tickets` | Core entity — status, priority, category, ai_context, timestamps |
| `Message` | `messages` | Conversation thread within a ticket (sender_type, content) |
| `AgentAction` | `agent_actions` | Audit trail — every AI action (classify, resolve, escalate) |
| `Tag` | `tags` | Labels for ticket categorization |
| `ticket_tags` | `ticket_tags` | Many-to-many junction table (Ticket ↔ Tag) |
| `KnowledgeArticle` | `knowledge_articles` | KB articles for RAG search |
| `KBEmbedding` | `kb_embeddings` | Vector chunks for similarity search (pgvector) |

### `src/db/session.py`
**Engine + session management** for async PostgreSQL:

- Creates `create_async_engine` with PgBouncer-compatible settings (`statement_cache_size=0`)
- `async_session_factory` — SQLAlchemy session factory
- `get_db_session()` — FastAPI dependency (yields session, auto-commits/rollbacks)
- `init_db()` — tests connection + runs `Base.metadata.create_all` (auto-creates tables)
- `close_db()` — closes all connections at shutdown

### `src/db/repositories/`

| File | What It Does |
|------|-------------|
| `customer_repo.py` | `get_or_create_customer()` — finds by email or creates new; `get_customer_by_email()`; `get_customer_by_id()` |
| `ticket_repo.py` | Full CRUD: `create_ticket()`, `get_ticket_by_id()`, `list_tickets()`, `update_ticket_status()`, `add_message()`, `add_agent_action()`, `get_or_create_ai_agent()`, query helpers |

### `src/db/__init__.py`
Re-exports all models and `get_db_session` for convenient imports.

---

## `src/services/` — Business Logic

| File | What It Does |
|------|-------------|
| `analytics_service.py` | `compute_dashboard_metrics()` — takes a list of ticket dicts and returns aggregated stats (counts, rates, breakdowns) |

---

## `src/tools/` — Agent Tools

These are tools the AI agent can use. Some are active, some are mock
placeholders for future integration.

| File | Status | What It Does |
|------|--------|-------------|
| `knowledge_base.py` | **Active** | In-memory KB search — stores sample articles, searches by keyword match. Used by the `search_knowledge_base` node |
| `customer_service.py` | Mock | Returns mock customer profiles. In production: queries customer DB |
| `external_apis.py` | Mock | Simulated integrations (order status, refunds, password reset, bug reports) |
| `notifications.py` | Mock | Simulated Slack/email notifications |

---

## `src/utils/` — Shared Utilities

| File | What It Does |
|------|-------------|
| `logging.py` | Structured logging via `structlog`. JSON format in production, colored console in dev. `setup_logging()` initializes at startup; `get_logger()` creates per-module loggers |
| `metrics.py` | Simple in-memory metrics tracking — counters and latency timers. `track_latency()` context manager, `get_metrics()` returns stats |

---

## `frontend/` — Next.js Dashboard

```
frontend/
├── package.json          # Dependencies (next, react, tailwindcss)
├── next.config.ts        # Proxy rewrites: /api/v1/* → localhost:8000
├── tsconfig.json         # TypeScript config
├── postcss.config.mjs    # PostCSS + Tailwind setup
│
└── src/
    ├── lib/
    │   └── api.ts        # Typed API client — all fetch calls to the backend
    │
    └── app/
        ├── globals.css   # Global styles (CSS variables for dark theme)
        ├── layout.tsx    # Root layout — sidebar navigation, fonts, metadata
        ├── page.tsx      # Home page — ticket list + "New Ticket" form
        │
        ├── tickets/
        │   └── [id]/
        │       └── page.tsx  # Ticket detail — chat thread + AI classification sidebar
        │
        └── analytics/
            └── page.tsx  # Dashboard — metrics cards + charts
```

### Key Frontend Files

| File | What It Does |
|------|-------------|
| `api.ts` | Typed wrappers around `fetch()` for all backend endpoints. Types match backend Pydantic schemas |
| `page.tsx` (root) | Lists all tickets in a table, has a "New Ticket" dialog form |
| `tickets/[id]/page.tsx` | Chat interface — shows message thread, AI classification sidebar, audit trail |
| `analytics/page.tsx` | Dashboard with metric cards (total, open, resolved, escalated) and breakdowns |
| `next.config.ts` | **Critical** — proxies `/api/v1/*` requests to `http://localhost:8000` so frontend and backend can run on different ports |

---

## `scripts/` — Utility Scripts

| File | What It Does |
|------|-------------|
| `test_agent.py` | Standalone script to test the AI agent workflow without starting the server. Sends sample tickets and prints results |

---

## `docs/` — Documentation

| File | What It Covers |
|------|---------------|
| `01_environment_setup.md` | How to set up Python, Node.js, Supabase, and env vars |
| `02_project_setup.md` | Project initialization, folder structure, dependency installs |
| `03_database_models.md` | ERD and explanation of all SQLAlchemy models |
| `04_core_agent.md` | LangGraph workflow design, node descriptions, edge conditions |
| `05_api_routes.md` | REST API endpoint documentation |
| `API_KEYS_SETUP.md` | Step-by-step guide to get Google/Groq/LangSmith/Supabase keys |
| `HOW_TO_RUN.md` | Quick-start guide to run backend + frontend |
| `PROJECT_STRUCTURE.md` | **This file** — comprehensive project map |

---

## `alembic/` — Database Migrations

| File | What It Does |
|------|-------------|
| `env.py` | Alembic configuration — connects to the DB, auto-detects model changes |
| `script.py.mako` | Template for new migration files |
| `versions/` | Migration scripts (currently empty — using `create_all` for schema) |

> **Note:** Currently, tables are auto-created by `Base.metadata.create_all` in
> `session.py`. For schema changes in production, use Alembic:
> `alembic revision --autogenerate -m "description"` then `alembic upgrade head`.

---

## `tests/` — Test Skeleton

```
tests/
├── conftest.py       # Shared pytest fixtures
├── unit/             # Unit tests (individual functions)
├── integration/      # Integration tests (DB + API)
└── e2e/              # End-to-end tests (full workflow)
```

Currently a skeleton — tests can be added using `pytest` + `httpx` for API testing.

---

## Data Flow — Creating a Ticket

Here's exactly what happens when a user clicks "Create Ticket" on the frontend:

```
1. Frontend (page.tsx)
   └── createTicket({ email, subject, message })
       └── POST /api/v1/tickets (proxied via next.config.ts)

2. Backend (tickets.py → create_ticket)
   ├── get_or_create_customer(db, email)     → customers table
   ├── get_or_create_ai_agent(db)            → agents table
   ├── repo_create_ticket(db, ...)           → tickets table
   ├── repo_add_message(db, "customer", ...) → messages table
   │
   ├── process_ticket(ticket_id, ...)        → graph.py
   │   └── compiled_graph.ainvoke(state, config={
   │       "run_name": "ticket-{id}",
   │       "tags": ["customer-support", "channel:web"],
   │       "metadata": { ticket_id, email, subject },
   │       "configurable": { "thread_id": ticket_id }
   │   })
   │       ├── classify_ticket    → LLM call → intent, priority, sentiment
   │       ├── search_kb          → keyword search → relevant articles
   │       ├── generate_response  → LLM call → draft response
   │       ├── validate_response  → quality check → approve/retry
   │       └── finalize           → mark resolved
   │
   ├── Update ticket (status, priority, category, ai_context)
   ├── repo_add_message(db, "ai_agent", response) → messages table
   ├── add_agent_action(db, ...) × N               → agent_actions table
   └── Return CreateTicketResponse to frontend

3. LangSmith Dashboard
   └── Trace appears with thread_id = ticket_id
       ├── classify_ticket (LLM call details)
       ├── generate_response (LLM call details)
       └── Full input/output for each node
```

---

## Key Configuration

| Setting | Where | Purpose |
|---------|-------|---------|
| `DATABASE_URL` | `.env` | Supabase PostgreSQL connection (asyncpg driver, port 6543) |
| `LLM_PROVIDER` | `.env` | `google` or `groq` |
| `LLM_MODEL` | `.env` | Model name (e.g., `gemini-2.0-flash`, `llama-3.1-70b-versatile`) |
| `LANGCHAIN_TRACING_V2` | `.env` | `true` to enable LangSmith tracing |
| `LANGCHAIN_ENDPOINT` | `.env` | API URL (US: `https://api.smith.langchain.com`, EU: `https://eu.api.smith.langchain.com`) |
| `LANGCHAIN_API_KEY` | `.env` | LangSmith API key |
| `SUPABASE_URL` | `.env` | Supabase project URL |
| `SUPABASE_ANON_KEY` | `.env` | Supabase anonymous key |
