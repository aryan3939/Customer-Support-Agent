# `tools/` — Agent Tools

Tools are **actions the AI agent can take** during ticket processing.
They're called by the graph nodes when the agent needs external information
or wants to trigger side effects.

## Files

### `knowledge_base.py` ✅ Active
In-memory knowledge base with **keyword search**. Contains sample support
articles that the agent searches to find relevant context before responding.

Key functions:
- `search_kb(query, top_k=3)` — searches articles by keyword overlap, returns top matches
- Articles cover: password resets, billing, API issues, data export, team management

**Production upgrade**: Replace keyword search with vector similarity search
using the `kb_embeddings` table and pgvector.

### `customer_service.py` 🔶 Mock
Returns mock customer profiles (name, plan, ticket history) for demo purposes.
In production: would query the `customers` table or an external CRM.

### `external_apis.py` 🔶 Mock
Simulated third-party API integrations:
- `check_order_status()` — mock order tracking (like calling Shopify/Amazon)
- `create_refund_request()` — mock payment refund (like calling Stripe)
- `reset_customer_password()` — mock auth service (like calling Auth0)
- `create_bug_report()` — mock issue tracker (like calling JIRA)

These demonstrate the **integration pattern** — how the agent would call
external services with proper error handling and audit-friendly return values.

### `notifications.py` 🔶 Mock
Simulated notification channels:
- `notify_slack()` — mock Slack webhook
- `send_email_notification()` — mock email (SendGrid/SES)

## Why Mock Tools?

Mock tools show the **correct architecture** without requiring API keys:
1. Input validation
2. Structured logging
3. Audit-friendly return values
4. Error handling patterns

The agent's graph nodes can call these tools, and the audit trail records
every tool invocation. Replacing mocks with real APIs requires changing
only the tool implementation, not the graph or routes.

## How to Explain This

> "Tools extend the agent's capabilities beyond text generation. The knowledge
> base tool provides context for response generation. Mock external integrations
> demonstrate how the agent would connect to real services like Stripe or JIRA.
> Each tool follows a consistent pattern: validate input, log the action,
> return structured data. The mock approach lets me demonstrate the full
> architecture without requiring paid API accounts."
