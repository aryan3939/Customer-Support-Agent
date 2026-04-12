# `src/agents/` — AI Agent (LangGraph)

This is the **brain** of the application — the LangGraph state machine that processes every customer support ticket through an intelligent pipeline.

## What is LangGraph?

LangGraph is a framework for building **stateful, multi-step AI workflows** as directed graphs. Think of it like a flowchart where:
- **Nodes** = individual steps (functions that do something)
- **Edges** = connections between steps (which step runs next)
- **State** = a shared data object that flows through every node

Unlike simple `llm.invoke("answer this")` calls, LangGraph gives you:
- **Control flow** — explicit routing between steps
- **Conditional branching** — e.g., escalate if priority is urgent
- **Quality gates** — validate responses before sending
- **Full audit trail** — every node records what it did and why

## The Ticket Processing Graph

```
     START
       │
       ▼
 ┌──────────┐
 │ CLASSIFY  │ ← LLM analyzes intent, priority, sentiment, category
 └────┬─────┘
      │
 Should escalate? ──YES──→ [ESCALATE] → END
      │ NO                    (routes to human agent)
      ▼
 ┌───────────┐
 │ KB SEARCH  │ ← Embeds question → pgvector similarity search
 └────┬──────┘
      │
      ▼
 ┌──────────┐
 │ RESPOND   │ ← LLM generates response using KB context
 └────┬─────┘
      │
      ▼
 ┌──────────┐
 │ VALIDATE  │ ← LLM checks response quality & accuracy
 └────┬─────┘
      │
 Should escalate? ──YES──→ [ESCALATE] → END
      │ NO
      ▼
 ┌──────────┐
 │ FINALIZE  │ ← Marks ticket as resolved, logs actions
 └──────────┘
      │
     END
```

## Files in This Folder

| File | Purpose | Key Details |
|------|---------|-------------|
| `graph.py` | **Main workflow definition** — builds and compiles the LangGraph. Contains `process_ticket()` which is the single entry point for the entire AI system. | The graph is compiled once at module import time (singleton). Every ticket goes through this graph. |
| `state.py` | **State schema** — defines `TicketState`, the TypedDict that flows through every node. Also contains dataclasses for `TicketMessage`, `ClassificationResult`, `KBSearchResult`, and `ActionRecord`. | Uses `total=False` so nodes only return fields they update — LangGraph merges partial updates automatically. |
| `llm.py` | **LLM factory** — creates the right LangChain chat model based on `.env` config (`google` or `groq`). | Supports Google Gemini and Groq. Both implement `BaseChatModel`, so downstream code doesn't care which provider is used. |
| `models.py` | **Structured output models** — Pydantic models that define the exact JSON shape the LLM must return. Used with `llm.with_structured_output()`. | Ensures the LLM returns validated, typed data instead of raw text that needs manual parsing. |
| `__init__.py` | Package init — exports `process_ticket` for easy importing. | `from src.agents import process_ticket` |

### `nodes/` Subfolder
Each file is a single step in the LangGraph pipeline. See `nodes/README.md`.

### `edges/` Subfolder
Contains conditional routing functions that decide which path the graph takes. See `edges/README.md`.

## How State Flows Through Nodes

```python
# 1. Ticket arrives → initial state created
state = {
    "ticket_id": "abc-123",
    "customer_email": "user@example.com",
    "subject": "Can't login",
    "message": "I've been locked out...",
    "channel": "web",
}

# 2. Classifier node runs → adds classification fields
# Returns ONLY the fields it updates:
{
    "intent": "password_reset",
    "priority": "high",
    "sentiment": "frustrated",
    "category": "account",
    "confidence": 0.92,
}
# LangGraph MERGES this into the state automatically

# 3. KB search node runs → adds knowledge base results
{
    "kb_results": [
        {"article_title": "Password Reset Guide", "chunk_text": "...", "relevance_score": 0.89},
    ],
}

# 4. Resolver node runs → adds draft response
{
    "draft_response": "I understand you're locked out. Here's how to reset..."
}

# 5. Validator node runs → approves and finalizes
{
    "final_response": "I understand you're locked out. Here's how to reset...",
    "needs_escalation": False,
}
```

## How to Use

```python
from src.agents.graph import process_ticket

result = await process_ticket(
    ticket_id="abc-123",
    customer_email="user@example.com",
    subject="Can't reset password",
    message="I've tried 3 times and no email arrives",
    channel="web",
)

# result contains: intent, priority, sentiment, final_response, actions_taken, etc.
```
