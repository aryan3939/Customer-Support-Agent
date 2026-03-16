"""
Ticket API Routes — REST endpoints for ticket management.

ENDPOINTS:
----------
    POST   /api/v1/tickets              → Create ticket + get AI response
    GET    /api/v1/tickets              → List tickets with filters
    GET    /api/v1/tickets/{id}         → Get ticket details
    POST   /api/v1/tickets/{id}/messages → Add follow-up message
    PATCH  /api/v1/tickets/{id}/status  → Update ticket status
    PATCH  /api/v1/tickets/{id}/resolve → Resolve a ticket
    GET    /api/v1/tickets/{id}/actions → Get audit trail

All routes are protected by Supabase JWT authentication.
All routes persist to Supabase via SQLAlchemy async sessions.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps.auth import CurrentUser, get_current_user

from src.agents.graph import process_ticket
from src.api.schemas.ticket import (
    AddMessageRequest,
    CreateTicketRequest,
    CreateTicketResponse,
    TicketDetailResponse,
    TicketListResponse,
    TicketResponse,
    UpdateTicketStatusRequest,
    AgentInfo,
    ActionResponse,
    MessageResponse,
)
from src.db.session import get_db_session
from src.db.repositories.customer_repo import get_or_create_customer
from src.db.repositories.ticket_repo import (
    AI_AGENT_UUID,
    get_or_create_ai_agent,
    create_ticket as repo_create_ticket,
    get_ticket_by_id,
    list_tickets as repo_list_tickets,
    update_ticket_status as repo_update_status,
    add_message as repo_add_message,
    add_agent_action,
    get_actions_for_ticket,
    get_messages_for_ticket,
)
from src.utils.logging import get_logger

logger = get_logger(__name__)


# =============================================================================
# Router Setup
# =============================================================================

router = APIRouter(
    prefix="/api/v1/tickets",
    tags=["Tickets"],
)

# Default AI agent info for API responses
AI_AGENT = AgentInfo(
    id=str(AI_AGENT_UUID),
    name="Support AI",
    is_ai=True,
)


# =============================================================================
# POST /api/v1/tickets — Create a new ticket
# =============================================================================

@router.post(
    "",
    response_model=CreateTicketResponse,
    status_code=201,
    summary="Create a support ticket",
    description=(
        "Creates a new support ticket and processes it through the AI agent. "
        "Returns the AI-generated response, classification, and metadata."
    ),
)
async def create_ticket(
    request: CreateTicketRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Create a new support ticket → AI processes it → persisted to Supabase.
    """
    now = datetime.now(timezone.utc)
    
    # 1. Get or create customer
    customer, _ = await get_or_create_customer(
        db, email=request.customer_email, name=request.customer_email.split("@")[0],
    )
    
    # 2. Ensure AI agent exists in DB
    ai_agent = await get_or_create_ai_agent(db)
    
    # 3. Create ticket in DB (initial status = "new")
    ticket = await repo_create_ticket(
        db,
        customer_id=customer.id,
        subject=request.subject,
        status="new",
    )
    ticket_id = str(ticket.id)
    
    logger.info(
        "creating_ticket",
        ticket_id=ticket_id,
        customer_email=request.customer_email,
        subject=request.subject,
        channel=request.channel,
    )
    
    # 4. Store the customer's initial message
    await repo_add_message(
        db, ticket_id=ticket.id,
        sender_type="customer", content=request.message,
        metadata=request.metadata,
    )

    # 5. Run the AI agent workflow
    try:
        agent_result = await process_ticket(
            ticket_id=ticket_id,
            customer_email=request.customer_email,
            subject=request.subject,
            message=request.message,
            channel=request.channel,
        )
    except Exception as e:
        logger.error("agent_processing_failed", ticket_id=ticket_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"AI agent failed to process ticket: {str(e)}",
        )
    
    # 6. Update ticket with AI results
    status = "escalated" if agent_result.get("needs_escalation") else "open"
    response_text = agent_result.get("final_response") or agent_result.get("draft_response", "")
    
    ticket.status = status
    ticket.priority = agent_result.get("priority", "medium")
    ticket.category = agent_result.get("category")
    ticket.assigned_agent_id = ai_agent.id
    ticket.ai_context = {
        "intent": agent_result.get("intent"),
        "confidence": agent_result.get("confidence"),
        "sentiment": agent_result.get("sentiment"),
        "kb_results_count": len(agent_result.get("kb_results", [])),
    }
    ticket.updated_at = now
    
    # 7. Store AI response as a message
    await repo_add_message(
        db, ticket_id=ticket.id,
        sender_type="ai_agent", content=response_text,
    )
    
    # 8. Store all agent actions in the audit trail
    for action in agent_result.get("actions_taken", []):
        await add_agent_action(
            db,
            ticket_id=ticket.id,
            action_type=action.get("action_type", "unknown"),
            action_data=action.get("action_data", {}),
            reasoning=action.get("reasoning", ""),
            outcome=action.get("outcome", ""),
            agent_id=ai_agent.id,
        )
    
    # Flush all changes (commit happens in get_db_session context manager)
    await db.flush()
    
    logger.info(
        "ticket_created",
        ticket_id=ticket_id,
        status=status,
        priority=agent_result.get("priority"),
        escalated=agent_result.get("needs_escalation", False),
    )
    
    return CreateTicketResponse(
        id=ticket_id,
        status=status,
        priority=agent_result.get("priority", "medium"),
        category=agent_result.get("category"),
        sentiment=agent_result.get("sentiment"),
        assigned_to=AI_AGENT,
        initial_response=response_text,
        escalated=agent_result.get("needs_escalation", False),
        escalation_reason=agent_result.get("escalation_reason"),
        created_at=now,
    )


