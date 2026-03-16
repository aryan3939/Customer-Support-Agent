"""
Agent Tools — LangChain @tool-wrapped functions for LLM tool selection.

WHY THIS FILE EXISTS:
---------------------
This is what makes the agent AGENTIC. Instead of hardcoding a fixed
pipeline (classify → search_kb → respond), we give the LLM a TOOLBOX
and let it CHOOSE which tools to call based on the customer's message.

Example:
    Customer: "Where is my order #12345?"
    LLM thinks: "I should check the order status" → calls check_order_status
    
    Customer: "I need a refund"
    LLM thinks: "I should search the refund policy AND check their account"
    → calls search_knowledge_base, then lookup_customer_info

HOW IT WORKS:
-------------
    1. Tools are defined with @tool decorator (LangChain standard)
    2. Each tool has a name, description, and typed arguments
    3. The LLM reads the descriptions to decide which tools are relevant
    4. LangGraph's ToolNode automatically executes the selected tools
    5. Results flow back to the LLM for reasoning/response generation
"""

import json
from langchain_core.tools import tool

from src.services.embedding_service import embedding_service
from src.utils.logging import get_logger

logger = get_logger(__name__)


# =============================================================================
# Knowledge Base Search Tool (wraps knowledge_base.py)
# =============================================================================

@tool
async def search_knowledge_base(query: str) -> str:
    """Search the knowledge base for relevant support articles.
    
    Use this tool when the customer asks about:
    - How to do something (password reset, account setup, 2FA)
    - Product features, pricing, or subscription plans
    - Policies (refunds, shipping, billing)
    - Troubleshooting steps for technical issues
    - General help or FAQ-type questions
    
    Args:
        query: The search query based on the customer's question.
    """
    from src.tools.knowledge_base import _search_pgvector, _search_keyword_fallback
    
    logger.info("tool_called", tool="search_knowledge_base", query=query[:100])
    
    try:
        results = await _search_pgvector(query, top_k=3)
        if not results:
            results = _search_keyword_fallback(query, top_k=3)
    except Exception:
        results = _search_keyword_fallback(query, top_k=3)
    
    if not results:
        return "No relevant knowledge base articles found."
    
    formatted = []
    for r in results:
        formatted.append(
            f"📄 {r['article_title']} (relevance: {r.get('relevance_score', 0):.2f})\n"
            f"{r['chunk_text']}"
        )
    
    return "\n\n---\n\n".join(formatted)


# =============================================================================
# Order Status Tool (wraps external_apis.py)
# =============================================================================

@tool
async def check_order_status(order_id: str) -> str:
    """Check the status of a customer's order by order ID.
    
    Use this tool when the customer asks about:
    - Where is my order / package
    - Order tracking or delivery status
    - Shipping updates or estimated delivery date
    - Whether an order has been shipped
    
    Args:
        order_id: The order ID to look up (e.g., "12345", "ORD-789").
    """
    from src.tools.external_apis import check_order_status as _check_order
    
    logger.info("tool_called", tool="check_order_status", order_id=order_id)
    
    result = await _check_order(order_id)
    
    return (
        f"Order {result['order_id']}:\n"
        f"  Status: {result['status']}\n"
        f"  Carrier: {result['carrier']}\n"
        f"  Tracking: {result['tracking_number']}\n"
        f"  Estimated delivery: {result['estimated_delivery']}"
    )


# =============================================================================
# Refund Request Tool (wraps external_apis.py)
# =============================================================================

