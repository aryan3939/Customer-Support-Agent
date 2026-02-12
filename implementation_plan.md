# Autonomous Customer Support Agent - Implementation Plan

A production-ready AI-powered customer support system that autonomously handles tickets, escalates issues intelligently, and integrates with external tools while maintaining a complete audit trail.

---

## Project Overview

### Problem Statement
Traditional customer support systems require significant human intervention for routine queries, leading to:
- High operational costs
- Inconsistent response quality
- Slow response times
- Poor scalability during peak loads

### Solution
An autonomous agent system that:
- Handles routine queries end-to-end without human intervention
- Intelligently escalates complex/sensitive issues to human agents
- Learns from historical data to improve responses
- Maintains complete transparency through audit trails

---

## Tech Stack

### Core Technologies

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| **Agent Framework** | LangGraph | 0.2.x | State machine orchestration, agent workflows |
| **LLM Integration** | LangChain | 0.3.x | Tool calling, prompt management, memory |
| **LLM Provider** | Groq / Google Gemini / Ollama | Free tier | Primary reasoning engine |
| **API Framework** | FastAPI | 0.115.x | REST API, WebSocket support |
| **Database** | PostgreSQL | 16.x | Primary data store |
| **Vector Store** | pgvector | 0.7.x | Embedding storage for RAG |
| **Embeddings** | HuggingFace / Ollama | Free | Text embeddings for RAG |
| **Task Queue** | Celery + Redis | 5.4.x | Async task processing |
| **Caching** | Redis | 7.x | Session caching, rate limiting |

### Supporting Libraries

| Library | Purpose |
|----------|---------|
| `pydantic` | Data validation, settings management |
| `sqlalchemy` | ORM, database migrations |
| `alembic` | Database schema versioning |
| `httpx` | Async HTTP client for integrations |
| `tenacity` | Retry logic for external APIs |
| `structlog` | Structured logging |
| `prometheus-client` | Metrics and monitoring |

---

## System Architecture

### High-Level Architecture

```mermaid
graph TB
    subgraph "Client Layer"
        WEB[Web Dashboard]
        API_CLIENT[API Clients]
        WEBHOOK[Webhook Sources]
    end

    subgraph "API Layer"
        FASTAPI[FastAPI Server]
        WS[WebSocket Handler]
        AUTH[Auth Middleware]
    end

    subgraph "Agent Layer"
        LANGGRAPH[LangGraph Orchestrator]
        CLASSIFIER[Ticket Classifier]
        RESOLVER[Auto-Resolver Agent]
        ESCALATOR[Escalation Agent]
        TOOLS[Tool Executor]
    end

    subgraph "Integration Layer"
        KB[Knowledge Base RAG]
        CRM[CRM Connector]
        EMAIL[Email Service]
        SLACK[Slack Notifier]
    end

    subgraph "Data Layer"
        PG[(PostgreSQL)]
        PGVECTOR[(pgvector)]
        REDIS[(Redis)]
    end

    WEB --> FASTAPI
    API_CLIENT --> FASTAPI
    WEBHOOK --> FASTAPI
    
    FASTAPI --> AUTH
    AUTH --> LANGGRAPH
    FASTAPI --> WS
    
    LANGGRAPH --> CLASSIFIER
    LANGGRAPH --> RESOLVER
    LANGGRAPH --> ESCALATOR
    LANGGRAPH --> TOOLS
    
    TOOLS --> KB
    TOOLS --> CRM
    TOOLS --> EMAIL
    TOOLS --> SLACK
    
    KB --> PGVECTOR
    LANGGRAPH --> PG
    LANGGRAPH --> REDIS
```

### Component Responsibilities

| Component | Responsibility |
|-----------|----------------|
| **FastAPI Server** | HTTP/WebSocket endpoints, request validation, response formatting |
| **LangGraph Orchestrator** | Workflow execution, state transitions, agent coordination |
| **Ticket Classifier** | Intent detection, priority assignment, category tagging |
| **Auto-Resolver Agent** | Handle resolvable queries using KB and tools |
| **Escalation Agent** | Determine escalation criteria, route to appropriate human |
| **Tool Executor** | Execute external integrations safely with retry logic |

---

## Database Schema

### Entity Relationship Diagram

