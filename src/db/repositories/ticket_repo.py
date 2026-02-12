"""
Ticket Repository — database queries for tickets.

WHY A REPOSITORY LAYER?
-----------------------
Repositories isolate database queries from business logic.

    Route → Service → Repository → Database
    
This means if you switch databases (e.g., Supabase → DynamoDB),
you only change the repository, nothing else.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Ticket, Message, AgentAction, Customer, Agent
from src.utils.logging import get_logger

logger = get_logger(__name__)


# =============================================================================
# AI Agent — get or create the system AI agent row
# =============================================================================

# Fixed UUID so all AI actions map to the same agent row
AI_AGENT_UUID = uuid.UUID("00000000-0000-0000-0000-000000000001")


async def get_or_create_ai_agent(db: AsyncSession) -> Agent:
    """
    Get or create the system AI agent in the database.
    Returns the same Agent row every time (idempotent).
    """
    agent = await db.get(Agent, AI_AGENT_UUID)
    if agent:
        return agent

    agent = Agent(
        id=AI_AGENT_UUID,
        name="Support AI",
        email="ai-agent@system.internal",
        role="ai_support",
        is_ai=True,
        is_active=True,
    )
    db.add(agent)
    await db.flush()
    logger.info("ai_agent_created", id=str(agent.id))
    return agent


# =============================================================================
# Ticket CRUD
# =============================================================================

async def create_ticket(
    db: AsyncSession,
    customer_id: uuid.UUID,
    subject: str,
    priority: str = "medium",
    category: str | None = None,
    status: str = "new",
    ai_context: dict | None = None,
) -> Ticket:
    """Create a new ticket in the database."""
    ticket = Ticket(
        customer_id=customer_id,
        subject=subject,
        priority=priority,
        category=category,
        status=status,
        ai_context=ai_context or {},
    )
    db.add(ticket)
    await db.flush()
    
    logger.info("ticket_created_in_db", ticket_id=str(ticket.id))
    return ticket


async def get_ticket_by_id(
    db: AsyncSession,
    ticket_id: uuid.UUID,
) -> Ticket | None:
    """Fetch a ticket by its ID with related data."""
    result = await db.execute(
        select(Ticket)
        .options(selectinload(Ticket.customer))
        .where(Ticket.id == ticket_id)
    )
    return result.scalar_one_or_none()


async def list_tickets(
    db: AsyncSession,
    status: str | None = None,
    priority: str | None = None,
    category: str | None = None,
    customer_email: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[Ticket], int]:
    """List tickets with optional filters and pagination."""
    query = select(Ticket).options(selectinload(Ticket.customer))
    count_query = select(func.count(Ticket.id))
    
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
        query = query.join(Customer).where(Customer.email == customer_email)
        count_query = count_query.join(Customer).where(Customer.email == customer_email)
    
    query = query.order_by(Ticket.created_at.desc()).limit(limit).offset(offset)
    
    result = await db.execute(query)
    count_result = await db.execute(count_query)
    
    return list(result.scalars().all()), count_result.scalar_one()


async def update_ticket_status(
    db: AsyncSession,
    ticket_id: uuid.UUID,
    new_status: str,
) -> Ticket | None:
    """Update a ticket's status."""
    ticket = await get_ticket_by_id(db, ticket_id)
    if not ticket:
        return None
    
    ticket.status = new_status
    ticket.updated_at = datetime.now(timezone.utc)
    
    if new_status in ("resolved", "closed"):
        ticket.resolved_at = datetime.now(timezone.utc)
    
    await db.flush()
    return ticket


# =============================================================================
# Messages
# =============================================================================

async def add_message(
    db: AsyncSession,
    ticket_id: uuid.UUID,
    sender_type: str,
    content: str,
    metadata: dict | None = None,
) -> Message:
    """Add a message to a ticket."""
    message = Message(
        ticket_id=ticket_id,
        sender_type=sender_type,
        content=content,
        metadata_=metadata or {},
    )
    db.add(message)
    await db.flush()
    return message


# =============================================================================
# Agent Actions (Audit Trail)
# =============================================================================

async def add_agent_action(
    db: AsyncSession,
    ticket_id: uuid.UUID,
    action_type: str,
    action_data: dict | None = None,
    reasoning: str = "",
    outcome: str = "",
    agent_id: uuid.UUID | None = None,
) -> AgentAction:
    """Record an AI agent action for the audit trail."""
    action = AgentAction(
        ticket_id=ticket_id,
        agent_id=agent_id,
        action_type=action_type,
        action_data=action_data or {},
        reasoning={"thought": reasoning} if isinstance(reasoning, str) else reasoning,
        outcome=outcome,
    )
    db.add(action)
    await db.flush()
    return action


async def get_actions_for_ticket(
    db: AsyncSession,
    ticket_id: uuid.UUID,
) -> list[AgentAction]:
    """Get all agent actions for a ticket, ordered by time."""
    result = await db.execute(
        select(AgentAction)
        .where(AgentAction.ticket_id == ticket_id)
        .order_by(AgentAction.created_at)
    )
    return list(result.scalars().all())


async def get_messages_for_ticket(
    db: AsyncSession,
    ticket_id: uuid.UUID,
) -> list[Message]:
    """Get all messages for a ticket, ordered by time."""
    result = await db.execute(
        select(Message)
        .where(Message.ticket_id == ticket_id)
        .order_by(Message.created_at)
    )
    return list(result.scalars().all())
