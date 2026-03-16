# 05 — API Routes & Pydantic Schemas

How the REST API is built — endpoints, validation, dependency injection,
and request/response schemas.

---

## 5.1 FastAPI Route Architecture

### How Routes Work

```python
# Every route function follows this pattern:
@router.post("/tickets", response_model=TicketDetailResponse)
async def create_ticket(
    request: CreateTicketRequest,                                # ← Pydantic validates body
    current_user: CurrentUser = Depends(get_current_user),       # ← JWT verified
    db: AsyncSession = Depends(get_db_session),                  # ← DB connection from pool
):
    # By the time this runs, authentication and validation are DONE
    # The function just focuses on business logic
```

**Key concept:** FastAPI's `Depends()` system injects objects automatically:
- `get_current_user` — reads JWT from `Authorization` header, verifies it, returns user
- `get_db_session` — grabs a connection from the pool, auto-commits/rollbacks

---

## 5.2 Ticket Endpoints (`api/routes/tickets.py`)

### POST `/api/v1/tickets` — Create Ticket

The most complex endpoint. Here's what happens:

```
1. Request validated    (Pydantic: email, subject 5-200 chars, message 10+ chars)
2. JWT verified         (get_current_user: extracts email and role)
3. Customer found/created (get_or_create_customer: ensure DB record exists)
4. Ticket saved         (INSERT into tickets table with status "new")
5. Initial message saved (INSERT into messages with sender_type "customer")
6. AI agent processes   (LangGraph: classify → search → respond → validate)
7. AI response saved    (INSERT into messages with sender_type "ai_agent")
8. Classification saved (UPDATE ticket with intent, priority, sentiment, category)
9. Audit trail saved    (INSERT into agent_actions for each AI step)
10. Full ticket returned (ticket + messages + actions as JSON)
```

**Request body:**
```json
{
    "customer_email": "user@example.com",
    "subject": "Cannot reset my password",
    "message": "I tried clicking forgot password 3 times but no reset email arrives.",
    "channel": "web"
}
```

**Response:** Full ticket with messages, classification, and audit trail.

---

### POST `/api/v1/tickets/{id}/messages` — Send Follow-Up

When a customer sends a follow-up message:

```
1. Message saved to database
2. ALL previous messages loaded (conversation context)
3. AI agent processes the new message WITH full conversation history
4. AI response saved as new message
5. Updated ticket returned
```

**Key detail:** The conversation history is passed to the LLM so it understands the full context. The AI doesn't just answer the latest message in isolation.

---

### GET `/api/v1/tickets` — List Tickets

Returns the user's tickets with optional filters:
- `status` — filter by status (open, resolved, etc.)
- `priority` — filter by priority (low, medium, high, urgent)
- `limit` / `offset` — pagination

**Security:** Only shows tickets where `customer_email` matches the JWT email. Customers can never see other customers' tickets.

---

### PATCH `/api/v1/tickets/{id}/resolve` — Resolve Ticket

Sets:
- `status = "resolved"`
- `resolved_at = datetime.now()`
- `resolved_by = "customer"` or `"admin"` (from request body)
- Adds a resolution message to the conversation

---

### GET `/api/v1/tickets/{id}/actions` — View Audit Trail

Returns every AI decision as a list:
```json
[
    {
        "action_type": "classify_ticket",
        "action_data": {"intent": "password_reset", "priority": "high"},
        "reasoning": {"thought": "Customer mentions password reset multiple times..."},
        "outcome": "success"
    },
    {
        "action_type": "search_kb",
        "action_data": {"query": "password reset", "results_count": 3},
        "outcome": "success"
    },
    ...
]
```

---

## 5.3 Admin Endpoints (`api/routes/admin.py`)

Require `role == "admin"` in the JWT (enforced by `require_admin` dependency).

### GET `/api/v1/admin/conversations` — List All Conversations

Admin version of ticket listing — sees ALL tickets across all customers.

**Advanced filters:**
- `status`, `priority`, `category` — standard filters
- `email` — search by customer email
- `date_from` / `date_to` — date range
- `resolved_by` — filter by who resolved (ai_agent, admin, customer)
- `sort` — sort by date, priority, or status

### POST `/api/v1/admin/conversations/{id}/reply` — Reply as Agent

Sends a message with `sender_type = "human_agent"`. No AI auto-reply is triggered.

### PATCH `/api/v1/admin/conversations/{id}/resolve` — Admin Resolve

Resolves any ticket with `resolved_by = "admin"`.

---

## 5.4 Analytics Endpoint (`api/routes/analytics.py`)

### GET `/api/v1/analytics/dashboard`

Returns aggregated metrics:
```json
{
    "total_tickets": 150,
    "by_status": {"resolved": 120, "open": 20, "escalated": 10},
    "by_priority": {"low": 50, "medium": 60, "high": 30, "urgent": 10},
    "by_category": {"account": 40, "billing": 35, "technical": 45, "general": 30},
    "avg_resolution_time_minutes": 12.5
}
```

---

## 5.5 Pydantic Schemas (`api/schemas/`)

### Request Models (Validation)

```python
class CreateTicketRequest(BaseModel):
    customer_email: EmailStr                    # Must be valid email
    subject: str = Field(min_length=5, max_length=200)  # 5-200 chars
    message: str = Field(min_length=10)         # At least 10 chars
    channel: str = "web"                        # Default: web
```

If any validation fails, FastAPI returns a **422 Unprocessable Entity** with details:
```json
{
    "detail": [
        {
            "loc": ["body", "subject"],
            "msg": "String should have at least 5 characters",
            "type": "string_too_short"
        }
    ]
}
```

### Response Models (Serialization)

```python
class TicketResponse(BaseModel):
    id: str
    subject: str
    status: str
    priority: str
    category: str | None
    sentiment: str | None
    created_at: datetime
    resolved_at: datetime | None

class TicketDetailResponse(TicketResponse):
    messages: list[MessageResponse]      # All conversation messages
    actions: list[AgentActionResponse]   # AI audit trail
    customer_email: str
```

---

## 5.6 Authentication (`api/deps/auth.py`)

### JWT Verification Flow

```
Frontend includes:  Authorization: Bearer eyJhbGci...
                        ↓
get_current_user() called by FastAPI Depends()
                        ↓
Strip "Bearer " prefix → extract raw JWT
                        ↓
Fetch public key from Supabase JWKS endpoint
    https://<project>.supabase.co/auth/v1/.well-known/jwks.json
                        ↓
Verify JWT signature (ES256/EdDSA/HS256), check expiration
                        ↓
Extract: user_id (sub), email, role (from user_metadata)
                        ↓
Return CurrentUser(id=..., email=..., role=...)
```

### Why JWKS Instead of a Shared Secret?

Supabase migrated from HS256 (symmetric shared secret) to ES256 (asymmetric ECC).
With JWKS:
- Supabase signs JWTs with a **private key** (only Supabase has it)
- We verify JWTs with the **public key** (fetched from JWKS endpoint)
- No shared secret needed — more secure, rotatable
