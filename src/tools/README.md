# `src/tools/` — Agent Tools (LangChain)

Tools are **functions the AI agent can invoke** during ticket processing.
They extend the agent's capabilities beyond just generating text — the agent
can search the knowledge base, look up customer data, call external APIs,
and send notifications.

## How LangChain Tools Work

In LangChain, a "tool" is a function decorated with `@tool` that the LLM
can decide to call. The agent reasons about which tool to use based on the
customer's request:

```
Customer: "What's your refund policy?"
    ↓
Agent thinks: "I need to search the knowledge base for refund policies"
    ↓
Agent calls: knowledge_base.search("refund policy")
    ↓
Gets results → uses them as context for the response
```

## Files

### `knowledge_base.py` — Vector Knowledge Base Search (15KB, largest tool)

The most important tool — implements **RAG (Retrieval Augmented Generation)**
by searching a pgvector-powered knowledge base.

**How it works:**

1. **Embed the query** — the customer's question is converted to a 384-dimensional vector using `sentence-transformers`
2. **Vector similarity search** — pgvector finds the most similar article embeddings using cosine distance
3. **Keyword fallback** — if vector search returns no results, falls back to SQL `LIKE` search on title/content
4. **Return ranked results** — the top-N matching articles, sorted by relevance

```sql
-- The actual pgvector query (simplified):
SELECT *, 1 - (embedding <=> $1) AS similarity
FROM knowledge_base_articles
WHERE 1 - (embedding <=> $1) > 0.3    -- minimum threshold
ORDER BY similarity DESC
LIMIT 5
```

**Why both vector AND keyword search?**
- Vector search finds **semantically similar** articles (understands meaning)
- Keyword search is a **safety net** — catches exact matches the embeddings might miss
- Results are combined and deduplicated

---

### `customer_service.py` — Customer Data Lookup (1.5KB)

Looks up customer information from the database — past tickets, account status,
purchase history (when available). Used by the AI to personalize responses.

---

### `external_apis.py` — External Service Integration (3KB)

Stub implementations for calling external APIs:

| Function | Purpose | Status |
|----------|---------|--------|
| `check_order_status(order_id)` | Look up order/shipping status | Stub (returns mock data) |
| `process_refund(order_id, amount)` | Initiate a refund | Stub (returns mock confirmation) |
| `reset_password(email)` | Trigger password reset email | Stub (returns mock success) |

**Design:** These are intentionally stubs. In production, you'd replace them with
real API calls to your order system, payment processor, or identity provider.
The interface stays the same — routes don't need to change.

---

### `notifications.py` — Alert System (1.2KB)

Sends notifications when certain events happen:

| Function | Purpose | Status |
|----------|---------|--------|
| `notify_escalation(ticket_id, reason)` | Alert human agents about escalated tickets | Stub (logs to console) |
| `send_resolution_email(email, ticket_id)` | Email customer that their ticket is resolved | Stub (logs to console) |

**Production:** You'd connect these to Slack (webhook), SendGrid (email), or PagerDuty (alerts).

---

### `__init__.py` — Package Init

Exports tools for use in agent nodes.
