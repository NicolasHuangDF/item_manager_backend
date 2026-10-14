from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_property_access
from app.core.database import get_db
from app.models import Container, Item, ItemBatch, PropertyMember, Reminder, User
from app.schemas import DashboardSummary

router = APIRouter(tags=["看板"])


@router.get(
    "/properties/{property_id}/dashboard/summary",
    response_model=DashboardSummary,
    summary="房屋资源概览",
)
async def dashboard_summary(
    property_id: str,
    expiry_days: int = Query(default=30, ge=0, le=365),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DashboardSummary:
    await get_property_access(db, property_id, user)

    item_count = await db.scalar(
        select(func.count(Item.id)).where(
            Item.property_id == property_id, Item.deleted_at.is_(None)
        )
    )
    container_count = await db.scalar(
        select(func.count(Container.id)).where(
            Container.property_id == property_id, Container.deleted_at.is_(None)
        )
    )
    member_count = await db.scalar(
        select(func.count(PropertyMember.id)).where(
            PropertyMember.property_id == property_id,
            PropertyMember.status == "active",
        )
    )
    low_stock_count = await db.scalar(
        select(func.count(Item.id)).where(
            Item.property_id == property_id,
            Item.deleted_at.is_(None),
            Item.low_stock_threshold.is_not(None),
            Item.current_quantity <= Item.low_stock_threshold,
        )
    )
    today = date.today()
    deadline = today + timedelta(days=expiry_days)
    expiring_count = await db.scalar(
        select(func.count(ItemBatch.id)).where(
            ItemBatch.property_id == property_id,
            ItemBatch.status == "active",
            or_(
                ItemBatch.expiry_date.between(today, deadline),
                ItemBatch.opened_expiry_date.between(today, deadline),
            ),
        )
    )
    pending_reminder_count = await db.scalar(
        select(func.count(Reminder.id)).where(
            Reminder.property_id == property_id, Reminder.status == "pending"
        )
    )
    total_quantity = await db.scalar(
        select(func.coalesce(func.sum(Item.current_quantity), 0)).where(
            Item.property_id == property_id, Item.deleted_at.is_(None)
        )
    )

    return DashboardSummary(
        property_id=property_id,
        item_count=int(item_count or 0),
        container_count=int(container_count or 0),
        member_count=int(member_count or 0),
        low_stock_count=int(low_stock_count or 0),
        expiring_count=int(expiring_count or 0),
        pending_reminder_count=int(pending_reminder_count or 0),
        total_quantity=Decimal(total_quantity or 0),
    )
