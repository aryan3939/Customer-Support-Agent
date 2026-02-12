"""
Customer Service Tool — fetch customer info for agent context.

Used by the AI agent to look up customer details before responding.
In production: queries the database. For now: mock data for testing.
"""

from src.utils.logging import get_logger

logger = get_logger(__name__)

# Mock customer data (replaced by real DB queries later)
_MOCK_CUSTOMERS = {
    "alice@example.com": {
        "name": "Alice Johnson",
        "plan": "pro",
        "total_tickets": 3,
        "account_age_days": 180,
        "recent_tickets": [
            {"subject": "Billing question", "status": "resolved"},
        ],
    },
    "bob@example.com": {
        "name": "Bob Smith",
        "plan": "enterprise",
        "total_tickets": 7,
        "account_age_days": 365,
        "recent_tickets": [
            {"subject": "API rate limits", "status": "resolved"},
            {"subject": "Feature request: SSO", "status": "closed"},
        ],
    },
}


async def get_customer_info(email: str) -> dict:
    """
    Fetch customer profile and history by email.
    
    Returns:
        Dict with customer details, plan, ticket history.
        Empty dict if customer not found (treated as new customer).
    """
    customer = _MOCK_CUSTOMERS.get(email, {})
    
    if customer:
        logger.info("customer_found", email=email, plan=customer.get("plan"))
    else:
        logger.info("new_customer", email=email)
    
    return customer
