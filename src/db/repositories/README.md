# `repositories/` — Database Query Functions

Repositories encapsulate all **SQL queries** behind clean Python functions.
This is the **Repository Pattern** — routes and services never interact
with the database directly.

## Why Repositories?

```
❌ Bad: SQL in routes
    @router.get("/tickets")
    async def list_tickets(db):
        result = await db.execute(select(Ticket).where(Ticket.status == "open"))
        ...

✅ Good: Repository layer
    @router.get("/tickets")
    async def list_tickets(db):
        tickets, total = await repo.list_tickets(db, status="open")
        ...
```

Benefits:
- **Testable** — mock the repo function, not the DB
- **Reusable** — same query used by routes, services, scripts
- **Swappable** — change from PostgreSQL to DynamoDB by rewriting only this layer

## Files

### `ticket_repo.py`
Full CRUD for tickets and related entities:

| Function | What It Does |
|----------|-------------|
| `get_or_create_ai_agent(db)` | Creates/returns the system AI agent row (idempotent) |
| `create_ticket(db, customer_id, subject, ...)` | Inserts a new ticket |
| `get_ticket_by_id(db, ticket_id)` | Fetches one ticket with customer eagerly loaded |
| `list_tickets(db, status?, priority?, ...)` | Paginated list with filters, returns `(tickets, count)` |
| `update_ticket_status(db, ticket_id, status)` | Updates status (sets `resolved_at` for resolved/closed) |
| `add_message(db, ticket_id, sender_type, content)` | Adds a message to the conversation thread |
| `add_agent_action(db, ticket_id, action_type, ...)` | Records an AI action in the audit trail |
| `get_actions_for_ticket(db, ticket_id)` | Gets all actions for a ticket, ordered by time |
| `get_messages_for_ticket(db, ticket_id)` | Gets all messages for a ticket, ordered by time |

### `customer_repo.py`
Customer management:

| Function | What It Does |
|----------|-------------|
| `get_or_create_customer(db, email, name)` | Finds customer by email or creates new (returns `(customer, created)`) |
| `get_customer_by_email(db, email)` | Looks up customer by email |
| `get_customer_by_id(db, id)` | Looks up customer by UUID |

## How to Explain This

> "Repositories isolate database queries behind a clean interface. Every query
> is a documented function with typed parameters. This makes queries reusable
> (the same `list_tickets` works for API routes, analytics, and tests),
> testable (mock the function, not the database), and maintainable (all queries
> for one entity live in one file)."
