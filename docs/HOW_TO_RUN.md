# Customer Support Agent — How to Run

## Step-by-Step Setup Guide

---

### Step 1: Create Virtual Environment

Open your terminal in the project folder:

```bash
cd "d:\OneDrive - iitr.ac.in\Projects\Customer Support Agent"

# Create virtual environment
python -m venv .venv

# Activate it (Windows)
.venv\Scripts\activate

# You should see (.venv) in your terminal prompt
```

---

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

This installs: FastAPI, LangGraph, LangChain, SQLAlchemy, and everything else.

> **Note**: `sentence-transformers` downloads a ~90MB model on first use. If this is slow or you don't need embeddings yet, you can comment it out in `requirements.txt`.

---

### Step 3: Get Your API Key

You need a Google AI Studio API key (free):

1. Go to **https://aistudio.google.com/apikey**
2. Sign in with your Google account
3. Click **"Create API Key"**
4. Copy the key

---

### Step 4: Create Your .env File

```bash
copy .env.example .env
```

Now edit `.env` and fill in these **required** values:

```env
# REQUIRED — Your Google API key from Step 3
GOOGLE_API_KEY=AIzaSy...your_key_here...

# REQUIRED — Database URL
# Option A: Use Supabase (recommended)
#   Go to supabase.com → New Project → Settings → Database → Connection String
#   Use the "URI" format and replace [YOUR-PASSWORD] with your DB password
DATABASE_URL=postgresql+asyncpg://postgres.xxxxx:password@aws-0-region.pooler.supabase.com:6543/postgres

# Option B: Skip DB for now (app still works without it!)
# Just put any valid-looking URL, the app gracefully handles DB failures:
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/testdb
```

Everything else has sensible defaults and doesn't need changing.

---

### Step 5: Run the Server

```bash
uvicorn src.main:app --reload
```

You should see output like:
```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

> **Note**: If the database connection fails, the app will still start — it logs a warning and continues. The AI agent and all API endpoints work without the database (they use in-memory storage).

---

### Step 6: Test with Postman

#### 6a. Root / Health Check

```
GET http://localhost:8000/
GET http://localhost:8000/health
```

#### 6b. Create a Ticket (THE MAIN ONE!)

```
POST http://localhost:8000/api/v1/tickets
Content-Type: application/json

{
    "customer_email": "user@example.com",
    "subject": "Cannot reset my password",
    "message": "I have tried clicking forgot password 3 times but no reset email arrives. I checked spam too. Please help!",
    "channel": "web"
}
```

**What happens behind the scenes:**
1. FastAPI validates the request (Pydantic)
2. LangGraph workflow starts:
   - Classifier → asks Gemini to classify intent/priority/sentiment
   - KB Search → finds relevant articles (Password Reset Guide)
   - Resolver → generates response using KB context
   - Validator → QA checks the response
3. Returns the AI response + classification + audit trail

#### 6c. List All Tickets

```
GET http://localhost:8000/api/v1/tickets
```

#### 6d. Get Ticket Detail (use the ID from step 6b)

```
GET http://localhost:8000/api/v1/tickets/{ticket_id}
```

#### 6e. Send a Follow-Up Message

```
POST http://localhost:8000/api/v1/tickets/{ticket_id}/messages
Content-Type: application/json

{
    "content": "I still haven't received the reset email. Can you check if my account is locked?",
    "sender_type": "customer"
}
```

#### 6f. View AI Audit Trail

```
GET http://localhost:8000/api/v1/tickets/{ticket_id}/actions
```

#### 6g. Update Ticket Status

```
PATCH http://localhost:8000/api/v1/tickets/{ticket_id}/status
Content-Type: application/json

{"status": "resolved"}
```

#### 6h. Dashboard Metrics

```
GET http://localhost:8000/api/v1/analytics/dashboard
```

---

### Step 7: Swagger UI (Alternative to Postman)

FastAPI auto-generates interactive API docs:

- **http://localhost:8000/docs** — Swagger UI (try endpoints right in the browser)
- **http://localhost:8000/redoc** — Clean API documentation

---

### Test Script (No Server Needed)

To test the AI agent directly without the server:

```bash
python scripts/test_agent.py
```

This processes 3 sample tickets and shows classification + responses.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError` | Make sure venv is activated: `.venv\Scripts\activate` |
| `GOOGLE_API_KEY not set` | Edit `.env` and add your API key |
| `Database connection failed` | That's OK! App works without DB. Set any URL in `.env` |
| `Port 8000 already in use` | Use `uvicorn src.main:app --reload --port 8001` |
| `pip install fails` | Try: `pip install --upgrade pip` then retry |

---

## Project File Map

```
src/
├── main.py                    ← FastAPI app (START HERE)
├── config.py                  ← Settings from .env
│
├── agents/                    ← 🧠 AI Agent (LangGraph)
│   ├── state.py               ← TicketState data schema
│   ├── llm.py                 ← LLM factory (Google/Groq)
│   ├── graph.py               ← Main workflow graph
│   ├── nodes/
│   │   ├── classifier.py      ← Classify tickets (intent/priority)
│   │   ├── resolver.py        ← Generate AI responses
│   │   ├── escalator.py       ← Human handoff logic
│   │   └── validator.py       ← QA check responses
│   └── edges/
│       └── conditions.py      ← Routing logic between nodes
│
├── api/                       ← 🌐 REST API
│   ├── routes/
│   │   ├── tickets.py         ← Ticket CRUD endpoints
│   │   ├── analytics.py       ← Dashboard metrics
│   │   └── webhooks.py        ← Email intake webhook
│   ├── schemas/
│   │   ├── ticket.py          ← Request/response models
│   │   └── responses.py       ← Standard wrappers
│   └── middleware/
│       ├── auth.py            ← API key authentication
│       └── rate_limit.py      ← Rate limiting
│
├── tools/                     ← 🔧 Agent Tools
│   ├── knowledge_base.py      ← KB search (RAG)
│   ├── customer_service.py    ← Customer lookup
│   ├── external_apis.py       ← Order/refund/password APIs
│   └── notifications.py       ← Slack/email alerts
│
├── services/                  ← 📊 Business Logic
│   ├── ticket_service.py      ← Ticket operations
│   └── analytics_service.py   ← Metrics computation
│
├── db/                        ← 💾 Database
│   ├── models.py              ← SQLAlchemy ORM models
│   ├── session.py             ← Connection pool
│   └── repositories/
│       ├── ticket_repo.py     ← Ticket queries
│       └── customer_repo.py   ← Customer queries
│
└── utils/                     ← 🛠️ Utilities
    ├── logging.py             ← Structured logging
    └── metrics.py             ← Performance tracking
```
