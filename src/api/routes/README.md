# `routes/` — API Endpoint Handlers

Each file defines a **FastAPI APIRouter** with endpoints for one resource.
Routes are the "glue" between HTTP requests and backend logic.

## Files

### `tickets.py` — Ticket Management (6 endpoints)
The main API — handles the full ticket lifecycle:

| Method | Path | What It Does |
|--------|------|-------------|
| `POST` | `/api/v1/tickets` | Create a ticket → run AI agent → persist to Supabase |
| `GET` | `/api/v1/tickets` | List tickets with filters (status, priority, category, email) + pagination |
| `GET` | `/api/v1/tickets/{id}` | Get ticket details with messages + AI actions |
| `POST` | `/api/v1/tickets/{id}/messages` | Send a follow-up message → AI re-processes automatically |
| `PATCH` | `/api/v1/tickets/{id}/status` | Update ticket status (open, resolved, closed) |
| `GET` | `/api/v1/tickets/{id}/actions` | Get the AI audit trail (every action the agent took) |

**Key pattern**: Every endpoint receives `db: AsyncSession = Depends(get_db_session)`,
which injects a database session that auto-commits on success or rolls back on error.

### `analytics.py` — Dashboard Metrics (1 endpoint)
| Method | Path | What It Does |
|--------|------|-------------|
| `GET` | `/api/v1/analytics/dashboard` | Aggregate metrics: total/open/resolved/escalated counts, resolution rate, breakdowns |

Queries all tickets from Supabase and passes them to `compute_dashboard_metrics()`.

### `webhooks.py` — External Integrations (1 endpoint)
| Method | Path | What It Does |
|--------|------|-------------|
| `POST` | `/api/v1/webhooks/email` | Receive incoming emails (from SendGrid/SES) → auto-create tickets |

Maps email fields (`from`, `subject`, `body`) to a `CreateTicketRequest` and
reuses the `create_ticket()` function.

## How to Explain This

> "Routes follow the **thin controller** pattern — they handle HTTP concerns
> (parsing requests, returning responses, error codes) but delegate all logic
> to the agent graph and repository layer. This means the same ticket creation
> logic works whether triggered by the frontend, a webhook, or a CLI script."
