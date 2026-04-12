# `src/api/schemas/` — Request/Response Models (Pydantic)

Pydantic models that define the **exact shape** of every HTTP request body
and every HTTP response. They serve three critical purposes:

1. **Validation** — FastAPI uses them to validate incoming requests automatically. Invalid data gets a clear 422 error before your route code even runs.
2. **Serialization** — Convert SQLAlchemy ORM objects into clean JSON responses (no database internals leak out).
3. **Documentation** — FastAPI generates interactive Swagger UI docs from these models automatically.

## How It Works

```python
# In a route handler:
@router.post("/tickets", response_model=TicketDetailResponse)
async def create_ticket(request: CreateTicketRequest):
    # 'request' is ALREADY validated — Pydantic checked all fields
    # The return value is AUTOMATICALLY serialized via TicketDetailResponse
```

## Files

### `ticket.py` — Ticket Request/Response Models (6KB)

The main schemas for ticket operations:

| Model | Type | Purpose |
|-------|------|---------|
| `CreateTicketRequest` | Request | Validates ticket creation — `customer_email` (must be valid email), `subject` (5-200 chars), `message` (10+ chars), `channel` |
| `SendMessageRequest` | Request | Validates follow-up messages — `content` (required), `sender_type` (customer/human_agent/ai_agent) |
| `UpdateStatusRequest` | Request | Validates status changes — `status` must be one of the allowed values |
| `ResolveTicketRequest` | Request | Validates resolution — `resolved_by` (customer/admin/ai_agent) |
| `TicketResponse` | Response | Summary view — id, subject, status, priority, dates (used in list views) |
| `TicketDetailResponse` | Response | Full view — includes all messages and AI actions (used for ticket detail) |
| `MessageResponse` | Response | Single message — id, sender_type, content, timestamp |
| `AgentActionResponse` | Response | Single AI action — action_type, data, reasoning, outcome |

**Key pattern:** Request models are strict (validate everything), response models are permissive (accept whatever the DB returns).

---

### `responses.py` — Standard Response Wrappers (1KB)

Generic response wrappers used across endpoints:

| Model | Purpose |
|-------|---------|
| `SuccessResponse` | `{ "message": "Operation successful" }` — for simple confirmations |
| `ErrorResponse` | `{ "detail": "Error message" }` — for error responses |
| `PaginatedResponse` | `{ "items": [...], "total": 42, "limit": 20, "offset": 0 }` |

---

### `__init__.py` — Package Init

Exports all schema models for clean importing:
```python
from src.api.schemas import CreateTicketRequest, TicketDetailResponse
```
