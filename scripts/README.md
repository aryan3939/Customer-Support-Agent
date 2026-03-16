# `scripts/` — Standalone Utility Scripts

Scripts that run independently from the FastAPI server. They connect to the
database directly and perform one-off or setup tasks.

## Files

### `seed_kb.py` — Knowledge Base Seeder (33KB)

The largest script — populates the knowledge base with support articles and
their vector embeddings. **You must run this before the AI agent can answer
questions** — without KB articles, the RAG search returns nothing.

**What it does:**
1. Connects to Supabase PostgreSQL
2. Defines 20+ knowledge base articles covering common support topics:
   - Password reset procedures
   - Billing and payment FAQ
   - Account management
   - Shipping and returns
   - Technical troubleshooting
   - Product information
3. For each article, generates a 384-dimensional vector embedding using `sentence-transformers`
4. Inserts the articles + embeddings into the `knowledge_base_articles` table

**How to run:**
```bash
# From the project root (with venv activated)
python scripts/seed_kb.py
```

**Important notes:**
- Running it again is safe — it checks for existing articles and skips duplicates
- The first run downloads the embedding model (~90MB), subsequent runs use the cached model
- Takes about 30-60 seconds on first run (model download + embedding generation)

---

### `test_agent.py` — Standalone Agent Test (4.5KB)

Tests the AI agent without starting the full FastAPI server. Useful for
debugging the LangGraph workflow in isolation.

**What it does:**
1. Creates sample support tickets (various intents and tones)
2. Runs each through the `process_ticket()` function
3. Prints the classification results, KB search results, and AI responses
4. Shows the full audit trail for each ticket

**How to run:**
```bash
# From the project root (with venv activated)
python scripts/test_agent.py
```

**Sample tickets it tests:**
- Password reset request (routine)
- Billing dispute (angry customer)
- Bug report (technical)
- General question (low priority)
- Account security concern (urgent)

**Use this when:**
- You change the LangGraph workflow and want to verify it works
- You switch LLM providers and want to compare output
- You update the classifier prompt and want to check classification accuracy