@tool
async def create_refund_request(
    customer_email: str,
    amount: float,
    reason: str,
) -> str:
    """Initiate a refund request for a customer.
    
    Use this tool when the customer:
    - Explicitly requests a refund
    - Has been overcharged or double-charged
    - Is eligible for a refund per our policy (within 30 days)
    
    Do NOT use this tool if you're just explaining the refund policy.
    Only call when the customer has confirmed they want a refund.
    
    Args:
        customer_email: The customer's email address.
        amount: The refund amount in USD.
        reason: Brief reason for the refund.
    """
    from src.tools.external_apis import create_refund_request as _create_refund
    
    logger.info("tool_called", tool="create_refund_request", email=customer_email)
    
    result = await _create_refund(customer_email, amount, reason)
    
    return (
        f"Refund initiated:\n"
        f"  Refund ID: {result['refund_id']}\n"
        f"  Amount: ${result['amount']:.2f} {result['currency']}\n"
        f"  Status: {result['status']}\n"
        f"  Processing time: {result['estimated_processing_days']} business days"
    )


# =============================================================================
# Password Reset Tool (wraps external_apis.py)
# =============================================================================

@tool
async def reset_customer_password(email: str) -> str:
    """Trigger a password reset email for the customer.
    
    Use this tool when the customer:
    - Can't log in / forgot their password
    - Explicitly asks to reset their password
    - Is locked out of their account
    
    This sends a reset link to their registered email address.
    
    Args:
        email: The customer's email address.
    """
    from src.tools.external_apis import reset_customer_password as _reset_pw
    
    logger.info("tool_called", tool="reset_customer_password", email=email)
    
    result = await _reset_pw(email)
    
    return (
        f"Password reset email sent:\n"
        f"  Email: {result['email']}\n"
        f"  Link valid for: {result['expires_in_minutes']} minutes\n"
        f"  Status: {result['status']}"
    )


# =============================================================================
# Customer Info Lookup Tool (wraps customer_service.py)
# =============================================================================

@tool
async def lookup_customer_info(email: str) -> str:
    """Look up a customer's account information and history.
    
    Use this tool when you need to:
    - Check what plan/tier the customer is on
    - See how many previous tickets they've had
    - Understand their account history for context
    - Personalize the response based on their account
    
    Args:
        email: The customer's email address.
    """
    from src.tools.customer_service import get_customer_info
    
    logger.info("tool_called", tool="lookup_customer_info", email=email)
    
    info = await get_customer_info(email)
    
    if not info:
        return f"No account information found for {email}. Treating as a new customer."
    
    parts = [
        f"Customer: {info.get('name', 'Unknown')}",
        f"Plan: {info.get('plan', 'free')}",
        f"Total tickets: {info.get('total_tickets', 0)}",
        f"Account age: {info.get('account_age_days', 0)} days",
    ]
    
    recent = info.get("recent_tickets", [])
    if recent:
        parts.append("Recent tickets:")
        for t in recent[:3]:
            parts.append(f"  - {t.get('subject', '')} [{t.get('status', '')}]")
    
    return "\n".join(parts)


# =============================================================================
# Bug Report Tool (wraps external_apis.py)
# =============================================================================

@tool
async def create_bug_report(
    title: str,
    description: str,
    reporter_email: str,
    priority: str = "medium",
) -> str:
    """File an internal bug report for a technical issue.
    
    Use this tool when the customer reports:
    - A software bug or error they encountered
    - Something that is broken or not working as expected
    - A reproducible technical issue
    
    This creates a ticket in the engineering team's issue tracker.
    
    Args:
        title: Brief title describing the bug.
        description: Detailed description of the issue.
        reporter_email: The customer's email address.
        priority: Bug priority — "low", "medium", "high", or "urgent".
    """
    from src.tools.external_apis import create_bug_report as _create_bug
    
    logger.info("tool_called", tool="create_bug_report", title=title)
    
    result = await _create_bug(title, description, reporter_email, priority)
    
    return (
        f"Bug report created:\n"
        f"  Bug ID: {result['bug_id']}\n"
        f"  Title: {result['title']}\n"
        f"  Priority: {result['priority']}\n"
        f"  Status: {result['status']}\n"
        f"  Tracking URL: {result['url']}"
    )


# =============================================================================
# Tool Registry — all tools the agent can use
# =============================================================================

ALL_TOOLS = [
    search_knowledge_base,
    check_order_status,
    create_refund_request,
    reset_customer_password,
    lookup_customer_info,
    create_bug_report,
]