```mermaid
erDiagram
    CUSTOMERS ||--o{ TICKETS : creates
    TICKETS ||--o{ MESSAGES : contains
    TICKETS ||--o{ AGENT_ACTIONS : has
    TICKETS }o--|| AGENTS : assigned_to
    AGENTS ||--o{ AGENT_ACTIONS : performs
    TICKETS ||--o{ TICKET_TAGS : has
    TAGS ||--o{ TICKET_TAGS : applied_to
    KNOWLEDGE_ARTICLES ||--o{ KB_EMBEDDINGS : has

    CUSTOMERS {
        uuid id PK
        string email
        string name
        jsonb metadata
        timestamp created_at
    }

    TICKETS {
        uuid id PK
        uuid customer_id FK
        uuid assigned_agent_id FK
        string status
        string priority
        string category
        string subject
        text summary
        jsonb ai_context
        timestamp created_at
        timestamp updated_at
        timestamp resolved_at
    }

    MESSAGES {
        uuid id PK
        uuid ticket_id FK
        string sender_type
        text content
        jsonb metadata
        timestamp created_at
    }

    AGENTS {
        uuid id PK
        string name
        string email
        string role
        jsonb skills
        boolean is_ai
        boolean is_active
    }

    AGENT_ACTIONS {
        uuid id PK
        uuid ticket_id FK
        uuid agent_id FK
        string action_type
        jsonb action_data
        jsonb reasoning
        string outcome
        timestamp created_at
    }

    TAGS {
        uuid id PK
        string name
        string category
    }

    TICKET_TAGS {
        uuid ticket_id FK
        uuid tag_id FK
    }

    KNOWLEDGE_ARTICLES {
        uuid id PK
        string title
        text content
        string category
        jsonb metadata
        timestamp updated_at
    }

    KB_EMBEDDINGS {
        uuid id PK
        uuid article_id FK
        text chunk_text
        vector embedding
        int chunk_index
    }
```

### Key Tables Detail

#### `tickets` Table
```sql
CREATE TABLE tickets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES customers(id),
    assigned_agent_id UUID REFERENCES agents(id),
    status VARCHAR(50) NOT NULL DEFAULT 'new',
    priority VARCHAR(20) NOT NULL DEFAULT 'medium',
    category VARCHAR(100),
    subject VARCHAR(500) NOT NULL,
    summary TEXT,
    ai_context JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    
    CONSTRAINT valid_status CHECK (status IN ('new', 'open', 'pending_customer', 'pending_agent', 'escalated', 'resolved', 'closed')),
    CONSTRAINT valid_priority CHECK (priority IN ('low', 'medium', 'high', 'urgent'))
);

CREATE INDEX idx_tickets_status ON tickets(status);
CREATE INDEX idx_tickets_customer ON tickets(customer_id);
CREATE INDEX idx_tickets_created ON tickets(created_at DESC);
```

#### `agent_actions` Table (Audit Trail)
```sql
CREATE TABLE agent_actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_id UUID NOT NULL REFERENCES tickets(id),
    agent_id UUID NOT NULL REFERENCES agents(id),
    action_type VARCHAR(100) NOT NULL,
    action_data JSONB NOT NULL DEFAULT '{}',
    reasoning JSONB,  -- LLM's chain-of-thought for transparency
    outcome VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_actions_ticket ON agent_actions(ticket_id);
CREATE INDEX idx_actions_type ON agent_actions(action_type);
```

---

## API Design

### Endpoints Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/tickets` | Create new support ticket |
| `GET` | `/api/v1/tickets` | List tickets with filters |
| `GET` | `/api/v1/tickets/{id}` | Get ticket details |
| `POST` | `/api/v1/tickets/{id}/messages` | Add message to ticket |
| `POST` | `/api/v1/tickets/{id}/escalate` | Manual escalation |
| `PATCH` | `/api/v1/tickets/{id}/status` | Update ticket status |
| `GET` | `/api/v1/tickets/{id}/actions` | Get audit trail |
| `WS` | `/api/v1/tickets/{id}/stream` | Real-time updates |
| `POST` | `/api/v1/webhooks/email` | Email intake webhook |
| `GET` | `/api/v1/analytics/dashboard` | Support metrics |

### Request/Response Examples

#### Create Ticket
```http
POST /api/v1/tickets
Content-Type: application/json

{
  "customer_email": "user@example.com",
  "subject": "Cannot reset my password",
  "message": "I've tried resetting my password 3 times but never receive the email.",
  "channel": "web",
  "metadata": {
    "browser": "Chrome 120",
    "page_url": "/account/settings"
  }
}
```

