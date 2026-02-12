"""
External API Tools — simulated integrations with third-party services.

In a real product, these would call actual APIs (Stripe, JIRA, etc.).
For this project, they return mock responses to demonstrate the pattern.

WHY MOCK APIS?
--------------
AI engineers need to know HOW to integrate tools, not necessarily
have live accounts. These mocks show the correct structure:
    - Input validation
    - Error handling
    - Response formatting
    - Audit-friendly return values
"""

import uuid
from datetime import datetime, timezone

from src.utils.logging import get_logger

logger = get_logger(__name__)


async def check_order_status(order_id: str) -> dict:
    """
    Check order status from the order management system.
    Simulates calling an external order API.
    """
    logger.info("checking_order_status", order_id=order_id)
    
    # Mock response
    return {
        "order_id": order_id,
        "status": "shipped",
        "tracking_number": "1Z999AA10123456784",
        "estimated_delivery": "2025-02-15",
        "carrier": "UPS",
    }


async def create_refund_request(
    customer_email: str,
    amount: float,
    reason: str,
    invoice_id: str = "",
) -> dict:
    """
    Initiate a refund request via the payment system.
    Simulates calling Stripe/PayPal refund API.
    """
    refund_id = f"ref_{uuid.uuid4().hex[:12]}"
    
    logger.info(
        "refund_requested",
        refund_id=refund_id,
        customer_email=customer_email,
        amount=amount,
    )
    
    return {
        "refund_id": refund_id,
        "status": "pending",
        "amount": amount,
        "currency": "USD",
        "estimated_processing_days": 5,
        "message": f"Refund of ${amount:.2f} initiated. Processing in 5-7 business days.",
    }


async def reset_customer_password(email: str) -> dict:
    """
    Trigger a password reset email via the auth service.
    Simulates calling an auth/identity provider API.
    """
    logger.info("password_reset_triggered", email=email)
    
    return {
        "status": "sent",
        "email": email,
        "expires_in_minutes": 30,
        "message": f"Password reset link sent to {email}. Valid for 30 minutes.",
    }


async def create_bug_report(
    title: str,
    description: str,
    reporter_email: str,
    priority: str = "medium",
) -> dict:
    """
    Create an internal bug ticket in the issue tracker.
    Simulates calling JIRA/Linear/GitHub Issues API.
    """
    bug_id = f"BUG-{uuid.uuid4().hex[:6].upper()}"
    
    logger.info("bug_report_created", bug_id=bug_id, title=title)
    
    return {
        "bug_id": bug_id,
        "title": title,
        "status": "open",
        "priority": priority,
        "url": f"https://issues.example.com/{bug_id}",
        "message": f"Bug report {bug_id} created and assigned to engineering team.",
    }
