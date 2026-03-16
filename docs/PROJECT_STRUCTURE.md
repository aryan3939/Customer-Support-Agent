# 📂 Project Structure — File-by-File Explanation

Every file in this project explained. Read this to understand what each file does and why it exists.

---

## Root Directory

| File | Purpose |
|------|---------|
| `requirements.txt` | Python package dependencies — install via `pip install -r requirements.txt` |
| `pyproject.toml` | Python project metadata, tool configurations (black, ruff, pytest) |
| `.env.example` | Template for environment variables — copy to `.env` and fill in your keys |
| `.env` | **YOUR secrets** — never commit this (gitignored) |
| `.gitignore` | Files excluded from Git (venv, .env, __pycache__, etc.) |
| `docker-compose.yml` | Optional Redis container for caching — `docker-compose up -d` |
| `alembic.ini` | Alembic migration configuration — points to `alembic/env.py` |

---

## `src/` — Backend Application

### `src/main.py` — Application Entry Point

**What it does:**
- Creates the FastAPI application instance
- Configures CORS middleware (allows frontend → backend communication)
- Defines the lifespan handler (startup/shutdown logic)
- Registers all route files
- Provides `/` (root info) and `/health` (health check) endpoints

**Startup sequence:**
1. Initialize structured logging
2. Connect to PostgreSQL (Supabase)
3. Enable pgvector extension
4. Create database tables (if they don't exist)
5. Apply schema migrations (ALTER TABLE for missing columns)
6. Load the sentence-transformers embedding model
7. Register all API routes

---

### `src/config.py` — Configuration Management

**What it does:**
- Uses Pydantic Settings to read `.env` file values
- Validates all configuration at startup (fails fast if keys are missing)
- Provides typed access: `settings.DATABASE_URL`, `settings.LLM_MODEL`, etc.

**Key configuration groups:**
| Group | Variables |
|-------|----------|
| Database | `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_ANON_KEY` |
| LLM | `LLM_PROVIDER`, `GOOGLE_API_KEY`, `GROQ_API_KEY`, `LLM_MODEL` |
| Auth | `JWT_SECRET`, `SUPABASE_JWT_SECRET` |
| Tracing | `LANGCHAIN_TRACING_V2`, `LANGCHAIN_API_KEY` |
| Behavior | `ENABLE_AUTO_RESOLUTION`, `MAX_AUTO_ATTEMPTS`, `ESCALATION_CONFIDENCE_THRESHOLD` |

---

## `src/agents/` — AI Agent (LangGraph)

The brain of the application. Implements the ticket processing workflow as a state machine.

### `src/agents/graph.py` — The State Machine

**What it does:**
- Defines the LangGraph workflow: `classify → kb_search → respond → validate → finalize`
- Adds conditional edges for escalation decisions
- Compiles the graph at import time (singleton)
- Exports `process_ticket()` — the main entry point for the AI agent

### `src/agents/state.py` — Shared State Schema

**What it does:**
- Defines `TicketState` — the TypedDict that flows through every node
- Contains: ticket data, classification results, KB search results, AI response, audit actions
- Each node reads from and writes to this shared state

### `src/agents/llm.py` — LLM Factory

**What it does:**
- Creates the right LangChain LLM client based on `LLM_PROVIDER` setting
- Supports Google Gemini (`ChatGoogleGenerativeAI`) and Groq (`ChatGroq`)
- Configures temperature, model name, and API key

### `src/agents/models.py` — AI Output Schemas

**What it does:**
- Pydantic models for structured LLM outputs (e.g., `TicketClassification`)
- Used with LangChain's `with_structured_output()` for reliable JSON parsing from LLM

### `src/agents/nodes/` — Graph Nodes (Processing Steps)

| File | Node | What It Does |
|------|------|-------------|
| `classifier.py` | `classify` | LLM analyzes intent, priority, sentiment, category |
| `kb_searcher.py` | `kb_search` | Embeds question → pgvector similarity search → returns articles |
| `resolver.py` | `respond` | LLM generates response using KB context + ticket data |
| `validator.py` | `validate` | LLM checks response quality — approve or escalate |
| `escalator.py` | `escalate` | Marks ticket for human review, records reason |

### `src/agents/edges/conditions.py` — Routing Logic

**What it does:**
- `should_escalate_after_classify()` — checks if priority is urgent or sentiment is negative
- `should_escalate_after_validate()` — checks if validator flagged quality issues

---

## `src/api/` — REST API Layer

### `src/api/routes/tickets.py` — Customer Ticket Endpoints

| Endpoint | Function | What It Does |
|----------|----------|-------------|
| `POST /api/v1/tickets` | `create_ticket` | Creates ticket, runs AI agent, returns response |
| `GET /api/v1/tickets` | `list_tickets` | Lists user's tickets with filters + pagination |
| `GET /api/v1/tickets/{id}` | `get_ticket` | Full ticket details with messages and actions |
| `POST /api/v1/tickets/{id}/messages` | `add_message` | Follow-up message → triggers AI auto-reply |
| `PATCH /api/v1/tickets/{id}/status` | `update_ticket_status` | Change ticket status |
| `PATCH /api/v1/tickets/{id}/resolve` | `resolve_ticket` | Mark ticket as resolved |
| `GET /api/v1/tickets/{id}/actions` | `get_ticket_actions` | View AI audit trail |

### `src/api/routes/admin.py` — Admin Endpoints

| Endpoint | Function | What It Does |
|----------|----------|-------------|
| `GET /api/v1/admin/conversations` | `list_conversations` | All tickets with advanced filters |
| `GET /api/v1/admin/conversations/{id}` | `get_conversation` | Conversation details |
| `POST /api/v1/admin/conversations/{id}/reply` | `admin_reply` | Reply as human agent |
| `PATCH /api/v1/admin/conversations/{id}/resolve` | `admin_resolve` | Admin-resolve ticket |

### `src/api/routes/analytics.py` — Dashboard Metrics

Provides aggregated statistics for the analytics dashboard.

### `src/api/routes/webhooks.py` — External Integrations

Stub endpoints for email/Slack webhook integrations (future use).

### `src/api/schemas/` — Request/Response Models

| File | Purpose |
|------|---------|
| `ticket.py` | `CreateTicketRequest`, `TicketResponse`, `TicketDetailResponse`, etc. |

### `src/api/deps/auth.py` — Authentication

**What it does:**
- `get_current_user()` — extracts and verifies JWT from `Authorization` header
- Uses Supabase's JWKS endpoint to fetch public keys (supports ES256, EdDSA, HS256)
- Caches JWKS keys (auto-refreshes)
- `require_admin()` — requires `role: "admin"` in JWT claims

### `src/api/middleware/error_handler.py` — Error Handling

Catches unhandled exceptions and returns clean JSON error responses.

---

## `src/db/` — Database Layer

### `src/db/models.py` — SQLAlchemy ORM Models

Defines all database tables as Python classes:

| Model | Table | Key Fields |
|-------|-------|-----------|
| `Customer` | `customers` | id, email, name, metadata |
| `Ticket` | `tickets` | id, customer_id, subject, status, priority, category, ai_context |
| `Message` | `messages` | id, ticket_id, sender_type, content |
| `Agent` | `agents` | id, name, is_ai, specialties |
| `AgentAction` | `agent_actions` | id, agent_id, ticket_id, action_type, reasoning |
| `KnowledgeBaseArticle` | `knowledge_base_articles` | id, title, content, embedding (VECTOR) |

### `src/db/session.py` — Database Connection

**What it does:**
- Creates async SQLAlchemy engine with `asyncpg` driver
- Manages connection pooling (`pool_size=5`, `max_overflow=10`)
- `init_db()` — creates tables, enables pgvector, applies schema fixes
- `get_db_session()` — FastAPI dependency that provides a database session

### `src/db/repositories/` — Data Access

| File | Purpose |
|------|---------|
| `ticket_repo.py` | CRUD for tickets, messages, agent actions |
| `customer_repo.py` | Customer lookup and creation |

**Pattern:** Routes call repositories → repositories execute SQL → return models. Routes never write raw SQL.

---

## `src/services/` — Business Logic

| File | Purpose |
|------|---------|
| `ticket_service.py` | Orchestrates ticket creation (create customer → create ticket → run AI) |
| `embedding_service.py` | Singleton that loads `sentence-transformers` model and generates embeddings |
| `analytics_service.py` | Queries for dashboard metrics (ticket counts, resolution rates) |

---

## `src/tools/` — Agent Tools

LangChain tools that the AI agent can call during processing:

| File | Tool | What It Does |
|------|------|-------------|
| `knowledge_base.py` | `search_kb` | Vector similarity search with keyword fallback |
| `customer_service.py` | `get_customer` | Lookup customer info (purchase history, etc.) |
| `external_apis.py` | `check_order` | Stub for external API calls (order status, etc.) |
| `notifications.py` | `send_email` | Stub for email notifications |

---

## `src/utils/` — Utilities

| File | Purpose |
|------|---------|
| `logging.py` | Configures `structlog` — colored console (dev) or JSON (prod) |
| `metrics.py` | Simple performance counters for monitoring |

---

## `frontend/` — Next.js Frontend

### `frontend/src/app/` — Pages

| File/Folder | Route | Purpose |
|-------------|-------|---------|
| `layout.tsx` | All routes | Root layout — auth guard, sidebar navigation |
| `page.tsx` | `/` | Dashboard — ticket list + create ticket form |
| `login/page.tsx` | `/login` | Supabase email/password login |
| `tickets/[id]/page.tsx` | `/tickets/:id` | Ticket detail — chat messages + resolve/close |
| `admin/` | `/admin` | Admin conversation list |
| `admin/[id]/` | `/admin/:id` | Admin conversation detail + reply as agent |
| `analytics/` | `/analytics` | Analytics dashboard |
| `globals.css` | — | Tailwind CSS + custom CSS variables (dark theme) |

### `frontend/src/hooks/`

| File | Purpose |
|------|---------|
| `useAuth.ts` | React hook wrapping Supabase auth — provides `user`, `session`, `role`, `signOut` |

### `frontend/src/lib/`

| File | Purpose |
|------|---------|
| `api.ts` | Backend API client — `createTicket()`, `getTickets()`, `sendMessage()`, `resolveTicket()`, etc. |
| `supabase.ts` | Supabase browser client singleton |

---

## `scripts/` — Utility Scripts

| File | Purpose |
|------|---------|
| `seed_kb.py` | Populates the knowledge base with support articles + vector embeddings |
| `test_agent.py` | Standalone test — processes a ticket through the AI agent |

---

## `alembic/` — Database Migrations

| File | Purpose |
|------|---------|
| `env.py` | Alembic environment — configures async SQLAlchemy for migrations |
| `script.py.mako` | Template for new migration files |
| `versions/` | Individual migration scripts (e.g., `add_resolved_by.py`) |

---

## `tests/` — Test Suite (Scaffold)

```
tests/
├── e2e/          # End-to-end tests (empty — future)
├── integration/  # Integration tests (empty — future)
└── unit/         # Unit tests (empty — future)
```

Test directories are set up with `.gitkeep` placeholders. Tests can be added using `pytest`.

---

## `docs/` — Documentation

| File | Purpose |
|------|---------|
| `SETUP.md` | Complete setup guide with API key instructions |
| `ARCHITECTURE.md` | System design, data flow, design decisions |
| `PROJECT_STRUCTURE.md` | This file — every file explained |
| `API_REFERENCE.md` | All API endpoints with examples |
| `RAG_DEEP_DIVE.md` | How vector search and embeddings work |
| `COMPLETE_PROJECT_GUIDE.md` | Comprehensive project guide (legacy) |
| `01-06_*.md` | Step-by-step build guides (legacy) |
