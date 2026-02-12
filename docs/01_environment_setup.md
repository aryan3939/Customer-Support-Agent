# Phase 1: Environment Setup

## Why This Phase?

Before writing any application code, we need a **solid foundation**. Think of building a house:
you don't start with the roof — you pour the foundation first.

This phase answers three fundamental questions:

### 1. Where does our code run?

Our Python code needs an **isolated environment** (virtual environment) so our project's 
packages don't clash with other Python projects on your machine. For example, if another 
project uses `fastapi==0.100.0` but we need `fastapi==0.115.0`, they'd conflict without 
isolation.

### 2. Where does our data live?

We need two databases:
- **PostgreSQL** — stores all our structured data (tickets, customers, messages)
- **Redis** — stores temporary data in memory (cached responses, rate limits)

Instead of installing these natively (which is painful and OS-specific), we run them 
in **Docker containers** — identical, disposable environments.

### 3. What services does our AI agent talk to?

Our agent uses **Large Language Models** (LLMs) to understand and respond to tickets. 
We need API keys configured for Google AI Studio (or Groq) so the agent can "think."

---

## Files Created in This Phase

```
Customer Support Agent/
├── pyproject.toml        ← Project metadata + dependencies
├── requirements.txt      ← Same dependencies for pip
├── .env.example          ← Template for secret configuration
├── docker-compose.yml    ← Database services definition
├── .gitignore            ← Files Git should ignore
└── docs/
    └── 01_environment_setup.md  ← This file (you're reading it!)
```

---

## File-by-File Breakdown

### `pyproject.toml` — Project Configuration

This is the **modern standard** for Python project configuration (replaces the old `setup.py`).

```toml
[project]
name = "customer-support-agent"     # Package name
version = "0.1.0"                   # Semantic versioning: major.minor.patch
description = "..."                 # Human-readable description
requires-python = ">=3.11"         # Minimum Python version we support
```

**Why Python 3.11+?** It introduced significant performance improvements (~25% faster) 
and better error messages. Our async code benefits from this.

#### Dependencies Explained

**Core Web Framework:**
```toml
"fastapi>=0.115.0",           # Our REST API framework
"uvicorn[standard]>=0.32.0",  # The server that runs FastAPI
```
- **FastAPI** handles HTTP requests (when someone creates a ticket, it receives that request)
- **uvicorn** is the ASGI server — think of it as the engine that powers FastAPI
- `[standard]` installs extras like `websockets` and `httptools` for better performance
- `>=0.115.0` means "version 0.115.0 or newer" — allows compatible updates

**Agent Framework:**
```toml
"langgraph>=0.2.0",              # Defines agent workflow as a state machine
"langchain>=0.3.0",              # Connects to LLMs, manages prompts
"langchain-groq>=0.2.0",         # Groq-specific connector (FREE LLM)
"langchain-google-genai>=2.0.0", # Google AI Studio connector (FREE LLM)
```
- **LangGraph** = The brain's workflow. It says "first classify the ticket, then search 
  the knowledge base, then generate a response"
- **LangChain** = The glue between our code and AI models. It standardizes how we talk 
  to different LLMs
- The provider packages (`langchain-groq`, `langchain-google-genai`) are adapters — they 
  translate LangChain's standard interface into each provider's specific API format

**Database:**
```toml
"sqlalchemy>=2.0.0",          # ORM: write Python classes instead of raw SQL
"asyncpg>=0.30.0",            # Async PostgreSQL driver (fast!)
"alembic>=1.14.0",            # Tracks database schema changes over time
"pgvector>=0.3.0",            # Vector similarity search in PostgreSQL
```
- **SQLAlchemy** lets us write `Ticket(subject="Help")` instead of 
  `INSERT INTO tickets (subject) VALUES ('Help')` — much safer and readable
- **asyncpg** is the fastest PostgreSQL driver for Python. The `async` part means it 
  doesn't block other requests while waiting for the database
- **Alembic** = database version control. When we add a column, it generates a migration 
  file so every developer gets the same schema
- **pgvector** adds a `vector` column type to PostgreSQL for similarity search (RAG)

**Validation & Config:**
```toml
"pydantic>=2.0.0",            # Validates data automatically using type hints
"pydantic-settings>=2.0.0",   # Reads settings from .env files
"python-dotenv>=1.0.0",       # Loads .env file into environment variables
```
- **Pydantic** validates incoming data. If someone sends a ticket without a `subject`, 
  Pydantic automatically rejects it with a clear error message
