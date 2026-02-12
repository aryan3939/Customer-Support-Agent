# Phase 2: Core AI Agent

## Why This Phase?

Phase 1 built the house frame (server, database, config). Now we build the
**brain** — the AI agent that actually processes support tickets.

Without this phase, our app is just an empty shell. After this phase:
- Tickets can be classified automatically
- The AI searches a knowledge base for relevant answers
- It generates helpful responses
- It knows when to escalate to a human
- Every action is logged for transparency

---

## Architecture: The LangGraph Workflow

```
    ┌─────────────────────────────────────────────────────┐
    │                   TICKET ARRIVES                     │
    └──────────────────────┬──────────────────────────────┘
                           ▼
    ┌──────────────────────────────────────────────────────┐
    │  CLASSIFY — What does the customer want?             │
    │  → intent, category, priority, sentiment             │
    └──────────────────────┬──────────────────────────────┘
                           ▼
                   ┌───────────────┐
                   │  ESCALATE?    │
                   │ urgent+angry? │
                   │ low confidence│
                   └───┬───────┬───┘
               YES ←───┘       └───→ NO
                ▼                      ▼
    ┌───────────────┐    ┌──────────────────────────────┐
    │   ESCALATE    │    │  SEARCH KB — find relevant    │
    │ handoff to    │    │  articles from knowledge base │
    │ human agent   │    └──────────────┬───────────────┘
    └───────┬───────┘                   ▼
            │           ┌──────────────────────────────┐
            │           │  RESOLVE — generate response  │
            │           │  using KB + classification     │
            │           └──────────────┬───────────────┘
            │                          ▼
            │           ┌──────────────────────────────┐
            │           │  VALIDATE — QA check the      │
            │    ┌──────│  response before sending      │
            │    │      └──────────────┬───────────────┘
            │    │                 ┌───┴───┐
            │    │          PASS ←─┘       └─→ FAIL
            │    │           ▼                   ▼
            │    │    ┌────────────┐      (retry or escalate)
            │    └────│  RESPOND   │
            │         └─────┬──────┘
            ▼               ▼
    ┌──────────────────────────────────────────────────────┐
    │                      DONE                             │
    └──────────────────────────────────────────────────────┘
```

---

## Files Created

```
src/agents/
├── __init__.py          ← Re-exports process_ticket()
├── state.py             ← TicketState: data shape for the workflow
├── llm.py               ← LLM factory (Google/Groq)
├── graph.py             ← Main LangGraph workflow definition
├── nodes/
│   ├── classifier.py    ← Classifies tickets (intent, priority, etc.)
│   ├── resolver.py      ← Generates AI responses
│   ├── escalator.py     ← Handles human agent handoff
│   └── validator.py     ← QA-checks responses before sending
├── edges/
│   └── conditions.py    ← Routing logic between nodes
└──

src/tools/
├── __init__.py
└── knowledge_base.py    ← KB search (sample articles for now)
```

---

## File-by-File Breakdown

### `state.py` — The Data Schema

LangGraph is a state machine. State flows through every node:

```python
class TicketState(TypedDict, total=False):
    # Input
    ticket_id: str
    subject: str
    message: str
    
    # Classification (set by classifier)
    intent: str        # "password_reset", "billing_inquiry"
    category: str      # "account", "billing", "technical"
    priority: str      # "low", "medium", "high", "urgent"
    sentiment: str     # "positive", "neutral", "negative", "angry"
    
    # Context (set by KB search)
    kb_results: list[dict]
    
    # Response (set by resolver/validator)
    draft_response: str
    final_response: str
    
    # Audit trail
    actions_taken: list[dict]
```

`total=False` means nodes only return the fields they update — LangGraph merges partial updates automatically.

---

### `llm.py` — LLM Factory

One function that returns the right LLM based on your `.env`:

```python
llm = get_llm()  # Returns Google Gemini or Groq based on LLM_PROVIDER
```

Switch providers by changing one line in `.env`. No code changes needed!

---

### `classifier.py` — Ticket Classification

The FIRST node. Uses a structured prompt to classify tickets:

```
Input: "I can't reset my password, tried 3 times!"
Output: {intent: "password_reset", priority: "high", sentiment: "negative", confidence: 0.92}
```

The prompt asks the LLM to return JSON with specific fields. Error handling
gracefully falls back to defaults if the LLM returns malformed JSON.

---

### `knowledge_base.py` — KB Search

Searches for relevant articles to ground the AI's response:

```
Input: "password reset" (from ticket)
Output: [{article: "Password Reset Guide", text: "Step 1: Go to login..."}]
```

**Phase 2**: Uses keyword matching against 5 sample articles.
**Phase 3**: Will use pgvector similarity search with real embeddings.

The 5 sample articles cover: password reset, billing/refunds, account setup,
troubleshooting, and shipping.

---

### `resolver.py` — Response Generation

Constructs a detailed prompt with ALL context:
- Customer's message
- Classification results
- KB article matches
- Customer history

Then asks the LLM to generate an empathetic, step-by-step response.

---

### `validator.py` — Quality Assurance

Checks responses before sending:
1. Not empty
2. Minimum 50 characters
3. Doesn't contain uncertainty markers ("I'm not sure", "I cannot")

If checks fail 3 times → escalate instead of sending a bad response.

---

### `escalator.py` — Human Handoff

When the AI can't handle a ticket, this node:
1. Determines why (urgent, angry, low confidence, max attempts)
2. Generates a handoff summary via LLM
3. Sets a customer-facing acknowledgment message

---

### `conditions.py` — Routing Logic

Two routing functions:
- `should_escalate_after_classify`: urgent+angry OR low confidence → escalate
- `should_escalate_after_validate`: pass → respond, fail → retry/escalate

---

### `graph.py` — The Main Workflow

Assembles everything into a LangGraph:

```python
graph = StateGraph(TicketState)
graph.add_node("classify", classify_ticket)
graph.add_node("search_kb", search_knowledge_base)
graph.add_node("resolve", generate_response)
graph.add_node("validate", validate_response)
graph.add_node("escalate", escalate_ticket)
graph.add_node("respond", _finalize_response)

graph.set_entry_point("classify")
graph.add_conditional_edges("classify", should_escalate_after_classify, {...})
graph.add_edge("search_kb", "resolve")
graph.add_edge("resolve", "validate")
graph.add_conditional_edges("validate", should_escalate_after_validate, {...})
```

Public API:
```python
result = await process_ticket(
    ticket_id="abc-123",
    customer_email="user@example.com",
    subject="Can't reset password",
    message="I've tried 3 times...",
)
```

---

## How to Test

### Quick Test Script

Run the test script to process a sample ticket:

```bash
# Activate venv
.venv\Scripts\activate

# Run the test
python scripts/test_agent.py
```

### What to Expect

The test script sends a sample ticket through the graph. You should see:
1. Structured log output showing each node executing
2. Classification results (intent, priority, sentiment)
3. KB search results
4. The AI-generated response
5. Complete audit trail

---

## What's Next?

With the agent core running, future phases add:
1. **API Routes** — REST endpoints to submit/manage tickets
2. **Database Integration** — Persist tickets and actions
3. **Vector Search** — Replace keyword KB search with pgvector
4. **More Tools** — Email, Slack notifications, CRM lookups
