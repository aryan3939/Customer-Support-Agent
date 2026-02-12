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

## Folder Structure

| Folder | Responsibility | Key Concept |
|--------|---------------|-------------|
| `agents/` | AI agent workflow (LangGraph state machine) | The "brain" — classifies tickets, searches KB, generates responses |
| `api/` | REST endpoints, request/response schemas, middleware | The "interface" — how the frontend talks to the backend |
| `db/` | SQLAlchemy models, database sessions, repositories | The "memory" — persists everything to Supabase PostgreSQL |
| `services/` | Business logic (analytics computations) | The "logic" — operations that aren't HTTP or DB-specific |
| `tools/` | Agent tools (KB search, external APIs, notifications) | The "hands" — actions the AI agent can take |
| `utils/` | Shared utilities (logging, metrics) | The "toolbox" — cross-cutting concerns used everywhere |

## Key Files

| File | Purpose |
|------|---------|
| `main.py` | FastAPI app entry point. Run with `uvicorn src.main:app --reload` |
| `config.py` | Loads `.env` settings via Pydantic. Validates at import time — crashes early if keys are missing |
| `__init__.py` | Package marker with version string |

## How to Run

```bash
# From the project root (with venv activated)
uvicorn src.main:app --reload --port 8000
```

## How to Explain This

> "The `src/` folder follows a **layered architecture** — each subfolder has
> a single responsibility. Routes handle HTTP, agents handle AI logic,
> repositories handle the database, and tools handle external integrations.
> This separation means you can test each layer independently and swap
> implementations without affecting the rest."