- **pydantic-settings** reads our `.env` file and creates a typed Python object from it
- **python-dotenv** loads `.env` into `os.environ` at startup

**HTTP & Async:**
```toml
"httpx>=0.28.0",              # Makes HTTP calls to external services
"redis>=5.0.0",               # Talks to our Redis container
"tenacity>=9.0.0",            # Retries failed operations automatically
```
- **httpx** is like `requests` but async. We use it to call CRM APIs, email services, etc.
- **redis** (the Python package) is the client that talks to our Redis Docker container
- **tenacity** handles transient failures: "If the email API fails, retry 3 times with 
  exponential backoff before giving up"

**Logging & Embeddings:**
```toml
"structlog>=24.0.0",            # Structured JSON logging
"sentence-transformers>=3.0.0", # Text embeddings (runs locally, FREE!)
```
- **structlog** produces machine-readable JSON logs instead of messy text. This makes 
  debugging much easier
- **sentence-transformers** converts text into vectors (lists of numbers) for similarity 
  search. It runs entirely on your CPU — no API key needed!

#### Dev Dependencies
```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",       # Run tests
    "pytest-asyncio>=0.24.0",  # Test async code
    "pytest-cov>=6.0.0",   # Measure code coverage
    "ruff>=0.8.0",         # Lint code (find bugs before running)
    "mypy>=1.13.0",        # Check type annotations
]
```
These are only needed during development, not in production. Install them with:
```bash
pip install -e ".[dev]"
```

#### Tool Configuration
```toml
[tool.ruff]
line-length = 100          # Max characters per line
target-version = "py311"   # Check against Python 3.11

[tool.pytest.ini_options]
asyncio_mode = "auto"      # Automatically handle async test functions
testpaths = ["tests"]      # Where to find test files
```

---

### `.env.example` — Environment Variables Template

**Why a `.env` file?**

We never hardcode secrets (API keys, passwords) in source code because:
1. **Security** — If code goes to GitHub, secrets are exposed
2. **Flexibility** — Different environments (dev/staging/prod) need different values
3. **Convention** — Every professional project uses environment variables

The `.env.example` is a **template** that gets committed to Git. The actual `.env` 
(with real secrets) is in `.gitignore` and never committed.

```env
# Format: KEY=value (no spaces around =)

DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/support_db
```

Breaking down the database URL:
```
postgresql+asyncpg://  ← Protocol: use asyncpg driver for PostgreSQL
postgres:postgres@     ← username:password
localhost:5432/        ← host:port (Docker maps to your localhost)
support_db             ← database name
```

```env
LLM_PROVIDER=google                    # Which LLM to use
GOOGLE_API_KEY=your_key_here           # The secret API key
LLM_MODEL=gemini-2.0-flash            # Specific model to use
LLM_TEMPERATURE=0.3                    # 0=precise, 1=creative
```

**Why temperature 0.3?** For customer support, we want consistent, accurate responses — 
not creative or unpredictable ones. Lower temperature = more deterministic output.

```env
ESCALATION_CONFIDENCE_THRESHOLD=0.7    # If AI is <70% sure, escalate to human
MAX_AUTO_ATTEMPTS=3                     # Try 3 times before giving up
```

These **feature flags** let us tune the agent's behavior without changing code.

---

### `docker-compose.yml` — Database Services

**Why Docker Compose?** It defines our infrastructure as code. Instead of following 
a 20-step installation guide, one command spins up everything identically.

```yaml
services:                              # List of containers to run
```

#### PostgreSQL Service
```yaml
  postgres:
    image: pgvector/pgvector:pg16      # Pre-built image with pgvector installed
    container_name: support_postgres   # Friendly name (for docker exec commands)
    environment:
      POSTGRES_USER: postgres          # Default superuser username
      POSTGRES_PASSWORD: postgres      # Password (fine for local dev!)
      POSTGRES_DB: support_db          # Auto-create this database on first run
    ports:
      - "5432:5432"                    # Map container port to host port
    volumes:
      - postgres_data:/var/lib/postgresql/data  # Persist data on restart
    healthcheck:                       # Docker checks if DB is ready
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s                     # Check every 5 seconds
    restart: unless-stopped            # Auto-restart if crashes
```

**Key decisions:**
- We use `pgvector/pgvector:pg16` instead of plain `postgres:16` because it comes 
  with pgvector pre-installed (no manual extension setup)
