# `schemas/` — Pydantic Request/Response Models

This folder defines the **data contracts** between the frontend and backend.
Every request body and response body is validated by a Pydantic model.

## Why Pydantic?

1. **Automatic validation** — Invalid data is rejected with clear error messages before reaching any logic
2. **Type safety** — Python type hints enforced at runtime
3. **Auto-generated docs** — FastAPI uses these models to build the `/docs` Swagger page
4. **Serialization** — Handles `datetime`, `UUID`, and other complex types automatically

## Files

### `ticket.py`
All ticket-related schemas:

| Schema | Used For |
|--------|---------|
| `CreateTicketRequest` | `POST /tickets` request body (email, subject, message, channel) |
| `CreateTicketResponse` | Response after creating a ticket (id, status, AI response, classification) |
| `TicketResponse` | Single ticket summary (used in lists and updates) |
| `TicketDetailResponse` | Full ticket with messages + actions (used in detail view) |
| `TicketListResponse` | Paginated list wrapper (tickets array + total/limit/offset) |
| `AddMessageRequest` | `POST /tickets/{id}/messages` request body (content, sender_type) |
| `UpdateTicketStatusRequest` | `PATCH /tickets/{id}/status` request body (new status) |
| `MessageResponse` | Individual message in a conversation thread |
| `ActionResponse` | Individual AI action in the audit trail |
| `AgentInfo` | Agent details embedded in responses (id, name, is_ai) |

### `responses.py`
Generic response wrappers:
- `SuccessResponse` — `{ "status": "ok", "data": ... }`
- `ErrorResponse` — `{ "status": "error", "message": "...", "code": 400 }`

## How to Explain This

> "Pydantic schemas serve as the **API contract** — they validate every request,
> ensure consistent response shapes, and automatically generate API documentation.
> The frontend TypeScript types in `api.ts` mirror these schemas exactly, so
> type safety extends from Python to TypeScript."
