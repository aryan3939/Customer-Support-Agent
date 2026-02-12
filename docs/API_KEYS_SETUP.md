# API Keys Setup Guide

This project needs **only 2 things** to run:

| Service | What For | Cost | Required? |
|---------|----------|------|-----------|
| **Google AI Studio** | LLM (Gemini) for AI responses | **FREE** — 60 req/min | ✅ Yes (or use Groq instead) |
| **LangSmith** | Trace & debug every LLM call | **FREE** — 5K traces/month | ✅ Highly recommended |
| **Supabase** | PostgreSQL database | **FREE** — 500MB | ⚠️ Optional (app works without it) |
| **Groq** | Alternative LLM (Llama/Mixtral) | **FREE** — 30 req/min | ❌ Optional |
| **Redis** | Caching | **FREE** (local Docker) | ❌ Optional |

---

## 1. Google AI Studio API Key (REQUIRED)

This is the **only key you must have** to run the project.

### Steps:

1. Go to **https://aistudio.google.com/apikey**

2. **Sign in** with your Google account (any Gmail works)

3. You'll see the **API Keys** page. Click **"Create API Key"**

4. It will ask you to select a Google Cloud project:
   - If you don't have one → Click **"Create API key in new project"**
   - If you have one → Select it and click **"Create API key in existing project"**

5. **Copy the key** — it looks like: `AIzaSyC...about40characters...`

6. **Paste it in your `.env` file:**
   ```env
   LLM_PROVIDER=google
   GOOGLE_API_KEY=AIzaSyC_paste_your_key_here
   LLM_MODEL=gemini-2.0-flash
   ```

### Verify it works:

```bash
curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=YOUR_KEY_HERE" -H "Content-Type: application/json" -d "{\"contents\":[{\"parts\":[{\"text\":\"Say hello\"}]}]}"
```

If you see a JSON response with text → your key works!

### Free Tier Limits:
- 60 requests per minute
- 1,500 requests per day
- No credit card needed

### Links:
- Create key: https://aistudio.google.com/apikey
- Documentation: https://ai.google.dev/gemini-api/docs/api-key
- Models list: https://ai.google.dev/gemini-api/docs/models

---

## 2. LangSmith API Key (HIGHLY RECOMMENDED)

LangSmith gives you **complete visibility** into what your AI agent is doing — every LLM call, every token, every decision, with latency and cost tracking.

### Why You Need This (especially for interviews):
- **See every LLM prompt and response** in a visual timeline
- **Trace the full LangGraph workflow** — classify → search KB → resolve → validate
- **Debug issues** — which node failed? What did the LLM actually return?
- **Track costs and latency** — how long each LLM call took
- Interviewers will be impressed you have **observability** set up

### Steps:

1. Go to **https://smith.langchain.com**

2. Click **"Sign Up"** (supports GitHub, Google, or email)

3. After signing in, go to **Settings → API Keys**
   - Direct link: **https://smith.langchain.com/settings**

4. Click **"Create API Key"**
   - **Type**: Personal key is fine
   - **Expiration**: Never (for development)
   - Click **"Create API Key"**

5. **Copy the key** — it looks like: `lsv2_pt_...about50characters...`

6. **Paste in your `.env` file:**
   ```env
   LANGCHAIN_TRACING_V2=true
   LANGCHAIN_API_KEY=lsv2_pt_paste_your_key_here
   LANGCHAIN_PROJECT=customer-support-agent
   LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
   ```

### What You'll See in the Dashboard:

After processing a ticket, go to **https://smith.langchain.com** → your project:

- **Trace view**: Full graph execution timeline showing each node
- **LLM calls**: Exact prompts sent, responses received, tokens used
- **Latency**: How long each step took (classification, KB search, etc.)
- **Errors**: Any failures with full stack traces

### How It Works (Zero Code Changes!):

LangSmith auto-instruments all LangChain/LangGraph calls via env vars:
```
LANGCHAIN_TRACING_V2=true  →  enables tracing
LANGCHAIN_API_KEY=...      →  where to send traces
```
That's it! Your `graph.py`, `classifier.py`, `resolver.py` etc. are all auto-traced.

### Free Tier Limits:
- 5,000 traces per month
- Unlimited team members
- 14-day data retention
- No credit card needed

### To Disable Tracing:
Set `LANGCHAIN_TRACING_V2=false` in `.env` — the app works fine without it.

### Links:
- Dashboard: https://smith.langchain.com
- API keys: https://smith.langchain.com/settings
- Documentation: https://docs.smith.langchain.com

---

## 3. Supabase Database (OPTIONAL)

The app works without a database (uses in-memory storage). But if you want persistence:

### Steps:

1. Go to **https://supabase.com/dashboard**

2. Click **"Sign Up"** (or sign in with GitHub)

