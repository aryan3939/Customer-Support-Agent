# `src/api/middleware/` — Middleware & Cross-Cutting Concerns

Middleware runs on **every request** — before *and* after the route handler.
It's used for concerns that apply globally (error handling, rate limiting,
logging, CORS) rather than to specific endpoints.

## Files

### `auth.py` — API Key Authentication Middleware (1.7KB)

Legacy API key authentication middleware. This was the **original auth system**
before Supabase JWT auth was added. It's still available as an alternative
authentication method for programmatic API access (server-to-server calls).

**How it differs from JWT auth:**
- **JWT auth** (`api/deps/auth.py`) — used by the frontend, verifies Supabase tokens
- **API key auth** (`middleware/auth.py`) — used for programmatic access, simpler but less secure

---

### `rate_limit.py` — Rate Limiting (1.6KB)

Prevents API abuse by limiting request frequency. This is a placeholder/stub
that can be connected to Redis for production use.

**How rate limiting works:**
```
Client sends request → Rate limiter checks counter
    ├── Under limit → Allow request, increment counter
    └── Over limit → Return 429 Too Many Requests
```

**Configuration:** Uses `REDIS_URL` from settings for distributed rate limiting across multiple server instances.

---

### `__init__.py` — Package Init

Makes the folder importable.

## How Middleware Is Registered

In `main.py`, middleware is added to the FastAPI app:

```python
app = FastAPI()

# CORS middleware — allows frontend (localhost:3000) to call backend (localhost:8000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,  # ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

> **Note:** The primary authentication is done via FastAPI's `Depends()` system
> (see `api/deps/auth.py`), not via middleware. This gives per-route control.
