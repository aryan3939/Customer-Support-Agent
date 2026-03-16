# 01 — Environment Setup

This guide walks through setting up the development environment from scratch.
It explains every tool, dependency, and configuration decision.

---

## 1.1 Python Virtual Environment

### What is a Virtual Environment?

A virtual environment is an **isolated Python installation**. Without one, all
Python projects on your machine share the same packages — upgrading a package
for one project can break another. Virtual environments prevent this.

```bash
# Create a virtual environment named "venv"
python -m venv venv

# Activate it (Windows CMD)
venv\Scripts\activate

# Activate it (Windows PowerShell)
venv\Scripts\Activate.ps1

# Activate it (macOS/Linux)
source venv/bin/activate
```

**How to tell it's active:** Your terminal prompt changes to show `(venv)` at the start.

**What happens internally:**
- `python -m venv venv` creates a `venv/` folder with a fresh Python installation
- `activate` modifies your `PATH` so `python` and `pip` point to the venv's copies
- All `pip install` commands install into `venv/lib/site-packages/` instead of globally

---

## 1.2 Installing Dependencies

```bash
pip install -r requirements.txt
```

### What Gets Installed (and Why)

| Package | Version | Purpose | Why We Need It |
|---------|---------|---------|---------------|
| `fastapi` | Latest | Web framework | REST API with automatic validation and docs |
| `uvicorn[standard]` | Latest | ASGI server | Runs FastAPI with async support, auto-reload |
| `sqlalchemy[asyncio]` | 2.0+ | ORM | Maps Python classes to database tables |
| `asyncpg` | Latest | PostgreSQL driver | Async PostgreSQL connection (required by SQLAlchemy async) |
| `alembic` | Latest | Migrations | Database schema versioning |
| `pydantic` | 2.0+ | Validation | Request/response schemas with type checking |
| `pydantic-settings` | Latest | Config | Loads `.env` files into typed Settings class |
| `python-dotenv` | Latest | Env loader | Makes `.env` vars available in `os.environ` |
| `langgraph` | Latest | AI workflow | State machine for ticket processing pipeline |
| `langchain` | Latest | AI framework | LLM abstractions, prompt templates, tools |
| `langchain-core` | Latest | AI core | Base classes for LLM interactions |
| `langchain-google-genai` | Latest | Google LLM | Gemini model integration |
| `langchain-groq` | Latest | Groq LLM | Groq model integration (alternative) |
| `PyJWT[crypto]` | Latest | JWT auth | Decode and verify Supabase JWTs (ES256 support) |
| `sentence-transformers` | Latest | Embeddings | Local vector embeddings for RAG |
| `pgvector` | Latest | Vector DB | SQLAlchemy integration for pgvector extension |
| `structlog` | Latest | Logging | Structured, machine-parsable log output |
| `httpx` | Latest | HTTP client | Async HTTP requests (used in tests and tools) |

### Why `PyJWT[crypto]` Instead of `PyJWT`?

The `[crypto]` extra installs `cryptography`, which adds support for
**asymmetric JWT algorithms** (ES256, RS256, EdDSA). Without it, PyJWT only
supports HS256 (symmetric/shared secret). Supabase now uses **ES256** (ECC P-256)
for JWT signing, so `[crypto]` is required.

### Why `asyncpg` Instead of `psycopg2`?

`asyncpg` is an **async** PostgreSQL driver — it doesn't block the event loop
while waiting for database queries. This is critical for FastAPI, which is async.
With `psycopg2` (sync), every concurrent request would block, defeating the
purpose of async.

---

## 1.3 Project Root Files

| File | Purpose | Why It Exists |
|------|---------|--------------|
| `requirements.txt` | Python dependencies | All packages needed to run the project |
| `.env.example` | Environment variable template | Copy this to `.env` and fill in your values |
| `.env` | **Your actual environment variables** (gitignored) | Secret keys, database URLs — never committed |
| `.gitignore` | Files Git should ignore | Prevents `.env`, `venv/`, `__pycache__/`, etc. from being committed |
| `alembic.ini` | Alembic configuration | Database migration tool config |
| `docker-compose.yml` | Docker services | Redis for caching (optional) |
| `pyproject.toml` | Python project metadata | Package name, version, build config |

---

## 1.4 The `.env` File

The `.env` file is the **single source of truth** for all configuration. It's loaded
by `python-dotenv` and parsed by Pydantic Settings into typed Python objects.

```bash
# Copy the template
copy .env.example .env        # Windows
cp .env.example .env          # macOS/Linux
```

**Key categories of variables:**
- **Database** — `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`
- **LLM** — `LLM_PROVIDER`, `GOOGLE_API_KEY` or `GROQ_API_KEY`, `LLM_MODEL`
- **LangSmith** — `LANGCHAIN_TRACING_V2`, `LANGCHAIN_API_KEY`
- **Security** — `JWT_SECRET`, `SUPABASE_JWT_SECRET`
- **Behavior** — `ESCALATION_CONFIDENCE_THRESHOLD`, `MAX_AUTO_ATTEMPTS`

See `SETUP.md` for step-by-step instructions on getting each API key.

---

## 1.5 Node.js & Frontend Dependencies

The frontend is a separate Next.js 15 application in the `frontend/` folder.

```bash
cd frontend
npm install
```

This installs:
- **next** — React framework with server-side rendering
- **react** + **react-dom** — UI library
- **typescript** — Type-safe JavaScript
- **tailwindcss** — Utility-first CSS framework
- **@supabase/supabase-js** — Supabase client for authentication

The frontend has its own `.env.local` file for Supabase configuration:
```env
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGci...
```
