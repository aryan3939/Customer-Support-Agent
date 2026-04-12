# `src/api/` — REST API Layer

This folder is the **interface** between the frontend and the backend. It handles
every HTTP request that comes into the application — authentication, validation,
routing to business logic, and formatting responses.

## Architecture

```
Incoming HTTP Request
      │
      ▼
[Middleware] → Error handler wraps all routes in try/catch
      │
      ▼
[Deps/Auth] → JWT verified via Supabase JWKS, user extracted
      │
      ▼
[Schemas] → Request body validated against Pydantic models
      │
      ▼
[Routes] → Business logic runs (DB queries, AI agent, etc.)
      │
      ▼
[Schemas] → Response serialized to JSON via Pydantic models
      │
      ▼
HTTP Response (JSON)
```

## Subfolders

| Folder | Purpose | Key Concept |
|--------|---------|-------------|
| `routes/` | Route handlers — the actual endpoint functions | Each file groups related endpoints (tickets, admin, analytics, webhooks) |
| `schemas/` | Pydantic request/response models | Validates input on the way in, serializes output on the way out |
| `deps/` | FastAPI dependencies — injected into route functions | Auth (`get_current_user`), DB session (`get_db_session`) |
| `middleware/` | Request/response middleware | Error handling, rate limiting |

## Key Files

| File | Purpose |
|------|---------|
| `__init__.py` | Package init — minimal, just marks the folder as a package |

## How FastAPI Dependency Injection Works

FastAPI's `Depends()` system automatically injects objects into route functions:

```python
@router.post("/tickets")
async def create_ticket(
    request: CreateTicketRequest,                        # ← Pydantic validates the body
    current_user: CurrentUser = Depends(get_current_user),  # ← JWT verified, user extracted
    db: AsyncSession = Depends(get_db_session),             # ← DB connection from pool
):
    # By the time this code runs, authentication and validation are DONE
    # Just focus on business logic!
```

**Why this matters:** Authentication and DB connections are handled declaratively.
Routes stay clean and focused. Easy to swap implementations for testing.
