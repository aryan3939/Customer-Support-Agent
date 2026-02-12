# `api/` — REST API Layer

This folder defines the **HTTP interface** of the application — how the
frontend (and external services) communicate with the backend.

## Architecture

```
Incoming Request
    │
    ▼
Middleware (auth, rate limiting)
    │
    ▼
Routes (tickets.py, analytics.py, webhooks.py)
    │
    ▼
Schemas (Pydantic validation)
    │
    ▼
Service/Agent/Repository layer
```

## Folder Structure

| Folder | What It Contains |
|--------|-----------------|
| `routes/` | FastAPI endpoint handlers — one file per resource |
| `schemas/` | Pydantic models for request/response validation |
| `middleware/` | Request interceptors (auth, rate limiting) |

## Design Decisions

1. **Routes are thin** — they parse the request, call the right service/repo, and return the response. No business logic lives here.
2. **Schemas validate everything** — Pydantic catches invalid data before it reaches any logic. Type safety enforced at the API boundary.
3. **Every route uses `Depends(get_db_session)`** — FastAPI's dependency injection provides a database session per request, auto-committed on success or rolled back on error.

## How to Explain This

> "The API layer follows FastAPI best practices: routes are thin controllers
> that delegate to services and repositories, Pydantic schemas enforce type
> safety at the boundary, and dependency injection manages database sessions.
> Middleware handles cross-cutting concerns like auth and rate limiting
> without polluting route logic."
