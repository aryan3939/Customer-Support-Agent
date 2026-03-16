"""
Knowledge Base Search Tool — RAG search for relevant articles.

WHY THIS TOOL EXISTS:
---------------------
When a customer asks "How do I reset my password?", the AI needs 
FACTUAL, ACCURATE information — not hallucinated steps. This tool
searches our knowledge base for relevant articles and returns them
as context for the resolver node.

This is RAG (Retrieval Augmented Generation):
    1. Customer asks a question
    2. We RETRIEVE relevant KB articles (vector similarity search)
    3. We AUGMENT the LLM prompt with those articles
    4. The LLM GENERATES a response based on real data

Without RAG: LLM makes up answers (hallucination)
With RAG: LLM bases answers on real KB articles (grounded)

HOW IT WORKS:
-------------
    1. Takes the ticket's subject + message + intent
    2. Embeds the search query using sentence-transformers → 384-dim vector
    3. Queries pgvector for the closest KB chunk vectors (cosine similarity)
    4. Returns top-K matching article chunks as context
    
    "password reset" → embed → [0.03, -0.12, ...] → cosine search → 
    find "Password Reset Guide" chunk (similarity: 0.87) → return it

FALLBACK:
---------
    If the database is unavailable (e.g., local dev without DB), falls back
    to keyword-based search against a hardcoded article list. This ensures
    the agent always works, even without infrastructure.
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.state import TicketState
from src.services.embedding_service import embedding_service
from src.utils.logging import get_logger

logger = get_logger(__name__)


# =============================================================================
# pgvector Similarity Search (Primary — Production)
# =============================================================================

async def _search_pgvector(search_text: str, top_k: int = 3) -> list[dict]:
    """
    Search the knowledge base using pgvector cosine similarity.
    
    How it works:
        1. Embed the search query → 384-dim vector
        2. Use pgvector's <=> operator (cosine distance) to find closest chunks
        3. JOIN with knowledge_articles to get article title
        4. Return top-K results sorted by similarity
    
    The <=> operator computes cosine DISTANCE (not similarity):
        distance = 1 - cosine_similarity
        So distance 0.0 = perfect match, 2.0 = opposite
        We convert to similarity: similarity = 1 - distance
    
    Args:
        search_text: Combined ticket subject + message + intent
        top_k: Number of top results to return
    
    Returns:
        List of dicts with article_id, article_title, chunk_text, relevance_score
    """
    from src.db.session import async_session_factory
    
    # Step 1: Embed the search query
    query_vector = embedding_service.embed_text(search_text)
    
    # Step 2: Query pgvector for closest matches
    # The <=> operator computes cosine distance; we sort ascending (closest first)
    # and convert distance to similarity score for the result
    query = text("""
        SELECT 
            e.chunk_text,
            e.chunk_index,
            a.id AS article_id,
            a.title AS article_title,
            1 - (e.embedding <=> :query_vector::vector) AS similarity
        FROM kb_embeddings e
        JOIN knowledge_articles a ON e.article_id = a.id
        ORDER BY e.embedding <=> :query_vector::vector ASC
        LIMIT :top_k
    """)
    
    async with async_session_factory() as session:
        result = await session.execute(
            query,
            {
                "query_vector": str(query_vector),
                "top_k": top_k,
            },
        )
        rows = result.fetchall()
    
    # Step 3: Format results
    results = []
    for row in rows:
        results.append({
            "article_id": str(row.article_id),
            "article_title": row.article_title,
            "chunk_text": row.chunk_text,
            "relevance_score": round(float(row.similarity), 4),
        })
    
    return results


# =============================================================================
# Keyword Search Fallback (for when DB is unavailable)
# =============================================================================

# Hardcoded articles used as fallback when postgres/pgvector is not available.
# These are the same articles that get seeded into the DB by scripts/seed_kb.py.
FALLBACK_KB_ARTICLES = [
    {
        "article_id": "kb-001",
        "article_title": "Password Reset Guide",
        "chunk_text": (
            "To reset your password: 1) Go to the login page and click 'Forgot Password'. "
            "2) Enter your registered email address. 3) Check your email for a reset link "
            "(check spam folder too). 4) Click the link and set a new password. "
            "5) Password must be at least 8 characters with one number and one special character. "
            "If you don't receive the email within 5 minutes, try again or contact support. "
            "Note: Reset links expire after 24 hours for security."
        ),
        "keywords": ["password", "reset", "forgot", "login", "locked", "account access", "can't log in", "sign in"],
    },
    {
        "article_id": "kb-002",
        "article_title": "Two-Factor Authentication (2FA) Setup",
        "chunk_text": (
            "To enable 2FA: 1) Go to Account Settings → Security → Two-Factor Authentication. "
            "2) Choose your method: Authenticator App (recommended) or SMS. "
            "3) Scan the QR code with Google Authenticator, Authy, or Microsoft Authenticator. "
            "4) Enter the 6-digit verification code to confirm setup. "
            "5) Save the backup recovery codes in a safe place — you'll need these if you lose your phone. "
            "To disable 2FA: Go to Settings → Security → Disable 2FA (requires current password). "
            "If locked out of 2FA, contact support with your backup recovery code."
        ),
        "keywords": ["2fa", "two-factor", "authenticator", "verification", "security", "otp", "mfa", "backup code"],
    },
    {
        "article_id": "kb-010",
        "article_title": "Billing & Refund Policy",
        "chunk_text": (
            "Refund Policy: We offer full refunds within 30 days of purchase. "
            "After 30 days, we can offer prorated credit toward your account. "
            "To request a refund: 1) Go to Account Settings → Billing → View Invoices. "
            "2) Click 'Request Refund' on the relevant invoice. "
            "3) Provide a brief reason for the refund request. "
            "4) Refunds are processed within 5-7 business days to your original payment method. "
            "For overcharges or billing errors, contact us and we'll resolve it within 24 hours. "
            "Enterprise customers: contact your account manager for refund requests."
        ),
        "keywords": ["billing", "refund", "charge", "invoice", "payment", "money back", "overcharge", "credit"],
    },
    {
        "article_id": "kb-011",
        "article_title": "Subscription Plans & Pricing",
        "chunk_text": (
            "Our plans: "
            "FREE PLAN — Up to 3 users, 1GB storage, basic features, community support. "
            "PRO PLAN ($29/month billed monthly, $24/month billed annually) — Up to 25 users, "
            "50GB storage, advanced analytics, priority support, API access. "
            "ENTERPRISE PLAN (custom pricing) — Unlimited users, unlimited storage, dedicated "
            "account manager, SSO, custom integrations, 24/7 phone support, SLA guarantee. "
            "All plans include a 14-day free trial with no credit card required."
        ),
        "keywords": ["pricing", "plan", "subscription", "cost", "upgrade", "downgrade", "free", "pro", "enterprise", "trial"],
    },
    {
        "article_id": "kb-014",
        "article_title": "Billing Disputes & Unexpected Charges",
        "chunk_text": (
            "If you see an unexpected charge: 1) Check Billing → Invoice History for details. "
            "2) Common causes: plan auto-renewal, usage overage, add-on features, tax changes. "
            "3) If the charge is incorrect, contact billing support with your invoice number. "
            "We respond to billing disputes within 1 business day. "
            "For fraud/unauthorized charges: 1) Change your password immediately. "
            "2) Contact us at billing@example.com with 'URGENT' in the subject. "
            "3) We'll investigate and issue a refund within 48 hours if confirmed fraudulent."
        ),
        "keywords": ["dispute", "unexpected charge", "wrong charge", "fraud", "unauthorized", "double charge", "overcharge"],
    },
    {
        "article_id": "kb-020",
        "article_title": "General Troubleshooting Guide",
        "chunk_text": (
            "Common troubleshooting steps: 1) Clear browser cache and cookies. "
            "2) Try a different browser (Chrome, Firefox, Edge recommended). "
            "3) Disable browser extensions that might interfere. "
            "4) Check our status page at status.example.com for outages. "
            "5) Try incognito/private browsing mode. "
            "6) Ensure JavaScript is enabled in your browser settings. "
            "7) Check if your network/firewall is blocking our domain."
        ),
        "keywords": ["error", "bug", "broken", "not working", "crash", "slow", "issue", "problem", "troubleshoot", "fix"],
    },
    {
        "article_id": "kb-040",
        "article_title": "Shipping & Delivery Information",
        "chunk_text": (
            "Shipping options: "
            "Standard shipping: 5-7 business days ($5.99 or free over $50). "
            "Express shipping: 2-3 business days ($12.99). "
            "Overnight shipping: Next business day ($24.99). "
            "Track your order: Go to Orders → click your order → 'Track Package'. "
            "If your package hasn't arrived within the expected timeframe: "
            "1) Check the tracking status for updates. "
            "2) Verify the shipping address is correct. "
            "3) Contact us if tracking shows 'delivered' but you haven't received it."
        ),
        "keywords": ["shipping", "delivery", "order", "track", "package", "arrived", "transit", "carrier"],
    },
    {
        "article_id": "kb-050",
        "article_title": "Contact Us & Support Hours",
        "chunk_text": (
            "Support channels: "
            "Email: support@example.com (24/7, response within 4 hours). "
            "Live Chat: Available on our website Mon-Fri, 9 AM - 6 PM EST. "
            "Phone: +1-800-EXAMPLE (Mon-Fri, 9 AM - 5 PM EST, Enterprise only). "
            "Help Center: help.example.com for self-service articles. "
            "Average response times: Email 2-4 hours, Chat 5 minutes, Phone instant."
        ),
        "keywords": ["contact", "support", "help", "hours", "phone", "email", "chat", "reach", "talk"],
    },
]


def _search_keyword_fallback(search_text: str, top_k: int = 3) -> list[dict]:
    """
    Fallback keyword-based search when pgvector DB is unavailable.
    
    Scores articles by counting how many of their keywords appear
    in the search text. Simple but functional.
    """
    scored = []
    for article in FALLBACK_KB_ARTICLES:
        score = sum(1 for kw in article["keywords"] if kw in search_text)
        if score > 0:
            scored.append({
                "article_id": article["article_id"],
                "article_title": article["article_title"],
                "chunk_text": article["chunk_text"],
                "relevance_score": min(score / len(article["keywords"]), 1.0),
            })
    
    scored.sort(key=lambda x: x["relevance_score"], reverse=True)
    return scored[:top_k]


# =============================================================================
# LangGraph Node Function (Entry Point)
# =============================================================================

async def search_knowledge_base(state: TicketState) -> dict:
    """
    LangGraph node that searches the knowledge base for relevant articles.
    
    Strategy:
        1. Try pgvector similarity search (production — uses embeddings + DB)
        2. If DB unavailable, fall back to keyword matching (always works)
    
    Input state fields used:
        - subject: ticket subject
        - message: customer's message
        - intent: classified intent
        
    Output state fields set:
        - kb_results: list of matching article chunks with similarity scores
        - current_node: "search_kb"
        - actions_taken: appended with search action
    """
    subject = state.get("subject", "").lower()
    message = state.get("message", "").lower()
    intent = state.get("intent", "").lower()
    
    search_text = f"{subject} {message} {intent}"
    
    logger.info(
        "searching_knowledge_base",
        ticket_id=state.get("ticket_id", "unknown"),
        search_query=search_text[:100],
    )
    
    # --- Try pgvector search, fallback to keyword matching ---
    search_method = "pgvector"
    try:
        top_results = await _search_pgvector(search_text, top_k=3)
        
        if not top_results:
            # DB might be empty — fall back to keywords
            logger.info("pgvector_no_results_falling_back_to_keywords")
            search_method = "keyword_fallback"
            top_results = _search_keyword_fallback(search_text, top_k=3)
            
    except Exception as e:
        logger.warning(
            "pgvector_search_failed_using_fallback",
            error=str(e),
        )
        search_method = "keyword_fallback"
        top_results = _search_keyword_fallback(search_text, top_k=3)
    
    logger.info(
        "kb_search_complete",
        ticket_id=state.get("ticket_id", "unknown"),
        results_found=len(top_results),
        search_method=search_method,
        top_article=top_results[0]["article_title"] if top_results else "none",
    )
    
    action = {
        "action_type": "search_knowledge_base",
        "action_data": {
            "results_found": len(top_results),
            "search_method": search_method,
            "articles": [r["article_title"] for r in top_results],
        },
        "reasoning": f"Searched via {search_method}, found {len(top_results)} matches",
        "outcome": "success",
    }
    
    return {
        "kb_results": top_results,
        "current_node": "search_kb",
        "actions_taken": state.get("actions_taken", []) + [action],
    }