# =============================================================================
# GET /api/v1/tickets — List tickets
# =============================================================================

@router.get(
    "",
    response_model=TicketListResponse,
    summary="List support tickets",
    description="Returns a paginated list of tickets, optionally filtered.",
)
async def list_tickets(
    status: str | None = Query(None, description="Filter by status"),
    priority: str | None = Query(None, description="Filter by priority"),
    category: str | None = Query(None, description="Filter by category"),
    customer_email: str | None = Query(None, description="Filter by email"),
    limit: int = Query(20, ge=1, le=100, description="Results per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """List all tickets with optional filtering and pagination."""
    # Customers only see their own tickets; admins see everything
    if current_user.role != "admin":
        customer_email = current_user.email
    
    tickets, total = await repo_list_tickets(
        db,
        status=status,
        priority=priority,
        category=category,
        customer_email=customer_email,
        limit=limit,
        offset=offset,
    )
    
    return TicketListResponse(
        tickets=[
            TicketResponse(
                id=str(t.id),
                customer_email=t.customer.email if t.customer else "unknown",
                subject=t.subject,
                status=t.status,
                priority=t.priority,
                category=t.category,
                sentiment=t.ai_context.get("sentiment") if t.ai_context else None,
                assigned_to=AI_AGENT if t.assigned_agent_id else None,
                created_at=t.created_at,
                updated_at=t.updated_at,
                resolved_at=t.resolved_at,
            )
            for t in tickets
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


# =============================================================================
# GET /api/v1/tickets/{id} — Get ticket details
# =============================================================================

@router.get(
    "/{ticket_id}",
    response_model=TicketDetailResponse,
    summary="Get ticket details",
    description="Returns a ticket with its full message thread and action audit trail.",
)
async def get_ticket(
    ticket_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Get detailed ticket info including messages and actions."""
    
    try:
        tid = uuid.UUID(ticket_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ticket ID format")
    
    ticket = await get_ticket_by_id(db, tid)
    if not ticket:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")
    
    # Customers can only view their own tickets
    if current_user.role != "admin" and ticket.customer and ticket.customer.email != current_user.email:
        raise HTTPException(status_code=403, detail="You can only view your own tickets")
    
    messages = await get_messages_for_ticket(db, tid)
    actions = await get_actions_for_ticket(db, tid)
    
    return TicketDetailResponse(
        id=str(ticket.id),
        customer_email=ticket.customer.email if ticket.customer else "unknown",
        subject=ticket.subject,
        status=ticket.status,
        priority=ticket.priority,
        category=ticket.category,
        sentiment=ticket.ai_context.get("sentiment") if ticket.ai_context else None,
        assigned_to=AI_AGENT if ticket.assigned_agent_id else None,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        resolved_at=ticket.resolved_at,
        messages=[
            MessageResponse(
                id=str(m.id),
                ticket_id=str(m.ticket_id),
                sender_type=m.sender_type,
                content=m.content,
                created_at=m.created_at,
                metadata=m.metadata_ or {},
            )
            for m in messages
        ],
        actions=[
            ActionResponse(
                action_type=a.action_type,
                action_data=a.action_data or {},
                outcome=a.outcome,
                reasoning=a.reasoning.get("thought", "") if isinstance(a.reasoning, dict) else a.reasoning,
                created_at=a.created_at,
            )
            for a in actions
        ],
        ai_context=ticket.ai_context or {},
    )


# =============================================================================
# POST /api/v1/tickets/{id}/messages — Add a message (follow-up)
# =============================================================================

@router.post(
    "/{ticket_id}/messages",
    response_model=MessageResponse,
    status_code=201,
    summary="Add a message to a ticket",
    description="Send a follow-up message on an existing ticket.",
)
async def add_message(
    ticket_id: str,
    request: AddMessageRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Add a follow-up message to an existing ticket."""
    try:
        tid = uuid.UUID(ticket_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ticket ID format")
    
    ticket = await get_ticket_by_id(db, tid)
    if not ticket:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")
    
    # Store the new message
    message = await repo_add_message(
        db, ticket_id=tid,
        sender_type=request.sender_type,
        content=request.content,
    )
    ticket.updated_at = datetime.now(timezone.utc)
    
    # If customer sent a follow-up, process through AI agent again
    if request.sender_type == "customer":
        try:
            # Ensure AI agent exists for the audit trail
            ai_agent = await get_or_create_ai_agent(db)
            
            agent_result = await process_ticket(
                ticket_id=ticket_id,
                customer_email=ticket.customer.email if ticket.customer else "",
                subject=ticket.subject,
                message=request.content,
                channel="web",
            )
            
            ai_response = agent_result.get("final_response") or agent_result.get("draft_response", "")
            
            await repo_add_message(
                db, ticket_id=tid,
                sender_type="ai_agent",
                content=ai_response,
            )
            
            # Store new actions
            for action in agent_result.get("actions_taken", []):
                await add_agent_action(
                    db,
                    ticket_id=tid,
                    action_type=action.get("action_type", "unknown"),
                    action_data=action.get("action_data", {}),
                    reasoning=action.get("reasoning", ""),
                    outcome=action.get("outcome", ""),
                    agent_id=ai_agent.id,
                )
            
        except Exception as e:
            logger.error("follow_up_processing_failed", error=str(e))
    
    await db.flush()
    
    return MessageResponse(
        id=str(message.id),
        ticket_id=ticket_id,
        sender_type=message.sender_type,
        content=message.content,
        created_at=message.created_at,
        metadata=message.metadata_ or {},
    )


# =============================================================================
# PATCH /api/v1/tickets/{id}/status — Update status
# =============================================================================

@router.patch(
    "/{ticket_id}/status",
    response_model=TicketResponse,
    summary="Update ticket status",
    description="Change the status of a ticket (e.g., resolve, close).",
)
async def update_ticket_status(
    ticket_id: str,
    request: UpdateTicketStatusRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Update a ticket's status."""
    try:
        tid = uuid.UUID(ticket_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ticket ID format")
    
    ticket = await repo_update_status(db, tid, request.status)
    if not ticket:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")
    
    logger.info(
        "ticket_status_updated",
        ticket_id=ticket_id,
        new_status=request.status,
    )
    
    return TicketResponse(
        id=str(ticket.id),
        customer_email=ticket.customer.email if ticket.customer else "unknown",
        subject=ticket.subject,
        status=ticket.status,
        priority=ticket.priority,
        category=ticket.category,
        sentiment=ticket.ai_context.get("sentiment") if ticket.ai_context else None,
        assigned_to=AI_AGENT if ticket.assigned_agent_id else None,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        resolved_at=ticket.resolved_at,
    )


# =============================================================================
# PATCH /api/v1/tickets/{id}/resolve — Resolve a ticket
# =============================================================================

class ResolveTicketRequest(BaseModel):
    resolved_by: str = "customer"  # "customer" or "admin"

@router.patch(
    "/{ticket_id}/resolve",
    response_model=TicketResponse,
    summary="Resolve a ticket",
    description="Mark a ticket as resolved. Customers can resolve their own tickets, admins can resolve any.",
)
async def resolve_ticket(
    ticket_id: str,
    request: ResolveTicketRequest | None = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Resolve a ticket."""
    try:
        tid = uuid.UUID(ticket_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ticket ID format")
    
    ticket = await get_ticket_by_id(db, tid)
    if not ticket:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")
    
    # Determine who is resolving
    resolved_by = "admin" if current_user.role == "admin" else "customer"
    if request and request.resolved_by:
        resolved_by = request.resolved_by
    
    # Customers can only resolve their own tickets
    if current_user.role != "admin" and ticket.customer and ticket.customer.email != current_user.email:
        raise HTTPException(status_code=403, detail="You can only resolve your own tickets")
    
    now = datetime.now(timezone.utc)
    ticket.status = "resolved"
    ticket.resolved_at = now
    ticket.resolved_by = resolved_by
    ticket.updated_at = now
    await db.flush()
    
    # Record in audit trail
    await add_agent_action(
        db,
        ticket_id=tid,
        agent_id=AI_AGENT_UUID,
        action_type="resolve_ticket",
        action_data={"resolved_by": resolved_by, "resolved_by_user": current_user.email},
        reasoning=f"Ticket resolved by {resolved_by}",
        outcome="success",
    )
    
    logger.info(
        "ticket_resolved",
        ticket_id=ticket_id,
        resolved_by=resolved_by,
        user=current_user.email,
    )
    
    return TicketResponse(
        id=str(ticket.id),
        customer_email=ticket.customer.email if ticket.customer else "unknown",
        subject=ticket.subject,
        status=ticket.status,
        priority=ticket.priority,
        category=ticket.category,
        sentiment=ticket.ai_context.get("sentiment") if ticket.ai_context else None,
        assigned_to=AI_AGENT if ticket.assigned_agent_id else None,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        resolved_at=ticket.resolved_at,
    )


# =============================================================================
# GET /api/v1/tickets/{id}/actions — Get audit trail
# =============================================================================

@router.get(
    "/{ticket_id}/actions",
    summary="Get ticket audit trail",
    description="Returns all AI actions taken on this ticket for transparency.",
)
async def get_ticket_actions(
    ticket_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Get the complete audit trail for a ticket."""
    try:
        tid = uuid.UUID(ticket_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ticket ID format")
    
    ticket = await get_ticket_by_id(db, tid)
    if not ticket:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")
    
    actions = await get_actions_for_ticket(db, tid)
    
    return {
        "ticket_id": ticket_id,
        "actions": [
            {
                "action_type": a.action_type,
                "action_data": a.action_data,
                "reasoning": a.reasoning,
                "outcome": a.outcome,
                "created_at": a.created_at,
            }
            for a in actions
        ],
        "total": len(actions),
    }
