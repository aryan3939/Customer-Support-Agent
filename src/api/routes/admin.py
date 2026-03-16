"""
Admin API Routes — admin-only endpoints for conversation management.

ENDPOINTS:
----------
    GET    /api/v1/admin/conversations              → List all conversations with filters
    GET    /api/v1/admin/conversations/{id}         → Get conversation details
    POST   /api/v1/admin/conversations/{id}/reply   → Reply as admin
    PATCH  /api/v1/admin/conversations/{id}/resolve → Resolve as admin

All routes require admin role (verified via Supabase JWT).
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.deps.auth import CurrentUser, require_admin
from src.api.schemas.ticket import (
    TicketResponse,
    TicketDetailResponse,
    MessageResponse,
    ActionResponse,
    AgentInfo,
)
from src.db.models import Ticket, Message, Customer
from src.db.session import get_db_session
from src.db.repositories.ticket_repo import (
    AI_AGENT_UUID,
    get_ticket_by_id,
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
    prefix="/api/v1/admin",
    tags=["Admin"],
)

# Default AI agent info for API responses
AI_AGENT = AgentInfo(
    id=str(AI_AGENT_UUID),
    name="Support AI",
    is_ai=True,
)


# =============================================================================
# Schemas
# =============================================================================

class AdminReplyRequest(BaseModel):
    content: str


class ConversationSummary(BaseModel):
    id: str
    customer_email: str
    subject: str
    status: str
    priority: str
    category: str | None = None
    sentiment: str | None = None
    resolved_by: str | None = None
    assigned_to: AgentInfo | None = None
    message_count: int = 0
    latest_message_preview: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    resolved_at: datetime | None = None


class ConversationListResponse(BaseModel):
    conversations: list[ConversationSummary]
    total: int
    limit: int
    offset: int


# =============================================================================
# GET /api/v1/admin/conversations — List all conversations with filters
# =============================================================================

@router.get(
    "/conversations",
    response_model=ConversationListResponse,
    summary="List all conversations (admin)",
    description="Returns a filtered, paginated list of all conversations.",
)
async def list_conversations(
    status: str | None = Query(None, description="Filter by status"),
    priority: str | None = Query(None, description="Filter by priority"),
    category: str | None = Query(None, description="Filter by category"),
    customer_email: str | None = Query(None, description="Filter by customer email (partial match)"),
    ticket_id: str | None = Query(None, description="Filter by exact ticket ID"),
    date_from: str | None = Query(None, description="Filter tickets created after (ISO datetime)"),
    date_to: str | None = Query(None, description="Filter tickets created before (ISO datetime)"),
    resolved_by: str | None = Query(None, description="Filter by who resolved (customer/admin/ai_agent)"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order: asc or desc"),
    limit: int = Query(20, ge=1, le=100, description="Results per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    current_user: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
):
    """List all conversations with comprehensive filters — admin only."""
    
    query = (
        select(Ticket)
        .options(selectinload(Ticket.customer))
    )
    count_query = select(func.count(Ticket.id))
    
    # Apply filters
    if status:
        query = query.where(Ticket.status == status)
        count_query = count_query.where(Ticket.status == status)
    if priority:
        query = query.where(Ticket.priority == priority)
        count_query = count_query.where(Ticket.priority == priority)
    if category:
        query = query.where(Ticket.category == category)
        count_query = count_query.where(Ticket.category == category)
    if customer_email:
        query = query.join(Customer).where(Customer.email.ilike(f"%{customer_email}%"))
        count_query = count_query.join(Customer).where(Customer.email.ilike(f"%{customer_email}%"))
    if ticket_id:
        try:
            tid = uuid.UUID(ticket_id)
            query = query.where(Ticket.id == tid)
            count_query = count_query.where(Ticket.id == tid)
        except ValueError:
            pass  # Invalid UUID, just ignore filter
    if date_from:
        try:
            dt_from = datetime.fromisoformat(date_from)
            query = query.where(Ticket.created_at >= dt_from)
            count_query = count_query.where(Ticket.created_at >= dt_from)
        except ValueError:
            pass
    if date_to:
        try:
            dt_to = datetime.fromisoformat(date_to)
            query = query.where(Ticket.created_at <= dt_to)
            count_query = count_query.where(Ticket.created_at <= dt_to)
        except ValueError:
            pass
    if resolved_by:
        query = query.where(Ticket.resolved_by == resolved_by)
        count_query = count_query.where(Ticket.resolved_by == resolved_by)
    
    # Sorting
    sort_column = getattr(Ticket, sort_by, Ticket.created_at)
    if sort_order == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())
    
    # Pagination
    query = query.limit(limit).offset(offset)
    
    result = await db.execute(query)
    tickets = list(result.scalars().all())
    count_result = await db.execute(count_query)
    total = count_result.scalar_one()
    
    # Get message counts and latest message previews
    conversations = []
    for t in tickets:
        # Get message count
        msg_count_result = await db.execute(
            select(func.count(Message.id)).where(Message.ticket_id == t.id)
        )
        msg_count = msg_count_result.scalar_one()
        
        # Get latest message preview
        latest_msg_result = await db.execute(
            select(Message.content)
            .where(Message.ticket_id == t.id)
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        latest_msg = latest_msg_result.scalar_one_or_none()
        preview = latest_msg[:120] + "..." if latest_msg and len(latest_msg) > 120 else latest_msg
        
        conversations.append(ConversationSummary(
            id=str(t.id),
            customer_email=t.customer.email if t.customer else "unknown",
            subject=t.subject,
            status=t.status,
            priority=t.priority,
            category=t.category,
            sentiment=t.ai_context.get("sentiment") if t.ai_context else None,
            resolved_by=t.resolved_by,
            assigned_to=AI_AGENT if t.assigned_agent_id else None,
            message_count=msg_count,
            latest_message_preview=preview,
            created_at=t.created_at,
            updated_at=t.updated_at,
            resolved_at=t.resolved_at,
        ))
    
    return ConversationListResponse(
        conversations=conversations,
        total=total,
        limit=limit,
        offset=offset,
    )


# =============================================================================
# GET /api/v1/admin/conversations/{id} — Get conversation details
# =============================================================================

@router.get(
    "/conversations/{ticket_id}",
    response_model=TicketDetailResponse,
    summary="Get conversation details (admin)",
    description="Returns a conversation with its full message thread and action audit trail.",
)
async def get_conversation(
    ticket_id: str,
    current_user: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
):
    """Get detailed conversation info — admin only."""
    try:
        tid = uuid.UUID(ticket_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ticket ID format")
    
    ticket = await get_ticket_by_id(db, tid)
    if not ticket:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")
    
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
# POST /api/v1/admin/conversations/{id}/reply — Reply as admin
# =============================================================================

@router.post(
    "/conversations/{ticket_id}/reply",
    response_model=MessageResponse,
    status_code=201,
    summary="Reply to a conversation (admin)",
    description="Send a reply as an admin/human agent.",
)
async def admin_reply(
    ticket_id: str,
    request: AdminReplyRequest,
    current_user: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
):
    """Reply to a conversation as a human agent — admin only."""
    try:
        tid = uuid.UUID(ticket_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ticket ID format")
    
    ticket = await get_ticket_by_id(db, tid)
    if not ticket:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")
    
    # Store the admin's message
    message = await repo_add_message(
        db, ticket_id=tid,
        sender_type="human_agent",
        content=request.content,
        metadata={"admin_email": current_user.email},
    )
    
    # Update ticket
    ticket.updated_at = datetime.now(timezone.utc)
    if ticket.status == "new":
        ticket.status = "open"
    
    # Record in audit trail
    await add_agent_action(
        db,
        ticket_id=tid,
        agent_id=AI_AGENT_UUID,
        action_type="admin_reply",
        action_data={
            "message_length": len(request.content),
            "admin_email": current_user.email,
        },
        reasoning=f"Admin {current_user.email} replied to ticket",
        outcome="success",
    )
    
    await db.flush()
    
    logger.info(
        "admin_reply_sent",
        ticket_id=ticket_id,
        admin=current_user.email,
    )
    
    return MessageResponse(
        id=str(message.id),
        ticket_id=ticket_id,
        sender_type=message.sender_type,
        content=message.content,
        created_at=message.created_at,
        metadata=message.metadata_ or {},
    )


# =============================================================================
# PATCH /api/v1/admin/conversations/{id}/resolve — Resolve as admin
# =============================================================================

@router.patch(
    "/conversations/{ticket_id}/resolve",
    response_model=TicketResponse,
    summary="Resolve a conversation (admin)",
    description="Mark a conversation as resolved by admin.",
)
async def admin_resolve(
    ticket_id: str,
    current_user: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
):
    """Resolve a conversation — admin only."""
    try:
        tid = uuid.UUID(ticket_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ticket ID format")
    
    ticket = await get_ticket_by_id(db, tid)
    if not ticket:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")
    
    now = datetime.now(timezone.utc)
    ticket.status = "resolved"
    ticket.resolved_at = now
    ticket.resolved_by = "admin"
    ticket.updated_at = now
    
    # Record in audit trail
    await add_agent_action(
        db,
        ticket_id=tid,
        agent_id=AI_AGENT_UUID,
        action_type="resolve_ticket",
        action_data={"resolved_by": "admin", "admin_email": current_user.email},
        reasoning=f"Ticket resolved by admin {current_user.email}",
        outcome="success",
    )
    
    await db.flush()
    
    logger.info(
        "admin_resolved_ticket",
        ticket_id=ticket_id,
        admin=current_user.email,
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
