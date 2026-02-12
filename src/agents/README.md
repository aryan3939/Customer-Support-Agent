# `agents/` — AI Agent (LangGraph Workflow)

This folder contains the **AI agent** — the core intelligence of the system.
It's built with **LangGraph**, which models the agent as a **state machine**
(a directed graph where each node performs one step).

## Why LangGraph?

Traditional chatbots are a single LLM call. Real support agents need to:
1. **Classify** the issue (billing? technical? account?)
2. **Search** their knowledge base for relevant articles
3. **Generate** a personalized response using context
4. **Validate** the response quality before sending
5. **Escalate** if the AI can't handle it

LangGraph lets you define each step as a separate **node** and connect them
with **edges** (including conditional logic like "escalate if urgent + angry").

## The Workflow

```
┌──────────────┐
│    START     │
└──────┬───────┘
       ▼
┌──────────────┐     ┌──────────────────┐
│  Classify    │────▶│  Escalate?       │──── YES ──▶ escalate_ticket ──▶ END
│  Ticket      │     │  (urgent+angry)  │
└──────────────┘     └───────┬──────────┘
                             │ NO
                             ▼
                    ┌──────────────────┐
                    │  Search KB       │
                    │  (find articles) │
                    └───────┬──────────┘
                            ▼
                    ┌──────────────────┐
                    │  Generate        │
                    │  Response (LLM)  │
                    └───────┬──────────┘
                            ▼
                    ┌──────────────────┐     ┌──────────────┐
                    │  Validate        │────▶│  Retry or    │──── ESCALATE ──▶ END
                    │  Response        │     │  Escalate?   │
                    └──────────────────┘     └──────┬───────┘
                                                    │ OK
                                                    ▼
                                            ┌──────────────┐
                                            │  Finalize    │──▶ END
                                            │  Response    │
                                            └──────────────┘
```

## Files

| File | What It Does |
|------|-------------|
| `graph.py` | Builds and compiles the LangGraph state machine. Exposes `process_ticket()` — the single public API |
| `state.py` | Defines `TicketState` (TypedDict) — all data that flows through the graph |
| `llm.py` | LLM factory — creates `ChatGoogleGenerativeAI` or `ChatGroq` based on config |
| `nodes/` | Node functions — each file is one step in the workflow |
| `edges/` | Edge condition functions — routing logic between nodes |

## How to Explain This

> "I used **LangGraph** because support ticket handling isn't a single LLM call —
> it's a multi-step workflow. Each step (classify, search, respond, validate) is
> a separate node in a directed graph. The graph supports conditional routing
> (e.g., escalate immediately if the customer is angry and the issue is urgent)
> and retry logic (if the generated response fails quality checks). This gives
> me full control over the agent's behavior, a complete audit trail of every
> action, and the ability to observe each step independently in LangSmith."
