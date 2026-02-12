"""
Ticket Service — business logic layer for ticket operations.

WHY A SERVICE LAYER?
--------------------
Routes handle HTTP (request/response). Services handle BUSINESS LOGIC.
This separation means:
    - Routes stay thin (just parse request → call service → return response)
    - Business logic is reusable (routes, CLI, tests can all call services)
    - Testing is easier (test service functions directly, no HTTP needed)
"""

import uuid
from datetime import datetime, timezone

from src.agents.graph import process_ticket
from src.utils.logging import get_logger

logger = get_logger(__name__)

# In-memory store (shared with routes for now)
_tickets: dict[str, dict] = {}


async def create_ticket(
    customer_email: str,
    subject: str,
    message: str,
    channel: str = "web",
    metadata: dict | None = None,
) -> dict:
    """
    Create a new ticket and process it through the AI agent.
    
    This is the core business logic:
    1. Generate a unique ticket ID
    2. Run the AI agent workflow
    3. Store the result
    4. Return the complete ticket data
    """
    ticket_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    
    logger.info("creating_ticket_via_service", ticket_id=ticket_id)
    
    # Process through AI agent
    agent_result = await process_ticket(
        ticket_id=ticket_id,
        customer_email=customer_email,
        subject=subject,
        message=message,
        channel=channel,
    )
    
    status = "escalated" if agent_result.get("needs_escalation") else "open"
    response_text = agent_result.get("final_response") or agent_result.get("draft_response", "")
    
    ticket = {
        "id": ticket_id,
        "customer_email": customer_email,
        "subject": subject,
        "status": status,
        "priority": agent_result.get("priority", "medium"),
        "category": agent_result.get("category"),
        "sentiment": agent_result.get("sentiment"),
        "channel": channel,
        "metadata": metadata or {},
        "created_at": now,
        "updated_at": now,
        "resolved_at": None,
        "ai_response": response_text,
        "escalated": agent_result.get("needs_escalation", False),
        "escalation_reason": agent_result.get("escalation_reason"),
        "actions": agent_result.get("actions_taken", []),
    }
    
    _tickets[ticket_id] = ticket
    return ticket


def get_ticket(ticket_id: str) -> dict | None:
    """Get a ticket by ID."""
    return _tickets.get(ticket_id)


def list_tickets(
    status: str | None = None,
    priority: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """List tickets with optional filters. Returns (tickets, total_count)."""
    tickets = list(_tickets.values())
    
    if status:
        tickets = [t for t in tickets if t["status"] == status]
    if priority:
        tickets = [t for t in tickets if t["priority"] == priority]
    
    total = len(tickets)
    tickets.sort(key=lambda t: t["created_at"], reverse=True)
    
    return tickets[offset:offset + limit], total