#### Response
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "open",
  "priority": "medium",
  "category": "account_access",
  "assigned_to": {
    "id": "ai-agent-001",
    "name": "Support AI",
    "is_ai": true
  },
  "initial_response": "I understand you're having trouble with password reset emails. Let me check your account status and email delivery logs...",
  "created_at": "2025-02-09T10:30:00Z"
}
```

---

## LangGraph Workflow Design

### State Schema

```python
from typing import TypedDict, Literal, Optional, List
from langgraph.graph import StateGraph

class TicketState(TypedDict):
    # Core ticket info
    ticket_id: str
    customer_id: str
    subject: str
    messages: List[dict]
    
    # Classification
    intent: Optional[str]
    category: Optional[str]
    priority: Literal["low", "medium", "high", "urgent"]
    sentiment: Literal["positive", "neutral", "negative", "angry"]
    
    # Processing state
    current_node: str
    attempts: int
    needs_human: bool
    escalation_reason: Optional[str]
    
    # Context
    kb_results: List[dict]
    customer_history: dict
    tool_results: List[dict]
    
    # Response
    draft_response: Optional[str]
    final_response: Optional[str]
    actions_taken: List[dict]
```

### Workflow Graph

```mermaid
graph TD
    START((Start)) --> CLASSIFY[Classify Ticket]
    
    CLASSIFY --> PRIORITY{Priority Check}
    PRIORITY -->|Urgent + Angry| ESCALATE[Escalate to Human]
    PRIORITY -->|Normal| ENRICH[Enrich Context]
    
    ENRICH --> KB_SEARCH[Search Knowledge Base]
    KB_SEARCH --> HISTORY[Fetch Customer History]
    HISTORY --> ANALYZE[Analyze & Plan]
    
    ANALYZE --> DECISION{Can Resolve?}
    DECISION -->|Yes| RESOLVE[Generate Resolution]
    DECISION -->|No| ESCALATE
    DECISION -->|Need Tool| USE_TOOL[Execute Tool]
    
    USE_TOOL --> TOOL_RESULT{Tool Success?}
    TOOL_RESULT -->|Yes| ANALYZE
    TOOL_RESULT -->|Failed 3x| ESCALATE
    
    RESOLVE --> VALIDATE[Validate Response]
    VALIDATE --> VALID{Response OK?}
    VALID -->|Yes| RESPOND[Send Response]
    VALID -->|No| ANALYZE
    
    RESPOND --> FOLLOWUP{Needs Follow-up?}
    FOLLOWUP -->|Yes| SCHEDULE[Schedule Follow-up]
    FOLLOWUP -->|No| COMPLETE[Mark Resolved]
    
    SCHEDULE --> COMPLETE
    ESCALATE --> NOTIFY[Notify Human Agent]
    NOTIFY --> HANDOFF[Prepare Handoff Summary]
    HANDOFF --> END((End))
    COMPLETE --> END
```

### Node Implementations

```python
# Key node implementations

def classify_ticket(state: TicketState) -> TicketState:
    """Classify intent, category, priority, and sentiment."""
    prompt = f"""Analyze this support ticket:
    Subject: {state['subject']}
    Message: {state['messages'][-1]['content']}
    
    Return JSON with:
    - intent: (password_reset|billing_inquiry|bug_report|feature_request|general_question|complaint|other)
    - category: (account|billing|technical|product|shipping|other)
    - priority: (low|medium|high|urgent)
    - sentiment: (positive|neutral|negative|angry)
    """
    # LLM call with structured output
    result = llm.invoke(prompt, response_format=ClassificationSchema)
    return {**state, **result}


def should_escalate(state: TicketState) -> Literal["escalate", "continue"]:
    """Conditional edge: determine if immediate escalation needed."""
    if state["priority"] == "urgent" and state["sentiment"] == "angry":
        return "escalate"
    if state["attempts"] >= 3:
        return "escalate"
    return "continue"


def search_knowledge_base(state: TicketState) -> TicketState:
    """RAG search against KB articles."""
    query = f"{state['subject']} {state['messages'][-1]['content']}"
    results = kb_retriever.invoke(query, k=5)
    return {**state, "kb_results": results}


