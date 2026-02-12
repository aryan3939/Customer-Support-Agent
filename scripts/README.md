# `scripts/` — Utility Scripts

Standalone scripts for testing, debugging, and administration.
These run **outside** the FastAPI server — useful for quick checks
without starting the full app.

## Files

### `test_agent.py`
Tests the AI agent workflow **without starting the server**.

Sends sample tickets directly through `process_ticket()` and prints:
- Classification results (intent, category, priority, sentiment)
- AI-generated response
- Actions taken (audit trail)
- Whether escalation was triggered

**Usage:**
```bash
# From project root (with venv activated)
python -m scripts.test_agent
```

**When to use:**
- After changing LLM prompts — quickly verify classification accuracy
- After switching LLM providers — check response quality
- For debugging — see exactly what the graph produces without HTTP overhead

## How to Explain This

> "The test script lets me validate the agent's behavior in isolation —
> I can change a prompt and immediately see how it affects classification
> and response quality, without starting the server or using the frontend.
> It's a fast feedback loop for agent development."
