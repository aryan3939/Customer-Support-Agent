# Setup Guide

Step-by-step guide to set up and run the OpenMetadata AI Agent.

## Prerequisites

- **Python 3.11+** installed
- **Git** installed
- A free [Supabase](https://supabase.com) account
- A free [OpenRouter](https://openrouter.ai) account
- (Optional) A [LangSmith](https://smith.langchain.com) account for tracing

## Step 1: Environment Setup

```bash
# Navigate to the project
cd aryan3939

# Create a Python virtual environment
python -m venv .venv

# Activate it
# Windows:
.venv\Scripts\activate
# Linux/Mac:
# source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Crawl4AI browser dependencies
crawl4ai-setup
```

## Step 2: Create Supabase Project

1. Go to [supabase.com](https://supabase.com) and create a new project
2. Wait for the project to initialize (~2 minutes)
3. Go to **Project Settings** → **API**
4. Copy:
   - **Project URL** (e.g., `https://xxxx.supabase.co`)
   - **Service Role Key** (under "Project API keys" — the `service_role` key, NOT the `anon` key)

## Step 3: Set Up Database Schema

1. In your Supabase dashboard, go to **SQL Editor**
2. Click **New Query**
3. Copy the entire contents of `setup_db.sql` from the project root
4. Click **Run** (or Ctrl+Enter)
5. Verify: Go to **Table Editor** — you should see 4 tables:
   - `sources`
   - `documents`
   - `conversations`
   - `messages`

## Step 4: Get API Keys

### OpenRouter
1. Go to [openrouter.ai](https://openrouter.ai)
2. Sign up / Log in
3. Go to **Keys** → **Create Key**
4. Copy the API key

### LangSmith (Optional but recommended)
1. Go to [smith.langchain.com](https://smith.langchain.com)
2. Sign up / Log in
3. Go to **Settings** → **API Keys** → **Create API Key**
4. Copy the API key

## Step 5: Configure Environment

```bash
# Copy the template
copy .env.example .env    # Windows
# cp .env.example .env    # Linux/Mac

# Edit .env with your actual values:
```

Your `.env` should look like:
```
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_SERVICE_KEY=eyJhbGci...your-service-role-key...
OPENROUTER_API_KEY=sk-or-v1-...your-openrouter-key...
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_pt_...your-langsmith-key...
LANGCHAIN_PROJECT=openmetadata-agent
```

## Step 6: Run Ingestion

```bash
python scripts/run_ingestion.py
```

**What this does:**
1. Fetches the sitemap from docs.open-metadata.org
2. Selects ~40-60 pages from v1.12.x documentation
3. Scrapes each page using Crawl4AI (takes 2-5 minutes)
4. Chunks the content into ~500-token pieces with overlap
5. Generates embeddings using all-MiniLM-L6-v2 (local, no API)
6. Stores everything in your Supabase database

**Verify:** Check your Supabase Table Editor:
- `sources` table should have ~40-60 rows
- `documents` table should have ~200-400 rows (chunks)

## Step 7: Chat with the Agent

```bash
python -m src.main
```

You'll see an interactive terminal interface. Try questions like:
- "How do I deploy OpenMetadata using Docker?"
- "What is data lineage?"
- "How to connect Snowflake?"

## Step 8: Evaluate Retrieval Quality

```bash
python eval/run_eval.py --verbose
```

This runs 10 golden queries and reports:
- **HR@5** (Hit Rate): Target ≥ 80%
- **MRR@5** (Mean Reciprocal Rank): Target ≥ 0.6

## Troubleshooting

| Issue | Solution |
|---|---|
| `ModuleNotFoundError` | Make sure your venv is activated and `pip install -r requirements.txt` completed |
| Supabase connection error | Check `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` in `.env` |
| OpenRouter 401 error | Check `OPENROUTER_API_KEY` in `.env` |
| Crawl4AI browser error | Run `crawl4ai-setup` to install Playwright browsers |
| Embedding model download slow | First run downloads ~80MB model; subsequent runs use cache |
| Empty search results | Make sure ingestion ran successfully; check `documents` table |

## Configuration

Edit `config.yaml` to change:
- **LLM model**: Change `llm.model` to any OpenRouter model
- **Chunk size**: Adjust `chunking.chunk_size` and `chunking.chunk_overlap`
- **Retrieval**: Tune `retrieval.top_k` and `retrieval.similarity_threshold`
- **Doc version**: Change `ingestion.docs_version` to target a different version
