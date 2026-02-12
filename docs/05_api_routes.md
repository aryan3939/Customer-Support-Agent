# Phase 3: API Routes

## Why This Phase?

Phase 2 built the AI agent brain. But that brain is trapped inside Python
functions — no external client can USE it. This phase adds the **HTTP interface**:

- **Web frontend** sends a POST → ticket gets processed → gets AI response back
- **Mobile app** hits the same API → same result
- **Postman** for testing → instant playground

---

## Endpoints

| Method | Endpoint | What It Does |
|--------|----------|-------------|
| `POST` | `/api/v1/tickets` | Create ticket → AI processes → returns response |
| `GET` | `/api/v1/tickets` | List tickets with filters & pagination |
| `GET` | `/api/v1/tickets/{id}` | Get ticket details + messages + audit trail |
| `POST` | `/api/v1/tickets/{id}/messages` | Add follow-up message (AI auto-replies) |
| `PATCH` | `/api/v1/tickets/{id}/status` | Update ticket status |
| `GET` | `/api/v1/tickets/{id}/actions` | View AI agent audit trail |

---

## Files Created

```
src/api/
├── __init__.py
├── schemas/
│   ├── __init__.py
│   └── ticket.py          ← Request/response Pydantic models
└── routes/
    └── tickets.py         ← 6 REST endpoints
```

---

## How It All Connects

```
Client (Browser/Postman)
    │
    ▼  POST /api/v1/tickets  {"subject": "...", "message": "..."}
┌───────────────────────────────────────────────────────┐
│  FastAPI                                               │
│  ├─ Pydantic validates the request (schemas/ticket.py) │
│  ├─ Route handler creates ticket (routes/tickets.py)   │
│  │   └─ Calls process_ticket() (agents/graph.py)       │
│  │       └─ classify → search_kb → resolve → validate  │
│  └─ Returns JSON response                              │
└───────────────────────────────────────────────────────┘
    │
    ▼  Response: {"id": "...", "initial_response": "Here's how to...", "priority": "high"}
```

---

## Request/Response Examples

### Create a Ticket

```bash
curl -X POST http://localhost:8000/api/v1/tickets \
  -H "Content-Type: application/json" \
  -d '{
    "customer_email": "user@example.com",
    "subject": "Cannot reset my password",
    "message": "I have tried 3 times but no email arrives. Checked spam too.",
    "channel": "web"
  }'
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "open",
  "priority": "high",
  "category": "account",
  "sentiment": "negative",
  "assigned_to": {"id": "ai-agent-001", "name": "Support AI", "is_ai": true},
  "initial_response": "I understand you're having trouble with password reset emails...",
  "escalated": false,
  "created_at": "2025-02-10T00:30:00Z"
}
```

### List Tickets

```bash
# All tickets
curl http://localhost:8000/api/v1/tickets

# Filtered
curl "http://localhost:8000/api/v1/tickets?status=open&priority=high&limit=10"
```

### Get Ticket Details

```bash
curl http://localhost:8000/api/v1/tickets/550e8400-e29b-41d4-a716-446655440000
```

Returns full ticket with message thread and AI action audit trail.

### Add Follow-Up Message

```bash
curl -X POST http://localhost:8000/api/v1/tickets/550e8400/messages \
  -H "Content-Type: application/json" \
  -d '{"content": "I still have not received the email"}'
```

The AI automatically processes the follow-up and adds its response.

---

## Key Concepts

### Pydantic Schemas (`schemas/ticket.py`)

Schemas define the SHAPE of data. FastAPI uses them for:
- **Validation**: `customer_email` must be a valid email, `subject` min 5 chars
- **Documentation**: Swagger UI generated automatically at `/docs`
- **Serialization**: Python objects → JSON responses

### In-Memory Storage (Phase 3)

Currently, tickets are stored in a Python dict:
```python
_tickets_store: dict[str, dict] = {}
```

This means data disappears on server restart. Phase 4 will persist to Supabase.
For development and testing, in-memory is perfect.

### Swagger UI

Once the server is running, visit:
- **`http://localhost:8000/docs`** — Interactive API playground
- **`http://localhost:8000/redoc`** — Clean API documentation

You can test ALL endpoints directly from the browser!

---

## How to Test

```bash
# 1. Start the server
cd "d:\OneDrive - iitr.ac.in\Projects\Customer Support Agent"
.venv\Scripts\activate
uvicorn src.main:app --reload

# 2. Open Swagger UI
# Go to http://localhost:8000/docs in your browser

# 3. Try "POST /api/v1/tickets" → click "Try it out"
# Enter a ticket and see the AI response!
```

---

## What's Next?

- **Phase 4**: Persist tickets to Supabase database
- **Phase 5**: WebSocket for real-time updates
- **Phase 6**: Frontend UI