def generate_resolution(state: TicketState) -> TicketState:
    """Generate AI response using context."""
    prompt = f"""You are a helpful customer support agent.
    
    Customer Query: {state['messages'][-1]['content']}
    
    Relevant Knowledge Base Articles:
    {format_kb_results(state['kb_results'])}
    
    Customer History Summary:
    {state['customer_history']}
    
    Generate a helpful, empathetic response that resolves their issue.
    Be specific and include step-by-step instructions if applicable.
    """
    response = llm.invoke(prompt)
    return {**state, "draft_response": response}
```

---

## Available Tools for Agent

| Tool Name | Description | Integration |
|-----------|-------------|-------------|
| `search_knowledge_base` | RAG search against internal KB | pgvector |
| `get_customer_info` | Fetch customer profile & history | PostgreSQL |
| `check_order_status` | Query order management system | REST API |
| `create_refund_request` | Initiate refund workflow | Payment API |
| `reset_password` | Trigger password reset email | Auth Service |
| `create_bug_ticket` | Create internal JIRA ticket | JIRA API |
| `schedule_callback` | Book callback slot | Calendar API |
| `send_email` | Send email to customer | Email Service |
| `notify_slack` | Alert team on Slack | Slack API |

---

## Project Structure

```
customer-support-agent/
├── README.md
├── pyproject.toml
├── docker-compose.yml
├── .env.example
│
├── alembic/                    # Database migrations
│   ├── alembic.ini
│   └── versions/
│
├── src/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app entrypoint
│   ├── config.py               # Settings & environment
│   │
│   ├── api/                    # API Layer
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── tickets.py
│   │   │   ├── webhooks.py
│   │   │   └── analytics.py
│   │   ├── schemas/            # Pydantic models
│   │   │   ├── ticket.py
│   │   │   └── responses.py
│   │   └── middleware/
│   │       ├── auth.py
│   │       └── rate_limit.py
│   │
│   ├── agents/                 # LangGraph Agent Layer
│   │   ├── __init__.py
│   │   ├── graph.py            # Main workflow graph
│   │   ├── state.py            # State definitions
│   │   ├── nodes/
│   │   │   ├── classifier.py
│   │   │   ├── resolver.py
│   │   │   ├── escalator.py
│   │   │   └── validator.py
│   │   └── edges/
│   │       └── conditions.py
│   │
│   ├── tools/                  # Agent Tools
│   │   ├── __init__.py
│   │   ├── knowledge_base.py
│   │   ├── customer_service.py
│   │   ├── external_apis.py
│   │   └── notifications.py
│   │
│   ├── db/                     # Database Layer
│   │   ├── __init__.py
│   │   ├── models.py           # SQLAlchemy models
│   │   ├── session.py
│   │   └── repositories/
│   │       ├── ticket_repo.py
│   │       └── customer_repo.py
│   │
│   ├── services/               # Business Logic
│   │   ├── ticket_service.py
│   │   └── analytics_service.py
│   │
│   └── utils/
│       ├── logging.py
│       └── metrics.py
│
├── tests/
│   ├── conftest.py
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
└── scripts/
    ├── seed_kb.py              # Populate knowledge base
    └── simulate_tickets.py     # Load testing
```

---

## Implementation Checkpoints

### Phase 1: Foundation (Week 1)
- [ ] Initialize project structure with `pyproject.toml`
- [ ] Set up PostgreSQL + pgvector with Docker
- [ ] Create database models and migrations
- [ ] Implement basic FastAPI skeleton with health check
- [ ] Set up structured logging and configuration

**Deliverable:** Running API with database connectivity

---

### Phase 2: Core Agent (Week 2)
- [ ] Define LangGraph state schema
- [ ] Implement classification node
- [ ] Implement knowledge base search tool
- [ ] Build basic resolution workflow
- [ ] Add audit trail logging for all agent actions

**Deliverable:** Agent can classify tickets and search KB

---

### Phase 3: Full Workflow (Week 3)
- [ ] Implement escalation logic and conditions
- [ ] Add customer history enrichment
- [ ] Build response validation node
- [ ] Implement retry logic with backoff
- [ ] Add human handoff preparation

**Deliverable:** Complete ticket lifecycle handling

---

### Phase 4: Integrations (Week 4)
- [ ] Implement external tool integrations (CRM, email)
- [ ] Add webhook endpoints for email intake
- [ ] Build real-time WebSocket updates
- [ ] Implement Slack notifications for escalations

**Deliverable:** Connected to external systems

---

### Phase 5: Production Readiness (Week 5)
- [ ] Add comprehensive error handling
- [ ] Implement rate limiting and auth
- [ ] Add Prometheus metrics
- [ ] Write integration tests
- [ ] Create Docker deployment setup
- [ ] Load testing with simulated tickets

**Deliverable:** Production-ready system

---

## Testing Strategy

### Unit Tests
```bash
# Test individual nodes in isolation
pytest tests/unit/agents/test_classifier.py -v

