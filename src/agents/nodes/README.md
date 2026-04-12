# `src/agents/nodes/` — Graph Nodes (Pipeline Steps)

Each file in this folder is a **single node** in the LangGraph state machine.
A node is a Python function that:
1. Receives the current `TicketState`
2. Does one specific task (classify, search, generate, etc.)
3. Returns a **partial state update** (only the fields it changed)

LangGraph then merges the partial update into the full state and passes it to the next node.

## Files

### `classifier.py` — Ticket Classification Node

**What it does:** Sends the customer's message to the LLM and asks it to classify:
- **Intent** — what the customer wants (e.g., `password_reset`, `billing_inquiry`, `refund_request`)
- **Category** — which department handles it (`account`, `billing`, `technical`, etc.)
- **Priority** — how urgent (`low`, `medium`, `high`, `urgent`)
- **Sentiment** — customer's emotional state (`positive`, `neutral`, `negative`, `angry`)
- **Confidence** — how sure the AI is (0.0 to 1.0)

**How it works:**
```python
# Uses structured output — LLM returns a validated Pydantic object
llm_with_structure = llm.with_structured_output(ClassificationResult)
result = await llm_with_structure.ainvoke(prompt)
# result.intent = "password_reset", result.priority = "high", etc.
```

**Key decision:** If `priority == "urgent"` or `sentiment == "angry"` or `confidence < 0.7`, the ticket is flagged for potential escalation.

---

### `kb_searcher.py` — Knowledge Base Search Node

**What it does:** Searches the vector knowledge base for articles relevant to the customer's issue. Uses **RAG (Retrieval Augmented Generation)** — the found articles become context for the response generator.

**How it works:**
1. Takes the `subject` and `message` from the ticket state
2. Calls the KB search tool (`tools/knowledge_base.py`)
3. The tool embeds the query using `sentence-transformers` and runs a pgvector cosine similarity search
4. Returns the top-N matching articles as `kb_results` in the state

**Why this matters:** Without KB context, the LLM would hallucinate answers. With it, responses are **grounded in real company data**.

---

### `resolver.py` — Response Generation Node

**What it does:** Generates the AI's response to the customer. This is where the LLM actually writes the reply, using:
- The original customer message
- Classification data (intent, sentiment)
- KB search results (real articles to reference)
- Conversation history (for follow-ups)

**How it works:**
```
Prompt = "You are a customer support agent. The customer is {sentiment} about {intent}.
          Here are relevant knowledge base articles: {kb_results}.
          Write a helpful, empathetic response."
```

The LLM generates a draft response which is stored as `draft_response` in the state.

---

### `validator.py` — Response Quality Check Node

**What it does:** A second LLM call that reviews the draft response for quality. Checks:
- **Accuracy** — does the response align with KB articles?
- **Helpfulness** — does it actually answer the question?
- **Tone** — is it appropriate for the customer's sentiment?
- **Completeness** — are all parts of the question addressed?

If the response passes, it's promoted to `final_response`. If it fails, the ticket is flagged for escalation.

---

### `escalator.py` — Human Escalation Node

**What it does:** When a ticket needs human attention, this node:
1. Marks `needs_escalation = True`
2. Records the reason (e.g., "Customer is angry and AI confidence is low")
3. Logs an `escalate` action to the audit trail
4. Sets the ticket status to `escalated`

**Escalation triggers:**
- `priority == "urgent"` — critical issues must go to humans
- `sentiment == "angry"` — hostile customers need human empathy
- `confidence < 0.7` — AI isn't sure enough to respond
- Validator rejects the response — quality check failed

---

### `__init__.py` — Package Init

Exports all node functions for clean imports in `graph.py`.
