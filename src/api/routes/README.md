# `src/api/routes/` — Route Handlers

Each file defines a group of related API endpoints. Routes are registered
with FastAPI's `APIRouter` and mounted on the main app in `main.py`.

## Files

### `tickets.py` — Customer Ticket Endpoints (20KB, largest file)

The main ticket CRUD + AI processing endpoints. Only shows tickets
belonging to the authenticated user (filtered by email from JWT).

| Endpoint | Method | What It Does |
|----------|--------|-------------|
| `/api/v1/tickets` | `POST` | **Creates a ticket** → runs the entire LangGraph AI pipeline → returns classification + AI response + audit trail |
| `/api/v1/tickets` | `GET` | Lists the user's tickets with filters (`status`, `priority`, `limit`, `offset`) |
| `/api/v1/tickets/{id}` | `GET` | Gets full ticket detail — all messages, all AI actions |
| `/api/v1/tickets/{id}/messages` | `POST` | Sends a follow-up message — if `sender_type == "customer"`, the AI auto-replies using full conversation context |
| `/api/v1/tickets/{id}/status` | `PATCH` | Updates ticket status (`new`, `open`, `resolved`, `closed`, `escalated`) |
| `/api/v1/tickets/{id}/resolve` | `PATCH` | Resolves a ticket — sets `resolved_at`, `resolved_by`, logs action |
| `/api/v1/tickets/{id}/actions` | `GET` | Returns the AI's audit trail — every decision it made with reasoning |

**Important constant:** `AI_AGENT_UUID` — a hardcoded UUID for the AI agent record in the `agents` table. Used when logging `agent_actions`.

---

### `admin.py` — Admin Panel Endpoints (15KB)

Admin-only endpoints that require `role == "admin"` in the JWT.
Provides full conversation management across all customers.

| Endpoint | Method | What It Does |
|----------|--------|-------------|
| `/api/v1/admin/conversations` | `GET` | Lists ALL tickets with advanced filters (status, priority, category, email, date range, resolved_by, sort) |
| `/api/v1/admin/conversations/{id}` | `GET` | Full conversation detail for any ticket |
| `/api/v1/admin/conversations/{id}/reply` | `POST` | Sends a message as a human agent (sets `sender_type = "human_agent"`) |
| `/api/v1/admin/conversations/{id}/resolve` | `PATCH` | Resolves any conversation as admin |

**Authorization:** Every admin route checks `current_user.role == "admin"` and returns 403 Forbidden otherwise.

---

### `analytics.py` — Dashboard Metrics (1.2KB)

Single endpoint that returns aggregated statistics.

| Endpoint | Method | What It Does |
|----------|--------|-------------|
| `/api/v1/analytics/dashboard` | `GET` | Returns ticket counts by status, priority, category + average resolution time |

---

### `webhooks.py` — External Integrations (1.8KB)

Stub endpoints for receiving events from external services (email providers, Slack, etc.). Currently a placeholder for future integrations.

---

### `__init__.py` — Package Init

Makes the `routes` folder importable.