3. Click **"New Project"**
   - **Name**: `customer-support-agent`
   - **Database Password**: Choose a strong password → **SAVE THIS PASSWORD!**
   - **Region**: Pick the closest to you (e.g., `South Asia (Mumbai)` for India)
   - Click **"Create new project"**

4. Wait ~2 minutes for the project to initialize

5. **Get your connection string:**
   - Click **"Connect"** button (top bar)
   - Select **"ORMs"** tab
   - Copy the URI — it looks like:
     ```
     postgresql://postgres.abcxyz:[YOUR-PASSWORD]@aws-0-ap-south-1.pooler.supabase.com:6543/postgres
     ```

6. **Important!** Replace `[YOUR-PASSWORD]` with the actual password you set in Step 3

7. **Add `+asyncpg` after `postgresql`** (our app needs the async driver):
   ```
   postgresql+asyncpg://postgres.abcxyz:yourpassword@aws-0-ap-south-1.pooler.supabase.com:6543/postgres
   ```

8. **Paste in your `.env` file:**
   ```env
   DATABASE_URL=postgresql+asyncpg://postgres.abcxyz:yourpassword@aws-0-ap-south-1.pooler.supabase.com:6543/postgres
   ```

### Also get these (from Project Settings → API):
```env
SUPABASE_URL=https://abcxyz.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOi...long_key...
```

### If you DON'T want to set up Supabase yet:

Just put a placeholder — the app will log a warning but continue working:
```env
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/testdb
```

### Free Tier Limits:
- 500 MB database storage
- 2 active projects
- 50,000 monthly active users
- No credit card needed

### Links:
- Dashboard: https://supabase.com/dashboard
- Connection docs: https://supabase.com/docs/guides/database/connecting-to-postgres

---

## 4. Groq API Key (OPTIONAL — Alternative LLM)

Use Groq **instead of** Google if you want faster responses (but smaller models).

### Steps:

1. Go to **https://console.groq.com**

2. Click **"Sign Up"** (supports Google, GitHub, or email)

3. After signing in, go to **https://console.groq.com/keys**

4. Click **"Create API Key"**
   - **Name**: anything (e.g., `customer-support-agent`)
   - Click **"Submit"**

5. **Copy the key** — it looks like: `gsk_...about50characters...`

6. **Update your `.env` to use Groq instead of Google:**
   ```env
   LLM_PROVIDER=groq
   GROQ_API_KEY=gsk_paste_your_key_here
   LLM_MODEL=llama-3.1-70b-versatile
   ```

### Free Tier Limits:
- 30 requests per minute
- 14,400 requests per day
- No credit card needed

### Available Models:
| Model | Speed | Quality |
|-------|-------|---------|
| `llama-3.1-70b-versatile` | Fast | Good |
| `mixtral-8x7b-32768` | Very fast | Good |
| `llama-3.1-8b-instant` | Fastest | Basic |

### Links:
- Create key: https://console.groq.com/keys
- Docs: https://console.groq.com/docs/quickstart
- Models: https://console.groq.com/docs/models

---

## 5. Redis (OPTIONAL — for caching)

Redis is only needed if you want caching. Skip this for now.

### If you want to run it:

```bash
# Option A: Docker (easiest)
docker run -d --name redis -p 6379:6379 redis:7-alpine

# Option B: docker-compose (included in project)
docker-compose up -d
```

```env
REDIS_URL=redis://localhost:6379/0
```

No API key needed — runs locally.

---

## Your Final `.env` File

Here's what your `.env` should look like with the minimum setup:

```env
# === REQUIRED ===
GOOGLE_API_KEY=AIzaSyC_your_actual_key_here

# === DATABASE (use placeholder if no Supabase) ===
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/testdb

# === LANGSMITH (highly recommended) ===
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_pt_your_key_here
LANGCHAIN_PROJECT=customer-support-agent
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com

# === DEFAULTS (don't need to change) ===
LLM_PROVIDER=google
LLM_MODEL=gemini-2.0-flash
LLM_TEMPERATURE=0.3
APP_NAME=Customer Support Agent
APP_ENV=development
DEBUG=true
LOG_LEVEL=DEBUG
APP_HOST=0.0.0.0
APP_PORT=8000
REDIS_URL=redis://localhost:6379/0
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
JWT_SECRET=dev-secret-change-in-production
API_KEY_SALT=dev-salt-change-in-production
ENABLE_AUTO_RESOLUTION=true
MAX_AUTO_ATTEMPTS=3
ESCALATION_CONFIDENCE_THRESHOLD=0.7
```

### After filling `.env`, run:
```bash
venv\Scripts\activate
pip install -r requirements.txt
uvicorn src.main:app --reload
```

Then test: **http://localhost:8000/docs**

After creating a ticket, check your traces at: **https://smith.langchain.com**
