# 🏗️ Complete Engineering Guide — Building an AI Customer Support Agent from Scratch

> **Target audience:** You're an engineer who wants to build this entire project from
> zero. This guide explains every decision, every file, every line of reasoning.
> After reading this, you'll understand the project deeply enough to explain it
> in an interview, teach it to someone else, or build something similar on your own.

> **Length warning:** This is a 10,000+ line deep-dive. It's not a tutorial you
> skim — it's a reference you study. Use the table of contents to jump to sections.

---

## Table of Contents

- [Part 1: Engineering Mindset & Project Planning](#part-1-engineering-mindset--project-planning)
- [Part 2: Project Foundation](#part-2-project-foundation)
- [Part 3: Database Layer](#part-3-database-layer)
- [Part 4: AI Agent Core — The LangGraph Pipeline](#part-4-ai-agent-core--the-langgraph-pipeline)
- [Part 5: RAG & Knowledge Base](#part-5-rag--knowledge-base)
- [Part 6: FastAPI REST API Layer](#part-6-fastapi-rest-api-layer)
- [Part 7: Authentication & Authorization](#part-7-authentication--authorization)
- [Part 8: Frontend — Next.js 15](#part-8-frontend--nextjs-15)
- [Part 9: Integration, Testing & Deployment](#part-9-integration-testing--deployment)
- [Part 10: Lessons Learned & How to Think About Similar Projects](#part-10-lessons-learned--how-to-think-about-similar-projects)

---

# Part 1: Engineering Mindset & Project Planning

## 1.1 How to Think About This Project

Before writing a single line of code, an experienced engineer asks three questions:

1. **What problem am I solving?**
2. **What are the moving parts?**
3. **What's the simplest architecture that handles them?**

### The Problem

Customer support is expensive. A medium-sized company might receive 500 tickets/day.
Each ticket requires a human to:
- Read and understand the issue
- Search internal documentation for the answer
- Write a personalized response
- Decide whether to escalate

An AI agent can handle 80% of these tickets autonomously — the routine questions
that have clear answers in the knowledge base. The remaining 20% (complex issues,
angry customers, edge cases) still go to humans.

### Why This is a Good Engineering Project

This project touches almost every concept a production engineer needs:

| Concept | Where It Appears |
|---------|-----------------|
| State machines | LangGraph agent workflow |
| RAG (Retrieval-Augmented Generation) | Knowledge base search with pgvector |
| REST API design | FastAPI with Pydantic validation |
| Database modeling | SQLAlchemy ORM with PostgreSQL |
| Authentication | JWT verification with Supabase Auth |
| Role-based access control | Customer vs Admin permissions |
| Structured logging | structlog with JSON output |
| Async programming | asyncio throughout the backend |
| Frontend SPA | Next.js 15 with React hooks |
| Vector similarity search | sentence-transformers + pgvector |
| Configuration management | Pydantic Settings + .env files |
| Repository pattern | Clean separation of DB queries |
| Error handling | Graceful fallbacks at every layer |
| Audit trails | Complete action logging for AI decisions |

### The Moving Parts

Before writing code, sketch out the system on paper:

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND                             │
│   Next.js 15 → Login, Dashboard, Ticket Detail, Admin      │
│   Talks to backend via REST API                             │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP (JWT in Authorization header)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                     BACKEND (FastAPI)                        │
│                                                             │
│   ┌─────────┐  ┌──────────┐  ┌──────────┐  ┌───────────┐  │
│   │ Auth    │  │ Ticket   │  │ Admin    │  │ Health    │  │
│   │ Middleware│ │ Routes   │  │ Routes   │  │ Routes    │  │
│   └────┬────┘  └────┬─────┘  └────┬─────┘  └───────────┘  │
│        │            │              │                        │
│        ▼            ▼              ▼                        │
│   ┌──────────────────────────────────────────┐             │
│   │            AI AGENT (LangGraph)          │             │
│   │  classify → search_kb → resolve →        │             │
│   │  validate → respond (or escalate)        │             │
│   └──────────────────┬───────────────────────┘             │
│                      │                                      │
│   ┌──────────────────▼───────────────────────┐             │
│   │         DATABASE LAYER (SQLAlchemy)       │             │
│   │  Models → Repositories → Sessions        │             │
│   └──────────────────┬───────────────────────┘             │
└──────────────────────┼──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              SUPABASE (PostgreSQL + Auth)                    │
│   • Database with pgvector extension                        │
│   • JWT authentication                                      │
│   • Connection pooling via Supavisor (port 6543)           │
└─────────────────────────────────────────────────────────────┘
```

## 1.2 Technology Stack Selection

Every technology choice should have a *reason*. Here's why each was chosen:

### Backend Framework: FastAPI

**Why FastAPI over Flask or Django?**

| Feature | Flask | Django | FastAPI |
|---------|-------|--------|---------|
| Async support | No (needs ASGI plugin) | Partial | Native |
| Auto API docs | No | Via DRF | Yes (Swagger + ReDoc) |
| Type checking | No | No | Yes (Pydantic) |
| Performance | Moderate | Moderate | High (Starlette) |
| Learning curve | Low | High | Low-Medium |
| Dependency injection | No | Partial | First-class |

**The deciding factor:** We're calling LLM APIs (1-5 second response times). In Flask,
each request blocks a thread while waiting. In FastAPI, the thread is freed to handle
other requests while waiting. With 50 concurrent users, Flask needs 50 threads;
FastAPI needs 1 event loop.

**Engineering principle:** Always pick async-native frameworks when your workload is I/O-bound.

### AI Framework: LangGraph (not raw LangChain)

**Why not just call the LLM API directly?**

```python
# Raw approach — works for simple cases
response = openai.chat.completions.create(messages=[...])

# Problem: No workflow control, no retries, no conditional routing,
# no state management, no observability
```

**Why LangGraph over LangChain?**

LangChain is a library for calling LLMs. LangGraph is a framework for building
*workflows* with LLMs. Our agent needs:

- Sequential steps (classify → search → respond)
- Conditional routing (escalate if urgent+angry)
- Retry logic (retry resolution up to 3 times)
- State that flows through the pipeline

LangGraph models this as a **directed graph** (state machine):
- **Nodes** = functions that do work
- **Edges** = connections between functions
- **State** = data that flows through the graph
- **Conditional edges** = if/else routing

This is fundamentally different from a simple chain:

```python
# LangChain chain (linear, no branching):
chain = prompt | llm | parser  # Always goes A → B → C

# LangGraph (graph with branching):
# classify → escalate (if urgent+angry)
# classify → search_kb → resolve → validate → respond (normal path)
# validate → resolve (retry if validation fails)
# validate → escalate (if 3 retries fail)
```

**Engineering principle:** When your workflow has branching logic, model it as a
graph, not a chain. This is the same principle behind finite state machines,
which are fundamental to systems design.

### Database: Supabase (PostgreSQL)

**Why not MongoDB?**

Our data is *relational*. Tickets belong to customers. Messages belong to tickets.
Actions belong to tickets and agents. These are relationships — exactly what SQL
databases are designed for.

MongoDB would force us to denormalize (duplicate data) or do application-level joins.
PostgreSQL handles this natively with foreign keys and JOINs.

**Why Supabase specifically?**

1. **Free PostgreSQL hosting** — no credit card needed
2. **Built-in Auth** — JWT issuance, user management, email verification
3. **pgvector extension** — vector similarity search in the same database
4. **Connection pooling** — PgBouncer/Supavisor built-in (port 6543)
5. **Dashboard** — SQL editor, table viewer, auth management in the browser

**Engineering principle:** Choose hosted databases for learning projects. Self-hosting
PostgreSQL requires managing backups, security patches, connection limits.
Supabase handles all of that.

### Embeddings: sentence-transformers (local, free)

**Why not OpenAI embeddings?**

| Feature | OpenAI ada-002 | sentence-transformers |
|---------|---------------|----------------------|
| Cost | $0.0001/1K tokens | Free (runs locally) |
| Requires internet | Yes | No (after first download) |
| Speed | ~100ms (API call) | ~5ms (local inference) |
| Dimensions | 1536 | 384 |
| Quality | Excellent | Good (sufficient for KB search) |

For a learning project, running embeddings locally means:
- No API key needed
- No cost
- No internet dependency
- Faster development iteration

**Engineering principle:** Use the simplest tool that satisfies your requirements.
384-dim vectors are more than enough for finding "which KB article matches this query."

### Frontend: Next.js 15

**Why not plain React (Vite)?**

- Next.js provides server-side rendering, routing, and API routes out of the box
- The App Router (Next.js 13+) is the modern standard
- Server components reduce client-side JavaScript
- Built-in environment variable handling for Supabase keys

**Why not a separate frontend at all?**

You could build this as a pure API with Postman testing. But a frontend:
- Proves the API actually works end-to-end
- Shows you understand full-stack development
- Demonstrates auth flow (login → JWT → API calls)
- Makes the project presentable in interviews

## 1.3 Build Sequence — What to Code First

This is the most important section for an engineer building from scratch.
You can't build everything at once — you need to build in *layers*.

**The golden rule:** Build from the bottom up. Each layer should be testable
before you build the next one on top.

```
Week 1: Foundation
├── Day 1: Project setup, config, logging
├── Day 2: Database models
├── Day 3: Database session + repositories
└── Day 4: Test DB with a simple script

Week 2: AI Agent
├── Day 5: LangGraph state + LLM factory
├── Day 6: Classifier node
├── Day 7: KB search tool (keyword fallback)
├── Day 8: Resolver + Validator + Escalator nodes
└── Day 9: Wire up the graph, test standalone

Week 3: API Layer
├── Day 10: FastAPI main.py + health check
├── Day 11: Auth middleware (JWT verification)
├── Day 12: Ticket routes (create, list, get)
├── Day 13: Follow-up message routes + resolve
└── Day 14: Admin routes

Week 4: Frontend + RAG
├── Day 15: Next.js setup + Supabase client
├── Day 16: Login page + auth hook
├── Day 17: Dashboard + ticket creation
├── Day 18: Ticket detail + chat view
├── Day 19: Admin panel
├── Day 20: RAG (embeddings + pgvector search)
└── Day 21: KB seeding script + final testing
```

**Why this order?**

1. **Config + Logging first** — every other file imports these. If they break,
   everything breaks. Build them once, correctly.

2. **Database models before agent** — the agent needs to know what data it's
   working with. Models define the schema.

3. **Agent before API** — you want to test the AI pipeline in isolation
   (with a simple script) before wrapping it in HTTP endpoints.

4. **API before frontend** — test every endpoint with Swagger UI before
   building a frontend that calls them.

5. **RAG last** — the agent works with keyword fallback. RAG is an optimization,
   not a requirement. Ship first, optimize later.

---

# Part 2: Project Foundation

## 2.1 Directory Structure — Why This Layout?

Before writing code, create the folder structure. This isn't arbitrary — it
reflects the *layers* of the application:

```
Customer Support Agent/
├── src/                          # All backend source code
│   ├── __init__.py               # Makes src a Python package
│   ├── config.py                 # Configuration management
│   ├── main.py                   # FastAPI application entry point
│   │
│   ├── agents/                   # AI agent (LangGraph pipeline)
│   │   ├── __init__.py
│   │   ├── graph.py              # Graph definition + process_ticket()
│   │   ├── state.py              # TicketState TypedDict
│   │   ├── models.py             # Pydantic models for structured LLM output
│   │   ├── llm.py                # LLM factory (Google/Groq)
│   │   ├── nodes/                # Graph nodes (functions)
│   │   │   ├── classifier.py     # Classify intent, priority, sentiment
│   │   │   ├── resolver.py       # Generate AI response
│   │   │   ├── validator.py      # Quality-check the response
│   │   │   └── escalator.py      # Prepare handoff to human
│   │   └── edges/                # Conditional routing
│   │       └── conditions.py     # Escalation rules
│   │
│   ├── api/                      # HTTP layer (FastAPI routes)
│   │   ├── routes/               # Route handlers
│   │   │   ├── tickets.py        # Customer ticket CRUD
│   │   │   └── admin.py          # Admin panel endpoints
│   │   ├── schemas/              # Pydantic request/response models
│   │   │   └── ticket.py         # All ticket-related schemas
│   │   ├── deps/                 # Dependencies (auth)
│   │   │   └── auth.py           # JWT verification + role checking
│   │   └── middleware/           # Request/response middleware
│   │
│   ├── db/                       # Database layer
│   │   ├── models.py             # SQLAlchemy ORM models
│   │   ├── session.py            # Engine, session factory, init/close
│   │   └── repositories/         # Database query functions
│   │       ├── ticket_repo.py    # Ticket CRUD queries
│   │       └── customer_repo.py  # Customer lookup/creation
│   │
│   ├── services/                 # Business logic services
│   │   └── embedding_service.py  # Sentence-transformer singleton
│   │
│   ├── tools/                    # LangGraph tools
│   │   └── knowledge_base.py     # KB search (pgvector + keyword fallback)
│   │
│   └── utils/                    # Shared utilities
│       ├── logging.py            # Structured logging setup
│       └── metrics.py            # Simple request metrics
│
├── frontend/                     # Next.js 15 application
├── scripts/                      # Utility scripts (seed_kb.py)
├── tests/                        # Test suite
├── alembic/                      # Database migrations
├── docs/                         # Documentation
├── .env                          # Environment variables (not in git)
├── .env.example                  # Template for .env
├── requirements.txt              # Python dependencies
└── README.md                     # Project overview
```

**Why this matters:**

- **Separation of concerns** — each folder has one responsibility
- **Import clarity** — `from src.db.models import Ticket` tells you exactly where it lives
- **Testability** — you can test `src/agents/` without starting the web server
- **Scalability** — adding a new feature means adding files, not modifying existing ones

**Engineering principle:** Your directory structure IS your architecture.
If someone new looks at your folders, they should understand the system's
layers without reading any code.

## 2.2 File 1: `requirements.txt` — Understanding Every Dependency

The first file you create. Every dependency should have a reason.

```txt
# === Core Web Framework ===
fastapi>=0.115.0          # Web framework — async, type-safe, auto-docs
uvicorn[standard]>=0.32.0 # ASGI server — runs FastAPI in production

# === LangChain + LangGraph ===
langgraph>=0.2.0            # State machine framework for AI workflows
langchain>=0.3.0            # Base LLM abstractions (messages, prompts)
langchain-groq>=0.2.0       # Groq LLM provider (Llama, Mixtral)
langchain-google-genai>=2.0 # Google AI Studio (Gemini models)
langsmith>=0.1.0            # Tracing & observability for LangChain

# === Database ===
sqlalchemy>=2.0.0          # ORM — maps Python classes to DB tables
asyncpg>=0.30.0            # Async PostgreSQL driver
alembic>=1.14.0            # Database migration manager
pgvector>=0.3.0            # pgvector support for SQLAlchemy

# === Data Validation & Config ===
pydantic>=2.0.0            # Data validation with Python type hints
pydantic-settings>=2.0.0   # Read config from .env files
python-dotenv>=1.0.0       # Load .env file into os.environ
email-validator>=2.0.0     # EmailStr validation for Pydantic

# === HTTP & Async ===
httpx>=0.28.0              # Async HTTP client (for external API calls)
tenacity>=9.0.0            # Retry decorator with exponential backoff

# === Logging ===
structlog>=24.0.0          # Structured logging (JSON output in production)

# === Embeddings (runs locally) ===
sentence-transformers>=3.0.0  # Local embedding model for RAG

# === Security (Auth) ===
PyJWT[crypto]>=2.0.0       # JWT decode/verify with ES256, EdDSA support

# === Development ===
pytest>=8.0.0              # Test runner
pytest-asyncio>=0.24.0     # Async test support
ruff>=0.8.0                # Fast Python linter
```

**Why `PyJWT[crypto]` and not just `PyJWT`?**

PyJWT without `[crypto]` only supports HS256 (symmetric). Supabase uses ES256
(asymmetric/ECC), which requires the `cryptography` package. The `[crypto]`
extra installs it automatically.

**Why `asyncpg` and not `psycopg2`?**

`psycopg2` is synchronous — it blocks the event loop. `asyncpg` is fully async,
which is required for our FastAPI setup. One blocked database query in psycopg2
would freeze the entire server for all users.

**Why `pgvector` (the Python package)?**

This adds the `Vector` column type to SQLAlchemy so we can define:
```python
embedding = mapped_column(Vector(384))  # 384-dim vector column
```

Without the package, SQLAlchemy doesn't know what a `vector` column is.

## 2.3 File 2: `src/config.py` — Centralized Configuration

**Why a config file?**

Without it, you'd scatter `os.getenv("DATABASE_URL")` across 20 files.
If you rename an environment variable, you'd need to find-and-replace everywhere.

With a config file:
- All settings are in ONE place
- Type validation at startup (not at runtime)
- Default values documented
- IDE autocomplete works

**The engineering approach:**

```python
"""
src/config.py — Centralized configuration using Pydantic Settings.

HOW IT WORKS:
    1. Pydantic Settings reads from .env file automatically
    2. Each field has a type annotation and optional default
    3. If a REQUIRED field is missing, the app CRASHES at startup
       (which is what you want — fail fast, fail loud)

WHY PYDANTIC SETTINGS:
    - Type coercion: "5" → int(5), "true" → bool(True)
    - Validation: DATABASE_URL must be a valid string
    - Documentation: Each field is self-documenting
    - IDE support: settings.DATABASE_URL with autocomplete

ALTERNATIVE APPROACH (and why it's worse):
    # Bad: scattered os.getenv calls
    db_url = os.getenv("DATABASE_URL")  # What if it's None?
    pool_size = int(os.getenv("POOL_SIZE", "5"))  # Manual int conversion
    
    # Good: centralized, typed, validated
    settings.DATABASE_URL  # Guaranteed to be a string
    settings.POOL_SIZE     # Guaranteed to be an int
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Tell Pydantic where to find the .env file
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,    # DATABASE_URL == database_url
    )
    
    # === Application ===
    APP_NAME: str = "Customer Support Agent"
    APP_ENV: str = "development"        # development | staging | production
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"            # DEBUG | INFO | WARNING | ERROR
    
    # === Database ===
    DATABASE_URL: str = ""              # PostgreSQL connection string
    
    # === Supabase ===
    SUPABASE_URL: str = ""              # https://xxx.supabase.co
    SUPABASE_ANON_KEY: str = ""         # Public anon key
    SUPABASE_JWT_SECRET: str = ""       # For HS256 fallback
    
    # === LLM Configuration ===
    LLM_PROVIDER: str = "google"        # google | groq
    GOOGLE_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    LLM_MODEL: str = "gemini-2.0-flash"
    LLM_TEMPERATURE: float = 0.3       # Lower = more deterministic
    
    # === Embeddings ===
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    
    # === LangSmith (optional) ===
    LANGCHAIN_TRACING_V2: bool = False
    LANGCHAIN_API_KEY: str = ""
    LANGCHAIN_PROJECT: str = "customer-support-agent"
    
    # === AI Behavior ===
    ENABLE_AUTO_RESOLUTION: bool = True
    MAX_AUTO_ATTEMPTS: int = 3
    ESCALATION_CONFIDENCE_THRESHOLD: float = 0.7


# Singleton instance — import this everywhere
settings = Settings()
```

**Key design decisions:**

1. **`model_config` with `env_file=".env"`** — Pydantic automatically reads from
   the .env file. No need to call `load_dotenv()` manually.

2. **Default values for everything** — The app starts even with an empty .env
   (useful for running tests without a database).

3. **`case_sensitive=False`** — `DATABASE_URL` and `database_url` both work.
   This prevents frustrating debugging when someone uses the wrong case.

4. **`LLM_TEMPERATURE: float = 0.3`** — Low temperature = more consistent output.
   For classification (where you want the same result every time), you want 0.0-0.3.
   For creative writing, you'd use 0.7-1.0.

5. **`ESCALATION_CONFIDENCE_THRESHOLD: float = 0.7`** — If the AI is less than
   70% confident in its classification, escalate instead of risking a bad response.
   This is a business decision encoded as a config parameter.

**Why a singleton (`settings = Settings()`) at module level?**

Python modules are imported once and cached. So `settings = Settings()` runs once,
at import time, and every file that does `from src.config import settings` gets the
same instance. No dependency injection needed.

## 2.4 File 3: `src/utils/logging.py` — Structured Logging

**Why not just `print()`?**

```python
# Bad: print statements
print(f"Ticket created: {ticket_id}")  # No timestamp, no level, no context
print(f"Error: {e}")                   # Which ticket? Which user? Which node?

# Good: structured logging
logger.info("ticket_created", ticket_id="abc-123", email="user@example.com")
# Output: {"timestamp": "2025-02-10T05:00:00", "level": "info",
#          "event": "ticket_created", "ticket_id": "abc-123", ...}
```

Benefits:
1. **Searchable** — `grep "ticket_id=abc-123"` finds everything about one ticket
2. **Filterable** — show only errors in production
3. **Parseable** — log aggregation tools (Grafana, CloudWatch) understand JSON
4. **Contextual** — each log entry carries structured metadata

**The implementation:**

```python
"""
src/utils/logging.py — Structured logging with structlog.

PROCESSOR PIPELINE:
    logger.info("ticket_created", email="user@example.com")
        ↓
    [Add timestamp] → [Add log level] → [Add logger name]
        ↓
    [Format exceptions] → [Render as JSON or colored text]
        ↓
    {timestamp: "...", level: "info", event: "ticket_created", email: "..."}
"""

import logging
import sys
from typing import Literal

import structlog


def setup_logging(
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO",
    json_format: bool = False,
) -> None:
    """
    Configure structured logging for the entire application.
    Call ONCE at application startup (in main.py).
    
    After this, any module can use:
        import structlog
        logger = structlog.get_logger()
        logger.info("something_happened", key="value")
    """
    
    # Shared processors — run on EVERY log message
    shared_processors = [
        structlog.stdlib.add_log_level,        # Adds "level": "info"
        structlog.stdlib.add_logger_name,       # Adds "logger": "src.agents.graph"
        structlog.processors.format_exc_info,   # Pretty-prints stack traces
        structlog.processors.TimeStamper(fmt="iso"),  # Adds ISO 8601 timestamp
        structlog.stdlib.ExtraAdder(),          # Passes through extra kwargs
    ]
    
    # Choose output format
    if json_format:
        # Production: machine-readable JSON
        renderer = structlog.processors.JSONRenderer()
    else:
        # Development: colored human-readable output
        renderer = structlog.dev.ConsoleRenderer(colors=True)
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,  # Respect log level
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,        # Performance optimization
    )
    
    # Configure standard library logging (catches third-party logs)
    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)
    
    # Quiet down noisy third-party loggers
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def get_logger(name: str | None = None):
    """Get a structured logger. Usage: logger = get_logger(__name__)"""
    return structlog.get_logger(name)
```

**Why `cache_logger_on_first_use=True`?**

Without caching, structlog creates a new logger object for every log call.
With caching, it creates one per module and reuses it. In a system processing
hundreds of requests per second, this matters.

**Why suppress `uvicorn.access` logs?**

Uvicorn logs every HTTP request (GET /api/v1/tickets 200). In development,
this floods the console and makes it hard to see your own logs. In production,
you'd use a reverse proxy (Nginx) for access logging instead.

## 2.5 File 4: `src/utils/metrics.py` — Simple Metrics

**Why track metrics?**

When the CEO asks "How's the AI agent performing?", you need numbers:
- How many tickets did the agent process?
- What's the average processing time?
- How many were escalated?

In production, you'd use Prometheus or Datadog. For a learning project,
a simple in-memory tracker demonstrates the concept:

```python
"""
src/utils/metrics.py — Simple in-memory metrics tracking.

WHAT WE TRACK:
    - Counters: ticket_created, ticket_escalated, agent_error
    - Latencies: agent_processing, kb_search, llm_call
"""

import time
from collections import defaultdict
from contextlib import asynccontextmanager

from src.utils.logging import get_logger

logger = get_logger(__name__)

# In-memory storage (resets on server restart)
_counters: dict[str, int] = defaultdict(int)
_latencies: dict[str, list[float]] = defaultdict(list)


def increment(metric_name: str, value: int = 1) -> None:
    """Increment a counter. Example: increment("tickets_created")"""
    _counters[metric_name] += value


@asynccontextmanager
async def track_latency(operation_name: str):
    """
    Context manager to track operation latency.
    
    Usage:
        async with track_latency("agent_processing"):
            result = await process_ticket(...)
        # Automatically logs: operation_latency op=agent_processing latency=2.3s
    """
    start = time.time()
    try:
        yield
    finally:
        elapsed = time.time() - start
        _latencies[operation_name].append(elapsed)
        logger.debug(
            "operation_latency",
            operation=operation_name,
            latency_seconds=round(elapsed, 3),
        )


def get_metrics() -> dict:
    """Return all collected metrics (for the /health endpoint)."""
    latency_stats = {}
    for op, times in _latencies.items():
        if times:
            latency_stats[op] = {
                "count": len(times),
                "avg_seconds": round(sum(times) / len(times), 3),
                "min_seconds": round(min(times), 3),
                "max_seconds": round(max(times), 3),
            }
    return {"counters": dict(_counters), "latencies": latency_stats}
```

**Key concept: Context Managers for Timing**

```python
# Without context manager (error-prone):
start = time.time()
result = await process_ticket(...)
elapsed = time.time() - start  # What if process_ticket raises an exception?

# With context manager (always works):
async with track_latency("agent_processing"):
    result = await process_ticket(...)
# elapsed is recorded even if an exception occurs (finally block)
```

---

## 2.6 File 5: `src/main.py` — The Application Entry Point

**Why is this the last foundation file?**

Because it imports from every other foundation file: config, logging, session, routes.
You can't write it until those exist.

```python
"""
src/main.py — FastAPI application entry point.

THIS FILE DOES 4 THINGS:
    1. Configure logging (FIRST — before any other imports log anything)
    2. Create the FastAPI app with metadata
    3. Manage lifecycle (startup: init DB + load model, shutdown: close DB)
    4. Register routes and middleware

RUN WITH:
    uvicorn src.main:app --reload
"""

import structlog
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.utils.logging import setup_logging, get_logger


# === Step 1: Configure logging FIRST ===
# This MUST happen before any other module creates a logger
setup_logging(
    log_level=settings.LOG_LEVEL,
    json_format=(settings.APP_ENV == "production"),
)

logger = get_logger(__name__)


# === Step 2: Application lifespan (startup/shutdown) ===
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle events.
    
    STARTUP:
        1. Initialize database connection pool
        2. Load the embedding model into memory
    
    SHUTDOWN:
        1. Close all database connections
    """
    logger.info(
        "application_starting",
        app=settings.APP_NAME,
        env=settings.APP_ENV,
    )
    
    # --- Startup ---
    from src.db.session import init_db, close_db
    from src.services.embedding_service import embedding_service
    
    await init_db()                    # Test DB + create tables
    embedding_service.load_model()     # Load sentence-transformer (~90MB)
    
    logger.info(
        "application_started",
        message="All systems ready ✓",
        embedding_dim=embedding_service.get_dimension(),
    )
    
    yield  # Application runs here
    
    # --- Shutdown ---
    await close_db()
    logger.info("application_stopped")


# === Step 3: Create the FastAPI app ===
app = FastAPI(
    title=settings.APP_NAME,
    description="AI-powered customer support agent with LangGraph",
    version="1.0.0",
    lifespan=lifespan,
)


# === Step 4: CORS middleware ===
# Required for the Next.js frontend (localhost:3000) to call
# the backend (localhost:8000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# === Step 5: Register routes ===
from src.api.routes.tickets import router as ticket_router
from src.api.routes.admin import router as admin_router

app.include_router(ticket_router)
app.include_router(admin_router)


# === Step 6: Health check ===
@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc),
        "environment": settings.APP_ENV,
    }
```

**Why `setup_logging()` is called BEFORE anything else:**

```python
# If you import a module before logging is configured:
from src.agents.graph import process_ticket  # This module calls get_logger()
setup_logging()  # Too late! The logger was already created with defaults

# Correct order:
setup_logging()  # Configure first
from src.agents.graph import process_ticket  # Now get_logger() uses our config
```

**Why CORS middleware?**

Browsers enforce the **Same-Origin Policy**: JavaScript on `localhost:3000`
(frontend) cannot call `localhost:8000` (backend) unless the backend explicitly
allows it via CORS headers.

Without CORS:
```
Frontend → fetch("http://localhost:8000/api/v1/tickets")
Browser → BLOCKED! Different origin (port 3000 ≠ 8000)
```

With CORS:
```
Frontend → fetch("http://localhost:8000/api/v1/tickets")
Backend → Response includes: Access-Control-Allow-Origin: http://localhost:3000
Browser → Allowed! Here's the response.
```

**Why `asynccontextmanager` for lifespan?**

FastAPI's lifespan replaces the old `@app.on_event("startup")` pattern:

```python
# Old way (deprecated):
@app.on_event("startup")
async def startup():
    await init_db()

@app.on_event("shutdown")
async def shutdown():
    await close_db()

# New way (lifespan context manager):
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()        # Startup
    yield                  # App runs
    await close_db()       # Shutdown
```

The context manager pattern guarantees `close_db()` runs even if the app crashes,
because `yield` is wrapped in a try/finally internally.

---

That completes Part 2. At this point you have:
- ✅ A working config system that reads from .env
- ✅ Structured logging with colored dev output and JSON production output
- ✅ Simple metrics tracking
- ✅ A FastAPI app that starts, initializes the database, and loads models

You can already run `uvicorn src.main:app --reload` and see the health check work.

---

# Part 3: Database Layer

This is the second layer you build, after the foundation. The database layer has
three files, each with a specific role:

| File | Role |
|------|------|
| `src/db/models.py` | Define what the tables look like (schema) |
| `src/db/session.py` | Manage connections to the database (pool) |
| `src/db/repositories/*.py` | Run queries against the tables (CRUD) |

**Why this separation?**

- **Models** define the schema — they don't know how to connect to a database
- **Session** manages connections — it doesn't know what tables exist
- **Repositories** run queries — they use sessions and know about models

This is the **Repository Pattern**, and it's crucial for maintainability:

```python
# Without Repository Pattern (business logic mixed with DB queries):
async def create_ticket_route(request):
    async with session() as db:
        ticket = Ticket(subject=request.subject)
        db.add(ticket)
        await db.commit()  # DB logic in the route handler!

# With Repository Pattern (clean separation):
async def create_ticket_route(request, db):
    ticket = await ticket_repo.create_ticket(db, subject=request.subject)
    # Route handler doesn't know about db.add(), commit(), etc.
```

## 3.1 File 6: `src/db/models.py` — The Database Schema

This is the biggest file in the project (~576 lines) because it defines
every table in the database. Let's build each model and explain why it
exists and why each column is typed the way it is.

### 3.1.1 Understanding SQLAlchemy ORM

Before looking at the code, understand what an ORM does:

```python
# Without ORM (raw SQL):
await db.execute("""
    INSERT INTO tickets (id, subject, status, customer_id)
    VALUES ($1, $2, $3, $4)
""", [uuid4(), "Cannot login", "new", customer_id])

# With ORM (SQLAlchemy):
ticket = Ticket(subject="Cannot login", status="new", customer_id=customer_id)
db.add(ticket)
# SQLAlchemy generates the INSERT statement for you
```

The ORM gives you:
- **Python objects instead of raw tuples** — `ticket.subject` vs `row[1]`
- **Type safety** — `ticket.subject` is a `str`, not `Any`
- **Relationship loading** — `ticket.customer.email` loads the customer automatically
- **Migration support** — Alembic reads your models to generate ALTER TABLE statements

### 3.1.2 The Base Class

Every SQLAlchemy model inherits from a `Base` class:

```python
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    """
    Base class for all ORM models.
    
    WHY:
        SQLAlchemy needs a registry to track all your models.
        Base provides that registry. When you call Base.metadata.create_all(),
        it creates tables for ALL classes that inherit from Base.
    """
    pass
```

This is boilerplate, but understanding it matters: every model class that
inherits from `Base` is automatically tracked by SQLAlchemy's metadata registry.
When you call `Base.metadata.create_all(engine)`, it inspects every subclass
and generates CREATE TABLE statements.

### 3.1.3 The Customer Model

```python
class Customer(Base):
    """
    A customer who submits support tickets.
    
    WHY THIS IS A SEPARATE TABLE:
        - Customers can submit MULTIPLE tickets
        - We need to track customer history across tickets
        - Deduplication: same email = same customer record
    
    ALTERNATIVE:
        Store customer_email directly on each ticket. But then:
        - No way to store customer metadata (name, company)
        - No way to count "how many tickets has this customer submitted?"
        - Data duplication (email stored in every ticket row)
    """
    __tablename__ = "customers"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,           # Auto-generate UUID
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,                   # No duplicate emails
        nullable=False,
        index=True,                    # Fast lookups by email
    )
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_: Mapped[dict] = mapped_column(
        "metadata",                    # Column name in DB is "metadata"
        JSONB,                         # PostgreSQL JSON binary
        default=dict,
        server_default="{}",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    
    # Relationship: one customer → many tickets
    tickets: Mapped[list["Ticket"]] = relationship(
        back_populates="customer",
    )
```

**Key design decisions:**

1. **UUID as primary key (not auto-increment integer)**

   ```python
   # Auto-increment (bad for distributed systems):
   id = Column(Integer, primary_key=True, autoincrement=True)
   # Problem: Two servers can generate the same ID
   
   # UUID (good for distributed systems):
   id = mapped_column(UUID(as_uuid=True), default=uuid.uuid4)
   # Problem: None. Each UUID is globally unique.
   ```

   UUIDs also prevent enumeration attacks (an attacker can't guess
   `/api/customers/1`, `/api/customers/2`, etc.).

2. **`JSONB` for metadata**

   JSONB lets you store arbitrary key-value data without adding columns:
   ```python
   customer.metadata_ = {"preferred_language": "es", "tier": "premium"}
   ```

   Why `metadata_` with an underscore? Because `metadata` is a reserved
   attribute in SQLAlchemy (it's used for table introspection). The `"metadata"`
   string in `mapped_column("metadata", JSONB)` tells SQLAlchemy to name the
   actual database column `metadata`, while Python uses `metadata_`.

3. **`server_default="{}"` vs `default=dict`**

   - `default=dict` — Python-side default. When you create a `Customer()` object
     without specifying metadata, Python sets it to `{}`.
   - `server_default="{}"` — Database-side default. If you insert a row via raw SQL
     (bypassing Python), the database sets it to `{}`.

   Both are needed for complete coverage.

4. **`index=True` on email**

   Without an index, finding a customer by email scans every row:
   `WHERE email = 'user@example.com'` → O(n) scan.

   With an index: O(log n) B-tree lookup. For 100,000 customers,
   that's ~17 comparisons instead of 100,000.

### 3.1.4 The Agent Model

```python
class Agent(Base):
    """
    A support agent — can be AI or human.
    
    WHY BOTH AI AND HUMAN IN THE SAME TABLE:
        - A ticket can be "assigned_to" either an AI or human agent
        - The foreign key (Ticket.assigned_agent_id → Agent.id) works for both
        - The audit trail (AgentAction.agent_id) tracks actions by either type
    """
    __tablename__ = "agents"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    is_ai: Mapped[bool] = mapped_column(default=False)    # True = AI agent, False = human
    is_active: Mapped[bool] = mapped_column(default=True)  # Can be deactivated
    
    # Reverse relationships
    assigned_tickets: Mapped[list["Ticket"]] = relationship(back_populates="assigned_agent")
    actions: Mapped[list["AgentAction"]] = relationship(back_populates="agent")
```

**The `is_ai` flag is a simple but powerful design choice.** Instead of having
separate `AIAgent` and `HumanAgent` tables (which would complicate foreign keys),
we use a single table with a boolean discriminator:

```python
# When creating the AI agent:
ai_agent = Agent(name="Support AI", is_ai=True)

# When a human logs in:
human_agent = Agent(name="John", email="john@company.com", is_ai=False)
```

### 3.1.5 The Ticket Model — The Central Entity

This is the most important model. Almost everything relates to it:

```python
class Ticket(Base):
    """
    A support ticket created by a customer.
    
    LIFECYCLE:
        new → open → (pending_customer | pending_agent | escalated) → resolved → closed
    
    This is the CENTRAL table — customers, messages, actions, and agents
    all link back to tickets.
    """
    __tablename__ = "tickets"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign Keys
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False,
    )
    assigned_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True,
    )
    
    # Ticket Fields
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="new")
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # AI context (flexible JSONB storage)
    ai_context: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),  # Auto-update!
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String(50), nullable=True)
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "status IN ('new','open','pending_customer','pending_agent','escalated','resolved','closed')",
            name="valid_status",
        ),
        CheckConstraint(
            "priority IN ('low','medium','high','urgent')",
            name="valid_priority",
        ),
        Index("idx_tickets_status", "status"),
        Index("idx_tickets_customer", "customer_id"),
        Index("idx_tickets_created", "created_at"),
    )
    
    # Relationships
    customer: Mapped["Customer"] = relationship(back_populates="tickets")
    assigned_agent: Mapped["Agent | None"] = relationship(back_populates="assigned_tickets")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="ticket", order_by="Message.created_at",
    )
    actions: Mapped[list["AgentAction"]] = relationship(
        back_populates="ticket", order_by="AgentAction.created_at",
    )
```

**Deep dive into key concepts:**

1. **CHECK constraints enforce valid values at the database level:**

   ```sql
   -- Even if your Python code has a bug, the database rejects invalid values:
   INSERT INTO tickets (status) VALUES ('invalid_status');
   -- ERROR: violates check constraint "valid_status"
   ```

   This is defense-in-depth. Your Pydantic schema validates in Python,
   but the CHECK constraint is your last line of defense.

2. **`onupdate=lambda: datetime.now(timezone.utc)`**

   Every time you modify any column on the ticket and call `db.flush()` or
   `db.commit()`, SQLAlchemy automatically sets `updated_at` to the current time.
   You never have to remember to update it manually.

3. **`ai_context: JSONB`**

   This stores the AI's classification results as flexible JSON:
   ```json
   {
     "intent": "password_reset",
     "confidence": 0.92,
     "sentiment": "frustrated",
     "kb_results_count": 3
   }
   ```

   **Why not separate columns for intent, confidence, sentiment?**

   Because the AI's output structure might change. If we add a new field like
   `language` or `urgency_score`, we'd need a database migration with separate
   columns. With JSONB, we just add a key — no migration needed.

   **Rule of thumb:** Use columns for data you query/filter on (status, priority).
   Use JSONB for data you only display or log (classification details).

4. **Indexes:**

   ```python
   Index("idx_tickets_status", "status"),     # WHERE status = 'open' → fast
   Index("idx_tickets_customer", "customer_id"),  # WHERE customer_id = X → fast
   Index("idx_tickets_created", "created_at"),    # ORDER BY created_at DESC → fast
   ```

   Without indexes, these queries scan the entire table. With 100,000 tickets,
   "show all open tickets" would take seconds. With an index: milliseconds.

### 3.1.6 The Message Model

```python
class Message(Base):
    """
    A single message in a ticket's conversation thread.
    
    sender_type values:
        "customer"     — the customer wrote this
        "ai_agent"     — our AI agent generated this
        "human_agent"  — a human support agent wrote this
        "system"       — automated system message (e.g., "ticket escalated")
    """
    __tablename__ = "messages"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tickets.id"), nullable=False)
    sender_type: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )
    
    __table_args__ = (
        CheckConstraint(
            "sender_type IN ('customer', 'ai_agent', 'human_agent', 'system')",
            name="valid_sender_type",
        ),
        Index("idx_messages_ticket", "ticket_id"),
    )
    
    ticket: Mapped["Ticket"] = relationship(back_populates="messages")
```

**Why `sender_type` as a string and not a foreign key to a users table?**

Because messages can come from different entity types:
- Customers (from the `customers` table)
- AI agents (from the `agents` table)
- Human agents (from the `agents` table)
- System (no table — it's automated)

A foreign key would require a single table for all senders, which doesn't
make sense when customers and agents have completely different attributes.
The `sender_type` string approach (called "polymorphic senders") is the
standard pattern for chat systems.

### 3.1.7 The AgentAction Model — Audit Trail

```python
class AgentAction(Base):
    """
    Records every action taken by an agent on a ticket.
    
    THIS IS THE AUDIT TRAIL — crucial for:
    1. Transparency: "Why did the AI say this?"
    2. Debugging: "Where did the workflow go wrong?"
    3. Compliance: "What happened to this ticket?"
    """
    __tablename__ = "agent_actions"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tickets.id"), nullable=False)
    agent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True)
    action_type: Mapped[str] = mapped_column(String(100), nullable=False)
    action_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, server_default="{}")
    reasoning: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    outcome: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )
```

**Why is the audit trail separate from messages?**

Messages are the *conversation* — what the customer and agent said.
Actions are the *internal workflow* — what the AI did behind the scenes.

A single ticket creation might generate 4 actions:
1. `classify_ticket` — AI classified intent, priority, sentiment
2. `search_knowledge_base` — AI searched for relevant articles
3. `generate_response` — AI drafted a response
4. `validate_response` — AI validated the response quality

These are invisible to the customer but invaluable for debugging.

### 3.1.8 Knowledge Base Models

```python
class KnowledgeArticle(Base):
    """A knowledge base article."""
    __tablename__ = "knowledge_articles"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_published: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )
    
    # One article → many embedding chunks
    chunks: Mapped[list["KBEmbedding"]] = relationship(back_populates="article")


class KBEmbedding(Base):
    """
    A chunk of a knowledge article with its vector embedding.
    
    WHY SEPARATE FROM KnowledgeArticle:
        One article might be 2000 words. Embedding models work best
        with ~100-500 word chunks. So we split each article into pieces,
        embed each piece, and store the embedding alongside the chunk text.
    """
    __tablename__ = "kb_embeddings"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    article_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("knowledge_articles.id"))
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(default=0)
    embedding = mapped_column(Vector(384))  # pgvector 384-dim vector
    
    article: Mapped["KnowledgeArticle"] = relationship(back_populates="chunks")
```

**The `Vector(384)` column is the heart of RAG:**

```sql
-- Under the hood, this creates a PostgreSQL column of type vector(384):
embedding vector(384)

-- pgvector lets you do similarity search:
SELECT chunk_text
FROM kb_embeddings
ORDER BY embedding <=> '[0.1, 0.2, ...]'::vector  -- <=> = cosine distance
LIMIT 5;
```

This is what makes the knowledge base *smart* — instead of keyword matching
("password" → article about passwords), we use semantic similarity
("I can't get into my account" → article about password reset, even though
neither "password" nor "reset" appears in the query).

## 3.2 File 7: `src/db/session.py` — Connection Management

This file manages the connection pool — how your application talks to
PostgreSQL efficiently.

### 3.2.1 Why Connection Pooling?

```python
# Without pooling (bad):
for request in incoming_requests:
    conn = await connect_to_database()   # 50ms to establish TCP + TLS
    result = await conn.execute(query)    # 5ms to run query
    await conn.close()                    # Connection destroyed
# Total: 55ms per request, mostly connection overhead

# With pooling (good):
pool = create_pool(min=5, max=20)  # Pre-create 5 connections
for request in incoming_requests:
    conn = pool.checkout()           # ~0ms (connection already established)
    result = await conn.execute(query)  # 5ms
    pool.return(conn)                # Connection returned, not destroyed
# Total: 5ms per request
```

### 3.2.2 The Implementation

```python
"""
src/db/session.py — Async database session management.

COMPONENTS:
    engine          — The connection pool + SQL dialect
    session_factory — Creates individual sessions (one per request)
    get_db_session  — FastAPI dependency that provides sessions
    init_db         — Called at startup to test connection + create tables
    close_db        — Called at shutdown to close all connections
"""

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text

from src.config import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


# 1. Create the async engine (connection pool)
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,           # Log all SQL statements in debug mode
    pool_size=5,                   # Maintain 5 permanent connections
    max_overflow=10,               # Allow up to 15 total (5 + 10)
    pool_timeout=30,               # Wait 30s for a connection before error
    pool_recycle=3600,             # Reconnect every hour (prevents stale connections)
    pool_pre_ping=True,            # Test connection before using (auto-reconnect)
)

# 2. Session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,        # Keep data accessible after commit
)


# 3. FastAPI dependency
async def get_db_session():
    """
    Provide an async database session for each request.
    
    LIFECYCLE:
        1. Check out a connection from the pool
        2. Yield session to the route handler
        3. If no exception: COMMIT all changes
        4. If exception: ROLLBACK all changes
        5. Always: close/return the connection to the pool
    
    WHY THIS PATTERN:
        - Auto-commit: route handlers don't need to call db.commit()
        - Auto-rollback: if a route raises an exception, all DB changes are reverted
        - Auto-cleanup: connection always returned to pool
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# 4. Startup: test connection + create tables
async def init_db():
    """
    Initialize the database:
        1. Enable pgvector extension (for vector similarity search)
        2. Create all tables that don't exist yet
    """
    logger.info("initializing_database")
    
    async with engine.begin() as conn:
        # Enable pgvector extension
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        
        # Create all tables defined in models.py
        from src.db.models import Base
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("database_initialized")


# 5. Shutdown: close all connections
async def close_db():
    """Close connection pool."""
    await engine.dispose()
    logger.info("database_closed")
```

**Critical concept: `expire_on_commit=False`**

```python
# With expire_on_commit=True (default, bad for our case):
ticket = Ticket(subject="Test")
db.add(ticket)
await db.commit()
print(ticket.subject)  # LAZY LOAD! Issues a SELECT to get the value again

# With expire_on_commit=False (what we use):
await db.commit()
print(ticket.subject)  # Uses cached value, no extra query
```

Since we return response objects from our route handlers, we need the data
to be accessible after commit. Without this flag, every attribute access
after commit would trigger a new SELECT query.

**`pool_pre_ping=True` — Why?**

Supabase (and most hosted databases) close idle connections after a timeout.
Without `pool_pre_ping`, your app might try to use a dead connection:

```
app → send query on stale connection → database says "connection closed" → 500 error
```

With `pool_pre_ping`:
```
app → ping the database first → "connection alive? no" → get a fresh one → send query → success
```

## 3.3 Files 8-9: `src/db/repositories/` — The Repository Layer

### 3.3.1 `customer_repo.py` — Customer Operations

```python
"""
src/db/repositories/customer_repo.py — Customer database operations.

PATTERN: Repository = pure database functions.
    - Input: session + parameters
    - Output: model instances
    - No business logic, no HTTP concepts, no AI logic
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Customer


async def get_or_create_customer(
    db: AsyncSession,
    email: str,
    name: str | None = None,
) -> tuple[Customer, bool]:
    """
    Find existing customer by email or create a new one.
    Returns: (customer, is_new) — the bool indicates if it was just created.
    
    WHY get_or_create:
        When a customer submits their first ticket, we don't have them in the DB.
        When they submit their second ticket, we DO have them.
        This function handles both cases in one call.
    """
    result = await db.execute(
        select(Customer).where(Customer.email == email)
    )
    customer = result.scalar_one_or_none()
    
    if customer:
        return customer, False  # Found existing
    
    # Create new customer
    customer = Customer(email=email, name=name or email.split("@")[0])
    db.add(customer)
    await db.flush()  # flush() assigns the UUID without committing
    return customer, True  # Newly created
```

**Why `db.flush()` instead of `db.commit()`?**

- `flush()` sends the INSERT to the database and gets back the generated UUID,
  but doesn't finalize the transaction.
- `commit()` finalizes everything.

We use `flush()` here because the route handler's `get_db_session()` does the
commit. If we committed inside the repository, we couldn't roll back the
entire operation if a later step fails.

**This is called "unit of work":** all operations within one request are part
of one transaction. Either everything succeeds or everything rolls back.

### 3.3.2 `ticket_repo.py` — Ticket Operations

```python
"""
src/db/repositories/ticket_repo.py — Ticket, message, and action operations.

This is the largest repository because tickets are the central entity.
Every ticket operation (create, read, update, list) lives here.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.db.models import Ticket, Message, AgentAction, Agent, Customer


# Fixed UUID for the AI agent (deterministic — same across all environments)
AI_AGENT_UUID = uuid.UUID("00000000-0000-0000-0000-000000000001")


async def get_or_create_ai_agent(db: AsyncSession) -> Agent:
    """Ensure the AI agent exists in the database."""
    result = await db.execute(select(Agent).where(Agent.id == AI_AGENT_UUID))
    agent = result.scalar_one_or_none()
    
    if not agent:
        agent = Agent(id=AI_AGENT_UUID, name="Support AI", is_ai=True)
        db.add(agent)
        await db.flush()
    
    return agent


async def create_ticket(
    db: AsyncSession,
    customer_id: uuid.UUID,
    subject: str,
    status: str = "new",
) -> Ticket:
    """Create a new ticket."""
    ticket = Ticket(
        customer_id=customer_id,
        subject=subject,
        status=status,
    )
    db.add(ticket)
    await db.flush()
    return ticket


async def get_ticket_by_id(db: AsyncSession, ticket_id: uuid.UUID) -> Ticket | None:
    """Get a ticket by ID with customer data loaded."""
    result = await db.execute(
        select(Ticket)
        .options(selectinload(Ticket.customer))  # Eager load customer
        .where(Ticket.id == ticket_id)
    )
    return result.scalar_one_or_none()


async def list_tickets(
    db: AsyncSession,
    status: str | None = None,
    priority: str | None = None,
    category: str | None = None,
    customer_email: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[Ticket], int]:
    """
    List tickets with optional filters and pagination.
    Returns: (tickets, total_count)
    """
    # Build the base query
    query = select(Ticket).options(selectinload(Ticket.customer))
    count_query = select(func.count(Ticket.id))
    
    # Apply filters dynamically
    if status:
        query = query.where(Ticket.status == status)
        count_query = count_query.where(Ticket.status == status)
    if priority:
        query = query.where(Ticket.priority == priority)
        count_query = count_query.where(Ticket.priority == priority)
    if category:
        query = query.where(Ticket.category == category)
        count_query = count_query.where(Ticket.category == category)
    if customer_email:
        query = query.join(Customer).where(Customer.email == customer_email)
        count_query = count_query.join(Customer).where(Customer.email == customer_email)
    
    # Sort by newest first + paginate
    query = query.order_by(Ticket.created_at.desc()).limit(limit).offset(offset)
    
    result = await db.execute(query)
    tickets = list(result.scalars().all())
    
    count_result = await db.execute(count_query)
    total = count_result.scalar_one()
    
    return tickets, total


async def add_message(
    db: AsyncSession,
    ticket_id: uuid.UUID,
    sender_type: str,
    content: str,
    metadata: dict | None = None,
) -> Message:
    """Add a message to a ticket."""
    message = Message(
        ticket_id=ticket_id,
        sender_type=sender_type,
        content=content,
        metadata_=metadata or {},
    )
    db.add(message)
    await db.flush()
    return message


async def add_agent_action(
    db: AsyncSession,
    ticket_id: uuid.UUID,
    action_type: str,
    action_data: dict,
    reasoning: str,
    outcome: str,
    agent_id: uuid.UUID | None = None,
) -> AgentAction:
    """Record an agent action in the audit trail."""
    action = AgentAction(
        ticket_id=ticket_id,
        agent_id=agent_id,
        action_type=action_type,
        action_data=action_data,
        reasoning={"thought": reasoning} if isinstance(reasoning, str) else reasoning,
        outcome=outcome,
    )
    db.add(action)
    await db.flush()
    return action
```

**Key concept: `selectinload` (Eager Loading)**

```python
# Without eager loading (N+1 query problem):
tickets = await db.execute(select(Ticket))  # 1 query: SELECT * FROM tickets
for t in tickets:
    print(t.customer.email)  # N queries: SELECT * FROM customers WHERE id = ?
# Total: 1 + N queries (if 20 tickets → 21 queries!)

# With eager loading:
tickets = await db.execute(
    select(Ticket).options(selectinload(Ticket.customer))
)
# Total: 2 queries:
#   SELECT * FROM tickets
#   SELECT * FROM customers WHERE id IN (?, ?, ?, ...)
```

The N+1 problem is one of the most common performance issues in ORM-based
applications. `selectinload` solves it by loading related data in a single
batch query.

**Why `AI_AGENT_UUID` is a fixed constant:**

```python
AI_AGENT_UUID = uuid.UUID("00000000-0000-0000-0000-000000000001")
```

The AI agent needs a consistent identity across server restarts. If we
generated a random UUID each time, the audit trail would show different
agent IDs for the same AI. A fixed UUID means "Support AI" always has the
same ID, making it easy to query all actions taken by the AI.

---

That completes Part 3. At this point you have:
- ✅ A complete database schema with 7+ tables
- ✅ Check constraints for data integrity
- ✅ Indexes for query performance
- ✅ Connection pooling with auto-reconnect
- ✅ A clean repository layer for all CRUD operations
- ✅ Proper eager loading to avoid N+1 queries

You can test this by running `init_db()` — it creates all tables in Supabase.
Open the Supabase dashboard and you'll see your tables in the Table Editor.

---

# Part 4: AI Agent Core — The LangGraph Pipeline

This is the most intellectually interesting part of the project. We're building
a multi-step AI workflow that takes a customer message and produces a response
through classification, knowledge search, generation, and validation.

## 4.1 Understanding the Architecture

The AI agent is a **state machine** implemented as a **directed graph**:

```
                    ┌─────────────┐
                    │  CLASSIFY   │ ← Entry point
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  ROUTING    │
                    └──┬───────┬──┘
                       │       │
              urgent+angry   normal
                       │       │
              ┌────────▼──┐  ┌─▼──────────┐
              │ ESCALATE  │  │ SEARCH KB  │
              └───────────┘  └──────┬─────┘
                                    │
                             ┌──────▼─────┐
                             │  RESOLVE   │
                             └──────┬─────┘
                                    │
                             ┌──────▼──────┐
                        ┌────│  VALIDATE   │────┐
                        │    └─────────────┘    │
                    valid │                  │ invalid
                        │                    │
                 ┌──────▼──────┐    retry ┌──▼──────────┐
                 │  FINALIZE   │  ◄────── │  (back to   │
                 └─────────────┘          │   RESOLVE)  │
                                          └─────────────┘
                                          ↓ (after 3 tries)
                                   ┌──────▼──────┐
                                   │  ESCALATE   │
                                   └─────────────┘
```

**Why this design?**

1. **Classification first** — you can't search the KB effectively without knowing
   the category. And you can't set priority without understanding the issue.

2. **Conditional escalation** — some tickets should NEVER be handled by AI
   (urgent + angry customer). Check this immediately after classification.

3. **Search before respond** — RAG. The response should be grounded in actual
   knowledge base articles, not hallucinated.

4. **Validation** — LLMs sometimes produce empty, truncated, or uncertain responses.
   Check quality before sending to the customer.

5. **Retry loop** — if validation fails, retry (up to 3 times). This dramatically
   reduces error rates compared to single-shot generation.

## 4.2 File 10: `src/agents/state.py` — The Shared State

In LangGraph, all nodes share a single state dictionary. This TypedDict defines
what data flows through the pipeline:

```python
"""
src/agents/state.py — Defines the data that flows through the LangGraph pipeline.

THINK OF THIS AS THE "BUS" — every node reads from it and writes to it.

A node like classify_ticket reads the message from state and writes
back the classification results (intent, priority, sentiment, confidence).
The next node reads those results and uses them.
"""

from typing import TypedDict, Any


class TicketState(TypedDict, total=False):
    """
    total=False means all fields are optional — nodes only set
    the fields they're responsible for.
    """
    
    # === INPUT (set by process_ticket before graph starts) ===
    ticket_id: str
    customer_email: str
    subject: str
    message: str
    channel: str                # "web", "email", "api", "chat"
    
    # === CLASSIFICATION (set by classifier node) ===
    intent: str                 # "password_reset", "billing_inquiry", etc.
    category: str               # "account", "billing", "technical", etc.
    priority: str               # "low", "medium", "high", "urgent"
    sentiment: str              # "positive", "neutral", "negative", "angry"
    confidence: float           # 0.0 - 1.0
    
    # === CONTEXT (set by KB search node) ===
    kb_results: list[dict[str, Any]]   # [{title, content, score}, ...]
    customer_history: list[dict]       # Previous tickets by this customer
    
    # === PROCESSING (updated by multiple nodes) ===
    needs_escalation: bool      # True if ticket should go to a human
    escalation_reason: str      # Why it was escalated
    attempts: int               # How many times resolver has been called
    
    # === RESPONSE (set by resolver, validated by validator) ===
    draft_response: str         # Generated response (before validation)
    final_response: str         # Validated response (sent to customer)
    
    # === AUDIT TRAIL ===
    actions_taken: list[dict[str, Any]]  # List of recorded actions
    error: str                  # Error message if something fails
```

**Why `total=False`?**

If `total=True` (default), every field would be required when creating the state.
But when the graph starts, we only have the input fields (ticket_id, message, etc.).
Classification results (`intent`, `priority`, etc.) don't exist yet.

`total=False` says "all fields are optional" — each node fills in what it can.

**Why a flat dictionary instead of nested objects?**

LangGraph works best with flat state. It uses dictionary merging to update state:

```python
# Node returns a partial update → LangGraph merges it into state
def classify(state):
    return {"intent": "billing", "priority": "high"}  # Only sets 2 fields

# LangGraph does: state.update({"intent": "billing", "priority": "high"})
```

Nested objects would require custom merge logic. Flat is simple and proven.

## 4.3 File 11: `src/agents/models.py` — Structured LLM Output

**The problem:** LLMs return text. We need structured data (intent, priority, etc.).

**The solution:** Pydantic models with `with_structured_output()`:

```python
"""
src/agents/models.py — Pydantic models for structured LLM output.

INSTEAD OF:
    response = llm.invoke("Classify this ticket...")
    # response.content = "Intent: billing, Priority: high, ..."
    # Now you need regex parsing — fragile!

WE DO:
    result = llm.with_structured_output(ClassificationResult).invoke(prompt)
    # result.intent = "billing"
    # result.priority = "high"
    # Pydantic validates the structure automatically!
"""

from pydantic import BaseModel, Field
from typing import Literal


class ClassificationResult(BaseModel):
    """
    Expected output from the classification LLM call.
    
    HOW with_structured_output WORKS:
        1. LangChain converts this Pydantic model to a JSON schema
        2. The JSON schema is sent to the LLM as a function/tool definition
        3. The LLM returns structured JSON matching this schema
        4. LangChain validates + parses it into a ClassificationResult object
    """
    intent: Literal[
        "password_reset", "billing_inquiry", "technical_issue",
        "account_access", "feature_request", "bug_report",
        "general_question", "complaint", "other",
    ] = Field(description="The customer's primary intent")
    
    category: Literal[
        "account", "billing", "technical", "product", "general",
    ] = Field(description="Broad category of the issue")
    
    priority: Literal[
        "low", "medium", "high", "urgent",
    ] = Field(description="How urgently this needs attention")
    
    sentiment: Literal[
        "positive", "neutral", "negative", "angry",
    ] = Field(description="Customer's emotional tone")
    
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="How confident the classification is (0-1)",
    )
```

**Why Literal types instead of plain strings?**

```python
# Without Literal (LLM might return anything):
intent: str  # Could be "billing", "Billing", "BILLING", "billing issue", etc.

# With Literal (LLM is constrained):
intent: Literal["billing_inquiry", ...]  # Must be one of these exact values
```

The `Field(description=...)` text helps the LLM understand what each field means.
When LangChain converts this to a JSON schema, the descriptions become part of
the function definition the LLM sees.

## 4.4 File 12: `src/agents/llm.py` — LLM Factory

**Why a factory?**

We want to switch between LLM providers (Google Gemini, Groq) without changing
any other code. The factory pattern creates the right client based on a config setting:

```python
"""
src/agents/llm.py — LLM client factory.

USAGE:
    from src.agents.llm import get_llm
    llm = get_llm()
    # Don't care if it's Gemini, Groq, or anything else
    # The interface is always BaseChatModel
"""

from langchain_core.language_models import BaseChatModel
from src.config import settings


def get_llm() -> BaseChatModel:
    """
    Create and return an LLM client based on config.
    
    WHY A FACTORY:
        - Single place to change the LLM provider
        - All consumers get the same interface (BaseChatModel)
        - Easy to add new providers
    """
    if settings.LLM_PROVIDER == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=settings.LLM_MODEL,            # "gemini-2.0-flash"
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=settings.LLM_TEMPERATURE, # 0.3
        )
    elif settings.LLM_PROVIDER == "groq":
        from langchain_groq import ChatGroq
        return ChatGroq(
            model_name=settings.LLM_MODEL,
            groq_api_key=settings.GROQ_API_KEY,
            temperature=settings.LLM_TEMPERATURE,
        )
    else:
        raise ValueError(f"Unknown LLM provider: {settings.LLM_PROVIDER}")
```

**Why are imports inside the function?**

```python
# Import at the top (bad — always imports both):
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq

# Import inside the function (good — only imports the one you use):
if provider == "google":
    from langchain_google_genai import ChatGoogleGenerativeAI
```

If you only use Google, you don't need `langchain-groq` installed at all.
Lazy imports prevent ImportError for unused providers.

**Engineering principle:** The factory pattern + lazy imports lets you
support multiple providers without coupling to any of them.

## 4.5 File 13: `src/agents/nodes/classifier.py` — The Classification Node

This is the first node in the pipeline. It takes the customer's message and
determines what they need, how urgent it is, and how they're feeling:

```python
"""
src/agents/nodes/classifier.py — Ticket classification node.

INPUT (from state):
    - message: "I can't login and I've been trying for hours!"
    - subject: "Login issue"

OUTPUT (to state):
    - intent: "account_access"
    - category: "account"
    - priority: "high" 
    - sentiment: "negative"
    - confidence: 0.88
    - actions_taken: [{action_type: "classify_ticket", ...}]
"""

from src.agents.llm import get_llm
from src.agents.models import ClassificationResult
from src.agents.state import TicketState
from src.utils.logging import get_logger

logger = get_logger(__name__)


async def classify_ticket(state: TicketState) -> dict:
    """
    Classify a customer support ticket using structured LLM output.
    
    THIS IS THE MOST IMPORTANT NODE because its output determines:
    1. Whether to escalate immediately
    2. What category to search in the KB
    3. The priority level displayed to admins
    """
    llm = get_llm()
    
    # Create a structured output chain
    # with_structured_output forces the LLM to return a ClassificationResult
    classifier = llm.with_structured_output(ClassificationResult)
    
    # The prompt is critical — it's the instructions for the LLM
    prompt = f"""Analyze this customer support ticket and classify it.

Subject: {state.get("subject", "")}
Message: {state.get("message", "")}
Channel: {state.get("channel", "web")}

Consider:
- What is the customer trying to do? (intent)
- What broad area does this fall under? (category)
- How urgent is this? Consider if the customer is blocked. (priority)
- What is the customer's emotional tone? (sentiment)
- How confident are you in this classification? (confidence)"""

    try:
        result: ClassificationResult = await classifier.ainvoke(prompt)
        
        logger.info(
            "ticket_classified",
            ticket_id=state.get("ticket_id"),
            intent=result.intent,
            priority=result.priority,
            sentiment=result.sentiment,
            confidence=result.confidence,
        )
        
        # Return partial state update — LangGraph merges this into state
        return {
            "intent": result.intent,
            "category": result.category,
            "priority": result.priority,
            "sentiment": result.sentiment,
            "confidence": result.confidence,
            "actions_taken": state.get("actions_taken", []) + [{
                "action_type": "classify_ticket",
                "action_data": {
                    "intent": result.intent,
                    "category": result.category,
                    "priority": result.priority,
                    "sentiment": result.sentiment,
                    "confidence": result.confidence,
                },
                "reasoning": "LLM-based classification with structured output",
                "outcome": "success",
            }],
        }
        
    except Exception as e:
        logger.error("classification_failed", error=str(e))
        # Fallback: default classification if LLM fails
        return {
            "intent": "general_question",
            "category": "general",
            "priority": "medium",
            "sentiment": "neutral",
            "confidence": 0.0,
            "error": f"Classification failed: {str(e)}",
            "actions_taken": state.get("actions_taken", []) + [{
                "action_type": "classify_ticket",
                "action_data": {"error": str(e)},
                "outcome": "failure",
            }],
        }
```

**Key engineering concepts:**

1. **Structured output eliminates parsing errors:**

   ```python
   # Old way (fragile):
   response = await llm.ainvoke("Classify this ticket...")
   # response.content might be "Intent: billing\nPriority: high"
   # or "The intent is billing and it's high priority"
   # or JSON, or markdown... who knows?
   # Parsing this reliably is a nightmare.
   
   # New way (robust):
   result = await classifier.ainvoke(prompt)
   # result.intent is ALWAYS a valid Literal value
   # result.priority is ALWAYS a valid Literal value
   # If the LLM doesn't comply, Pydantic raises a validation error
   ```

2. **Graceful fallback on error:**

   If the LLM API is down, we don't crash. We return safe defaults
   (`priority: "medium"`, `confidence: 0.0`) and record the error.
   The ticket still gets created — a human can classify it manually.

3. **Appending to `actions_taken`:**

   ```python
   "actions_taken": state.get("actions_taken", []) + [new_action]
   ```

   Each node appends its action to the list. At the end of the pipeline,
   `actions_taken` contains a complete audit trail of everything the AI did.

## 4.6 File 14: `src/agents/edges/conditions.py` — Routing Logic

After classification, we need to decide: should this ticket go to a human
immediately, or should we try to handle it with AI?

```python
"""
src/agents/edges/conditions.py — Conditional edge functions.

These functions return STRINGS that LangGraph uses to pick the next node.
Think of them as if/else statements that determine the workflow path.
"""

from src.agents.state import TicketState
from src.config import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


def should_escalate_after_classify(state: TicketState) -> str:
    """
    After classification, decide: escalate or proceed?
    
    ESCALATION RULES:
    1. Urgent priority + angry sentiment → always escalate
    2. Confidence below threshold → AI isn't sure, humans should handle it
    3. Explicit escalation flag set → another node requested escalation
    
    Returns: "escalate" or "search_kb"
    """
    priority = state.get("priority", "medium")
    sentiment = state.get("sentiment", "neutral")
    confidence = state.get("confidence", 1.0)
    
    # Rule 1: Urgent + angry → human needed
    if priority == "urgent" and sentiment == "angry":
        logger.info(
            "immediate_escalation",
            reason="urgent_priority_angry_sentiment",
            ticket_id=state.get("ticket_id"),
        )
        return "escalate"
    
    # Rule 2: Low confidence → AI isn't sure
    threshold = settings.ESCALATION_CONFIDENCE_THRESHOLD  # Default: 0.7
    if confidence < threshold:
        logger.info(
            "immediate_escalation",
            reason="low_confidence",
            confidence=confidence,
            threshold=threshold,
        )
        return "escalate"
    
    # Rule 3: Explicit flag
    if state.get("needs_escalation"):
        return "escalate"
    
    # Normal path: search knowledge base
    return "search_kb"


def should_escalate_after_validate(state: TicketState) -> str:
    """
    After validation, decide: finalize, retry, or escalate?
    
    Returns: "finalize", "respond", or "escalate"
    """
    # If final_response is set, validation passed
    if state.get("final_response"):
        return "finalize"
    
    # If we've retried too many times, escalate
    attempts = state.get("attempts", 0)
    if attempts >= settings.MAX_AUTO_ATTEMPTS:  # Default: 3
        logger.info(
            "escalation_after_max_retries",
            attempts=attempts,
            ticket_id=state.get("ticket_id"),
        )
        return "escalate"
    
    # Otherwise, retry
    return "respond"
```

**This is where business rules meet code.** The escalation conditions are
configurable via `settings` (from .env), so the business team can tune them
without code changes:

```env
ESCALATION_CONFIDENCE_THRESHOLD=0.7   # Change to 0.5 for less escalation
MAX_AUTO_ATTEMPTS=3                    # Change to 5 for more retries
```

**Why separate condition functions instead of inline logic?**

```python
# Inline (hard to test, hard to modify):
graph.add_conditional_edges("classify", lambda s: "escalate" if s["priority"] == "urgent" else "search_kb")

# Separate function (testable, readable):
graph.add_conditional_edges("classify", should_escalate_after_classify, {...})
```

You can unit test `should_escalate_after_classify` with fake states without
running the full LangGraph pipeline.

## 4.7 File 15: `src/agents/nodes/resolver.py` — Response Generation

This node takes the classification results and KB search results to generate
a personalized response:

```python
"""
src/agents/nodes/resolver.py — Generate the AI response.

INPUT (from state):
    - subject, message, category, priority, sentiment
    - kb_results: [{title: "...", content: "..."}]

OUTPUT (to state):
    - draft_response: "Thank you for reaching out! To reset your password..."
"""

from src.agents.llm import get_llm
from src.agents.state import TicketState
from src.utils.logging import get_logger

logger = get_logger(__name__)


async def generate_response(state: TicketState) -> dict:
    """Generate a customer-facing response using LLM + context."""
    llm = get_llm()
    
    # Build context from KB results
    kb_context = ""
    kb_results = state.get("kb_results", [])
    if kb_results:
        kb_context = "RELEVANT KNOWLEDGE BASE ARTICLES:\n"
        for i, result in enumerate(kb_results, 1):
            kb_context += f"\n{i}. {result.get('title', 'Untitled')}:\n"
            kb_context += f"   {result.get('content', '')}\n"
    
    # The prompt instructs the LLM on tone, structure, and constraints
    prompt = f"""You are a helpful customer support agent. Generate a response
to the following customer ticket.

CUSTOMER TICKET:
Subject: {state.get("subject", "")}
Message: {state.get("message", "")}

CLASSIFICATION:
Category: {state.get("category", "general")}
Priority: {state.get("priority", "medium")}
Sentiment: {state.get("sentiment", "neutral")}

{kb_context}

RULES:
1. Be empathetic and professional
2. Address the specific issue mentioned
3. If KB articles are provided, use their content to give accurate information
4. Include specific steps the customer can take
5. If you're unsure, acknowledge it and offer to connect with a specialist
6. Keep the response concise but complete (100-300 words)
7. Do NOT make up information not in the KB articles"""

    try:
        response = await llm.ainvoke(prompt)
        draft = response.content.strip()
        
        logger.info(
            "response_generated",
            ticket_id=state.get("ticket_id"),
            response_length=len(draft),
            kb_articles_used=len(kb_results),
        )
        
        return {
            "draft_response": draft,
            "attempts": state.get("attempts", 0) + 1,
            "actions_taken": state.get("actions_taken", []) + [{
                "action_type": "generate_response",
                "action_data": {
                    "response_length": len(draft),
                    "kb_articles_used": len(kb_results),
                    "attempt": state.get("attempts", 0) + 1,
                },
                "reasoning": "LLM generated response with KB context",
                "outcome": "success",
            }],
        }
        
    except Exception as e:
        logger.error("response_generation_failed", error=str(e))
        return {
            "draft_response": "",
            "error": f"Response generation failed: {str(e)}",
            "actions_taken": state.get("actions_taken", []) + [{
                "action_type": "generate_response",
                "action_data": {"error": str(e)},
                "outcome": "failure",
            }],
        }
```

**Why "draft_response" and not "final_response"?**

Because the response hasn't been validated yet. The validator node checks it
before promoting it to `final_response`. This separation prevents bad responses
from reaching the customer.

**The prompt engineering is critical:**

1. **"Be empathetic and professional"** — sets the tone
2. **"Use KB articles"** — grounds the response in facts (RAG)
3. **"Do NOT make up information"** — prevents hallucination
4. **"100-300 words"** — prevents both too-short and too-long responses
5. **"If unsure, acknowledge it"** — honesty over confidence

## 4.8 File 16: `src/agents/nodes/validator.py` — Quality Checks

This node catches bad responses before they reach the customer:

```python
"""
src/agents/nodes/validator.py — Response quality validation.

CHECKS:
    1. Not empty
    2. Minimum length (50 characters)
    3. No uncertainty markers ("I don't know", "I'm not sure")
    4. Actually addresses the issue (basic check)
"""

from src.agents.state import TicketState
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Phrases that indicate the AI is uncertain
UNCERTAINTY_MARKERS = [
    "i don't know",
    "i'm not sure",
    "i cannot help",
    "i am unable",
    "unfortunately, i don't have",
    "i don't have enough information",
]


async def validate_response(state: TicketState) -> dict:
    """
    Validate the draft response quality.
    
    If valid: moves draft to final_response
    If invalid: leaves final_response empty (triggers retry or escalation)
    """
    draft = state.get("draft_response", "")
    
    # Check 1: Not empty
    if not draft or not draft.strip():
        logger.warning("validation_failed", reason="empty_response")
        return {
            "actions_taken": state.get("actions_taken", []) + [{
                "action_type": "validate_response",
                "action_data": {"reason": "empty_response"},
                "outcome": "failed",
            }],
        }
    
    # Check 2: Minimum length
    if len(draft.strip()) < 50:
        logger.warning("validation_failed", reason="too_short", length=len(draft))
        return {
            "actions_taken": state.get("actions_taken", []) + [{
                "action_type": "validate_response",
                "action_data": {"reason": "too_short", "length": len(draft)},
                "outcome": "failed",
            }],
        }
    
    # Check 3: No uncertainty markers
    draft_lower = draft.lower()
    for marker in UNCERTAINTY_MARKERS:
        if marker in draft_lower:
            logger.warning("validation_failed", reason="uncertainty", marker=marker)
            return {
                "actions_taken": state.get("actions_taken", []) + [{
                    "action_type": "validate_response",
                    "action_data": {"reason": "uncertainty_marker", "marker": marker},
                    "outcome": "failed",
                }],
            }
    
    # All checks passed! Promote draft to final
    logger.info("validation_passed", ticket_id=state.get("ticket_id"))
    return {
        "final_response": draft,
        "actions_taken": state.get("actions_taken", []) + [{
            "action_type": "validate_response",
            "action_data": {"response_length": len(draft)},
            "reasoning": "All validation checks passed",
            "outcome": "success",
        }],
    }
```

**Why validate at all? Doesn't the LLM always give good answers?**

No! LLMs can:
- Return empty strings (API timeout)
- Return very short responses ("I'll look into that.")
- Admit uncertainty ("I don't have enough information")
- Generate off-topic responses

The validator catches these cases. If validation fails:
1. First attempt → retry (back to resolver with the same context)
2. Second attempt → retry again
3. Third attempt → escalate to human

This retry loop dramatically improves response quality.

## 4.9 File 17: `src/agents/nodes/escalator.py` — Escalation Handler

When the AI can't handle a ticket, this node prepares the handoff:

```python
"""
src/agents/nodes/escalator.py — Handle ticket escalation to humans.

THIS NODE:
    1. Determines WHY the ticket is being escalated
    2. Generates a customer-facing acknowledgment
    3. Creates a handoff summary for the human agent
"""

from src.agents.llm import get_llm
from src.agents.state import TicketState
from src.utils.logging import get_logger

logger = get_logger(__name__)


async def escalate_ticket(state: TicketState) -> dict:
    """Escalate ticket to a human agent."""
    
    # Determine the escalation reason
    reasons = []
    priority = state.get("priority", "medium")
    sentiment = state.get("sentiment", "neutral")
    confidence = state.get("confidence", 1.0)
    attempts = state.get("attempts", 0)
    
    if priority == "urgent":
        reasons.append(f"Urgent priority ({priority})")
    if sentiment == "angry":
        reasons.append(f"Negative sentiment ({sentiment})")
    if confidence < 0.7:
        reasons.append(f"Low classification confidence ({confidence:.0%})")
    if attempts >= 3:
        reasons.append(f"AI response failed validation after {attempts} attempts")
    if not reasons:
        reasons.append("Manually flagged for escalation")
    
    escalation_reason = "; ".join(reasons)
    
    # Generate customer-facing message
    llm = get_llm()
    prompt = f"""Generate a brief, empathetic message telling the customer
their ticket is being transferred to a human support specialist.

Reason (internal, don't share): {escalation_reason}
Customer sentiment: {sentiment}

Be warm and reassuring. 2-3 sentences max."""

    try:
        response = await llm.ainvoke(prompt)
        customer_message = response.content.strip()
    except Exception:
        customer_message = (
            "I'm connecting you with a support specialist who can better "
            "assist you with this issue. They'll be with you shortly."
        )
    
    logger.info(
        "ticket_escalated",
        ticket_id=state.get("ticket_id"),
        reason=escalation_reason,
    )
    
    return {
        "needs_escalation": True,
        "escalation_reason": escalation_reason,
        "final_response": customer_message,
        "actions_taken": state.get("actions_taken", []) + [{
            "action_type": "escalate_ticket",
            "action_data": {
                "reason": escalation_reason,
                "priority": priority,
                "sentiment": sentiment,
                "confidence": confidence,
                "attempts": attempts,
            },
            "reasoning": f"Escalated because: {escalation_reason}",
            "outcome": "escalated",
        }],
    }
```

**Why generate a customer message dynamically?**

A static "Your ticket has been escalated" feels robotic. The generated message
adapts to the customer's sentiment:
- Angry customer → warmer, more empathetic language
- Neutral customer → professional and straightforward
- Urgent issue → acknowledgment of urgency

## 4.10 File 18: `src/agents/graph.py` — Wiring It All Together

This is where the entire pipeline comes together. Every node and edge is
assembled into a state machine:

```python
"""
src/agents/graph.py — The main LangGraph definition.

THIS FILE:
    1. Imports all nodes and conditions
    2. Builds the state graph
    3. Compiles it into an executable
    4. Provides process_ticket() as the entry point
"""

from langgraph.graph import StateGraph, END

from src.agents.state import TicketState
from src.agents.nodes.classifier import classify_ticket
from src.agents.nodes.resolver import generate_response
from src.agents.nodes.validator import validate_response
from src.agents.nodes.escalator import escalate_ticket
from src.agents.edges.conditions import (
    should_escalate_after_classify,
    should_escalate_after_validate,
)
from src.tools.knowledge_base import search_knowledge_base
from src.utils.logging import get_logger
from src.config import settings

logger = get_logger(__name__)


def build_graph() -> StateGraph:
    """
    Construct the LangGraph state machine.
    
    GRAPH STRUCTURE:
        classify → (conditional) → escalate OR search_kb
        search_kb → resolve
        resolve → validate
        validate → (conditional) → finalize OR retry(resolve) OR escalate
        escalate → END
        finalize → END
    """
    graph = StateGraph(TicketState)
    
    # === Add Nodes ===
    # Each node is a function that takes state and returns partial state update
    graph.add_node("classify", classify_ticket)
    graph.add_node("search_kb", search_knowledge_base)
    graph.add_node("resolve", generate_response)
    graph.add_node("validate", validate_response)
    graph.add_node("escalate", escalate_ticket)
    graph.add_node("finalize", lambda state: state)  # No-op, just passes through
    
    # === Set Entry Point ===
    graph.set_entry_point("classify")
    
    # === Add Edges ===
    # After classify: escalate immediately or search KB
    graph.add_conditional_edges(
        "classify",
        should_escalate_after_classify,
        {
            "escalate": "escalate",
            "search_kb": "search_kb",
        },
    )
    
    # After search: always go to resolve
    graph.add_edge("search_kb", "resolve")
    
    # After resolve: always go to validate
    graph.add_edge("resolve", "validate")
    
    # After validate: finalize, retry, or escalate
    graph.add_conditional_edges(
        "validate",
        should_escalate_after_validate,
        {
            "finalize": "finalize",
            "respond": "resolve",    # Retry → back to resolve
            "escalate": "escalate",
        },
    )
    
    # Terminal nodes → END
    graph.add_edge("escalate", END)
    graph.add_edge("finalize", END)
    
    return graph


# Compile once at module level (reuse for every request)
compiled_graph = build_graph().compile()


async def process_ticket(
    ticket_id: str,
    customer_email: str,
    subject: str,
    message: str,
    channel: str = "web",
) -> TicketState:
    """
    Main entry point — process a customer ticket through the AI pipeline.
    
    Called by the ticket creation route.
    Returns the final state with the AI's response and all metadata.
    """
    # Initialize state with input data
    initial_state: TicketState = {
        "ticket_id": ticket_id,
        "customer_email": customer_email,
        "subject": subject,
        "message": message,
        "channel": channel,
        "actions_taken": [],
        "attempts": 0,
    }
    
    # Configure LangSmith tracing (if enabled)
    config = {
        "run_name": f"ticket-{ticket_id[:8]}",
        "tags": ["customer-support", f"channel:{channel}"],
        "metadata": {
            "ticket_id": ticket_id,
            "customer_email": customer_email,
        },
        "configurable": {"thread_id": ticket_id},
    }
    
    logger.info(
        "processing_ticket",
        ticket_id=ticket_id,
        subject=subject,
    )
    
    # Run the graph
    final_state = await compiled_graph.ainvoke(initial_state, config=config)
    
    logger.info(
        "ticket_processed",
        ticket_id=ticket_id,
        escalated=final_state.get("needs_escalation", False),
        priority=final_state.get("priority"),
        attempts=final_state.get("attempts"),
    )
    
    return final_state
```

**Why compile once at module level?**

```python
# Bad: compile on every request
async def process_ticket(...)
    graph = build_graph().compile()  # ~100ms compilation each time
    result = await graph.ainvoke(...)

# Good: compile once, reuse
compiled_graph = build_graph().compile()  # Compiled once at import time

async def process_ticket(...)
    result = await compiled_graph.ainvoke(...)  # No compilation overhead
```

The graph structure never changes (it's defined by the code), so there's
no reason to rebuild it for each request.

**LangSmith integration:**

The `config` dictionary enables tracing when `LANGCHAIN_TRACING_V2=true`:

```python
config = {
    "run_name": f"ticket-{ticket_id[:8]}",  # Shows in LangSmith dashboard
    "tags": ["customer-support"],            # Filter by tag
    "metadata": {"ticket_id": ticket_id},    # Searchable metadata
    "configurable": {"thread_id": ticket_id},  # Group related runs
}
```

In LangSmith, you'd see:
```
Run: ticket-abc12345
├── classify_ticket (input → output, 1.2s)
├── search_knowledge_base (input → output, 0.3s)
├── generate_response (input → output, 2.1s)
└── validate_response (input → output, 0.01s)
Total: 3.61s
```

This is invaluable for debugging — you can see exactly what each node
received and returned, including the prompts sent to the LLM.

---

That completes Part 4. At this point you have:
- ✅ A complete AI pipeline with 5 nodes
- ✅ Structured LLM output (no parsing needed)
- ✅ Conditional routing (escalate vs. continue)
- ✅ Retry logic for failed validations
- ✅ Complete audit trail of all AI actions
- ✅ LangSmith tracing for observability
- ✅ Graceful fallbacks at every step

You can test the pipeline standalone:
```python
import asyncio
from src.agents.graph import process_ticket

result = asyncio.run(process_ticket(
    ticket_id="test-123",
    customer_email="test@example.com",
    subject="Cannot reset my password",
    message="I've tried 3 times but the reset email never arrives.",
))
print(result["final_response"])
print(result["priority"])
print(result["actions_taken"])
```

---

# Part 5: RAG & Knowledge Base

RAG (Retrieval-Augmented Generation) is the technique that makes our AI agent
actually *useful*. Without RAG, the LLM would hallucinate answers based on its
training data. With RAG, it answers based on YOUR knowledge base.

## 5.1 How RAG Works (Conceptual)

```
Customer: "How do I reset my password?"
                    │
                    ▼
    ┌──────────────────────────────┐
    │  1. EMBED the question       │
    │  "reset password" → [0.2,    │
    │   0.8, 0.1, ...]             │
    └──────────────┬───────────────┘
                   │
                   ▼
    ┌──────────────────────────────┐
    │  2. SEARCH the vector DB     │
    │  Find KB chunks with similar │
    │  embeddings (cosine distance)│
    │                              │
    │  Top result: "Password Reset │
    │  Guide — Step 1: Go to..."   │
    └──────────────┬───────────────┘
                   │
                   ▼
    ┌──────────────────────────────┐
    │  3. GENERATE response using  │
    │  the customer question +     │
    │  retrieved KB content        │
    │                              │
    │  "To reset your password,    │
    │   go to Settings > Security  │
    │   > Reset Password..."       │
    └──────────────────────────────┘
```

**The key insight:** We don't ask the LLM "How do I reset my password?"
(which would produce a generic answer). We ask "Given this knowledge base
article about password resets, answer the customer's question."

## 5.2 File 19: `src/services/embedding_service.py` — Local Embeddings

This service converts text into numerical vectors (embeddings):

```python
"""
src/services/embedding_service.py — Local embedding model using sentence-transformers.

THIS IS A SINGLETON:
    The model is ~80MB. Loading it takes 2-5 seconds.
    We load it ONCE at startup and reuse it for every request.

WHAT AN EMBEDDING IS:
    Text → [0.023, -0.156, 0.892, ...]  (384 numbers)
    
    Two pieces of text about the same topic will have similar vectors.
    "reset password" and "can't login" will be close in vector space.
    "reset password" and "billing inquiry" will be far apart.
"""

import numpy as np
from sentence_transformers import SentenceTransformer
from src.config import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


class EmbeddingService:
    """Singleton service for text embedding."""
    
    _instance = None
    _model = None
    
    @classmethod
    def get_instance(cls) -> "EmbeddingService":
        """Get or create the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def load_model(self):
        """
        Load the sentence-transformers model.
        Called once at application startup (in main.py lifespan).
        
        MODEL: all-MiniLM-L6-v2
            - Size: ~80MB
            - Dimensions: 384
            - Speed: ~5ms per embed
            - Quality: Good for semantic search
        """
        if self._model is not None:
            return
        
        logger.info("loading_embedding_model", model=settings.EMBEDDING_MODEL)
        self._model = SentenceTransformer(settings.EMBEDDING_MODEL)
        logger.info("embedding_model_loaded")
    
    def embed(self, text: str) -> list[float]:
        """
        Convert a single text to a 384-dimensional vector.
        
        Usage:
            service = EmbeddingService.get_instance()
            vector = service.embed("How do I reset my password?")
            # vector = [0.023, -0.156, 0.892, ...]  (384 numbers)
        """
        if self._model is None:
            self.load_model()
        
        embedding = self._model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Embed multiple texts at once (much faster than embedding one at a time).
        
        WHY BATCH:
            Embedding 100 texts individually: 100 × 5ms = 500ms
            Embedding 100 texts in batch:     ~50ms (GPU/CPU parallelism)
        """
        if self._model is None:
            self.load_model()
        
        embeddings = self._model.encode(texts, convert_to_numpy=True, batch_size=32)
        return [emb.tolist() for emb in embeddings]
```

**Why a singleton?**

```python
# Bad: load model per request (each load is 2-5 seconds)
def embed_text(text):
    model = SentenceTransformer("all-MiniLM-L6-v2")  # 3 seconds!
    return model.encode(text)

# Good: load once, reuse forever
service = EmbeddingService.get_instance()  # Loaded once at startup
service.embed(text)  # ~5ms per call
```

The embedding model uses ~200MB of RAM. Loading it once and keeping it in
memory means subsequent embeddings are nearly instant.

**Understanding vector dimensions:**

The model outputs 384 numbers per text. These aren't random — they encode
*meaning*. Texts with similar meaning have vectors that point in similar
directions in 384-dimensional space.

```python
# Similar meaning → small cosine distance
embed("reset password")      # → [0.2, 0.8, 0.1, ...]
embed("change my password")  # → [0.2, 0.7, 0.1, ...]  # Very close!
embed("can't login")         # → [0.3, 0.6, 0.2, ...]  # Close (related topic)
embed("billing question")    # → [0.9, 0.1, 0.5, ...]  # Far away!
```

## 5.3 File 20: `src/tools/knowledge_base.py` — KB Search

This is the tool the AI agent uses to find relevant knowledge articles:

```python
"""
src/tools/knowledge_base.py — Knowledge base search with vector + keyword fallback.

SEARCH STRATEGY (in order of preference):
    1. pgvector similarity search (best quality, requires embeddings)
    2. Keyword search (fallback if DB is unavailable)
    3. Hardcoded articles (ultimate fallback — always works)
"""

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.state import TicketState
from src.services.embedding_service import EmbeddingService
from src.db.session import async_session_factory
from src.db.models import KBEmbedding, KnowledgeArticle
from src.utils.logging import get_logger

logger = get_logger(__name__)


async def search_knowledge_base(state: TicketState) -> dict:
    """
    Search the KB for articles relevant to the customer's message.
    
    THIS IS A LANGGRAPH NODE — takes state, returns partial state update.
    """
    query = state.get("message", "") or state.get("subject", "")
    category = state.get("category")
    
    try:
        results = await _vector_search(query, category)
        search_method = "vector"
    except Exception as e:
        logger.warning("vector_search_failed", error=str(e))
        results = _keyword_search(query)
        search_method = "keyword_fallback"
    
    logger.info(
        "kb_search_complete",
        method=search_method,
        results_count=len(results),
        ticket_id=state.get("ticket_id"),
    )
    
    return {
        "kb_results": results,
        "actions_taken": state.get("actions_taken", []) + [{
            "action_type": "search_knowledge_base",
            "action_data": {
                "query": query[:200],
                "method": search_method,
                "results_count": len(results),
            },
            "outcome": "success",
        }],
    }


async def _vector_search(query: str, category: str | None = None, limit: int = 5) -> list[dict]:
    """
    Perform pgvector similarity search.
    
    HOW IT WORKS:
        1. Embed the customer's query → [0.2, 0.8, ...]
        2. Find KB chunks with the most similar embeddings
        3. Return the top 5 closest matches
    """
    # Step 1: Embed the query
    embedding_service = EmbeddingService.get_instance()
    query_embedding = embedding_service.embed(query)
    
    # Step 2: Search using cosine distance (<=> operator in pgvector)
    async with async_session_factory() as session:
        # Convert Python list to PostgreSQL vector format
        embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"
        
        # Raw SQL for pgvector (SQLAlchemy doesn't have native pgvector query support)
        sql = text("""
            SELECT 
                kb.chunk_text,
                ka.title,
                ka.category,
                kb.embedding <=> :embedding::vector AS distance
            FROM kb_embeddings kb
            JOIN knowledge_articles ka ON kb.article_id = ka.id
            WHERE ka.is_published = true
            ORDER BY kb.embedding <=> :embedding::vector
            LIMIT :limit
        """)
        
        result = await session.execute(sql, {
            "embedding": embedding_str,
            "limit": limit,
        })
        rows = result.fetchall()
    
    # Step 3: Format results for the resolver node
    return [
        {
            "title": row.title,
            "content": row.chunk_text,
            "category": row.category,
            "score": round(1 - row.distance, 4),  # Convert distance to similarity
        }
        for row in rows
    ]


# === KEYWORD FALLBACK ===
# Used when the database is unavailable (development, testing, no internet)

FALLBACK_ARTICLES = [
    {
        "title": "Password Reset Guide",
        "content": "To reset your password: 1) Go to Settings > Security. 2) Click 'Reset Password'. 3) Enter your email. 4) Check your inbox for a reset link.",
        "keywords": ["password", "reset", "login", "access", "locked"],
    },
    {
        "title": "Billing FAQ",
        "content": "Billing cycles run monthly. You can view invoices in Settings > Billing. For refunds, submit a request within 30 days of purchase.",
        "keywords": ["billing", "payment", "invoice", "charge", "refund", "subscription"],
    },
    {
        "title": "Account Setup Guide",
        "content": "To set up your account: 1) Verify your email. 2) Complete your profile. 3) Set up two-factor authentication. 4) Connect your team workspace.",
        "keywords": ["account", "setup", "profile", "register", "sign up", "verify"],
    },
]


def _keyword_search(query: str) -> list[dict]:
    """Simple keyword matching — fallback when vector search is unavailable."""
    query_words = set(query.lower().split())
    scored = []
    
    for article in FALLBACK_ARTICLES:
        matches = len(query_words.intersection(article["keywords"]))
        if matches > 0:
            scored.append({
                "title": article["title"],
                "content": article["content"],
                "score": matches / len(article["keywords"]),
            })
    
    return sorted(scored, key=lambda x: x["score"], reverse=True)[:3]
```

**The `<=>` operator is pgvector's cosine distance:**

```sql
-- Find the 5 KB chunks most similar to the query embedding
SELECT chunk_text, embedding <=> '[0.2, 0.8, ...]'::vector AS distance
FROM kb_embeddings
ORDER BY distance ASC  -- Closest first
LIMIT 5;
```

Cosine distance returns 0 (identical) to 2 (opposite). We convert to
similarity with `1 - distance`, so 1.0 = perfect match, 0.0 = no relation.

**Why two search methods?**

| Scenario | Vector Search | Keyword Fallback |
|----------|---------------|-----------------|
| Production | ✅ Used (accurate) | — |
| No embeddings yet | ❌ Fails | ✅ Used |
| DB offline | ❌ Fails | ✅ Used |
| Development | ❌ May not have data | ✅ Used |

The fallback ensures the agent ALWAYS has some KB context, even during
development or when the database is down. This is defensive engineering.

## 5.4 File 21: `scripts/seed_kb.py` — Populating the Knowledge Base

This script is run once to populate the database with KB articles and
their vector embeddings:

```python
"""
scripts/seed_kb.py — Seed the knowledge base with articles + embeddings.

RUN WITH:
    python -m scripts.seed_kb

WHAT IT DOES:
    1. Define KB articles (title, content, category)
    2. Split each article into chunks (~300 words each)
    3. Generate embeddings for each chunk
    4. Insert into knowledge_articles and kb_embeddings tables
"""

import asyncio
import uuid

from sqlalchemy import text
from src.db.session import async_session_factory, engine, init_db
from src.db.models import KnowledgeArticle, KBEmbedding, Base
from src.services.embedding_service import EmbeddingService
from src.utils.logging import get_logger, setup_logging

logger = get_logger(__name__)


# === Knowledge Base Articles ===
ARTICLES = [
    {
        "title": "Password Reset & Account Recovery",
        "category": "account",
        "content": """
            Complete guide to resetting your password and recovering access.
            
            Self-Service Password Reset:
            1. Navigate to the login page
            2. Click "Forgot Password?"
            3. Enter the email address associated with your account
            4. Check your email inbox (and spam folder) for the reset link
            5. Click the link within 24 hours (it expires after that)
            6. Create a new password meeting our security requirements:
               - At least 8 characters
               - Include uppercase and lowercase letters
               - Include at least one number
               - Include at least one special character
            
            Account Recovery (if you no longer have access to your email):
            1. Contact support with your account details
            2. Verify identity through alternative methods
            3. Support will update your email and send a reset link
            
            Common Issues:
            - Reset email not arriving: Check spam/junk folder
            - Link expired: Request a new reset link
            - "Email not found": Verify the email you registered with
        """,
    },
    {
        "title": "Billing & Subscription Management",
        "category": "billing",
        "content": """
            Understanding your billing, managing subscriptions, and handling
            refund requests.
            
            Billing Cycles:
            - All subscriptions are billed monthly on the date you signed up
            - You can view your billing date in Settings > Billing > Overview
            - Invoices are emailed automatically and available in the dashboard
            
            Changing Your Plan:
            - Upgrades take effect immediately (prorated charge)
            - Downgrades take effect at the next billing cycle
            - Navigate to Settings > Billing > Change Plan
            
            Refund Policy:
            - Full refund within 14 days of initial purchase
            - Prorated refund for annual plans cancelled mid-term
            - No refund for promotional or discounted purchases
            - Submit refund requests through Settings > Billing > Request Refund
            
            Payment Methods:
            - We accept Visa, Mastercard, American Express
            - PayPal and bank transfer available for annual plans
            - Update payment: Settings > Billing > Payment Method
        """,
    },
    # ... more articles for technical support, features, etc.
]


def chunk_text(text: str, max_words: int = 200) -> list[str]:
    """
    Split text into chunks of approximately max_words.
    
    WHY CHUNK:
        Embedding models work best with short text (100-500 words).
        A 2000-word article would produce a vague embedding
        that doesn't match specific queries well.
        
        Smaller chunks = more precise matching.
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    current_chunk = []
    current_length = 0
    
    for paragraph in paragraphs:
        words = len(paragraph.split())
        if current_length + words > max_words and current_chunk:
            chunks.append("\n\n".join(current_chunk))
            current_chunk = [paragraph]
            current_length = words
        else:
            current_chunk.append(paragraph)
            current_length += words
    
    if current_chunk:
        chunks.append("\n\n".join(current_chunk))
    
    return chunks


async def seed():
    """Main seeding function."""
    setup_logging(log_level="INFO")
    
    # Initialize database and embedding model
    await init_db()
    embedding_service = EmbeddingService.get_instance()
    embedding_service.load_model()
    
    async with async_session_factory() as session:
        # Clear existing data
        await session.execute(text("DELETE FROM kb_embeddings"))
        await session.execute(text("DELETE FROM knowledge_articles"))
        await session.commit()
        
        for article_data in ARTICLES:
            # 1. Create the article record
            article = KnowledgeArticle(
                title=article_data["title"],
                content=article_data["content"],
                category=article_data["category"],
            )
            session.add(article)
            await session.flush()  # Get the UUID
            
            # 2. Chunk the content
            chunks = chunk_text(article_data["content"])
            
            # 3. Embed all chunks in batch
            embeddings = embedding_service.embed_batch(chunks)
            
            # 4. Create embedding records
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                kb_embedding = KBEmbedding(
                    article_id=article.id,
                    chunk_text=chunk,
                    chunk_index=i,
                    embedding=embedding,
                )
                session.add(kb_embedding)
            
            logger.info(
                "article_seeded",
                title=article_data["title"],
                chunks=len(chunks),
            )
        
        await session.commit()
    
    logger.info("kb_seeding_complete", total_articles=len(ARTICLES))


if __name__ == "__main__":
    asyncio.run(seed())
```

**The chunking strategy matters:**

```python
# Bad: embed the entire 2000-word article as one vector
embedding = embed("Complete guide to password reset... [2000 words]")
# Result: vague vector that doesn't match specific queries well

# Good: embed each section separately
embedding_1 = embed("Self-Service Password Reset: 1. Navigate to login...")
embedding_2 = embed("Account Recovery: Contact support with...")
embedding_3 = embed("Common Issues: Reset email not arriving...")
# Result: precise vectors that match specific queries accurately
```

A customer asking "reset email not arriving" will match chunk #3 perfectly,
but would only weakly match the full 2000-word article.

---

That completes Part 5. The RAG pipeline is:
1. ✅ Embed customer query using local sentence-transformers
2. ✅ Search PostgreSQL using pgvector cosine distance
3. ✅ Fall back to keyword search if DB is unavailable
4. ✅ Pass retrieved context to the resolver for grounded answers
5. ✅ Seeding script to populate the KB with articles + embeddings

---

# Part 6: FastAPI REST API Layer

The API layer translates HTTP requests into business operations. It's the
"front door" of your backend — everything the frontend does goes through here.

## 6.1 API Design Principles

Before writing routes, establish conventions:

| Convention | Rule | Example |
|-----------|------|---------|
| Base path | `/api/v1/` | Versioning from day one |
| Resource naming | Plural nouns | `/tickets`, not `/ticket` |
| HTTP methods | Standard REST | GET=read, POST=create, PUT=update, DELETE=remove |
| Response format | Consistent JSON | `{"ticket": {...}}` or `{"tickets": [...], "total": 42}` |
| Errors | HTTP status codes | 400=bad input, 401=no auth, 403=wrong role, 404=not found |
| Pagination | Offset-based | `?limit=20&offset=0` |
| Filters | Query params | `?status=open&priority=high` |

**Why `/api/v1/`?**

API versioning prevents breaking changes. If you redesign the ticket schema,
you can serve `/api/v2/tickets` with the new format while keeping `/api/v1/tickets`
working for existing clients.

## 6.2 File 22: `src/api/schemas/ticket.py` — Request/Response Validation

Pydantic schemas ensure that:
- Incoming data is valid (correct types, required fields present)
- Outgoing data is consistent (same shape every time)
- API documentation is auto-generated (Swagger UI reads these models)

```python
"""
src/api/schemas/ticket.py — Pydantic models for request/response validation.

CONVENTION:
    - *Create schemas = what the client sends to CREATE something
    - *Response schemas = what the server sends BACK
    - *Update schemas = what the client sends to MODIFY something
    - *Filter schemas = query parameters for listing/searching
"""

from pydantic import BaseModel, Field, EmailStr
from datetime import datetime
from typing import Literal


# === Request Schemas ===

class TicketCreate(BaseModel):
    """What the frontend sends to create a ticket."""
    subject: str = Field(
        min_length=3,
        max_length=500,
        description="Brief description of the issue",
        examples=["Cannot reset my password"],
    )
    message: str = Field(
        min_length=10,
        max_length=5000,
        description="Detailed description of the issue",
    )
    channel: Literal["web", "email", "api", "chat"] = Field(
        default="web",
        description="How the ticket was submitted",
    )


class MessageCreate(BaseModel):
    """What the frontend sends to add a follow-up message."""
    content: str = Field(
        min_length=1,
        max_length=5000,
        description="Message content",
    )


class StatusUpdate(BaseModel):
    """Update the ticket status."""
    status: Literal[
        "open", "pending_customer", "pending_agent",
        "escalated", "resolved", "closed",
    ]


# === Response Schemas ===

class TicketResponse(BaseModel):
    """Ticket data sent back to the client."""
    id: str
    subject: str
    status: str
    priority: str
    category: str | None = None
    customer_email: str | None = None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None = None
    ai_context: dict = {}
    
    model_config = {"from_attributes": True}  # Read from ORM objects


class TicketDetailResponse(BaseModel):
    """Detailed ticket view with messages and actions."""
    ticket: TicketResponse
    messages: list[dict]
    actions: list[dict]


class TicketListResponse(BaseModel):
    """Paginated list of tickets."""
    tickets: list[TicketResponse]
    total: int
    limit: int
    offset: int
```

**Key concept: `model_config = {"from_attributes": True}`**

This allows Pydantic to read data from SQLAlchemy model attributes:

```python
# Without from_attributes (manual conversion):
return TicketResponse(
    id=str(ticket.id),
    subject=ticket.subject,
    status=ticket.status,
    # ... every field manually
)

# With from_attributes (automatic):
return TicketResponse.model_validate(ticket)
# Pydantic reads ticket.id, ticket.subject, etc. automatically
```

**Why `Field(min_length=3)`?**

Validates at the Pydantic level. If someone sends `{"subject": ""}`,
FastAPI automatically returns a 422 error with a clear message:
```json
{
    "detail": [{
        "type": "string_too_short",
        "loc": ["body", "subject"],
        "msg": "String should have at least 3 characters"
    }]
}
```

## 6.3 File 23: `src/api/routes/tickets.py` — Customer Ticket Routes

This is the largest route file. Let's walk through the key endpoints:

```python
"""
src/api/routes/tickets.py — Customer-facing ticket endpoints.

ENDPOINTS:
    POST   /tickets           — Create a new ticket (triggers AI processing)
    GET    /tickets           — List the current user's tickets
    GET    /tickets/{id}      — Get ticket details with messages
    POST   /tickets/{id}/messages — Add a follow-up message
    PUT    /tickets/{id}/status   — Update ticket status
    POST   /tickets/{id}/resolve  — Mark ticket as resolved
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps.auth import get_current_user, CurrentUser
from src.api.schemas.ticket import (
    TicketCreate, MessageCreate, StatusUpdate,
    TicketResponse, TicketDetailResponse, TicketListResponse,
)
from src.db.session import get_db_session
from src.db.repositories import ticket_repo, customer_repo
from src.agents.graph import process_ticket
from src.utils.logging import get_logger
from src.utils.metrics import increment, track_latency

logger = get_logger(__name__)

router = APIRouter(prefix="/tickets", tags=["Tickets"])


@router.post("", response_model=TicketResponse, status_code=201)
async def create_ticket(
    data: TicketCreate,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Create a new support ticket and process it with the AI agent.
    
    FLOW:
        1. Get or create customer record
        2. Create ticket in DB
        3. Add the customer's message
        4. Run AI pipeline (classify → search → resolve → validate)
        5. Save AI response as a message
        6. Update ticket with classification data
        7. Return the ticket
    """
    # Step 1: Customer
    customer, is_new = await customer_repo.get_or_create_customer(
        db, email=user.email, name=user.email.split("@")[0],
    )
    if is_new:
        logger.info("new_customer_created", email=user.email)
    
    # Step 2: Ticket
    ticket = await ticket_repo.create_ticket(
        db, customer_id=customer.id, subject=data.subject,
    )
    
    # Step 3: Customer message
    await ticket_repo.add_message(
        db, ticket_id=ticket.id,
        sender_type="customer", content=data.message,
    )
    
    # Step 4: AI processing
    async with track_latency("agent_processing"):
        ai_result = await process_ticket(
            ticket_id=str(ticket.id),
            customer_email=user.email,
            subject=data.subject,
            message=data.message,
            channel=data.channel,
        )
    
    # Step 5: Save AI response
    if ai_result.get("final_response"):
        await ticket_repo.add_message(
            db, ticket_id=ticket.id,
            sender_type="ai_agent",
            content=ai_result["final_response"],
        )
    
    # Step 6: Update ticket with AI data
    ticket.priority = ai_result.get("priority", "medium")
    ticket.category = ai_result.get("category")
    ticket.status = "escalated" if ai_result.get("needs_escalation") else "open"
    ticket.ai_context = {
        "intent": ai_result.get("intent"),
        "sentiment": ai_result.get("sentiment"),
        "confidence": ai_result.get("confidence"),
    }
    
    # Step 7: Save audit trail
    for action in ai_result.get("actions_taken", []):
        await ticket_repo.add_agent_action(
            db, ticket_id=ticket.id,
            action_type=action["action_type"],
            action_data=action.get("action_data", {}),
            reasoning=action.get("reasoning", ""),
            outcome=action.get("outcome", ""),
        )
    
    increment("tickets_created")
    await db.flush()
    
    logger.info(
        "ticket_created",
        ticket_id=str(ticket.id),
        priority=ticket.priority,
        escalated=ticket.status == "escalated",
    )
    
    return ticket


@router.get("", response_model=TicketListResponse)
async def list_tickets(
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    status: str | None = Query(None, description="Filter by status"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """List the current user's tickets with pagination."""
    tickets, total = await ticket_repo.list_tickets(
        db, customer_email=user.email,
        status=status, limit=limit, offset=offset,
    )
    return TicketListResponse(
        tickets=[TicketResponse.model_validate(t) for t in tickets],
        total=total, limit=limit, offset=offset,
    )


@router.get("/{ticket_id}", response_model=TicketDetailResponse)
async def get_ticket(
    ticket_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Get detailed ticket info with full message history and audit trail."""
    ticket = await ticket_repo.get_ticket_by_id(db, ticket_id)
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Authorization: customers can only see their own tickets
    if ticket.customer.email != user.email and user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    
    return TicketDetailResponse(
        ticket=TicketResponse.model_validate(ticket),
        messages=[...],  # Simplified for brevity
        actions=[...],
    )
```

**Key architectural patterns:**

1. **Dependency injection via `Depends()`:**

   ```python
   async def create_ticket(
       data: TicketCreate,              # Auto-parsed from request body
       user: CurrentUser = Depends(get_current_user),  # JWT decoded
       db: AsyncSession = Depends(get_db_session),      # DB session
   ):
   ```

   FastAPI calls `get_current_user` and `get_db_session` before your function
   runs. If auth fails, your function is never called (401 error returned).
   If DB fails, your function is never called (500 error).

2. **The create_ticket flow is the most complex endpoint:**

   It orchestrates multiple layers:
   - Repository layer (customer_repo, ticket_repo)
   - AI layer (process_ticket)
   - Metrics layer (track_latency, increment)
   - Logging layer (structured logging)

   Each layer is independent — you can test the repository without the AI,
   test the AI without the database, etc.

3. **Authorization inline:**

   ```python
   if ticket.customer.email != user.email and user.role != "admin":
       raise HTTPException(status_code=403, detail="Access denied")
   ```

   Customers can only see their own tickets. Admins can see everything.
   This is object-level authorization.

## 6.4 File 24: `src/api/routes/admin.py` — Admin Panel Routes

Admin routes are similar to customer routes but with broader access and
additional capabilities:

```python
"""
src/api/routes/admin.py — Admin-only endpoints.

ALL ENDPOINTS require admin role (enforced by require_admin dependency).
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps.auth import require_admin, CurrentUser
from src.db.session import get_db_session
from src.db.repositories import ticket_repo
from src.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/conversations")
async def list_all_conversations(
    admin: CurrentUser = Depends(require_admin),  # Admin-only!
    db: AsyncSession = Depends(get_db_session),
    status: str | None = Query(None),
    priority: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """
    List ALL conversations across all customers.
    
    Unlike /tickets (which shows only the current user's tickets),
    this shows everything — for admin oversight.
    """
    tickets, total = await ticket_repo.list_tickets(
        db, status=status, priority=priority,
        limit=limit, offset=offset,
        # No customer_email filter = all customers
    )
    return {
        "conversations": [format_conversation(t) for t in tickets],
        "total": total,
    }


@router.post("/conversations/{ticket_id}/reply")
async def admin_reply(
    ticket_id: str,
    data: dict,
    admin: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
):
    """Allow admin to reply to a ticket as a human agent."""
    ticket = await ticket_repo.get_ticket_by_id(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Add the admin's reply
    await ticket_repo.add_message(
        db, ticket_id=ticket.id,
        sender_type="human_agent",
        content=data["content"],
        metadata={"admin_email": admin.email},
    )
    
    # Update ticket status
    ticket.status = "pending_customer"
    
    logger.info(
        "admin_reply",
        ticket_id=ticket_id,
        admin=admin.email,
    )
    
    return {"status": "reply_sent"}


@router.post("/conversations/{ticket_id}/resolve")
async def admin_resolve(
    ticket_id: str,
    admin: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
):
    """Admin resolves a ticket."""
    ticket = await ticket_repo.get_ticket_by_id(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    ticket.status = "resolved"
    ticket.resolved_by = "human"
    ticket.resolved_at = datetime.now(timezone.utc)
    
    return {"status": "resolved"}
```

**The difference between `get_current_user` and `require_admin`:**

```python
# Customer route — any authenticated user
@router.get("/tickets")
async def list_tickets(user: CurrentUser = Depends(get_current_user)):
    # user.role could be "customer" or "admin"

# Admin route — admin role required
@router.get("/admin/conversations")
async def list_all(admin: CurrentUser = Depends(require_admin)):
    # admin.role is guaranteed to be "admin"
    # Non-admins get a 403 error automatically
```

---

# Part 7: Authentication & Authorization

Authentication answers "who are you?" Authorization answers "what can you do?"

## 7.1 How Supabase Auth Works

```
┌─────────────┐     1. Login (email+password)      ┌──────────────┐
│   Frontend   │ ──────────────────────────────────► │  Supabase    │
│   (Next.js)  │                                     │  Auth Server │
│              │ ◄────────────────────────────────── │              │
└──────┬───────┘     2. Returns JWT token            └──────────────┘
       │
       │  3. API call with JWT in Authorization header
       │     Authorization: Bearer eyJhbGciOiJ...
       ▼
┌─────────────┐     4. Verify JWT signature          ┌──────────────┐
│   Backend    │ ──────────────────────────────────► │  Supabase    │
│   (FastAPI)  │     (using Supabase's public keys)  │  JWKS endpoint│
│              │                                     └──────────────┘
└─────────────┘     5. Extract user_id, email, role
```

**The JWT token contains:**

```json
{
  "aud": "authenticated",
  "exp": 1707123456,
  "sub": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",  // user_id
  "email": "customer@example.com",
  "user_metadata": {
    "role": "customer"  // or "admin"
  }
}
```

The backend NEVER talks to the Supabase database for auth. It verifies
the JWT signature using cryptographic keys — fast and stateless.

## 7.2 File 25: `src/api/deps/auth.py` — JWT Verification

```python
"""
src/api/deps/auth.py — Authentication dependencies for FastAPI.

HOW JWT VERIFICATION WORKS:
    1. Client sends: Authorization: Bearer <token>
    2. We decode the JWT header (without verifying) to read the key ID (kid)
    3. We fetch Supabase's public keys (JWKS) from their endpoint
    4. We find the matching key and verify the JWT signature
    5. If valid: extract user_id, email, role
    6. If invalid: return 401 Unauthorized
"""

from dataclasses import dataclass
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from jwt import PyJWKClient

from src.config import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)

# FastAPI security scheme — expects "Authorization: Bearer <token>"
security = HTTPBearer()

# JWKS client — fetches and caches Supabase's public keys
jwks_url = f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json"
jwks_client = PyJWKClient(jwks_url, cache_keys=True)


@dataclass
class CurrentUser:
    """Represents the authenticated user."""
    id: str           # UUID from JWT sub claim
    email: str
    role: str         # "customer" or "admin"


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> CurrentUser:
    """
    Decode and verify the JWT token.
    
    VERIFICATION STEPS:
        1. Get the signing key from Supabase's JWKS endpoint
        2. Decode the JWT with signature verification
        3. Check that the token hasn't expired
        4. Extract user claims (id, email, role)
    
    SUPPORTED ALGORITHMS:
        - ES256 (Elliptic Curve) — default for Supabase
        - EdDSA (Edwards Curve)
        - HS256 (HMAC) — fallback
    """
    token = credentials.credentials
    
    try:
        # Try asymmetric verification first (ES256/EdDSA)
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256", "EdDSA"],
            audience="authenticated",  # Supabase sets this
        )
    except Exception:
        try:
            # Fallback: symmetric verification (HS256)
            payload = jwt.decode(
                token,
                settings.SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                audience="authenticated",
            )
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
            )
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}",
            )
    
    # Extract user info from JWT claims
    user_id = payload.get("sub")
    email = payload.get("email", "")
    
    # Role from user_metadata (set during Supabase signup or via admin API)
    user_metadata = payload.get("user_metadata", {})
    role = user_metadata.get("role", "customer")
    
    return CurrentUser(id=user_id, email=email, role=role)


async def require_admin(
    user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """
    Require admin role. Use as a dependency on admin-only routes.
    
    DEPENDENCY CHAIN:
        require_admin depends on get_current_user
        get_current_user depends on HTTPBearer
        
        So: Extract token → verify JWT → check role → proceed (or 403)
    """
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user
```

**Why JWKS instead of a hardcoded secret?**

```python
# Hardcoded secret (HS256 — symmetric):
jwt.decode(token, "my-secret-key", algorithms=["HS256"])
# Problem: secret must be shared between client and server
# If the secret leaks, anyone can forge tokens

# JWKS (ES256 — asymmetric):
signing_key = jwks_client.get_signing_key_from_jwt(token)
jwt.decode(token, signing_key.key, algorithms=["ES256"])
# Only Supabase has the PRIVATE key (to sign tokens)
# We only need the PUBLIC key (to verify tokens)
# Even if the public key leaks, no one can forge tokens
```

**The fallback chain: ES256 → HS256**

Supabase has changed their JWT algorithm over time. Some projects use ES256
(newer), some use HS256 (older). Our code tries both:

```python
try:
    # Modern: asymmetric (ES256/EdDSA)
    signing_key = jwks_client.get_signing_key_from_jwt(token)
    payload = jwt.decode(token, signing_key.key, ...)
except Exception:
    # Legacy: symmetric (HS256)
    payload = jwt.decode(token, settings.SUPABASE_JWT_SECRET, ...)
```

**`cache_keys=True` is a performance optimization:**

Without caching, every request would make an HTTP call to Supabase to fetch
the public keys. With caching, we fetch once and reuse until rotation.

## 7.3 Role-Based Access Control (RBAC)

Our system has two roles:

| Role | Can Do | Set Via |
|------|--------|---------|
| `customer` | Create tickets, view own tickets, send messages | Default on signup |
| `admin` | View all tickets, reply as agent, resolve, close | Set via `user_metadata.role` in Supabase |

**How to make a user an admin:**

In the Supabase dashboard → Authentication → Users → select user →
Edit User → Raw User Meta Data:
```json
{
  "role": "admin"
}
```

Or via the Supabase admin API:
```python
supabase.auth.admin.update_user_by_id(
    user_id, {"user_metadata": {"role": "admin"}}
)
```

**Security layers (defense in depth):**

```
Layer 1: Frontend        — Hides admin UI from non-admins
Layer 2: JWT Middleware   — Rejects requests without valid tokens
Layer 3: Role Dependency  — Rejects non-admin tokens on admin routes
Layer 4: Object-level    — Customers can only access their own tickets
Layer 5: Database        — CHECK constraints prevent invalid data
```

Each layer assumes the previous layer might fail. This is the principle of
defense in depth — no single layer is the "security layer."

---

Parts 6-7 covered:
- ✅ Pydantic schemas for request/response validation
- ✅ Customer-facing ticket routes with AI integration
- ✅ Admin-only routes with role enforcement
- ✅ JWT verification with JWKS (asymmetric) and HS256 (fallback)
- ✅ Role-based access control with dependency injection
- ✅ Defense-in-depth security model

---

# Part 8: Frontend — Next.js 15

The frontend is a Next.js 15 application that provides the user interface
for both customers and admins. It communicates with the backend exclusively
through the REST API.

## 8.1 Frontend Architecture

```
frontend/
├── src/
│   └── app/
│       ├── page.tsx              # Main page (login + dashboard + ticket detail)
│       ├── layout.tsx            # Root layout with providers
│       └── globals.css           # Global styles
├── lib/
│   ├── supabase.ts              # Supabase client configuration
│   └── api.ts                   # API client for backend calls
├── hooks/
│   └── useAuth.ts               # Authentication hook
├── components/                   # Reusable UI components
├── .env.local                   # Environment variables (Supabase URL/key)
├── next.config.ts               # Next.js configuration
├── package.json                 # Dependencies
└── tsconfig.json                # TypeScript configuration
```

**Why a single-page application (SPA) pattern in Next.js?**

Our app is a dashboard — all views share the same authenticated context.
Instead of separate pages for login, dashboard, and ticket detail, we
use a single page with state-driven rendering:

```typescript
// Simplified page.tsx flow:
export default function Home() {
  const { user, isLoading } = useAuth();
  const [selectedTicket, setSelectedTicket] = useState(null);

  if (isLoading) return <LoadingSpinner />;
  if (!user) return <LoginForm />;
  
  if (selectedTicket) {
    return <TicketDetail ticket={selectedTicket} />;
  }
  
  return <Dashboard onSelectTicket={setSelectedTicket} />;
}
```

This gives instant navigation (no page reload) and keeps the auth
state in memory.

## 8.2 Supabase Client Setup

```typescript
// lib/supabase.ts
import { createClient } from "@supabase/supabase-js";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

export const supabase = createClient(supabaseUrl, supabaseAnonKey);
```

**Why `NEXT_PUBLIC_` prefix?**

Next.js only exposes environment variables to the browser if they start with
`NEXT_PUBLIC_`. Variables without this prefix are server-only (never sent to
the client). Since the Supabase anon key is designed to be public (it only
grants row-level security access), it's safe to use `NEXT_PUBLIC_`.

## 8.3 Authentication Hook

```typescript
// hooks/useAuth.ts
import { useState, useEffect } from "react";
import { supabase } from "@/lib/supabase";
import type { User, Session } from "@supabase/supabase-js";

export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Get initial session
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      setUser(session?.user ?? null);
      setIsLoading(false);
    });

    // Listen for auth state changes (login, logout, token refresh)
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (_event, session) => {
        setSession(session);
        setUser(session?.user ?? null);
      }
    );

    // Cleanup subscription on unmount
    return () => subscription.unsubscribe();
  }, []);

  const signIn = async (email: string, password: string) => {
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) throw error;
  };

  const signUp = async (email: string, password: string) => {
    const { error } = await supabase.auth.signUp({ email, password });
    if (error) throw error;
  };

  const signOut = async () => {
    await supabase.auth.signOut();
  };

  return { user, session, isLoading, signIn, signUp, signOut };
}
```

**Why `onAuthStateChange`?**

Supabase auto-refreshes JWT tokens when they're about to expire. Without
`onAuthStateChange`, the UI wouldn't update with the new token, and API
calls would start failing with 401 errors.

The listener detects:
- `SIGNED_IN` — user logged in
- `SIGNED_OUT` — user logged out
- `TOKEN_REFRESHED` — token auto-refreshed (silent)
- `USER_UPDATED` — user metadata changed

## 8.4 API Client

```typescript
// lib/api.ts
import { supabase } from "@/lib/supabase";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function apiCall(endpoint: string, options: RequestInit = {}) {
  // Get the current JWT token from Supabase session
  const { data: { session } } = await supabase.auth.getSession();
  const token = session?.access_token;

  if (!token) throw new Error("Not authenticated");

  const response = await fetch(`${API_BASE}/api/v1${endpoint}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${token}`,  // JWT in every request
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

// API methods
export const api = {
  // Customer API
  createTicket: (data: { subject: string; message: string }) =>
    apiCall("/tickets", { method: "POST", body: JSON.stringify(data) }),

  getTickets: (params?: { status?: string; limit?: number; offset?: number }) =>
    apiCall(`/tickets?${new URLSearchParams(params as any)}`),

  getTicket: (id: string) =>
    apiCall(`/tickets/${id}`),

  addMessage: (ticketId: string, content: string) =>
    apiCall(`/tickets/${ticketId}/messages`, {
      method: "POST",
      body: JSON.stringify({ content }),
    }),

  // Admin API
  getConversations: (params?: Record<string, string>) =>
    apiCall(`/admin/conversations?${new URLSearchParams(params)}`),

  adminReply: (ticketId: string, content: string) =>
    apiCall(`/admin/conversations/${ticketId}/reply`, {
      method: "POST",
      body: JSON.stringify({ content }),
    }),
};
```

**Why a centralized API client?**

Without it, every component would need to:
1. Get the session
2. Extract the token
3. Build the URL
4. Set headers
5. Handle errors

With the API client, components just call `api.createTicket(data)`.

## 8.5 Frontend Components Overview

The key UI components and their responsibilities:

### Login Form

```typescript
// Simplified login component
function LoginForm() {
  const { signIn, signUp } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isSignUp, setIsSignUp] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    try {
      if (isSignUp) {
        await signUp(email, password);
        // Show "check your email" message
      } else {
        await signIn(email, password);
        // useAuth will update user state → page re-renders with Dashboard
      }
    } catch (err: any) {
      setError(err.message);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <input type="email" value={email} onChange={e => setEmail(e.target.value)} />
      <input type="password" value={password} onChange={e => setPassword(e.target.value)} />
      <button type="submit">{isSignUp ? "Sign Up" : "Sign In"}</button>
      <button type="button" onClick={() => setIsSignUp(!isSignUp)}>
        {isSignUp ? "Have an account? Sign in" : "Need an account? Sign up"}
      </button>
      {error && <p className="error">{error}</p>}
    </form>
  );
}
```

### Dashboard (Ticket List)

```typescript
function Dashboard({ onSelectTicket, isAdmin }) {
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchTickets = async () => {
      const data = isAdmin
        ? await api.getConversations()
        : await api.getTickets();
      setTickets(data.tickets || data.conversations);
      setLoading(false);
    };
    fetchTickets();
  }, [isAdmin]);

  if (loading) return <LoadingSpinner />;

  return (
    <div className="dashboard">
      <TicketGrid
        tickets={tickets}
        onSelect={onSelectTicket}
      />
    </div>
  );
}
```

### Ticket Detail (Chat View)

```typescript
function TicketDetail({ ticketId }) {
  const [ticket, setTicket] = useState(null);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState("");

  useEffect(() => {
    api.getTicket(ticketId).then(data => {
      setTicket(data.ticket);
      setMessages(data.messages);
    });
  }, [ticketId]);

  const sendMessage = async () => {
    if (!newMessage.trim()) return;
    await api.addMessage(ticketId, newMessage);
    setNewMessage("");
    // Refresh messages
    const data = await api.getTicket(ticketId);
    setMessages(data.messages);
  };

  return (
    <div className="ticket-detail">
      {/* Header with ticket info */}
      <div className="header">
        <h2>{ticket?.subject}</h2>
        <StatusBadge status={ticket?.status} />
        <PriorityBadge priority={ticket?.priority} />
      </div>

      {/* Message thread */}
      <div className="messages">
        {messages.map(msg => (
          <MessageBubble
            key={msg.id}
            content={msg.content}
            sender={msg.sender_type}
            timestamp={msg.created_at}
          />
        ))}
      </div>

      {/* Input area */}
      <div className="input-area">
        <textarea
          value={newMessage}
          onChange={e => setNewMessage(e.target.value)}
          placeholder="Type a follow-up message..."
        />
        <button onClick={sendMessage}>Send</button>
      </div>
    </div>
  );
}
```

**The chat view follows the standard messaging pattern:**

```
┌─────────────────────────────────────────┐
│  Subject: Cannot reset my password      │
│  Status: open   Priority: high          │
├─────────────────────────────────────────┤
│                                         │
│  [Customer] I can't reset my password   │
│  10:30 AM                               │
│                                         │
│          [AI Agent] To reset your        │
│          password, go to Settings >      │
│          Security > Reset Password...    │
│          10:30 AM                        │
│                                         │
│  [Customer] That didn't work, the       │
│  email never arrives                    │
│  10:35 AM                               │
│                                         │
├─────────────────────────────────────────┤
│  [Type a message...              ] Send │
└─────────────────────────────────────────┘
```

Messages are rendered differently based on `sender_type`:
- Customer messages → left-aligned, one color
- AI/Agent messages → right-aligned, different color
- System messages → centered, gray

## 8.6 Frontend ↔ Backend Flow

Here's the complete flow for creating a ticket:

```
1. User fills out form and clicks "Submit"
   └── Frontend calls api.createTicket({ subject, message })

2. API client gets JWT from Supabase session
   └── Adds "Authorization: Bearer <jwt>" header

3. Fetch POST /api/v1/tickets with JSON body
   └── Hits FastAPI server

4. FastAPI extracts JWT → get_current_user dependency
   └── Verifies signature, extracts user.email

5. FastAPI parses body → TicketCreate schema
   └── Validates min_length, max_length

6. Route handler runs:
   a. get_or_create_customer(email)
   b. create_ticket(customer_id, subject)
   c. add_message(ticket_id, "customer", message)
   d. process_ticket(ticket_id, ...) → AI pipeline
   e. add_message(ticket_id, "ai_agent", response)
   f. Update ticket status/priority

7. Returns HTTP 201 with ticket JSON

8. Frontend receives response
   └── Updates state → re-renders ticket list
```

---

# Part 9: Integration, Testing & Deployment

## 9.1 Running the Project Locally

### Backend

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy and fill environment variables
cp .env.example .env
# Edit .env with your Supabase URL, keys, and LLM API key

# 4. Seed the knowledge base (once)
python -m scripts.seed_kb

# 5. Start the backend server
uvicorn src.main:app --reload --port 8000
```

### Frontend

```bash
# 1. Navigate to frontend directory
cd frontend

# 2. Install dependencies
npm install

# 3. Copy environment variables
cp .env.example .env.local
# Edit with NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY, NEXT_PUBLIC_API_URL

# 4. Start the development server
npm run dev
# Opens at http://localhost:3000
```

## 9.2 Testing Strategy

### Testing Layers

```
┌─────────────────────────────────────┐
│     End-to-End Tests (E2E)         │  ← Least: full flow, slow
│   Frontend → API → DB → AI Agent   │
├─────────────────────────────────────┤
│     Integration Tests              │  ← Middle: API endpoints
│   API routes with test DB          │
├─────────────────────────────────────┤
│     Unit Tests                     │  ← Most: individual functions
│   Repos, nodes, conditions, etc.   │
└─────────────────────────────────────┘
```

### Unit Test Examples

```python
# tests/test_conditions.py
"""Test the escalation condition functions in isolation."""

from src.agents.edges.conditions import (
    should_escalate_after_classify,
    should_escalate_after_validate,
)


def test_escalate_urgent_angry():
    """Urgent + angry → escalate."""
    state = {"priority": "urgent", "sentiment": "angry", "confidence": 0.95}
    assert should_escalate_after_classify(state) == "escalate"


def test_no_escalate_normal():
    """Medium priority + neutral → proceed to KB search."""
    state = {"priority": "medium", "sentiment": "neutral", "confidence": 0.85}
    assert should_escalate_after_classify(state) == "search_kb"


def test_escalate_low_confidence():
    """Low confidence → escalate (AI isn't sure)."""
    state = {"priority": "medium", "sentiment": "neutral", "confidence": 0.3}
    assert should_escalate_after_classify(state) == "escalate"


def test_finalize_when_response_exists():
    """If final_response is set, validation passed → finalize."""
    state = {"final_response": "Your issue has been resolved."}
    assert should_escalate_after_validate(state) == "finalize"


def test_retry_when_under_max_attempts():
    """If no final_response and under max attempts → retry."""
    state = {"attempts": 1}
    assert should_escalate_after_validate(state) == "respond"


def test_escalate_after_max_attempts():
    """If no final_response and max attempts reached → escalate."""
    state = {"attempts": 3}
    assert should_escalate_after_validate(state) == "escalate"
```

```python
# tests/test_validator.py
"""Test response validation logic."""

import pytest
from src.agents.nodes.validator import validate_response


@pytest.mark.asyncio
async def test_valid_response():
    """A good response should pass validation."""
    state = {"draft_response": "Thank you for reaching out! " * 10}
    result = await validate_response(state)
    assert "final_response" in result  # Promoted to final


@pytest.mark.asyncio
async def test_empty_response():
    """Empty responses should fail validation."""
    state = {"draft_response": ""}
    result = await validate_response(state)
    assert "final_response" not in result  # Not promoted


@pytest.mark.asyncio
async def test_uncertain_response():
    """Responses with uncertainty markers should fail."""
    state = {"draft_response": "I don't know the answer to your question, but..."}
    result = await validate_response(state)
    assert "final_response" not in result
```

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_conditions.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

## 9.3 Environment Configuration

### Required Environment Variables

```env
# === Database (from Supabase Dashboard > Settings > Database) ===
DATABASE_URL=postgresql+asyncpg://postgres.xxx:password@aws-0-us-east-1.pooler.supabase.com:6543/postgres

# === Supabase Auth (from Dashboard > Settings > API) ===
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_JWT_SECRET=your-jwt-secret-from-api-settings

# === LLM Provider (choose one) ===
LLM_PROVIDER=google
GOOGLE_API_KEY=AIzaSy...
# OR
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_...

# === Optional: LangSmith Tracing ===
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_pt_...
LANGCHAIN_PROJECT=customer-support-agent
```

**Port 6543 (not 5432):**

Supabase provides two connection methods:
- Port 5432 → direct connection (limited to 60 connections)
- Port 6543 → connection pooler (PgBouncer/Supavisor, supports thousands)

Always use port 6543 for backend applications. It handles connection pooling
at the infrastructure level.

## 9.4 Deployment Considerations

For production deployment, consider these changes:

### Backend (e.g., Railway, Render, Fly.io)

```bash
# Dockerfile for production
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt --no-cache-dir

COPY . .

# Start with production settings
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Production config changes:**
```env
APP_ENV=production
DEBUG=false
LOG_LEVEL=INFO
LLM_TEMPERATURE=0.3
```

### Frontend (Vercel — recommended for Next.js)

```bash
# Just connect your Git repo to Vercel
# Set environment variables in Vercel dashboard
# Deploys automatically on push
```

### Key Production Checklist

- [ ] Set `DEBUG=false` in production
- [ ] Use `LOG_LEVEL=INFO` (not DEBUG)
- [ ] Enable `LANGCHAIN_TRACING_V2=true` for observability
- [ ] Set CORS origins to your actual domain
- [ ] Use HTTPS for all communication
- [ ] Set up database backups in Supabase
- [ ] Monitor error rates and latency
- [ ] Configure rate limiting for API endpoints

---

# Part 10: Lessons Learned & How to Think About Similar Projects

## 10.1 Key Architectural Decisions (and Why They Matter)

### 1. Start with the data model

The database schema drives everything. Once you define `Ticket`, `Message`,
`Customer`, and `Agent`, the rest of the application naturally follows.

**If you change the schema later, everything breaks** — migrations, queries,
API responses, frontend rendering. Get the schema right first.

### 2. Build in layers

```
Foundation (config, logging) → Database → AI Agent → API → Frontend
```

Each layer only depends on layers below it. The AI agent doesn't know
about HTTP routes. The API doesn't know about React components.
This is the **dependency inversion principle** in practice.

### 3. Always have a fallback

Every external dependency (LLM API, database, embedding model) can fail.
Our code handles this:
- LLM fails → safe default classification + error audit trail
- Vector search fails → keyword fallback
- Response invalid → retry loop → escalation
- Auth fails → clear HTTP error code

**The system degrades gracefully instead of crashing.**

### 4. Audit everything

The `actions_taken` list in the AI pipeline and the `agent_actions` table
in the database create a complete record of every AI decision. This is
critical for:
- **Debugging:** "Why did the AI say this?" → check the audit trail
- **Compliance:** "What happened to ticket X?" → full history
- **Testing:** "Did the AI improve?" → compare prompts and results
- **Trust:** "Can I trust the AI?" → show the reasoning

### 5. Separate "what it does" from "how it does it"

```python
# What: process a ticket through the AI pipeline
result = await process_ticket(ticket_id, email, subject, message)

# How: classified → searched KB → generated response → validated → finalized
# The route handler doesn't know or care about the internal pipeline.
```

This is the **abstraction principle**. `process_ticket()` could use
LangGraph, a simple if/else chain, or a third-party API — the route
handler wouldn't change.

## 10.2 Design Patterns Used in This Project

| Pattern | Where | Why |
|---------|-------|-----|
| **Repository** | `ticket_repo.py`, `customer_repo.py` | Isolate database queries from business logic |
| **Factory** | `llm.py` | Create LLM clients without knowing the provider |
| **Singleton** | `EmbeddingService` | Load heavy models once |
| **Dependency Injection** | FastAPI `Depends()` | Decouple components, enable testing |
| **State Machine** | LangGraph pipeline | Model complex workflows with clear transitions |
| **Strategy** | Keyword vs. vector KB search | Swap algorithms without changing the interface |
| **Observer** | `onAuthStateChange` | React to auth events without polling |
| **Middleware** | CORS, auth, logging | Cross-cutting concerns handled once |
| **Unit of Work** | `get_db_session` | Group DB operations into transactions |

## 10.3 How to Explain This Project in an Interview

### The 30-Second Pitch

> "I built a full-stack AI customer support agent. A customer submits a ticket
> through a Next.js frontend. The backend classifies it using an LLM, searches
> a knowledge base using vector similarity (RAG with pgvector), generates a
> grounded response, validates it for quality, and either responds or escalates
> to a human. The entire pipeline is built as a LangGraph state machine with
> conditional routing, retry logic, and a complete audit trail."

### Expected Follow-Up Questions

**Q: "Why LangGraph instead of a simple function chain?"**

> "The workflow has branching logic. After classification, some tickets get
> escalated immediately (urgent + angry). After response validation, failed
> responses trigger retries. After 3 failed retries, it escalates. This is
> naturally modeled as a directed graph with conditional edges — which is
> exactly what LangGraph provides."

**Q: "How do you prevent the AI from hallucinating?"**

> "Three layers: (1) RAG — the response is grounded in actual knowledge
> base articles retrieved via vector similarity search. (2) Prompt engineering —
> the system prompt explicitly says 'do NOT make up information not in the
> KB articles.' (3) Validation — after generation, I check for uncertainty
> markers ('I don't know'), empty responses, and minimum length. If validation
> fails, it retries or escalates."

**Q: "How does authentication work?"**

> "Supabase handles user registration and JWT issuance. The frontend sends
> the JWT with every API call. The backend verifies it using Supabase's
> public keys (JWKS endpoint) with asymmetric cryptography (ES256). It
> extracts the user's email and role from the JWT claims. Admin-only routes
> have a `require_admin` dependency that checks the role."

**Q: "What would you change for production?"**

> "Add rate limiting, caching (Redis for KB search results), a celery/ARQ
> task queue for AI processing (don't block the HTTP request), WebSocket
> for real-time chat, more comprehensive tests, and Prometheus metrics
> instead of in-memory counters. I'd also add a feedback loop where
> human corrections improve the AI's future responses."

**Q: "How did you handle database design?"**

> "I used SQLAlchemy with the repository pattern. Models define the schema
> (with CHECK constraints for data integrity and indexes for performance).
> Repositories encapsulate all queries. Sessions use the Unit of Work
> pattern — all operations in a request are one transaction. The schema
> uses UUIDs (not auto-increment) for distributed safety and JSONB for
> flexible AI context storage."

## 10.4 Future Enhancements

If you continue building this project:

1. **WebSocket real-time chat** — Instead of polling for new messages,
   push updates instantly via WebSocket.

2. **Feedback loop** — When a human corrects an AI response, feed that
   correction back to improve future responses (fine-tuning or RAG updates).

3. **Multi-language support** — Detect customer language and respond in kind.

4. **SLA tracking** — Track response times against service level agreements.

5. **Caching** — Redis cache for KB search results and customer profiles.

6. **Task queue** — Move AI processing to background tasks (Celery/ARQ)
   so the HTTP response returns immediately.

7. **Analytics dashboard** — Charts for ticket volume, resolution times,
   escalation rates, sentiment trends.

8. **Email integration** — Accept tickets via email, not just the web form.

9. **Advanced RAG** — Hybrid search (vector + keyword), re-ranking,
   contextual chunking.

10. **A/B testing** — Test different prompts and measure which produces
    better responses.

---

## Conclusion

You've built a production-grade AI customer support agent from scratch.
Here's what you now understand:

- **Project architecture**: How to structure a full-stack application with
  clear separation of concerns.

- **AI workflows**: How to build multi-step LLM pipelines with state
  machines, conditional routing, and retry logic.

- **RAG**: How to embed text, store vectors, and perform similarity search
  to ground LLM responses in real data.

- **REST API design**: How to build typed, validated, documented APIs with
  FastAPI and Pydantic.

- **Authentication**: How to verify JWTs, implement RBAC, and practice
  defense-in-depth security.

- **Database design**: How to model relational data with SQLAlchemy,
  manage connections, and avoid N+1 queries.

- **Frontend integration**: How to connect a Next.js app to a Python
  backend through authenticated API calls.

This isn't just a project — it's a foundation for building any AI-powered
application. The patterns here (state machines, RAG, repository pattern,
structured logging, dependency injection) appear in every production system.

**Now go build something.**

---

*End of Engineering Guide*




