# `src/db/repositories/` — Repository Pattern (CRUD Operations)

Repositories are functions that encapsulate all database queries.
They are the **only place** where SQL operations happen — routes and
services call these functions instead of writing queries directly.

## Why the Repository Pattern?

```python
# ❌ BAD — SQL scattered in route handlers
@router.post("/tickets")
async def create_ticket(db: AsyncSession):
    customer = await db.execute(
        select(Customer).where(Customer.email == email)
    )
    # ... lots of SQL mixed with business logic

# ✅ GOOD — Repository abstracts the SQL away
@router.post("/tickets")
async def create_ticket(db: AsyncSession):
    customer = await get_or_create_customer(db, email)
    # Clean, readable, testable
```

**Benefits:**
- Routes stay clean — just business logic, no SQL
- SQL is centralized — change a query in one place, all callers benefit
- Testable — mock the repository in unit tests
- Reusable — the same query function used across routes, services, admin

## Files

### `ticket_repo.py` — Ticket CRUD (6.8KB)

All ticket-related database operations:

| Function | What It Does |
|----------|-------------|
| `create_ticket(db, customer_id, subject, channel, ...)` | INSERTs a new ticket with status `"new"` and default priority |
| `get_ticket_by_id(db, ticket_id)` | SELECTs a single ticket with all relationships eagerly loaded (messages, actions, customer, agent) |
| `get_tickets_by_customer(db, customer_email, status, priority, limit, offset)` | SELECTs tickets with optional filters, pagination, and eager loading — used for the ticket list |
| `add_message(db, ticket_id, content, sender_type, metadata)` | INSERTs a new message into the ticket thread |
| `update_ticket_status(db, ticket_id, status)` | UPDATEs the ticket's status field |
| `add_agent_action(db, ticket_id, agent_id, action_type, data, reasoning, outcome)` | INSERTs an audit trail entry — records every AI decision |
| `get_all_tickets(db, filters...)` | Admin query — SELECTs all tickets across all customers with advanced filtering (status, priority, category, date range, email search, sort) |

**Eager loading:** All queries use `selectinload()` or `joinedload()` to fetch related
data (messages, actions, customer) in the same query. Without this, accessing
`ticket.messages` would trigger a lazy load — a separate SQL query per relationship,
causing N+1 query problems.

```python
# Example: eager loading prevents N+1 queries
stmt = (
    select(Ticket)
    .options(
        selectinload(Ticket.messages),       # Load messages in same query
        selectinload(Ticket.agent_actions),  # Load actions in same query
        joinedload(Ticket.customer),         # Load customer via JOIN
    )
    .where(Ticket.id == ticket_id)
)
```

---

### `customer_repo.py` — Customer CRUD (1.5KB)

| Function | What It Does |
|----------|-------------|
| `get_or_create_customer(db, email, name)` | Finds a customer by email, or creates a new one if they don't exist. Used every time a ticket is created — ensures we have a customer record before creating the ticket. |

---

### `__init__.py` — Package Init

Makes the folder importable.
