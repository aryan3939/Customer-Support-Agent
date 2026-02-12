# Customer Support Agent — Complete Project Guide

> **Version**: 1.0  
> **Stack**: FastAPI · LangGraph · SQLAlchemy · Supabase · Next.js · LangSmith  
> **Last Updated**: February 2026

---

## Table of Contents

1. [What Is This Project?](#1-what-is-this-project)
2. [The Problem It Solves](#2-the-problem-it-solves)
3. [How It Works — The Big Picture](#3-how-it-works--the-big-picture)
4. [The AI Agent — Under the Hood](#4-the-ai-agent--under-the-hood)
5. [The Database — What Gets Stored](#5-the-database--what-gets-stored)
6. [The API — Every Endpoint Explained](#6-the-api--every-endpoint-explained)
7. [The Frontend — What the User Sees](#7-the-frontend--what-the-user-sees)
8. [Observability — LangSmith Tracing](#8-observability--langsmith-tracing)
9. [Technology Stack — Why Each Tool Was Chosen](#9-technology-stack--why-each-tool-was-chosen)
10. [How to Set Up and Run](#10-how-to-set-up-and-run)
11. [Configuration Reference](#11-configuration-reference)
12. [End-to-End Walkthrough — Creating a Ticket](#12-end-to-end-walkthrough--creating-a-ticket)
13. [Project Architecture — Visual Diagrams](#13-project-architecture--visual-diagrams)
14. [Folder Structure — Every File Explained](#14-folder-structure--every-file-explained)
15. [Extending the Project](#15-extending-the-project)
16. [FAQ](#16-faq)

---

## 1. What Is This Project?

This is an **AI-powered customer support system** that automatically handles incoming support tickets using a multi-step AI agent. Instead of a customer sending a message and waiting hours (or days) for a human to respond, this system:

1. **Instantly classifies** the ticket — detects intent (refund request? bug report? password issue?), assigns priority (low/medium/high/urgent), identifies category (billing, technical, account), and reads customer sentiment (positive, neutral, negative, angry).

2. **Searches a knowledge base** — finds relevant support articles to ground the response in real information, not hallucinations.

3. **Generates a helpful response** — writes a customer-facing reply using the classification, knowledge base results, and the customer's original message.

4. **Validates the response** — checks that the AI's reply is high quality, relevant, appropriately toned, and actually addresses the issue. If it fails, it **retries automatically**.

5. **Escalates when necessary** — if the customer is furious and the issue is urgent, or if the AI can't generate a good enough response after multiple attempts, it **routes the ticket to a human agent** instead of sending a bad response.

6. **Records everything** — every decision the AI makes is logged to the database as an audit trail, and every LLM call is traced in LangSmith for full observability.

**In short: it's an autonomous AI support agent with a safety net.** It handles the 80% of tickets it can, and intelligently escalates the 20% it shouldn't.

---

## 2. The Problem It Solves

### Without This System
```
Customer sends email
    → Sits in queue for 4-24 hours
    → Human agent reads it
    → Agent searches KB manually
    → Agent types a reply
    → Customer waits again for follow-up
```

**Problems:**
- Slow response times (hours to days)
- Expensive (human agents cost $30-60k/year each)
- Inconsistent quality (depends on which agent responds)
- No structured data (classification is manual and unreliable)
- No audit trail of reasoning

### With This System
```
Customer sends ticket
    → AI classifies in 2 seconds (intent, priority, sentiment)
    → AI searches knowledge base automatically
    → AI generates personalized response in 5 seconds
    → AI validates response quality
    → Customer gets a reply in under 10 seconds
    → Everything is logged, traceable, and auditable
```

**Benefits:**
- **< 10 second response time** (vs hours)
- **Consistent quality** — every response goes through validation
- **Structured data** — every ticket has priority, category, sentiment
- **Full audit trail** — every AI decision is recorded
- **Smart escalation** — AI knows when to defer to humans
- **Observable** — every LLM call visible in LangSmith

---

## 3. How It Works — The Big Picture

The system has three main parts:

```
┌────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Next.js)                         │
│                                                                    │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────────┐         │
│  │ Ticket   │    │ Ticket Detail│    │    Analytics      │         │
│  │ List     │    │ (Chat View)  │    │    Dashboard      │         │
│  └──────────┘    └──────────────┘    └──────────────────┘         │
│        │                │                     │                    │
│        └────────────────┼─────────────────────┘                    │
│                         │ /api/v1/* (proxied)                      │
└─────────────────────────┼──────────────────────────────────────────┘
                          │
┌─────────────────────────▼──────────────────────────────────────────┐
│                      BACKEND (FastAPI)                              │
│                                                                    │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ API Routes                                                   │   │
│  │   POST /tickets  │  GET /tickets  │  GET /analytics/dashboard│   │
│  └─────────┬───────────────────────────────────────────────────┘   │
│            │                                                        │
│  ┌─────────▼───────────────────────────────────────────────────┐   │
│  │ AI Agent (LangGraph State Machine)                           │   │
│  │                                                               │   │
│  │  classify ──▶ search_kb ──▶ generate ──▶ validate ──▶ send   │   │
│  │      │                                      │                 │   │
│  │      └──── escalate (if urgent & angry) ◀───┘                 │   │
│  └─────────┬───────────────────────────────────────────────────┘   │
│            │                                                        │
│  ┌─────────▼───────────────────────────────────────────────────┐   │
│  │ Database Layer (SQLAlchemy + asyncpg)                         │   │
│  │   Customers │ Tickets │ Messages │ Actions │ KB Articles      │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                         │                                          │
└─────────────────────────┼──────────────────────────────────────────┘
                          │
┌─────────────────────────▼──────────────────────────────────────────┐
│                     SUPABASE (PostgreSQL)                           │
│            Managed database with connection pooling                 │
└────────────────────────────────────────────────────────────────────┘
                          │
                    ┌─────▼─────┐
                    │ LangSmith │  ← Traces every LLM call
                    │ Dashboard │     with ticket metadata
                    └───────────┘
```

---

## 4. The AI Agent — Under the Hood

The AI agent is the core of this system. It's built with **LangGraph** — a framework that models AI workflows as **state machines** (directed graphs).

### Why a State Machine Instead of a Single LLM Call?

A single LLM call like `"Here's a support ticket, generate a response"` gives you:
- ❌ No classification data
- ❌ No knowledge base context
- ❌ No quality validation
- ❌ No escalation logic
- ❌ No audit trail
- ❌ No retry on bad responses

Our state machine gives you all of those. Each step is a separate, observable, testable node.

### The Workflow Step by Step

#### Step 1: Classify Ticket
**Input:** Raw customer message + subject  
**LLM Prompt:** "You are a support ticket classifier. Analyze this ticket and return structured JSON with: intent, category, priority, sentiment, confidence."  
**Output:**
```json
{
  "intent": "refund_request",
  "category": "billing",
  "priority": "high",
  "sentiment": "negative",
  "confidence": 0.92
}
```
**Why this matters:** Classification powers everything downstream — routing, prioritization, and response style.

#### Step 2: Escalation Check (Conditional Edge)
After classification, the system checks:
- Is priority `urgent` **AND** sentiment `angry`?
- If YES → skip AI response, route directly to human agent
- If NO → proceed to knowledge base search

**Why this matters:** An angry customer with an urgent issue needs a human, not a chatbot. This prevents the AI from making a bad situation worse.

#### Step 3: Search Knowledge Base
**Input:** Customer's message, detected intent, and category  
**Process:** Searches an in-memory knowledge base of support articles using keyword matching  
**Output:** Top 3 most relevant articles with titles, content, and match scores  

**Why this matters:** Grounding the AI's response in real knowledge base articles prevents hallucination. The AI references specific articles instead of making up solutions.

#### Step 4: Generate Response
**Input:** Original message + classification + KB results  
**LLM Prompt:** "You are a customer support agent. Given this classified ticket and these knowledge base articles, write a helpful, empathetic response."  
**Output:** A complete customer-facing response  

**Why this matters:** This is where the LLM actually generates the reply. The quality depends heavily on having good classification and KB context (from steps 1 and 3).

#### Step 5: Validate Response
**Input:** The generated response  
**Checks:**
- Is it long enough? (not a one-liner for a complex issue)
- Does it address the actual intent?
- Is the tone appropriate for the sentiment?
- Does it reference relevant KB content?

**Output:** `approve` / `retry` / `escalate`

**Why this matters:** This is the **safety net**. Without validation, the AI might send a generic "Have you tried turning it off and on again?" response to a billing dispute. Validation catches these mistakes.

#### Step 6a: Retry (if validation failed)
If validation fails, the system goes back to Step 4 with feedback about what was wrong. It retries up to 3 times. If all retries fail, it escalates to a human.

#### Step 6b: Finalize & Send (if validation passed)
Marks the ticket as resolved, logs the final action, and returns the response.

#### Step 6c: Escalate (if needed)
Generates a structured escalation with:
- Why the AI is escalating
- A summary for the human agent
- Suggested next steps

### The State Object

All steps share a `TicketState` — a Python dictionary that flows through the graph:

```python
TicketState = {
    # Input
    "ticket_id": "abc-123",
    "customer_email": "user@example.com",
    "subject": "Refund not processed",
    "message": "I requested a refund 2 weeks ago...",
    "channel": "web",

    # Classification (added by classify node)
    "intent": "refund_request",
    "category": "billing",
    "priority": "high",
    "sentiment": "negative",
    "confidence": 0.92,

    # Knowledge (added by search node)
    "kb_results": [
        {"title": "Refund Policy", "content": "...", "score": 0.85},
    ],

    # Response (added by generate/validate nodes)
    "draft_response": "I understand your frustration...",
    "final_response": "I understand your frustration...",

    # Control flow
    "needs_escalation": false,
    "escalation_reason": null,
    "attempts": 1,
    "actions_taken": [
        {"action_type": "classify", "outcome": "success", ...},
        {"action_type": "search_kb", "outcome": "3 articles found", ...},
        {"action_type": "generate_response", "outcome": "success", ...},
    ],
}
```

Every action the agent takes is recorded in `actions_taken`, creating a complete **audit trail**.

---

## 5. The Database — What Gets Stored

The system uses **Supabase** (managed PostgreSQL) with **SQLAlchemy** as the ORM (Object-Relational Mapper). Every piece of data is persisted — nothing lives only in memory.

### Tables

#### `customers`
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `email` | String | Customer's email (unique) |
| `name` | String | Display name |
| `metadata_` | JSON | Additional info (e.g., plan, company) |
| `created_at` | Timestamp | When the customer record was created |

A customer is auto-created on their first ticket. If the email already exists, the existing record is reused.

#### `agents`
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `name` | String | Agent name (e.g., "Support AI") |
| `email` | String | Agent's email |
| `role` | String | Role (e.g., `ai_support`, `tier_1`, `manager`) |
| `is_ai` | Boolean | Whether this is an AI agent or human |
| `is_active` | Boolean | Whether the agent is currently active |
| `skills` | JSON | What the agent can handle |

The system auto-creates a "Support AI" agent on first use.

#### `tickets`
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `customer_id` | UUID | FK → customers |
| `assigned_agent_id` | UUID | FK → agents (nullable) |
| `subject` | String | Ticket subject line |
| `status` | String | `new` → `open` → `resolved` / `escalated` / `closed` |
| `priority` | String | `low` / `medium` / `high` / `urgent` |
| `category` | String | `billing` / `technical` / `account` / etc. |
| `ai_context` | JSON | Classification data (intent, confidence, sentiment, etc.) |
| `created_at` | Timestamp | When the ticket was created |
| `updated_at` | Timestamp | Last modification time |
| `resolved_at` | Timestamp | When the ticket was resolved (nullable) |

#### `messages`
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `ticket_id` | UUID | FK → tickets |
| `sender_type` | String | `customer` / `ai_agent` / `human_agent` |
| `content` | Text | The message content |
| `metadata_` | JSON | Additional info (e.g., email headers) |
| `created_at` | Timestamp | When the message was sent |

Every ticket has at least 2 messages: the customer's original message and the AI's response. Follow-up messages create additional rows.

#### `agent_actions`
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `ticket_id` | UUID | FK → tickets |
| `agent_id` | UUID | FK → agents (nullable — AI actions may not have an explicit agent) |
| `action_type` | String | `classify`, `search_kb`, `generate_response`, `validate`, `escalate`, `send_response` |
| `action_data` | JSON | Detailed data about the action (e.g., classification results, search scores) |
| `reasoning` | JSON | Why the agent took this action |
| `outcome` | String | Result of the action (e.g., `success`, `3 articles found`) |
| `created_at` | Timestamp | When the action was taken |

This table is the **complete audit trail**. For any ticket, you can see exactly what the AI did, why it did it, and what the outcome was.

#### `knowledge_articles`
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `title` | String | Article title |
| `content` | Text | Full article text |
| `category` | String | Which category this article belongs to |
| `metadata_` | JSON | Tags, author, last reviewed date |
| `is_published` | Boolean | Whether the article is publicly available |

#### `kb_embeddings`
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `article_id` | UUID | FK → knowledge_articles |
| `chunk_text` | Text | A chunk of the article (for vector search) |
| `embedding` | Vector | The vector embedding of the chunk (for similarity search with pgvector) |
| `chunk_index` | Integer | Position of this chunk in the article |

This table enables **RAG (Retrieval-Augmented Generation)** — instead of the LLM hallucinating answers, it retrieves relevant article chunks by semantic similarity.

### Entity Relationships

```
Customer ──< Ticket >── Agent
                │
                ├──< Message
                ├──< AgentAction
                └──<>── Tag (many-to-many via ticket_tags)

KnowledgeArticle ──< KBEmbedding
```

One customer can have many tickets. Each ticket has many messages (the conversation thread) and many agent actions (the audit trail). Tickets can have multiple tags.

---

## 6. The API — Every Endpoint Explained

The backend exposes a RESTful JSON API. All endpoints are prefixed with `/api/v1/`.

### Ticket Endpoints

#### `POST /api/v1/tickets` — Create a Ticket

**Purpose:** Submit a new support ticket. The AI agent processes it and returns a response.

**Request Body:**
```json
{
  "customer_email": "alice@example.com",
  "subject": "Can't reset my password",
  "message": "I've tried 3 times but the reset email never arrives. My account email is alice@example.com.",
  "channel": "web",
  "metadata": {
    "browser": "Chrome",
    "os": "macOS"
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `customer_email` | string | ✅ | The customer's email address |
| `subject` | string | ✅ | Short description of the issue |
| `message` | string | ✅ | Full message from the customer |
| `channel` | string | ❌ | Where the ticket came from (`web`, `email`, `api`). Default: `web` |
| `metadata` | object | ❌ | Any additional context (browser, OS, page URL, etc.) |

**Response (201 Created):**
```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "open",
  "priority": "high",
  "category": "account",
  "sentiment": "negative",
  "assigned_to": {
    "id": "00000000-0000-0000-0000-000000000001",
    "name": "Support AI",
    "is_ai": true
  },
  "initial_response": "I understand you're having trouble with password reset emails. Let me help you with that...",
  "escalated": false,
  "escalation_reason": null,
  "created_at": "2026-02-10T12:00:00Z"
}
```

**What happens internally:**
1. Customer record is created (or found if email exists)
2. AI agent system-agent is created (first time only)
3. Ticket row inserted with status `new`
4. Customer's message stored as a `Message` row
5. AI agent processes through the full graph (classify → search → generate → validate)
6. Ticket updated with classification results + status changed to `open` (or `escalated`)
7. AI response stored as another `Message` row
8. All agent actions stored in `agent_actions` table
9. Response returned to the frontend

---

#### `GET /api/v1/tickets` — List All Tickets

**Purpose:** Get a paginated, filterable list of all tickets.

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| `status` | string | Filter by status (`new`, `open`, `resolved`, `escalated`, `closed`) |
| `priority` | string | Filter by priority (`low`, `medium`, `high`, `urgent`) |
| `category` | string | Filter by category (`billing`, `technical`, `account`, etc.) |
| `customer_email` | string | Filter by customer email |
| `limit` | int | Results per page (1-100, default: 20) |
| `offset` | int | Pagination offset (default: 0) |

**Example:** `GET /api/v1/tickets?status=open&priority=high&limit=10`

**Response:**
```json
{
  "tickets": [
    {
      "id": "a1b2c3d4-...",
      "customer_email": "alice@example.com",
      "subject": "Can't reset my password",
      "status": "open",
      "priority": "high",
      "category": "account",
      "sentiment": "negative",
      "assigned_to": { "id": "...", "name": "Support AI", "is_ai": true },
      "created_at": "2026-02-10T12:00:00Z",
      "updated_at": "2026-02-10T12:00:05Z",
      "resolved_at": null
    }
  ],
  "total": 42,
  "limit": 10,
  "offset": 0
}
```

---

#### `GET /api/v1/tickets/{id}` — Get Ticket Details

**Purpose:** Get a single ticket with its full conversation thread and AI audit trail.

**Response:**
```json
{
  "id": "a1b2c3d4-...",
  "customer_email": "alice@example.com",
  "subject": "Can't reset my password",
  "status": "open",
  "priority": "high",
  "category": "account",
  "sentiment": "negative",
  "assigned_to": { "id": "...", "name": "Support AI", "is_ai": true },
  "created_at": "2026-02-10T12:00:00Z",
  "updated_at": "2026-02-10T12:00:05Z",
  "resolved_at": null,
  "messages": [
    {
      "id": "msg-001",
      "ticket_id": "a1b2c3d4-...",
      "sender_type": "customer",
      "content": "I've tried 3 times but the reset email never arrives.",
      "created_at": "2026-02-10T12:00:00Z",
      "metadata": {}
    },
    {
      "id": "msg-002",
      "ticket_id": "a1b2c3d4-...",
      "sender_type": "ai_agent",
      "content": "I understand you're having trouble with password reset emails...",
      "created_at": "2026-02-10T12:00:05Z",
      "metadata": {}
    }
  ],
  "actions": [
    {
      "action_type": "classify",
      "outcome": "success",
      "reasoning": "Customer requesting password reset help, tone is frustrated",
      "created_at": "2026-02-10T12:00:01Z"
    },
    {
      "action_type": "search_kb",
      "outcome": "3 articles found",
      "reasoning": "Searched for password reset related articles",
      "created_at": "2026-02-10T12:00:02Z"
    },
    {
      "action_type": "generate_response",
      "outcome": "success",
      "reasoning": "Generated response using KB articles about password reset",
      "created_at": "2026-02-10T12:00:04Z"
    }
  ],
  "ai_context": {
    "intent": "password_reset",
    "confidence": 0.95,
    "sentiment": "negative",
    "kb_results_count": 3
  }
}
```

---

#### `POST /api/v1/tickets/{id}/messages` — Send a Follow-Up Message

**Purpose:** Add a follow-up message to an existing ticket. If sent by a customer, the AI agent automatically re-processes and responds.

**Request Body:**
```json
{
  "content": "I already checked my spam folder, it's not there either.",
  "sender_type": "customer"
}
```

**What happens:** The AI receives the follow-up message, re-runs through the graph, and generates a new response that takes the conversation history into account.

---

#### `PATCH /api/v1/tickets/{id}/status` — Update Ticket Status

**Purpose:** Change a ticket's status (e.g., mark as resolved or closed).

**Request Body:**
```json
{
  "status": "resolved"
}
```

Valid statuses: `new`, `open`, `resolved`, `escalated`, `closed`

If status is `resolved` or `closed`, the `resolved_at` timestamp is automatically set.

---

#### `GET /api/v1/tickets/{id}/actions` — Get Audit Trail

**Purpose:** Get the complete list of AI actions taken on a ticket.

**Response:**
```json
{
  "ticket_id": "a1b2c3d4-...",
  "actions": [
    {
      "action_type": "classify",
      "action_data": { "intent": "password_reset", "priority": "high" },
      "reasoning": { "thought": "Customer mentioned password reset multiple times" },
      "outcome": "success",
      "created_at": "2026-02-10T12:00:01Z"
    }
  ],
  "total": 4
}
```

---

### Analytics Endpoint

#### `GET /api/v1/analytics/dashboard` — Dashboard Metrics

**Purpose:** Aggregate support metrics for the analytics dashboard.

**Response:**
```json
{
  "total_tickets": 156,
  "open_tickets": 23,
  "resolved_tickets": 118,
  "escalated_tickets": 15,
  "resolution_rate": 75.6,
  "escalation_rate": 9.6,
  "priority_breakdown": {
    "low": 45,
    "medium": 67,
    "high": 33,
    "urgent": 11
  },
  "category_breakdown": {
    "billing": 42,
    "technical": 58,
    "account": 35,
    "general": 21
  },
  "sentiment_breakdown": {
    "positive": 28,
    "neutral": 65,
    "negative": 48,
    "angry": 15
  }
}
```

---

### Webhook Endpoint

#### `POST /api/v1/webhooks/email` — Email Intake

**Purpose:** Receive incoming support emails from external services (e.g., SendGrid Inbound Parse) and auto-create tickets.

**Request Body:** (from email service)
```json
{
  "from": "customer@example.com",
  "subject": "Order not delivered",
  "body": "My order #12345 was supposed to arrive 3 days ago...",
  "message_id": "msg_abc123",
  "headers": {}
}
```

This endpoint maps email fields to a ticket and reuses the same `create_ticket` logic, so email-originated tickets get the same AI treatment as web tickets.

---

## 7. The Frontend — What the User Sees

The frontend is a **Next.js 14** dashboard with three pages:

### Page 1: Ticket List (Home — `/`)
- Table showing all tickets with status, priority, category, sentiment badges
- Color-coded status indicators (green=resolved, yellow=open, red=escalated)
- "New Ticket" button that opens a dialog form
- The form asks for: email, subject, message, and channel
- After submission, the ticket appears in the table immediately

### Page 2: Ticket Detail (`/tickets/[id]`)
A two-column layout:

**Left (2/3 width) — Chat Interface:**
- Full conversation thread between customer and AI
- Messages styled as chat bubbles (customer on left, AI on right)
- Input box at the bottom to send follow-up messages
- Follow-up messages trigger the AI to respond again

**Right (1/3 width) — Sidebar:**
- **AI Classification card:** Shows intent, category, priority, sentiment, confidence with color-coded badges
- **Audit Trail card:** Shows every action the AI took (classify, search_kb, generate_response, etc.) with timestamps

### Page 3: Analytics Dashboard (`/analytics`)
- Metric cards across the top: Total Tickets, Open, Resolved, Escalated
- Resolution rate and escalation rate percentages
- Priority breakdown
- Category breakdown
- Sentiment breakdown

### How the Frontend Connects to the Backend

The frontend runs on `localhost:3000` and the backend on `localhost:8000`. Instead of configuring CORS, the frontend uses **Next.js rewrites** (`next.config.ts`) to proxy all `/api/v1/*` requests to the backend. This means:

- Frontend calls `fetch("/api/v1/tickets")` (same origin, no CORS)
- Next.js proxies → `http://localhost:8000/api/v1/tickets`
- Response flows back through the proxy

All API calls are centralized in `frontend/src/lib/api.ts` with **TypeScript types that mirror the backend Pydantic schemas**, giving end-to-end type safety.

---

## 8. Observability — LangSmith Tracing

Every time the AI agent processes a ticket, all LLM calls are traced in **LangSmith** — LangChain's observability platform.

### What Gets Traced

Each ticket creates a **trace run** with:
- **Run name:** `ticket-{first 8 chars of ID}` (e.g., `ticket-a1b2c3d4`)
- **Tags:** `customer-support`, `channel:web`
- **Metadata:** `ticket_id`, `customer_email`, `subject`, `channel`
- **Thread ID:** The full ticket UUID — groups all runs for the same ticket together

### What You Can See in LangSmith

For each trace:
- **Full LLM inputs and outputs** — the exact prompts sent and responses received
- **Latency per step** — how long classify vs generate took
- **Token usage** — how many tokens each call consumed
- **Error details** — if an LLM call failed, why
- **Thread view** — all traces for the same ticket grouped together (useful for follow-up messages)

### How to Access

1. Go to [LangSmith EU Dashboard](https://eu.smith.langchain.com) (or US if using US endpoint)
2. Select the project configured in `LANGCHAIN_PROJECT`
3. Each ticket appears as a named trace
4. Click into a trace to see the full step-by-step execution

### Configuration
Set these in `.env`:
```env
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_pt_...
LANGCHAIN_PROJECT=customer-support-agent
LANGCHAIN_ENDPOINT=https://eu.api.smith.langchain.com
```

---

## 9. Technology Stack — Why Each Tool Was Chosen

| Technology | Role | Why This One? |
|-----------|------|---------------|
| **FastAPI** | REST API framework | Async-native, auto-generates docs, Pydantic integration, dependency injection |
| **LangGraph** | AI agent workflow | State machine model gives control flow, retry logic, conditional routing, audit trail — unlike simple chains |
| **LangChain** | LLM abstraction | Provider-agnostic (swap Google ↔ Groq with one config change), structured output, prompt templates |
| **Groq / Google Gemini** | LLM providers | Groq = fast inference (Llama), Gemini = Google quality. Configurable via env var |
| **SQLAlchemy** | ORM | Industry standard, async support, relationship management, migration support |
| **asyncpg** | PostgreSQL driver | Fastest async Postgres driver for Python |
| **Supabase** | Managed PostgreSQL | Free tier, built-in connection pooling (PgBouncer), pgvector support for embeddings |
| **Next.js 14** | Frontend framework | App Router, server components, TypeScript, built-in API proxy |
| **Tailwind CSS** | Styling | Utility-first, dark mode support, responsive design |
| **LangSmith** | Observability | Purpose-built for LLM tracing — shows every LLM call with inputs/outputs/latency |
| **structlog** | Logging | Structured JSON logs, context propagation, beautiful dev output |
| **Pydantic** | Validation | Data validation at API boundaries, settings management, type safety |

---

## 10. How to Set Up and Run

### Prerequisites
- Python 3.11+ installed
- Node.js 18+ installed
- A Supabase account (free tier works)
- An LLM API key (Groq is free, or Google Gemini)
- A LangSmith API key (free tier works)

### Step 1: Clone and Install Backend

```bash
# Navigate to the project directory
cd "Customer Support Agent"

# Create virtual environment
python -m venv venv

# Activate it (Windows)
venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt
```

### Step 2: Configure Environment Variables

Copy `.env.example` to `.env` and fill in your keys:

```bash
copy .env.example .env
```

**Required variables:**
```env
# LLM Provider (choose one)
LLM_PROVIDER=groq
LLM_MODEL=llama-3.1-70b-versatile
GROQ_API_KEY=gsk_...

# Database (from Supabase dashboard → Settings → Database)
DATABASE_URL=postgresql+asyncpg://postgres.xxxx:password@aws-0-ap-south-1.pooler.supabase.com:6543/postgres

# LangSmith Tracing
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_pt_...
LANGCHAIN_PROJECT=customer-support-agent
LANGCHAIN_ENDPOINT=https://eu.api.smith.langchain.com
```

> See `docs/API_KEYS_SETUP.md` for detailed instructions on getting each key.

### Step 3: Run the Backend

```bash
uvicorn src.main:app --reload --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
database_connected ✓
database_tables_ready — All tables created/verified ✓
```

### Step 4: Install and Run the Frontend

```bash
cd frontend
npm install
npm run dev
```

Opens at `http://localhost:3000`.

### Step 5: Create Your First Ticket

1. Open `http://localhost:3000` in your browser
2. Click "New Ticket"
3. Fill in the form (email, subject, message)
4. Click "Create"
5. Watch the AI process the ticket and respond in seconds

### Step 6: Verify Everything Works

| What to Check | Where |
|----------------|-------|
| Ticket appears in the list | `http://localhost:3000` |
| Ticket detail shows chat + classification | Click on the ticket |
| Data is in Supabase | Supabase Dashboard → Table Editor |
| Trace appears in LangSmith | LangSmith Dashboard → Project |
| API docs are generated | `http://localhost:8000/docs` |

---

## 11. Configuration Reference

All configuration is in the `.env` file. Here's every variable:

### LLM Settings
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LLM_PROVIDER` | ✅ | `google` | LLM provider: `google` or `groq` |
| `LLM_MODEL` | ❌ | `gemini-2.0-flash` | Model name for the chosen provider |
| `GOOGLE_API_KEY` | If google | — | Google AI Studio API key |
| `GROQ_API_KEY` | If groq | — | Groq API key |

### Database
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | ✅ | — | PostgreSQL connection string (must use `asyncpg` driver) |
| `SUPABASE_URL` | ✅ | — | Supabase project URL |
| `SUPABASE_ANON_KEY` | ✅ | — | Supabase anonymous key |

### LangSmith
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LANGCHAIN_TRACING_V2` | ❌ | `false` | Enable/disable LLM tracing |
| `LANGCHAIN_API_KEY` | If tracing | — | LangSmith API key |
| `LANGCHAIN_PROJECT` | ❌ | `default` | Project name in LangSmith |
| `LANGCHAIN_ENDPOINT` | ❌ | US endpoint | API URL (use EU URL for EU accounts) |

### Application
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LOG_LEVEL` | ❌ | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `LOG_FORMAT` | ❌ | `console` | Log format (`console` for dev, `json` for production) |
| `CORS_ORIGINS` | ❌ | `["*"]` | Allowed CORS origins |

---

## 12. End-to-End Walkthrough — Creating a Ticket

Here's exactly what happens, step by step, when you create a ticket:

```
1. You click "Create Ticket" and fill in the form
   └── Frontend calls POST /api/v1/tickets with { email, subject, message }

2. Next.js proxy forwards to localhost:8000/api/v1/tickets
   └── FastAPI receives the request

3. Route handler: create_ticket()
   ├── 3a. get_or_create_customer(db, email="alice@example.com")
   │   └── Checks DB. New customer? Insert. Existing? Return record.
   │   └── Result: Customer { id: "cust-xxx", email: "alice@example.com" }
   │
   ├── 3b. get_or_create_ai_agent(db)
   │   └── Finds or creates the "Support AI" agent row
   │   └── Result: Agent { id: "00000...001", name: "Support AI", is_ai: true }
   │
   ├── 3c. repo_create_ticket(db, customer_id, subject)
   │   └── INSERT INTO tickets (customer_id, subject, status='new') ...
   │   └── Result: Ticket { id: "tick-xxx", status: "new" }
   │
   ├── 3d. repo_add_message(db, ticket_id, "customer", message)
   │   └── INSERT INTO messages (ticket_id, sender_type='customer', content=...) ...
   │
   ├── 3e. process_ticket(ticket_id, email, subject, message)
   │   │
   │   │   ┌─── LangSmith Config ──────────────────────────┐
   │   │   │ run_name: "ticket-tick-xxx"                    │
   │   │   │ tags: ["customer-support", "channel:web"]      │
   │   │   │ metadata: { ticket_id, email, subject }        │
   │   │   │ thread_id: "tick-xxx"                          │
   │   │   └───────────────────────────────────────────────┘
   │   │
   │   ├── Node 1: classify_ticket
   │   │   └── LLM call → "Classify this ticket..."
   │   │   └── Returns: { intent: "password_reset", priority: "high", ... }
   │   │
   │   ├── Edge: should_escalate_after_classify?
   │   │   └── priority=high, sentiment=negative → NOT urgent+angry → continue
   │   │
   │   ├── Node 2: search_knowledge_base
   │   │   └── Keywords: "password", "reset", "email"
   │   │   └── Returns: 3 matching articles
   │   │
   │   ├── Node 3: generate_response
   │   │   └── LLM call → "Using these KB articles, write a helpful response..."
   │   │   └── Returns: "I understand you're having trouble with password reset..."
   │   │
   │   ├── Node 4: validate_response
   │   │   └── Checks: length ✓, addresses intent ✓, tone ✓
   │   │   └── Result: "accept"
   │   │
   │   └── Node 5: finalize_response
   │       └── Sets status = "resolved", records send_response action
   │
   ├── 3f. Update ticket in DB
   │   └── SET status='open', priority='high', category='account',
   │   └── ai_context = { intent, confidence, sentiment, ... }
   │
   ├── 3g. repo_add_message(db, ticket_id, "ai_agent", response_text)
   │   └── INSERT INTO messages (sender_type='ai_agent', content=...) ...
   │
   ├── 3h. For each action in actions_taken:
   │   └── add_agent_action(db, ticket_id, action_type, ...)
   │   └── INSERT INTO agent_actions (ticket_id, action_type, ...) × 4-5 rows
   │
   └── 3i. Return CreateTicketResponse to frontend
       └── { id, status, priority, initial_response, escalated: false }

4. Frontend receives the response
   └── Ticket appears in the list with AI response
   └── Click to see chat thread + classification sidebar
```

**Total time: ~5-10 seconds** (mostly LLM inference time)  
**Database writes: 8-10 rows** (1 customer + 1 ticket + 2 messages + 4-5 actions)  
**LLM calls: 2** (classify + generate response)  
**LangSmith: 1 trace** with full step-by-step breakdown

---

## 13. Project Architecture — Visual Diagrams

### System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                            │
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │ Browser  │  │  Email   │  │   API    │  │   CLI    │       │
│  │ (Next.js)│  │(Webhook) │  │ Client   │  │ (test)   │       │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘       │
└───────┼──────────────┼─────────────┼─────────────┼─────────────┘
        │              │             │             │
        ▼              ▼             ▼             ▼
┌─────────────────────────────────────────────────────────────────┐
│                         API LAYER (FastAPI)                      │
│                                                                 │
│  ┌─────────┐  ┌────────────┐  ┌──────────────┐                │
│  │ Tickets │  │ Analytics  │  │   Webhooks   │                │
│  │ Routes  │  │   Route    │  │    Route     │                │
│  └────┬────┘  └─────┬──────┘  └──────┬───────┘                │
│       │              │               │                          │
│  ┌────▼──────────────▼───────────────▼─────────────────────┐   │
│  │ Pydantic Schemas (validation) + Middleware (auth, rate) │   │
│  └────┬────────────────────────────────────────────────────┘   │
└───────┼─────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│                      INTELLIGENCE LAYER                         │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              LangGraph State Machine                      │  │
│  │  classify → search_kb → generate → validate → finalize   │  │
│  └───────────────────┬──────────────────────────────────────┘  │
│                      │                                          │
│  ┌──────────┐  ┌─────▼──────┐  ┌──────────────┐              │
│  │   LLM    │  │    KB      │  │  External    │              │
│  │ (Groq/   │  │  Search    │  │  APIs (mock) │              │
│  │  Google)  │  │  Tool      │  │              │              │
│  └──────────┘  └────────────┘  └──────────────┘              │
└─────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│                      PERSISTENCE LAYER                          │
│                                                                 │
│  ┌──────────────────┐  ┌──────────────────────────────────┐   │
│  │   Repositories   │  │        SQLAlchemy ORM             │   │
│  │  (ticket_repo,   │──│  (models, sessions, migrations)   │   │
│  │   customer_repo) │  │                                    │   │
│  └──────────────────┘  └──────────────┬───────────────────┘   │
└────────────────────────────────────────┼────────────────────────┘
                                         │
                                         ▼
                              ┌──────────────────┐
                              │    Supabase      │
                              │   PostgreSQL     │
                              │  (via PgBouncer) │
                              └──────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                     OBSERVABILITY LAYER                          │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  LangSmith   │  │   structlog  │  │   In-memory Metrics  │  │
│  │ (LLM traces) │  │   (logging)  │  │   (counters/latency) │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

### Data Flow Diagram

```
Customer Message
       │
       ▼
  ┌─────────┐     ┌──────────┐     ┌──────────┐
  │ FastAPI  │────▶│ Customer │────▶│  Ticket  │
  │  Route   │     │   Repo   │     │   Repo   │
  └────┬─────┘     └──────────┘     └──────────┘
       │                                   │
       ▼                                   ▼
  ┌──────────┐                      ┌───────────┐
  │ LangGraph│                      │  Message   │
  │  Agent   │                      │   Repo     │
  └────┬─────┘                      └───────────┘
       │                                   │
       ├──▶ LLM (classify)                 │
       ├──▶ KB Search                      │
       ├──▶ LLM (generate)                 │
       ├──▶ Validate                       │
       │                                   │
       ▼                                   ▼
  ┌──────────┐                      ┌───────────┐
  │ AI Agent │                      │   Action   │
  │ Response │                      │   Repo     │
  └──────────┘                      └───────────┘
       │                                   │
       ▼                                   ▼
  JSON Response                     Supabase DB
  to Frontend                    (persisted forever)
```

---

## 14. Folder Structure — Every File Explained

```
Customer Support Agent/
│
├── .env                          # Your API keys and config (NEVER commit)
├── .env.example                  # Template showing all env vars
├── .gitignore                    # Git ignore rules
├── README.md                     # Quick-start readme
├── requirements.txt              # Python dependencies
├── pyproject.toml                # Project metadata + tool config
├── docker-compose.yml            # Optional Docker setup (Postgres + Redis)
├── alembic.ini                   # Alembic migration config
│
├── src/                          # ★ BACKEND
│   ├── main.py                   # FastAPI app entry point (uvicorn runs this)
│   ├── config.py                 # Pydantic settings (loads .env)
│   │
│   ├── agents/                   # AI Agent (LangGraph)
│   │   ├── graph.py              # State machine definition + process_ticket()
│   │   ├── state.py              # TicketState TypedDict
│   │   ├── llm.py                # LLM factory (Google or Groq)
│   │   ├── nodes/                # Graph nodes (one file = one step)
│   │   │   ├── classifier.py     # Step 1: classify intent/priority/sentiment
│   │   │   ├── resolver.py       # Step 3: generate AI response
│   │   │   ├── validator.py      # Step 4: quality-check response
│   │   │   └── escalator.py      # Escalation handler
│   │   └── edges/
│   │       └── conditions.py     # Routing logic (when to escalate/retry)
│   │
│   ├── api/                      # REST API
│   │   ├── routes/
│   │   │   ├── tickets.py        # 6 ticket endpoints (CRUD + messages + actions)
│   │   │   ├── analytics.py      # Dashboard metrics endpoint
│   │   │   └── webhooks.py       # Email intake webhook
│   │   ├── schemas/
│   │   │   ├── ticket.py         # Pydantic request/response models
│   │   │   └── responses.py      # Generic response wrappers
│   │   └── middleware/
│   │       ├── auth.py           # API key auth (placeholder)
│   │       └── rate_limit.py     # Rate limiting (placeholder)
│   │
│   ├── db/                       # Database
│   │   ├── models.py             # SQLAlchemy ORM models (8 tables)
│   │   ├── session.py            # Engine, sessions, init_db(), PgBouncer compat
│   │   └── repositories/
│   │       ├── ticket_repo.py    # Ticket/Message/Action queries
│   │       └── customer_repo.py  # Customer queries
│   │
│   ├── services/
│   │   └── analytics_service.py  # Dashboard metric computation
│   │
│   ├── tools/                    # Agent tools
│   │   ├── knowledge_base.py     # KB search (active)
│   │   ├── customer_service.py   # Customer lookup (mock)
│   │   ├── external_apis.py      # Order/refund/password APIs (mock)
│   │   └── notifications.py      # Slack/email notifications (mock)
│   │
│   └── utils/
│       ├── logging.py            # Structured logging (structlog)
│       └── metrics.py            # Simple counters + latency tracking
│
├── frontend/                     # ★ FRONTEND (Next.js)
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx          # Ticket list + create form
│   │   │   ├── layout.tsx        # Root layout with sidebar
│   │   │   ├── globals.css       # Dark theme CSS variables
│   │   │   ├── tickets/[id]/
│   │   │   │   └── page.tsx      # Ticket detail (chat + classification)
│   │   │   └── analytics/
│   │   │       └── page.tsx      # Dashboard with metrics
│   │   └── lib/
│   │       └── api.ts            # Typed API client
│   ├── next.config.ts            # API proxy config (→ localhost:8000)
│   └── package.json              # Node dependencies
│
├── scripts/
│   └── test_agent.py             # Standalone agent test (no server needed)
│
├── docs/                         # Documentation
│   ├── PROJECT_STRUCTURE.md      # File/folder map
│   ├── COMPLETE_PROJECT_GUIDE.md # This file
│   ├── HOW_TO_RUN.md             # Quick-start guide
│   ├── API_KEYS_SETUP.md         # Key setup instructions
│   ├── 01-05_*.md                # Phase-by-phase build docs
│   └── README.md                 # Docs reading guide
│
├── tests/                        # Test suite (pytest)
│   ├── conftest.py               # Shared fixtures
│   ├── unit/                     # Unit tests
│   ├── integration/              # Integration tests
│   └── e2e/                      # End-to-end tests
│
└── alembic/                      # Database migrations
    ├── env.py                    # Migration runner config
    ├── script.py.mako            # Migration template
    └── versions/                 # Migration scripts
```

---

## 15. Extending the Project

### Add a New LLM Provider
1. Edit `src/agents/llm.py`
2. Add a new `elif` branch for your provider
3. Set `LLM_PROVIDER=your_provider` in `.env`

### Add a New Agent Tool
1. Create `src/tools/your_tool.py` with an async function
2. Call it from the relevant graph node (e.g., `resolver.py`)
3. The audit trail will automatically log the tool call

### Add Vector Search (RAG Upgrade)
1. Generate embeddings for KB articles using OpenAI/Cohere embeddings
2. Store in the `kb_embeddings` table (pgvector column already defined)
3. Replace keyword search in `knowledge_base.py` with cosine similarity queries

### Add Real Authentication
1. Replace `src/api/middleware/auth.py` with JWT validation
2. Use Supabase Auth or Auth0 for token issuance
3. Extract user ID from token and attach to request context

### Add WebSocket for Real-Time
1. Add a `/ws/tickets/{id}` WebSocket endpoint
2. Push new messages to connected clients in real-time
3. Frontend subscribes when viewing a ticket detail page

### Deploy to Production
1. **Backend:** Deploy to Railway, Render, or AWS Lambda
2. **Frontend:** Deploy to Vercel (Next.js native platform)
3. **Database:** Supabase already handles this (managed PostgreSQL)
4. **Monitoring:** LangSmith for LLM traces, Datadog/CloudWatch for infrastructure

---

## 16. FAQ

### Q: What happens if the LLM API is down?
The `create_ticket` endpoint returns a 500 error with a message like `"AI agent failed to process ticket: Connection refused"`. The ticket is NOT created in the database (the transaction rolls back). The customer can retry.

### Q: Can I use a different LLM?
Yes. Set `LLM_PROVIDER` to `google` or `groq` in `.env`. To add a new provider, edit `src/agents/llm.py` — it's just a factory function with if/elif branches.

### Q: Can I use a different database?
Yes, but it requires changes to `src/db/session.py` (connection string and engine settings) and potentially the repositories (if switching to a non-SQL database). The ORM models stay the same for any SQL database.

### Q: How many tickets can it handle?
Each ticket takes ~5-10 seconds (dominated by LLM inference). With Groq's fast inference, you can process ~6-12 tickets/minute per worker. Add more uvicorn workers for more throughput.

### Q: Is the data secure?
- All data is stored in Supabase (SOC2 compliant)
- API keys are in `.env` (never committed to git)
- The `.gitignore` excludes `.env`, `venv/`, and `node_modules/`
- Middleware placeholders show where to add auth/rate limiting

### Q: Why are some tools "mock"?
Mock tools (`customer_service.py`, `external_apis.py`, `notifications.py`) demonstrate the **integration pattern** without requiring paid API accounts. They show how the agent would call Stripe, JIRA, Slack, etc. Replace the mock implementation with real API calls when ready.

### Q: How do I see what the AI is "thinking"?
Three ways:
1. **Frontend:** Click a ticket → check the "Audit Trail" sidebar
2. **Database:** Query the `agent_actions` table for a ticket
3. **LangSmith:** Open the trace to see every LLM call with full inputs/outputs

### Q: What if the AI generates a bad response?
The `validate_response` node catches low-quality responses and retries up to 3 times. If all retries fail, the ticket is **escalated** to a human agent instead of sending a bad response. This is the safety net.

### Q: Can multiple people use the frontend at the same time?
Yes. The backend is async (FastAPI + asyncpg), so it handles concurrent requests efficiently. Each request gets its own database session via dependency injection.

---

*This document is the single source of truth for understanding the Customer Support Agent project. For quick-start setup, see `HOW_TO_RUN.md`. For API key instructions, see `API_KEYS_SETUP.md`. For per-folder details, check the README.md inside each folder.*
