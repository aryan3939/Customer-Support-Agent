# Phase 1B: Project Setup Code

## Why This Step?

In the previous step we installed tools and configured secrets. Now we write the **first actual Python code** — the skeleton that everything else will be built on.

Think of it like building a house:
- Phase 1A (Environment) = Laying the foundation, connecting water and electricity
- **Phase 1B (This step)** = Building the frame — walls, roof structure, front door
- Phase 2+ = Furnishing the rooms (AI agent logic, tools, etc.)

We create three critical files:
1. **`config.py`** — How the app reads its settings
2. **`logging.py`** — How the app reports what it's doing
3. **`main.py`** — The front door (HTTP server)

Without these three, nothing else can work.

---

## Files Created

```
src/
├── __init__.py         ← Makes 'src' a Python package
├── config.py           ← Settings management
├── main.py             ← FastAPI application entry point
└── utils/
    ├── __init__.py     ← Makes 'utils' a Python package
    └── logging.py      ← Structured logging setup
```

---

## File-by-File Breakdown

### `src/config.py` — Settings Management

#### Why It Exists

Every application needs configuration: database URLs, API keys, feature flags. There are three ways to handle this, from worst to best:

```python
# ❌ BAD: Hardcoded secrets
database_url = "postgresql://admin:superSecretPassword@prod-server/db"

# ⚠️ OKAY: Environment variables (no validation)
import os
database_url = os.getenv("DATABASE_URL")  # Could be None — crashes later!

# ✅ BEST: Pydantic Settings (validated, typed, documented)
from src.config import settings
settings.DATABASE_URL  # Guaranteed to exist, correct type, validated
```

#### How It Works

Pydantic Settings automatically reads environment variables and validates them:

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",        # ← Read from this file
        case_sensitive=False,   # ← DATABASE_URL = database_url
        extra="ignore",         # ← Unknown vars in .env won't cause errors
    )
    
    DATABASE_URL: str           # REQUIRED — no default, must be in .env
    DEBUG: bool = True          # OPTIONAL — has a default value
    LLM_TEMPERATURE: float = Field(default=0.3, ge=0.0, le=1.0)  # Validated range
```

What happens at startup:
```
.env file → Pydantic reads it → Validates every field → Creates Settings object
                                    ↓ (if validation fails)
                              Crashes IMMEDIATELY with clear error:
                              "DATABASE_URL: field required"
```

This is called **"fail fast"** — better to crash at startup with a clear message than crash 10 minutes later with a confusing database error.

#### Key Design Decisions

**`Literal` types for constrained values:**
```python
APP_ENV: Literal["development", "staging", "production"] = "development"
LLM_PROVIDER: Literal["google", "groq"] = "google"
```
If someone sets `APP_ENV=invalid`, Pydantic rejects it immediately.

**`Field` for numeric constraints:**
```python
LLM_TEMPERATURE: float = Field(default=0.3, ge=0.0, le=1.0)
```
`ge=0.0` means "greater than or equal to 0", `le=1.0` means "less than or equal to 1". Prevents invalid temperatures.

**`get_settings()` function:**
```python
def get_settings() -> Settings:
    return Settings()
```
Why a function instead of just a global `settings`? Because in tests, we can override it:
```python
# In tests:
app.dependency_overrides[get_settings] = lambda: Settings(DEBUG=False)
```

**Module-level `settings` instance:**
```python
settings = get_settings()  # Runs on first import
```
For non-test code, this gives us a global singleton. If `.env` is missing required fields, the app crashes at import time — the earliest possible moment.

---

### `src/utils/logging.py` — Structured Logging

#### Why It Exists

**Standard Python logging:**
```
2025-02-10 05:00:00,000 INFO ticket created for user@example.com
```
This is just a string. To find all logs for ticket `abc-123`, you'd need regex.

**Structured logging (what we use):**
```json
{"timestamp": "2025-02-10T05:00:00", "level": "info", "event": "ticket_created", 
 "email": "user@example.com", "ticket_id": "abc-123"}
```
This is machine-readable JSON. Finding ticket `abc-123` = one database query.

#### How It Works

We use `structlog`, which wraps Python's standard `logging` with a processing pipeline:

```python
logger.info("ticket_created", email="user@example.com", ticket_id="abc-123")
```

This goes through a pipeline:
```
[Your log call]
    ↓
[add_log_level]     → Adds "level": "info"
[add_logger_name]   → Adds "logger": "src.main"
[TimeStamper]       → Adds "timestamp": "2025-02-10T05:00:00Z"
    ↓
[ConsoleRenderer]   → Pretty colored output (development)
   or
