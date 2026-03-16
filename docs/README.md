# 📚 Documentation Index

All documentation for the AI Customer Support Agent.

## Core Documentation

| Document | Description |
|----------|-------------|
| [SETUP.md](SETUP.md) | Complete setup guide — all API keys, database, frontend, testing, troubleshooting |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System design, data flow diagrams, design decisions, security |
| [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) | Every file in the project explained with purpose and context |
| [API_REFERENCE.md](API_REFERENCE.md) | All REST API endpoints with request/response examples |
| [RAG_DEEP_DIVE.md](RAG_DEEP_DIVE.md) | How the vector knowledge base and embeddings work |
| [COMPLETE_PROJECT_GUIDE.md](COMPLETE_PROJECT_GUIDE.md) | Comprehensive walkthrough — how the project was built step-by-step |

## Quick Reference

| Document | Description |
|----------|-------------|
| [HOW_TO_RUN.md](HOW_TO_RUN.md) | Quick-start commands to get running fast |
| [API_KEYS_SETUP.md](API_KEYS_SETUP.md) | Step-by-step API key setup with verification commands |

## Build Guides (Step-by-Step)

These guides walk through how the project was built, explaining every decision:

| Document | Topic |
|----------|-------|
| [01_environment_setup.md](01_environment_setup.md) | Python venv, dependencies, .env configuration |
| [02_project_setup.md](02_project_setup.md) | Config management, structured logging, FastAPI bootstrap |
| [03_database_models.md](03_database_models.md) | SQLAlchemy ORM models, relationships, connection pooling |
| [04_core_agent.md](04_core_agent.md) | LangGraph state machine, nodes, edges, structured output |
| [05_api_routes.md](05_api_routes.md) | REST API endpoints, Pydantic schemas, authentication |
| [06_auth_admin_resolution.md](06_auth_admin_resolution.md) | Supabase auth, admin panel, ticket resolution workflow |

## Reading Order

1. **Start with** [HOW_TO_RUN.md](HOW_TO_RUN.md) — get the project running
2. **Then read** [ARCHITECTURE.md](ARCHITECTURE.md) — understand the system design
3. **Follow the build guides** 01-06 — learn how each part was built
4. **Reference** [API_REFERENCE.md](API_REFERENCE.md) — when working with the API
5. **Deep-dive into** [RAG_DEEP_DIVE.md](RAG_DEEP_DIVE.md) — understand vector search