# Test tool functions
pytest tests/unit/tools/ -v
```

### Integration Tests
```bash
# Test full workflow with mock LLM
pytest tests/integration/test_ticket_workflow.py -v

# Test API endpoints
pytest tests/integration/test_api.py -v
```

### End-to-End Tests
```bash
# Full system test with real LLM (requires API key)
pytest tests/e2e/test_ticket_resolution.py -v --e2e
```

### Manual Verification
1. **Ticket Creation Flow:**
   - Submit ticket via API
   - Verify classification in logs
   - Check database records
   - Confirm response generated

2. **Escalation Flow:**
   - Submit high-priority angry ticket
   - Verify immediate escalation
   - Check Slack notification received
   - Confirm handoff summary quality

3. **Tool Execution Flow:**
   - Submit password reset request
   - Verify tool called correctly
   - Check audit trail logged
   - Confirm customer received email

---

## Configuration

### Environment Variables
```env
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/support_db
REDIS_URL=redis://localhost:6379/0

# LLM (Choose one - all free tier)
GROQ_API_KEY=gsk_xxx                    # Free: 30 req/min, Llama 3 70B
GOOGLE_API_KEY=xxx                       # Free: 60 req/min, Gemini 1.5 Flash
# OLLAMA_BASE_URL=http://localhost:11434 # Free: Local, unlimited
LLM_PROVIDER=groq                        # groq | google | ollama
LLM_MODEL=llama-3.1-70b-versatile        # or gemini-1.5-flash | llama3.2
LLM_TEMPERATURE=0.3

# Embeddings (Free options)
EMBEDDING_PROVIDER=huggingface           # huggingface | ollama
HF_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

# Integrations (Free tiers)
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...  # Free unlimited
MAILTRAP_API_KEY=xxx                     # Free: 1000 emails/month
# Or use: Resend (100 emails/day free), Brevo (300/day free)

# Security
JWT_SECRET=your-secret-key
API_KEY_SALT=your-salt

# Feature Flags
ENABLE_AUTO_RESOLUTION=true
MAX_AUTO_ATTEMPTS=3
ESCALATION_CONFIDENCE_THRESHOLD=0.7
```

---

## Monitoring & Observability

### Key Metrics
| Metric | Description |
|--------|-------------|
| `tickets_created_total` | Total tickets by channel |
| `tickets_resolved_auto` | Auto-resolved without human |
| `tickets_escalated` | Escalated to human agents |
| `resolution_time_seconds` | Time to resolve tickets |
| `llm_tokens_used` | Token usage for cost tracking |
| `tool_execution_duration` | External API latencies |

### Logging Structure
```json
{
  "timestamp": "2025-02-09T10:30:00Z",
  "level": "info",
  "event": "ticket_classified",
  "ticket_id": "550e8400-...",
  "intent": "password_reset",
  "priority": "medium",
  "confidence": 0.92,
  "latency_ms": 450
}
```

---

## Free Tier API Summary

| Service | Free Tier Limit | Use Case |
|---------|-----------------|----------|
| **Groq** | 30 req/min, 14,400/day | LLM inference (Llama 3 70B) |
| **Google Gemini** | 60 req/min, free tier | LLM inference (Gemini 1.5) |
| **Ollama** | Unlimited (local) | LLM inference (any open model) |
| **HuggingFace** | Unlimited (local) | Embeddings |
| **Discord Webhooks** | Unlimited | Notifications |
| **Mailtrap** | 1,000 emails/month | Email (dev/testing) |
| **Resend** | 100 emails/day | Email (production) |
| **Supabase** | 500MB DB, 1GB storage | PostgreSQL alternative |
| **Neon** | 0.5GB storage | PostgreSQL alternative |

---

## Next Steps After Approval

1. Set up project directory at `C:\Users\aryan\.gemini\antigravity\scratch\customer-support-agent`
2. Initialize Python project with dependencies
3. Create Docker Compose for PostgreSQL + Redis
4. Begin Phase 1 implementation

