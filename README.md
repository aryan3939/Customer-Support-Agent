# 🤖 AI Customer Support Agent

An autonomous AI-powered customer support system built with **LangGraph**, **LangChain**, **FastAPI**, and **PostgreSQL**.

## What It Does

- Receives support tickets via REST API
- AI classifies tickets (intent, priority, sentiment)
- Searches knowledge base for relevant answers (RAG)
- Generates helpful, context-aware responses
- Escalates to humans when needed (urgent/angry/uncertain)
- Maintains a complete audit trail of AI decisions

## Tech Stack

| Layer | Technology |
|-------|-----------|
| AI Workflow | LangGraph (state machine) |
| LLM | Google Gemini / Groq |
| API | FastAPI |
| Database | PostgreSQL (Supabase) + SQLAlchemy |
| Validation | Pydantic |
| Logging | structlog |

## Quick Start

```bash
# Clone and setup
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# Configure (add your Google API key)
copy .env.example .env

# Run
uvicorn src.main:app --reload

# Test → http://localhost:8000/docs
```

See **[docs/HOW_TO_RUN.md](docs/HOW_TO_RUN.md)** for the full guide with Postman examples.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/tickets` | Create ticket + AI response |
| `GET` | `/api/v1/tickets` | List with filters |
| `GET` | `/api/v1/tickets/{id}` | Full details + messages |
| `POST` | `/api/v1/tickets/{id}/messages` | Follow-up (AI auto-replies) |
| `PATCH` | `/api/v1/tickets/{id}/status` | Update status |
| `GET` | `/api/v1/tickets/{id}/actions` | AI audit trail |
| `GET` | `/api/v1/analytics/dashboard` | Metrics |

## Documentation

| Doc | What It Covers |
|-----|---------------|
| [01_environment_setup.md](docs/01_environment_setup.md) | Project dependencies & Docker |
| [02_project_setup.md](docs/02_project_setup.md) | Config, logging, FastAPI |
| [03_database_models.md](docs/03_database_models.md) | ORM, pooling, migrations |
| [04_core_agent.md](docs/04_core_agent.md) | LangGraph workflow & nodes |
| [05_api_routes.md](docs/05_api_routes.md) | REST API & Pydantic |
| [HOW_TO_RUN.md](docs/HOW_TO_RUN.md) | Step-by-step run guide |
