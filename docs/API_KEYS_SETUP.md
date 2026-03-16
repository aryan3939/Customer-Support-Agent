# 🔑 API Keys Setup Guide

Detailed instructions for getting every API key the project needs.
All services have **free tiers** — no credit card required.

---

## 1. Supabase (Database + Auth) — FREE

**What it provides:** PostgreSQL database with pgvector extension, built-in
authentication with JWT issuance, and a JWKS endpoint for token verification.

**Free Tier:** 500 MB database, 2 active projects, 50K monthly active users.

### Steps

1. Go to [supabase.com](https://supabase.com) and create a free account
2. Click **"New Project"** — name it, set a database password (save it!), pick nearest region
3. Wait ~2 minutes for initialization

### Get Your Database URL

1. Go to **Settings → Database**
2. Copy the **Connection String (URI)**
3. Replace `[YOUR-PASSWORD]` with your database password
4. **Change** `postgresql://` to `postgresql+asyncpg://` (our async driver)
5. **Change** port from `5432` to `6543` (connection pooler)

```env
DATABASE_URL=postgresql+asyncpg://postgres.abcdefgh:MyPassword@aws-0-ap-south-1.pooler.supabase.com:6543/postgres
```

### Get Your API Keys

1. Go to **Settings → API**
2. Copy **Project URL** → `SUPABASE_URL`
3. Copy **anon/public key** → `SUPABASE_ANON_KEY`
4. Copy **JWT Secret** → `SUPABASE_JWT_SECRET`

### Enable pgvector Extension

In **SQL Editor**, run:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### Verify It Works

```bash
# Test database connection (from Python):
python -c "
import asyncio, asyncpg
async def test():
    conn = await asyncpg.connect('postgresql://postgres.xxx:password@host:6543/postgres')
    print(await conn.fetchval('SELECT version()'))
    await conn.close()
asyncio.run(test())
"
```

---

## 2. Google AI Studio (LLM) — FREE (Recommended)

**What it provides:** Access to Gemini models for ticket classification and response generation.

**Free Tier:** 60 requests/min, 1,500 requests/day.

### Steps

1. Go to [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
2. Sign in with a Google account
3. Click **"Create API Key"**
4. If prompted, select "Create API key in new project"
5. Copy the key (looks like `AIzaSyC...` ~39 characters)

```env
LLM_PROVIDER=google
GOOGLE_API_KEY=AIzaSyC_paste_your_key_here
LLM_MODEL=gemini-2.0-flash
```

### Verify It Works

```bash
curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=YOUR_KEY" \
    -H "Content-Type: application/json" \
    -d '{"contents":[{"parts":[{"text":"Say hello"}]}]}'
```

If you see a JSON response with generated text → your key works!

### Available Models

| Model | Speed | Quality | Best For |
|-------|-------|---------|----------|
| `gemini-2.0-flash` | ⚡ Fast | Very Good | **Recommended** — best balance |
| `gemini-1.5-flash` | ⚡ Fast | Good | Faster, slightly less accurate |
| `gemini-1.5-pro` | 🐢 Slower | Best | Complex reasoning tasks |

---

## 3. Groq (LLM) — FREE (Alternative)

**What it provides:** Ultra-fast inference for open-source models (Llama, Mixtral).

**Free Tier:** 30 requests/min, 14,400 requests/day.

### Steps

1. Go to [console.groq.com/keys](https://console.groq.com/keys)
2. Create account (GitHub or email)
3. Click **"Create API Key"**
4. Copy the key (looks like `gsk_...` ~56 characters)

```env
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_paste_your_key_here
LLM_MODEL=llama-3.1-70b-versatile
```

### Available Models

| Model | Speed | Quality | Best For |
|-------|-------|---------|----------|
| `llama-3.1-70b-versatile` | ⚡ Fast | Good | **Recommended** — best open-source |
| `mixtral-8x7b-32768` | ⚡⚡ Very fast | Good | Long context windows |
| `llama-3.1-8b-instant` | ⚡⚡⚡ Fastest | Basic | Prototyping, low-complexity tasks |

---

## 4. LangSmith (Tracing & Observability) — FREE

**What it provides:** Complete visibility into every LLM call — prompts, responses,
token usage, latency, and full LangGraph workflow execution.

**Free Tier:** 5,000 traces/month, unlimited team members, 14-day retention.

### Why You Want This

After processing a ticket, you can see a visual timeline:
```
classify (1.2s) → kb_search (0.3s) → respond (2.1s) → validate (0.8s) → finalize (0.1s)
```

Click any node to see:
- The exact prompt sent to the LLM
- The exact response received
- Token count and cost
- Processing time
- Any errors with full stack traces

**Great for debugging and for interviews** — you can show exactly how the AI makes decisions.

### Steps

1. Go to [smith.langchain.com](https://smith.langchain.com)
2. Create account (GitHub, Google, or email)
3. Go to **Settings → API Keys** → Click "Create API Key"
4. Copy the key (looks like `lsv2_pt_...` ~58 characters)

```env
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_pt_paste_your_key_here
LANGCHAIN_PROJECT=customer-support-agent
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
```

### How It Works

LangSmith auto-instruments all LangChain/LangGraph calls via environment
variables — **zero code changes needed**. Just set `LANGCHAIN_TRACING_V2=true`.

To **disable** tracing: set `LANGCHAIN_TRACING_V2=false` — the app works fine without it.

---

## 5. Embeddings — FREE (No API Key Needed!)

The embedding model (`sentence-transformers/all-MiniLM-L6-v2`) runs **locally**
on your machine. No API key, no internet connection (after first download), no cost.

**What happens on first run:**
1. The model (~90MB) is downloaded from Hugging Face
2. It's cached in `~/.cache/huggingface/` — subsequent runs are instant
3. It generates 384-dimensional vectors from text

```env
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

---

## Complete `.env` Template

```env
# === DATABASE (Supabase) ===
DATABASE_URL=postgresql+asyncpg://postgres.xxx:password@host:6543/postgres
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGci...
SUPABASE_JWT_SECRET=your-jwt-secret

# === LLM ===
LLM_PROVIDER=google
GOOGLE_API_KEY=AIzaSyC_your_key
LLM_MODEL=gemini-2.0-flash
LLM_TEMPERATURE=0.3

# === LANGSMITH (optional) ===
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_pt_your_key
LANGCHAIN_PROJECT=customer-support-agent
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com

# === EMBEDDINGS (local, free) ===
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

# === APPLICATION ===
APP_NAME=Customer Support Agent
APP_ENV=development
DEBUG=true
LOG_LEVEL=DEBUG

# === SECURITY ===
JWT_SECRET=change-this-in-production
API_KEY_SALT=change-this-too

# === AI BEHAVIOR ===
ENABLE_AUTO_RESOLUTION=true
MAX_AUTO_ATTEMPTS=3
ESCALATION_CONFIDENCE_THRESHOLD=0.7
```
