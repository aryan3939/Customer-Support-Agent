"""
Webhook Routes — incoming integrations (e.g., email intake).

Webhooks let external services push data INTO our system:
    - Email provider → new support email → creates a ticket
    - Chat widget → new chat message → creates a ticket
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas.ticket import CreateTicketRequest
from src.api.routes.tickets import create_ticket
from src.db.session import get_db_session
from src.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/webhooks", tags=["Webhooks"])


@router.post(
    "/email",
    summary="Email intake webhook",
    description="Receives incoming support emails and creates tickets automatically.",
)
async def email_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Process an incoming email and create a support ticket.
    
    In production, this would be called by an email service
    (e.g., SendGrid Inbound Parse, AWS SES).
    """
    body = await request.json()
    
    logger.info("email_webhook_received", from_email=body.get("from", ""))
    
    # Map email fields to ticket fields
    ticket_request = CreateTicketRequest(
        customer_email=body.get("from", "unknown@example.com"),
        subject=body.get("subject", "Email Support Request"),
        message=body.get("body", body.get("text", "No message body")),
        channel="email",
        metadata={
            "email_id": body.get("message_id", ""),
            "headers": body.get("headers", {}),
        },
    )
    
    # Reuse the ticket creation endpoint (now DB-backed)
    return await create_ticket(ticket_request, db=db)
