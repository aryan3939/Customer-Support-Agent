# 🤖 AI Customer Support Agent

An **autonomous AI-powered customer support system** built with **LangGraph**, **FastAPI**, **Supabase (PostgreSQL + Auth)**, and a **Next.js** frontend. The AI agent classifies incoming tickets, searches a vector knowledge base (RAG), generates context-aware responses, and escalates to human agents when needed — all while maintaining a complete audit trail.

🌐 **Live Demo:** [customer-support-agent-one.vercel.app](https://customer-support-agent-one.vercel.app/)

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| **AI Ticket Processing** | LangGraph state machine classifies intent, priority, sentiment, and category |
| **RAG Knowledge Base** | pgvector-powered semantic search with keyword fallback |
| **Smart Escalation** | Auto-escalates urgent, angry, or low-confidence tickets to human agents |
| **Supabase Auth** | JWT-based authentication with customer & admin roles |
| **Admin Panel** | Full conversation management — reply as agent, resolve, filter by status/priority |
| **Real-time Dashboard** | Ticket list, analytics, and create-ticket form (auto-fills from auth) |
| **Audit Trail** | Every AI decision is logged for transparency and debugging |
| **Multi-LLM Support** | Google Gemini or Groq (both free tier) |
| **LangSmith Tracing** | Optional observability with LangSmith for debugging AI workflows |

---

## 🏗️ Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **AI Workflow** | LangGraph + LangChain | State machine for ticket processing |
| **LLM** | Google Gemini / Groq | Classification & response generation |
| **Embeddings** | sentence-transformers (local) | Vector embeddings for RAG search |
| **Backend API** | FastAPI + Pydantic | REST API with validation |
| **Database** | PostgreSQL (Supabase) + SQLAlchemy | Async ORM with connection pooling |
| **Vector Search** | pgvector (Supabase extension) | Similarity search for knowledge base |
| **Authentication** | Supabase Auth + JWKS | JWT verification with ES256/EdDSA support |
| **Frontend** | Next.js 15 + TypeScript | Dashboard, ticket view, admin panel |
| **Styling** | Tailwind CSS | Responsive, dark-themed UI |
| **Migrations** | Alembic | Database schema versioning |
| **Logging** | structlog | Structured JSON/colored logging |
| **Tracing** | LangSmith | AI workflow observability |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- A [Supabase](https://supabase.com) project (free tier)
- A Google AI Studio or Groq API key (free tier)

### 1. Clone & Install Backend

```bash
git clone https://github.com/aryan3939/Customer-Support-Agent.git
cd Customer-Support-Agent

# Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# Install Python dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
copy .env.example .env       # Windows
# cp .env.example .env       # macOS/Linux
```

Edit `.env` and fill in:
- `DATABASE_URL` — Your Supabase Postgres connection string
- `SUPABASE_URL` — Your Supabase project URL
- `SUPABASE_ANON_KEY` — From Supabase Dashboard → Settings → API
- `GOOGLE_API_KEY` or `GROQ_API_KEY` — Your LLM API key
- `LANGCHAIN_API_KEY` — (Optional) For LangSmith tracing

> See the [Engineering Guide](docs/ENGINEERING_GUIDE.md) for detailed setup instructions and configuration reference.

### 3. Seed the Knowledge Base

```bash
python -m scripts.seed_kb
```

This populates the vector knowledge base with support articles and their embeddings.

### 4. Start the Backend

```bash
uvicorn src.main:app --reload
```

The API will be available at `http://localhost:8000`. Visit `http://localhost:8000/docs` for the interactive Swagger UI.

### 5. Start the Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend runs at `http://localhost:3000`.

### 6. Configure Frontend Environment

```bash
cd frontend
copy .env.local.example .env.local
```

Edit `frontend/.env.local` with your Supabase URL and anon key.

---

## 📁 Project Structure

```
Customer Support Agent/
│
├── src/                          # ── Backend (Python/FastAPI) ──
│   ├── main.py                   # App entrypoint, lifespan, routes
│   ├── config.py                 # Pydantic settings from .env
│   │
│   ├── agents/                   # 🧠 AI Agent (LangGraph)
│   │   ├── graph.py              # State machine: classify → search → respond
│   │   ├── state.py              # TicketState schema (shared context)
│   │   ├── llm.py                # LLM factory (Gemini/Groq)
│   │   ├── models.py             # Pydantic models for AI outputs
│   │   ├── nodes/                # Graph nodes (each step)
│   │   │   ├── classifier.py     # Intent, priority, sentiment analysis
│   │   │   ├── kb_searcher.py    # RAG knowledge base retrieval
│   │   │   ├── resolver.py       # Response generation
│   │   │   ├── validator.py      # Response quality check
│   │   │   └── escalator.py      # Human escalation logic
│   │   └── edges/                # Conditional routing
│   │       └── conditions.py     # Escalation decision functions
│   │
│   ├── api/                      # 🌐 REST API
│   │   ├── routes/
│   │   │   ├── tickets.py        # CRUD + resolve + messages
│   │   │   ├── admin.py          # Admin panel endpoints
│   │   │   ├── analytics.py      # Dashboard stats
│   │   │   └── webhooks.py       # External integrations
│   │   ├── schemas/              # Pydantic request/response models
│   │   ├── deps/
│   │   │   └── auth.py           # JWT verification via Supabase JWKS
│   │   └── middleware/
│   │       └── error_handler.py  # Global exception handling
│   │
│   ├── db/                       # 💾 Database Layer
│   │   ├── models.py             # SQLAlchemy ORM models
│   │   ├── session.py            # Async engine, session, init_db
│   │   └── repositories/
│   │       ├── ticket_repo.py    # Ticket CRUD operations
│   │       └── customer_repo.py  # Customer lookup/creation
│   │
│   ├── services/                 # 🔧 Business Logic
│   │   ├── ticket_service.py     # Ticket processing orchestration
│   │   ├── embedding_service.py  # Vector embedding singleton
│   │   └── analytics_service.py  # Dashboard metrics queries
│   │
│   ├── tools/                    # 🛠️ Agent Tools (LangChain)
│   │   ├── knowledge_base.py     # Vector + keyword KB search
│   │   ├── customer_service.py   # Customer data lookup
│   │   ├── external_apis.py      # External service stubs
│   │   └── notifications.py      # Email/notification stubs
│   │
│   └── utils/
│       ├── logging.py            # structlog setup
│       └── metrics.py            # Performance counters
│
├── frontend/                     # ── Frontend (Next.js 15) ──
│   ├── src/app/
│   │   ├── layout.tsx            # Root layout with auth guard
│   │   ├── page.tsx              # Dashboard — ticket list + create
│   │   ├── login/page.tsx        # Supabase login page
│   │   ├── tickets/[id]/page.tsx # Ticket detail + chat view
│   │   ├── admin/                # Admin panel pages
│   │   └── analytics/            # Analytics dashboard
│   ├── src/hooks/useAuth.ts      # Supabase auth React hook
│   └── src/lib/
│       ├── api.ts                # Backend API client
│       └── supabase.ts           # Supabase browser client
│
├── scripts/
│   ├── seed_kb.py                # Knowledge base seeder
│   └── test_agent.py             # Standalone agent test
│
├── alembic/                      # Database migrations
├── docs/                         # 📚 Detailed documentation
├── .env.example                  # Environment template
├── requirements.txt              # Python dependencies
└── docker-compose.yml            # Redis for caching (optional)
```

> See the [Engineering Guide](docs/ENGINEERING_GUIDE.md) for a detailed file-by-file explanation.

---

## 🔌 API Endpoints

### Customer Endpoints (Authenticated)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/tickets` | Create ticket → AI processes → returns response |
| `GET` | `/api/v1/tickets` | List tickets (filtered by user's email) |
| `GET` | `/api/v1/tickets/{id}` | Get ticket details with messages and actions |
| `POST` | `/api/v1/tickets/{id}/messages` | Send follow-up → AI auto-replies |
| `PATCH` | `/api/v1/tickets/{id}/status` | Update ticket status |
| `PATCH` | `/api/v1/tickets/{id}/resolve` | Resolve ticket |
| `GET` | `/api/v1/tickets/{id}/actions` | View AI audit trail |

### Admin Endpoints (Admin role required)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/admin/conversations` | List all conversations with advanced filters |
| `GET` | `/api/v1/admin/conversations/{id}` | Get conversation details |
| `POST` | `/api/v1/admin/conversations/{id}/reply` | Reply as human agent |
| `PATCH` | `/api/v1/admin/conversations/{id}/resolve` | Admin-resolve conversation |

### Other

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/analytics/dashboard` | Dashboard metrics |
| `GET` | `/health` | Health check |
| `GET` | `/docs` | Interactive Swagger UI |

---

## 🧠 How the AI Agent Works

The AI agent is built as a **LangGraph state machine** with 5 nodes:

```
         START
           │
           ▼
      ┌──────────┐
      │ CLASSIFY  │ ← Analyzes intent, priority, sentiment, category
      └────┬─────┘
           │
      Should escalate? ──YES──→ [ESCALATE] → END
           │ NO
           ▼
      ┌──────────┐
      │ KB SEARCH │ ← Searches vector knowledge base (RAG)
      └────┬─────┘
           │
           ▼
      ┌──────────┐
      │ RESPOND   │ ← Generates AI response using context
      └────┬─────┘
           │
           ▼
      ┌──────────┐
      │ VALIDATE  │ ← Checks response quality & accuracy
      └────┬─────┘
           │
      Should escalate? ──YES──→ [ESCALATE] → END
           │ NO
           ▼
      ┌──────────┐
      │ FINALIZE  │ ← Marks ticket as resolved
      └──────────┘
           │
          END
```

### Escalation Triggers
- 🔴 **Urgent priority** — critical issues escalate immediately
- 😠 **Negative sentiment** — angry/frustrated customers get human help
- 🤔 **Low confidence** — if AI isn't sure, it asks a human
- ❓ **Unrecognized intent** — unknown request types escalate

---

## 📚 Documentation

The comprehensive **[Engineering Guide](docs/ENGINEERING_GUIDE.md)** (5,000+ lines) covers the entire project in detail:

| Part | Topic |
|------|-------|
| 1 | Engineering Mindset & Project Planning |
| 2 | Project Foundation (config, logging, entry point) |
| 3 | Database Layer (models, sessions, repositories) |
| 4 | AI Agent Core — LangGraph Pipeline |
| 5 | RAG & Knowledge Base (embeddings, pgvector) |
| 6 | FastAPI REST API Layer |
| 7 | Authentication & Authorization |
| 8 | Frontend — Next.js 15 |
| 9 | Integration, Testing & Deployment |
| 10 | Lessons Learned & Interview Prep |

---

## 🔐 Authentication Flow

```
User opens app → Supabase Login → JWT issued
       │
       ▼
Frontend stores JWT → Sends in Authorization header
       │
       ▼
Backend receives JWT → Verifies via Supabase JWKS endpoint
       │
       ▼
Extracts user email + role → Applies permissions
```

- **Customers** can only see and manage their own tickets
- **Admins** can see all conversations, reply as agent, resolve any ticket
- JWT supports ES256, EdDSA, and HS256 algorithms (auto-detected via JWKS)

---

## ☁️ Deployment

The app is deployed for **free** across three platforms:

| Component | Platform | Live URL |
|-----------|----------|----------|
| **Frontend** | [Vercel](https://vercel.com) | [customer-support-agent-one.vercel.app](https://customer-support-agent-one.vercel.app/) |
| **Backend** | [Hugging Face Spaces](https://huggingface.co/spaces) | [aryan3939-customer-support-agent.hf.space](https://aryan3939-customer-support-agent.hf.space) |
| **Database** | [Supabase](https://supabase.com) | PostgreSQL + pgvector (free tier) |
| **LLM** | [Groq](https://groq.com) | `openai/gpt-oss-120b` (free tier) |

### Self-Hosting

See [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) for step-by-step instructions to deploy your own instance on:
- **Backend:** Hugging Face Spaces (Docker, 2GB RAM free)
- **Frontend:** Vercel (unlimited for personal use)
- **Database:** Supabase (500MB free, pgvector built-in)

---

## 🤝 Contributing

This is a personal portfolio project, but suggestions and feedback are welcome! Feel free to open an issue or submit a pull request.

## 📄 License

 MIT License.

