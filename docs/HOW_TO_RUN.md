# 🚀 How to Run the Project

Quick-start guide to get the Customer Support Agent running locally.
For detailed explanations of each step, see the numbered build guides (01-06).

---

## Prerequisites

- Python 3.11+
- Node.js 18+
- Supabase account (free tier)
- Google AI Studio or Groq API key (free tier)

---

## 1. Clone & Set Up Backend

```bash
git clone <your-repo-url>
cd "Customer Support Agent"

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate         # Windows CMD
# source venv/bin/activate    # macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

---

## 2. Configure Environment Variables

```bash
copy .env.example .env        # Windows
# cp .env.example .env        # macOS/Linux
```

Edit `.env` with your credentials:

```env
# Database (from Supabase Dashboard → Settings → Database)
DATABASE_URL=postgresql+asyncpg://postgres.xxx:password@aws-0-region.pooler.supabase.com:6543/postgres

# Supabase (from Dashboard → Settings → API)
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGci...
SUPABASE_JWT_SECRET=your-jwt-secret

# LLM (from aistudio.google.com/apikey)
LLM_PROVIDER=google
GOOGLE_API_KEY=AIzaSyC...
LLM_MODEL=gemini-2.0-flash

# LangSmith tracing (optional, from smith.langchain.com)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_pt_...
```

See [API_KEYS_SETUP.md](API_KEYS_SETUP.md) for detailed instructions on getting each key.

---

## 3. Enable pgvector Extension

In the Supabase Dashboard → **SQL Editor**, run:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

---

## 4. Seed the Knowledge Base

```bash
python scripts/seed_kb.py
```

This populates the vector knowledge base with support articles and their embeddings.
First run downloads the embedding model (~90MB).

---

## 5. Start the Backend

```bash
uvicorn src.main:app --reload
```

You should see:
```
INFO: application_starting ...
INFO: database_connected ...
INFO: embedding_model_loaded — dimension=384
INFO: application_started — All systems ready ✓
```

Visit `http://localhost:8000/docs` for the interactive Swagger UI.

---

## 6. Set Up & Start the Frontend

```bash
cd frontend
npm install

# Configure Supabase for the frontend
copy .env.local.example .env.local     # Windows
```

Edit `frontend/.env.local`:
```env
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGci...
```

```bash
npm run dev
```

Visit `http://localhost:3000` — you'll see the login / sign-up page.

---

## 7. Create Users

### Customer (via Frontend)
1. Go to `http://localhost:3000/login`
2. Click **Sign Up** tab
3. Enter email and password → submit
4. Check email for confirmation link

### Admin (via Supabase SQL Editor)
1. Create a user (sign up via frontend or Supabase Dashboard)
2. Run in SQL Editor:
```sql
UPDATE auth.users
SET raw_user_meta_data = jsonb_set(
    COALESCE(raw_user_meta_data, '{}'),
    '{role}', '"admin"'
)
WHERE email = 'admin@example.com';
```

---

## 8. Test the System

1. **Sign in** as a customer at `http://localhost:3000/login`
2. **Create a ticket** — the AI processes it and shows the classification + response
3. **Click the ticket** to see the chat view
4. **Send follow-up messages** — the AI responds with full conversation context
5. **Resolve the ticket** from the ticket detail page

### Test the Agent Standalone

```bash
python scripts/test_agent.py
```

Processes sample tickets through the AI and prints results without needing the server.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError` | Activate venv: `venv\Scripts\activate` |
| `GOOGLE_API_KEY not set` | Edit `.env` and add your API key |
| `Database connection failed` | Check `DATABASE_URL` — correct password, host, port 6543 |
| `"alg value is not allowed"` | Install `PyJWT[crypto]`: `pip install PyJWT[crypto]` |
| Port 8000 already in use | Use `uvicorn src.main:app --reload --port 8001` |
| Frontend can't load tickets | Make sure backend is running on port 8000 |
| KB search returns no results | Run `python scripts/seed_kb.py` |
| Supabase signup no email | Check Supabase Dashboard → Authentication → Email settings |
