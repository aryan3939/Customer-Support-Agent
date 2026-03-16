# 02 — Project Setup (Config, Logging, FastAPI Bootstrap)

How the application bootstraps itself — from loading environment variables
to starting the HTTP server.

---

## 2.1 Configuration Management (`src/config.py`)

### The Problem

Every application needs settings: database URLs, API keys, feature flags.
Hardcoding them is dangerous (secrets in source code) and inflexible
(can't change without redeploying).

### The Solution: Pydantic Settings

We use `pydantic-settings` to:
1. Read settings from `.env` file (or environment variables)
2. **Validate** them at startup (fail fast if something is missing)
3. Provide **typed access** with IDE autocomplete (no typos)
4. **Centralize** ALL configuration in one place

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str                              # REQUIRED — no default
    LLM_PROVIDER: Literal["google", "groq"] = "google"  # Optional with default
    LLM_TEMPERATURE: float = Field(default=0.3, ge=0.0, le=1.0)  # Validated range
```

### How It Works

```
.env file:    DATABASE_URL=postgresql+asyncpg://...
                    ↓
load_dotenv()      sets it in os.environ
                    ↓
Settings()         reads from os.environ, validates types
                    ↓
settings.DATABASE_URL → "postgresql+asyncpg://..."  (typed, validated)
```

### Why `load_dotenv()` Before Pydantic?

Pydantic Settings reads `.env` into its own fields, but does **not** set
`os.environ`. The LangChain/LangSmith SDK reads `LANGCHAIN_*` variables
directly from `os.environ`. Without `load_dotenv()`, LangSmith tracing
wouldn't work even though the values are in `.env`.

### Settings Categories

| Section | Variables | Purpose |
|---------|-----------|---------|
| Application | `APP_NAME`, `APP_ENV`, `DEBUG`, `LOG_LEVEL` | Basic app config |
| Database | `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_ANON_KEY` | PostgreSQL connection |
| LLM | `LLM_PROVIDER`, `GOOGLE_API_KEY`, `GROQ_API_KEY`, `LLM_MODEL`, `LLM_TEMPERATURE` | AI configuration |
| LangSmith | `LANGCHAIN_TRACING_V2`, `LANGCHAIN_API_KEY`, `LANGCHAIN_PROJECT` | Tracing & observability |
| Embeddings | `EMBEDDING_MODEL` | RAG model selection |
| Security | `JWT_SECRET`, `API_KEY_SALT`, `SUPABASE_JWT_SECRET` | Auth configuration |
| AI Behavior | `ENABLE_AUTO_RESOLUTION`, `MAX_AUTO_ATTEMPTS`, `ESCALATION_CONFIDENCE_THRESHOLD` | Agent behavior tuning |

---

## 2.2 Structured Logging (`src/utils/logging.py`)

### Why Not Just `print()` or Basic `logging`?

```python
# ❌ Unstructured — works for debugging, useless at scale
print(f"Created ticket {ticket_id} for {email}")

# ✅ Structured — machine-parsable, searchable, filterable
logger.info("ticket_created", ticket_id="abc-123", customer="user@example.com")
```

### How structlog Works

structlog produces **key-value log entries** instead of free-text messages:

**Development output (colored terminal):**
```
2026-02-18 15:30:00 [info] ticket_created  ticket_id=abc-123 customer=user@example.com priority=high
```

**Production output (JSON — for Datadog, ELK, CloudWatch):**
```json
{"event": "ticket_created", "ticket_id": "abc-123", "customer": "user@example.com", "priority": "high", "timestamp": "2026-02-18T15:30:00Z"}
```

### Configuration

The logging format switches based on `APP_ENV`:
- `development` → Colored console output with human-friendly formatting
- `production` → JSON output for log aggregation services

```python
# In any file:
from src.utils.logging import get_logger
logger = get_logger(__name__)  # Logger named after the module

logger.info("something_happened", key="value", count=42)
logger.error("something_failed", error=str(e), ticket_id=str(tid))
```

---

## 2.3 FastAPI Application (`src/main.py`)

### What Happens When You Run `uvicorn src.main:app --reload`

```
1. Python imports src/main.py
2. config.py runs → loads .env, validates settings (crashes if invalid)
3. logging.py runs → configures structlog
4. FastAPI app is created with title, description, version
5. CORS middleware is added (allows frontend at :3000 to call backend at :8000)
6. Routes are registered (tickets, admin, analytics, webhooks)
7. Lifespan context manager starts:
   a. Connects to PostgreSQL (creates connection pool)
   b. Loads sentence-transformers embedding model
   c. Yields (app starts serving requests)
8. On shutdown:
   a. Closes database connections
   b. Flushes logs
```

### The Lifespan Pattern

FastAPI's modern way to handle startup/shutdown (replaces the deprecated
`@app.on_event("startup")` pattern):

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── STARTUP ──
    await init_db()                     # Connect to database
    embedding_service.load_model()      # Load AI model

    yield  # ← App runs here

    # ── SHUTDOWN ──
    await close_db()                    # Close connections
```

**Why a context manager?** Guarantees cleanup runs even if the app crashes.

### CORS Middleware

CORS (Cross-Origin Resource Sharing) is required because the frontend
(`localhost:3000`) needs to make API calls to the backend (`localhost:8000`).
Browsers block cross-origin requests by default for security.

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # Allow all origins in development
    allow_credentials=True,       # Allow cookies/auth headers
    allow_methods=["*"],          # Allow GET, POST, PATCH, DELETE, etc.
    allow_headers=["*"],          # Allow Authorization, Content-Type, etc.
)
```

### Route Registration

Routes are defined in separate files and connected to the app:

```python
from src.api.routes.tickets import router as tickets_router
from src.api.routes.admin import router as admin_router
from src.api.routes.analytics import router as analytics_router
from src.api.routes.webhooks import router as webhooks_router

app.include_router(tickets_router)    # /api/v1/tickets/*
app.include_router(admin_router)      # /api/v1/admin/*
app.include_router(analytics_router)  # /api/v1/analytics/*
app.include_router(webhooks_router)   # /api/v1/webhooks/*
```
