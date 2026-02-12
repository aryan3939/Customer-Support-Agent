# `nodes/` — LangGraph Node Functions

Each file in this folder is a **single node** in the LangGraph workflow.
A node is an async function that:
1. Receives the current `TicketState`
2. Does one specific job (usually an LLM call)
3. Returns a partial state update (merged back into the full state)

## Files

### `classifier.py` — Classify Ticket
**First node in the graph.** Sends the ticket to the LLM with a classification
prompt and extracts structured data:

- **Intent**: What the customer wants (e.g., `refund_request`, `password_reset`, `bug_report`)
- **Category**: Department (e.g., `billing`, `technical`, `account`)
- **Priority**: `low` / `medium` / `high` / `urgent`
- **Sentiment**: `positive` / `neutral` / `negative` / `angry`
- **Confidence**: 0.0–1.0 score of how sure the LLM is

### `resolver.py` — Generate Response
Takes the classification + KB search results and generates a customer-facing
response. The prompt includes:
- Original message and classification
- Relevant knowledge base articles (from the search step)
- Tone and formatting guidelines

### `validator.py` — Validate Response
Quality-checks the generated response before sending:
- Is it long enough? (not a one-liner)
- Does it address the customer's actual issue?
- Is the tone appropriate?
- Should it be retried or escalated?

### `escalator.py` — Escalate Ticket
Handles tickets the AI can't resolve:
- Generates a structured escalation reason
- Creates a handoff message for human agents
- Sets `needs_escalation = True` in the state

## How to Explain This

> "Each node follows the **Single Responsibility Principle** — the classifier
> only classifies, the resolver only generates responses, the validator only
> checks quality. This makes each step independently testable, debuggable
> (visible in LangSmith), and swappable. If I want to change how classification
> works, I only touch `classifier.py`."
