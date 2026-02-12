"""
Analytics Route — dashboard metrics endpoint.
Now queries Supabase instead of in-memory storage.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Ticket
from src.db.session import get_db_session
from src.services.analytics_service import compute_dashboard_metrics

router = APIRouter(prefix="/api/v1/analytics", tags=["Analytics"])


@router.get(
    "/dashboard",
    summary="Get support dashboard metrics",
    description="Returns aggregated metrics: resolution rate, category breakdown, etc.",
)
async def get_dashboard(db: AsyncSession = Depends(get_db_session)):
    """Compute and return support metrics from all tickets in Supabase."""
    result = await db.execute(select(Ticket))
    tickets = result.scalars().all()

    # Convert ORM objects to dicts for the analytics service
    ticket_dicts = [
        {
            "status": t.status,
            "priority": t.priority,
            "category": t.category,
            "sentiment": t.ai_context.get("sentiment") if t.ai_context else None,
        }
        for t in tickets
    ]

    return compute_dashboard_metrics(ticket_dicts)