- `volumes` = data survives `docker-compose down`. Without it, you'd lose all data 
  when the container stops
- `healthcheck` = other services can wait until PostgreSQL is actually ready to 
  accept connections

#### Redis Service
```yaml
  redis:
    image: redis:7-alpine              # Alpine = tiny image (~30MB vs ~130MB)
    container_name: support_redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data               # Persist cache between restarts
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]  # Simple PING/PONG check
    restart: unless-stopped
```

**Why `redis:7-alpine`?** The `alpine` variant is based on Alpine Linux, which is 
much smaller than the default Debian-based image. Same functionality, less disk space.

#### Volumes
```yaml
volumes:
  postgres_data:                       # Named volume for PostgreSQL
  redis_data:                          # Named volume for Redis
```

Docker manages these volumes. They persist even if you delete the container.

---

### `.gitignore` — Files Git Should Ignore

```
.venv/          # Virtual environment (each dev creates their own)
.env            # Secret keys (NEVER commit this!)
__pycache__/    # Python bytecode cache (auto-generated)
*.py[cod]       # Compiled Python files
.pytest_cache/  # Test cache
.mypy_cache/    # Type-checking cache
```

**Why ignore `.venv/`?** It's ~500MB of installed packages. Every developer recreates 
it from `requirements.txt` — no need to store it in Git.

**Why ignore `.env`?** It contains secrets. The template (`.env.example`) is committed 
instead, so developers know what variables to set.

---

### `requirements.txt` — Pip Compatibility

This is the same dependencies as `pyproject.toml` but in the traditional format. 
We include both because:
- `pyproject.toml` = modern standard, used by `pip install -e .`
- `requirements.txt` = universal, works everywhere, simpler for `pip install -r`

---

## Architecture: How It All Connects

```
┌─────────────────────────────────────────────────────────────┐
│                 YOUR DEVELOPMENT MACHINE                     │
│                                                              │
│   ┌──────────────────────────────────────────────────────┐  │
│   │        Python Virtual Environment (.venv)             │  │
│   │                                                       │  │
│   │   FastAPI ──→ LangGraph ──→ LangChain ──→ Google AI  │  │
│   │      │           │              │                     │  │
│   │      └───────────┴──────────────┘                     │  │
│   │                    │                                  │  │
│   └────────────────────│──────────────────────────────────┘  │
│                        ▼                                     │
│   ┌──────────────────────────────────────────────────────┐  │
│   │              Docker Containers                        │  │
│   │   ┌─────────────────┐    ┌─────────────────┐         │  │
│   │   │   PostgreSQL    │    │     Redis       │         │  │
│   │   │   + pgvector    │    │   (caching)     │         │  │
│   │   │   Port: 5432    │    │   Port: 6379    │         │  │
│   │   └─────────────────┘    └─────────────────┘         │  │
│   └──────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

**Data flow:**
1. User submits a support ticket → **FastAPI** receives it
2. FastAPI passes it to **LangGraph** → orchestrates the workflow
3. LangGraph uses **LangChain** → calls **Google AI** to classify & respond
4. Results stored in **PostgreSQL** (via SQLAlchemy)
5. Frequent lookups cached in **Redis**

---

## Setup Steps

### Step 1: Create Virtual Environment
```bash
cd "d:\OneDrive - iitr.ac.in\Projects\Customer Support Agent"
python -m venv .venv
.venv\Scripts\activate
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Configure Environment
```bash
copy .env.example .env
# Edit .env → add your Google API key from https://aistudio.google.com/apikey
```

### Step 4: Start Docker Services
```bash
docker-compose up -d
```

### Step 5: Verify
```bash
docker-compose ps
docker exec -it support_postgres psql -U postgres -c "SELECT version();"
docker exec -it support_redis redis-cli ping
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `docker-compose not recognized` | Start Docker Desktop first |
| `Port 5432 in use` | Stop existing PostgreSQL or change port in compose file |
| `pip install fails with C++ error` | Install Visual C++ Build Tools |
| `Cannot connect to database` | Check with `docker-compose logs postgres` |

---

## What's Next?

With the foundation in place, Phase 1 continues with:
1. **`src/config.py`** — Load `.env` settings into typed Python objects
2. **`src/utils/logging.py`** — Structured logging for debugging
3. **`src/main.py`** — FastAPI app skeleton with health check endpoint
4. **Database models** — SQLAlchemy models + Alembic migrations
