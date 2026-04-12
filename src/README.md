# `src/` — Backend Application

This is the **core backend** of the Customer Support Agent, built with
**FastAPI** (REST API) and **LangGraph** (AI agent workflow).

## How It Works

When a customer submits a support ticket, the request flows through these layers:

```
HTTP Request → API Routes → AI Agent Graph → Database → HTTP Response
                  │              │                │
                  │         LLM calls             │
                  │         (Groq/Google)          │
                  │              │                │
              Schemas        Tools            Repositories
           (validation)   (KB search,        (Supabase CRUD)
                          notifications)
```

### Step-by-Step Request Flow

1. **Request arrives** → FastAPI validates it against Pydantic schemas (`api/schemas/`)
2. **Authentication** → JWT token is verified via Supabase JWKS (`api/deps/auth.py`)
3. **Route handler** → The appropriate route function runs (`api/routes/tickets.py`)
4. **Database ops** → Customer is found/created, ticket is inserted (`db/repositories/`)
5. **AI agent** → LangGraph processes the ticket through 5 nodes (`agents/graph.py`)
6. **LLM calls** → Gemini/Groq classifies intent, generates response (`agents/nodes/`)
7. **KB search** → Vector similarity search finds relevant articles (`tools/knowledge_base.py`)
8. **Response** → FastAPI serializes the result and returns it as JSON

## Folder Structure

| Folder | Responsibility | Key Concept |
|--------|---------------|-------------|
| `agents/` | AI agent workflow (LangGraph state machine) | The "brain" — classifies tickets, searches KB, generates responses |
| `api/` | REST endpoints, request/response schemas, middleware | The "interface" — how the frontend talks to the backend |
| `db/` | SQLAlchemy models, database sessions, repositories | The "memory" — persists everything to Supabase PostgreSQL |
| `services/` | Business logic (analytics, embeddings, ticket orchestration) | The "logic" — complex operations that span multiple layers |
| `tools/` | Agent tools (KB search, external APIs, notifications) | The "hands" — actions the AI agent can take via LangChain tools |
| `utils/` | Shared utilities (logging, metrics) | The "toolbox" — cross-cutting concerns used everywhere |

## Key Files

| File | Purpose | Why It Matters |
|------|---------|---------------|
| `main.py` | FastAPI app entry point with lifespan events | Starts the server, loads the embedding model, connects to DB, registers all routes |
| `config.py` | Loads `.env` settings via Pydantic Settings | Validates all config at import time — if a required key is missing, the app crashes immediately with a clear error instead of failing randomly later |
| `__init__.py` | Package marker with version string | Makes `src` importable as a Python package |

## How to Run

```bash
# From the project root (with venv activated)
uvicorn src.main:app --reload --port 8000
```

## Architecture Pattern

> The `src/` folder follows a **layered architecture** — each subfolder has
> a single responsibility. Routes handle HTTP, agents handle AI logic,
> repositories handle the database, and tools handle external integrations.
> This separation means you can test each layer independently and swap
> implementations without affecting the rest.
>
> **Key pattern:** No layer imports "upward." Repositories don't know about
> routes, agents don't know about HTTP, and tools don't know about the
> database. Data flows DOWN through the layers via function arguments.