[JSONRenderer]      → JSON output (production)
```

#### Two Output Modes

**Development** (`json_format=False`):
```
2025-02-10 05:00:00 [info     ] ticket_created    email=user@example.com ticket_id=abc-123
```
Human-readable, colored in the terminal. Easy to scan visually.

**Production** (`json_format=True`):
```json
{"timestamp": "2025-02-10T05:00:00Z", "level": "info", "event": "ticket_created", "email": "user@example.com", "ticket_id": "abc-123"}
```
Machine-readable, one JSON object per line. Parsed by log aggregators (CloudWatch, Grafana, ELK).

#### Silencing Noisy Loggers
```python
logging.getLogger("uvicorn").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
```
Without this, uvicorn logs every single HTTP request, flooding our logs with noise. We only want to see warnings and errors from third-party libraries.

---

### `src/main.py` — FastAPI Application

#### Why It Exists

This is the **front door** of our application. Every HTTP request enters through here. It:
1. Starts the server
2. Routes requests to the right handler
3. Returns responses

#### The Lifespan Pattern

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP code — runs once when server starts
    logger.info("application_starting")
    # Connect to database, load models, etc.
    
    yield  # ← Server runs here, handling requests
    
    # SHUTDOWN code — runs once when server stops
    logger.info("application_stopped")
    # Close connections, flush caches, etc.
```

**Why `asynccontextmanager`?** It's FastAPI's modern pattern for startup/shutdown. The old way (`@app.on_event("startup")`) is deprecated. This guarantees cleanup runs even if the app crashes.

**What's `yield`?** It's a Python generator concept:
- Code before `yield` = startup
- `yield` itself = "pause here, let the app run"
- Code after `yield` = shutdown (guaranteed to execute)

#### FastAPI App Creation

```python
app = FastAPI(
    title=settings.APP_NAME,               # Shows in Swagger UI
    description="AI-powered customer...",   # Shows in Swagger UI
    version="0.1.0",                        # API version
    lifespan=lifespan,                      # Our startup/shutdown handler
    docs_url="/docs",                       # Swagger UI endpoint 
)
```

`docs_url="/docs"` gives us a **free interactive API documentation** page. Visit `http://localhost:8000/docs` to try out endpoints directly in the browser.

#### CORS Middleware

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.is_development else [],
    ...
)
```

**What is CORS?** Cross-Origin Resource Sharing. If your frontend runs on `localhost:3000` and your API on `localhost:8000`, the browser blocks requests between them by default (security). CORS middleware tells the browser "it's okay, allow it."

**Why `["*"]` in development?** Allow any frontend to connect during development. In production, you'd restrict this to your actual frontend domain.

#### Health Check Endpoint

```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": {
            "database": "not_configured",
            "redis": "not_configured",
        },
    }
```

**Why `health_check`?** Every production app needs one:
- **Load balancers** (AWS ALB, nginx) use it to check if a server is alive
- **Docker** uses it in `healthcheck` to restart crashed containers
- **Monitoring tools** alert you when it fails
- **You** can quickly verify the API is running

The `timestamp` field proves the response is live (not cached). The `checks` object will later report real database/Redis status.

---

## How They Connect

```
uvicorn src.main:app --reload
    │
    ├── 1. Python imports src.main
    │       └── Imports src.config → reads .env → creates Settings
    │       └── Imports src.utils.logging → (module is ready)
    │
    ├── 2. main.py runs setup_logging() → configures structlog
    │
    ├── 3. main.py creates app = FastAPI(lifespan=lifespan)
    │
    ├── 4. uvicorn starts the server
    │       └── Calls lifespan() STARTUP section
    │       └── Logs "application_started"
    │
    └── 5. Server is ready! Handles requests:
            GET /       → root()        → {"name": "...", "status": "running"}
            GET /health → health_check() → {"status": "healthy", ...}
            GET /docs   → Swagger UI     → Interactive API documentation
```

---

## Supabase Change

We switched from local Docker PostgreSQL to **Supabase** (cloud-hosted):

| Before | After |
|--------|-------|
| PostgreSQL in Docker | Supabase (cloud, free 500MB) |
| `docker-compose` had postgres + redis | `docker-compose` has Redis only |
| Connection: `localhost:5432` | Connection: Supabase URL |

**Why Supabase?**
- pgvector is **built-in** (no extension setup needed)
- Free tier: 500MB database, 1GB storage
- No Docker needed for the database
- Web dashboard to inspect data visually
- Automatic backups

---

## How to Test

```bash
# 1. Make sure .env exists with DATABASE_URL
copy .env.example .env
# Edit .env with your actual values

# 2. Activate venv
.venv\Scripts\activate

# 3. Run the server
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# 4. Visit in browser:
#    http://localhost:8000         → API root
#    http://localhost:8000/health  → Health check
#    http://localhost:8000/docs    → Swagger UI
```

---

## What's Next?

With the skeleton running, Phase 1 continues with:
1. **Database models** (`src/db/models.py`) — SQLAlchemy models for tickets, customers, etc.
2. **Alembic migrations** — Version-controlled database schema
3. **Database session** (`src/db/session.py`) — Connection pooling
