"""
Customer Repository — database queries for customers.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Customer
from src.utils.logging import get_logger

logger = get_logger(__name__)


async def get_or_create_customer(
    db: AsyncSession,
    email: str,
    name: str = "",
) -> tuple[Customer, bool]:
    """
    Find existing customer by email, or create a new one.
    
    Returns:
        (customer, created) — created=True if new customer was inserted
    """
    result = await db.execute(
        select(Customer).where(Customer.email == email)
    )
    customer = result.scalar_one_or_none()
    
    if customer:
        return customer, False
    
    customer = Customer(
        email=email,
        name=name or email.split("@")[0],
    )
    db.add(customer)
    await db.flush()
    
    logger.info("customer_created", email=email, id=str(customer.id))
    return customer, True


async def get_customer_by_email(
    db: AsyncSession,
    email: str,
) -> Customer | None:
    """Fetch a customer by email address."""
    result = await db.execute(
        select(Customer).where(Customer.email == email)
    )
    return result.scalar_one_or_none()


async def get_customer_by_id(
    db: AsyncSession,
    customer_id: uuid.UUID,
) -> Customer | None:
    """Fetch a customer by ID."""
    return await db.get(Customer, customer_id)
