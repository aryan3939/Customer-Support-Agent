"""
Analytics Service — compute support metrics from ticket data.

Provides dashboard-style metrics: resolution rates, avg response times,
category breakdowns, etc. Uses in-memory data for now.
"""

from datetime import datetime, timezone

from src.utils.logging import get_logger

logger = get_logger(__name__)


def compute_dashboard_metrics(tickets: list[dict]) -> dict:
    """
    Compute support dashboard metrics from a list of tickets.
    
    Returns:
        Dict with key metrics for display on a dashboard.
    """
    if not tickets:
        return {
            "total_tickets": 0,
            "open_tickets": 0,
            "resolved_tickets": 0,
            "escalated_tickets": 0,
            "resolution_rate": 0.0,
            "priority_breakdown": {},
            "category_breakdown": {},
            "sentiment_breakdown": {},
        }
    
    total = len(tickets)
    open_count = sum(1 for t in tickets if t.get("status") in ("new", "open"))
    resolved = sum(1 for t in tickets if t.get("status") in ("resolved", "closed"))
    escalated = sum(1 for t in tickets if t.get("status") == "escalated")
    
    # Priority breakdown
    priority_counts = {}
    for t in tickets:
        p = t.get("priority", "unknown")
        priority_counts[p] = priority_counts.get(p, 0) + 1
    
    # Category breakdown
    category_counts = {}
    for t in tickets:
        c = t.get("category", "unknown") or "unknown"
        category_counts[c] = category_counts.get(c, 0) + 1
    
    # Sentiment breakdown
    sentiment_counts = {}
    for t in tickets:
        s = t.get("sentiment", "unknown") or "unknown"
        sentiment_counts[s] = sentiment_counts.get(s, 0) + 1
    
    return {
        "total_tickets": total,
        "open_tickets": open_count,
        "resolved_tickets": resolved,
        "escalated_tickets": escalated,
        "resolution_rate": round(resolved / total * 100, 1) if total > 0 else 0.0,
        "escalation_rate": round(escalated / total * 100, 1) if total > 0 else 0.0,
        "priority_breakdown": priority_counts,
        "category_breakdown": category_counts,
        "sentiment_breakdown": sentiment_counts,
    }
