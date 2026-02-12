"""
Pydantic schemas for ticket API requests and responses.

WHY THIS FILE EXISTS:
---------------------
FastAPI uses Pydantic models for:
1. REQUEST VALIDATION — automatically reject invalid input
2. RESPONSE SERIALIZATION — format output consistently
3. DOCUMENTATION — auto-generate Swagger UI docs from schemas

Without schemas: you manually validate every field in every route.
With schemas: FastAPI does it for you AND generates API docs.

HOW IT WORKS:
-------------
    POST /api/v1/tickets  body: {"customer_email": "...", "subject": "..."}
                                        ↓
    Pydantic validates: is email valid? is subject present?
                                        ↓
    If invalid → 422 error with details
    If valid   → CreateTicketRequest object passed to route function
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field


# =============================================================================
# REQUEST SCHEMAS — what the client SENDS
# =============================================================================

class CreateTicketRequest(BaseModel):
    """
    Request body for POST /api/v1/tickets
    
    Example:
        {
            "customer_email": "user@example.com",
            "subject": "Cannot reset my password",
            "message": "I've tried 3 times but no email arrives.",
            "channel": "web",
            "metadata": {"browser": "Chrome 120"}
        }
    """
    customer_email: EmailStr = Field(
        ...,
        description="Customer's email address",
        examples=["user@example.com"],
    )
    subject: str = Field(
        ...,
        min_length=5,
        max_length=500,
        description="Brief description of the issue",
        examples=["Cannot reset my password"],
    )
    message: str = Field(
        ...,
        min_length=10,
        max_length=5000,
        description="Detailed description of the problem",
        examples=["I've tried resetting my password 3 times..."],
    )
    channel: Literal["web", "email", "api", "chat"] = Field(
        default="web",
        description="Source channel of the ticket",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional extra context (browser, page URL, etc.)",
    )


class AddMessageRequest(BaseModel):
    """
    Request body for POST /api/v1/tickets/{id}/messages
    
    Used when a customer sends a follow-up message on an existing ticket.
    """
    content: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Message content",
    )
    sender_type: Literal["customer", "human_agent"] = Field(
        default="customer",
        description="Who is sending this message",
    )


class UpdateTicketStatusRequest(BaseModel):
    """
    Request body for PATCH /api/v1/tickets/{id}/status
    """
    status: Literal[
        "new", "open", "pending_customer", "pending_agent",
        "escalated", "resolved", "closed"
    ] = Field(
        ...,
        description="New ticket status",
    )


class TicketFilterParams(BaseModel):
    """
    Query parameters for GET /api/v1/tickets (listing/filtering).
    """
    status: str | None = Field(default=None, description="Filter by status")
    priority: str | None = Field(default=None, description="Filter by priority")
    category: str | None = Field(default=None, description="Filter by category")
    customer_email: str | None = Field(default=None, description="Filter by customer")
    limit: int = Field(default=20, ge=1, le=100, description="Results per page")
    offset: int = Field(default=0, ge=0, description="Pagination offset")


# =============================================================================
# RESPONSE SCHEMAS — what the server RETURNS
# =============================================================================

class AgentInfo(BaseModel):
    """Assigned agent info in ticket responses."""
    id: str
    name: str
    is_ai: bool


class TicketResponse(BaseModel):
    """
    Response for a single ticket — GET /api/v1/tickets/{id}
    """
    id: str
    customer_email: str
    subject: str
    status: str
    priority: str
    category: str | None = None
    sentiment: str | None = None
    assigned_to: AgentInfo | None = None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None = None


class CreateTicketResponse(BaseModel):
    """
    Response for POST /api/v1/tickets
    
    Includes the AI agent's initial response.
    """
    id: str
    status: str
    priority: str
    category: str | None = None
    sentiment: str | None = None
    assigned_to: AgentInfo
    initial_response: str
    escalated: bool = False
    escalation_reason: str | None = None
    created_at: datetime


class MessageResponse(BaseModel):
    """A single message in a ticket thread."""
    id: str
    ticket_id: str
    sender_type: str
    content: str
    created_at: datetime
    metadata: dict[str, Any] = {}


class ActionResponse(BaseModel):
    """A single action in the audit trail."""
    action_type: str
    action_data: dict[str, Any] = {}
    outcome: str | None = None
    reasoning: str | None = None
    created_at: datetime | None = None


class TicketDetailResponse(TicketResponse):
    """
    Full ticket detail with messages and actions.
    Extends TicketResponse with nested data.
    """
    messages: list[MessageResponse] = []
    actions: list[ActionResponse] = []
    ai_context: dict[str, Any] = {}


class TicketListResponse(BaseModel):
    """Paginated list of tickets."""
    tickets: list[TicketResponse]
    total: int
    limit: int
    offset: int


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: datetime
    environment: str
    checks: dict[str, str]
