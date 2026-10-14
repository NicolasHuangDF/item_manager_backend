from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, NotFoundError
from app.models import Container, InventoryTransaction, Item, ItemBatch, User
from app.schemas import (
    StockAdjustRequest,
    StockInRequest,
    StockMoveRequest,
    StockOutRequest,
)


async def _container(db: AsyncSession, property_id: str, container_id: str) -> Container:
    container = await db.scalar(
        select(Container).where(
            Container.id == container_id,
            Container.property_id == property_id,
            Container.deleted_at.is_(None),
        )
    )
    if not container:
        raise NotFoundError("容器不存在")
    return container


async def _recalculate(db: AsyncSession, item: Item) -> Decimal:
    total = await db.scalar(
        select(func.coalesce(func.sum(ItemBatch.quantity), 0)).where(
            ItemBatch.item_id == item.id,
            ItemBatch.status == "active",
        )
    )
    item.current_quantity = Decimal(total or 0)
    return item.current_quantity


def _tx(
    *,
    item: Item,
    user: User,
    tx_type: str,
    delta: Decimal,
    quantity_after: Decimal | None,
    batch_id: str | None = None,
    container_id: str | None = None,
    unit_id: str | None = None,
    reason: str | None = None,
) -> InventoryTransaction:
    return InventoryTransaction(
        property_id=item.property_id,
        item_id=item.id,
        batch_id=batch_id,
        container_id=container_id,
        type=tx_type,
        quantity_delta=delta,
        quantity_after=quantity_after,
        unit_id=unit_id or item.unit_id,
        reason=reason,
        created_by=user.id,
    )


async def add_stock(
    db: AsyncSession, item: Item, user: User, payload: StockInRequest
) -> ItemBatch:
    if not item.track_inventory:
        raise BadRequestError("该物品未开启库存管理")
    container = await _container(db, item.property_id, payload.container_id)
    batch = ItemBatch(
        property_id=item.property_id,
        item_id=item.id,
        container_id=container.id,
        quantity=payload.quantity,
        unit_id=payload.unit_id or item.unit_id,
        production_date=payload.production_date,
        expiry_date=payload.expiry_date,
        status="active",
        note=payload.note,
        created_by=user.id,
        updated_by=user.id,
    )
    db.add(batch)
    await db.flush()
    db.add(
        _tx(
            item=item,
            user=user,
            tx_type="in",
            delta=payload.quantity,
            quantity_after=batch.quantity,
            batch_id=batch.id,
            container_id=container.id,
            unit_id=batch.unit_id,
            reason="入库",
        )
    )
    await _recalculate(db, item)
    await db.commit()
    await db.refresh(batch)
    return batch


async def consume_stock(
    db: AsyncSession, item: Item, user: User, payload: StockOutRequest
) -> list[InventoryTransaction]:
    if not item.track_inventory:
        raise BadRequestError("该物品未开启库存管理")

    stmt = select(ItemBatch).where(
        ItemBatch.item_id == item.id,
        ItemBatch.status == "active",
        ItemBatch.quantity > 0,
    )
    if payload.batch_id:
        stmt = stmt.where(ItemBatch.id == payload.batch_id)
    if payload.container_id:
        stmt = stmt.where(ItemBatch.container_id == payload.container_id)
    stmt = stmt.order_by(ItemBatch.expiry_date.asc(), ItemBatch.created_at.asc())

    remaining = payload.quantity
    transactions: list[InventoryTransaction] = []
    for batch in (await db.scalars(stmt)).all():
        if remaining <= 0:
            break
        take = min(Decimal(batch.quantity), remaining)
        if take <= 0:
            continue
        batch.quantity = Decimal(batch.quantity) - take
        batch.updated_by = user.id
        if batch.quantity <= 0:
            batch.quantity = Decimal("0")
            batch.status = "consumed"
        remaining -= take
        tx = _tx(
            item=item,
            user=user,
            tx_type="out",
            delta=-take,
            quantity_after=batch.quantity,
            batch_id=batch.id,
            container_id=batch.container_id,
            unit_id=batch.unit_id,
            reason=payload.reason or "出库",
        )
        db.add(tx)
        transactions.append(tx)

    if remaining > 0:
        raise BadRequestError("库存数量不足")
    await _recalculate(db, item)
    await db.commit()
    for tx in transactions:
        await db.refresh(tx)
    return transactions


async def move_stock(
    db: AsyncSession, item: Item, user: User, payload: StockMoveRequest
) -> list[InventoryTransaction]:
    if not item.track_inventory:
        raise BadRequestError("该物品未开启库存管理")
    if payload.from_container_id == payload.to_container_id:
        raise BadRequestError("源容器和目标容器不能相同")
    await _container(db, item.property_id, payload.from_container_id)
    await _container(db, item.property_id, payload.to_container_id)

    stmt = select(ItemBatch).where(
        ItemBatch.item_id == item.id,
        ItemBatch.container_id == payload.from_container_id,
        ItemBatch.status == "active",
        ItemBatch.quantity > 0,
    )
    if payload.batch_id:
        stmt = stmt.where(ItemBatch.id == payload.batch_id)
    stmt = stmt.order_by(ItemBatch.expiry_date.asc(), ItemBatch.created_at.asc())

    remaining = payload.quantity
    transactions: list[InventoryTransaction] = []
    for source in (await db.scalars(stmt)).all():
        if remaining <= 0:
            break
        take = min(Decimal(source.quantity), remaining)
        if take <= 0:
            continue
        source.quantity = Decimal(source.quantity) - take
        source.updated_by = user.id
        if source.quantity <= 0:
            source.quantity = Decimal("0")
            source.status = "moved"

        target = ItemBatch(
            property_id=item.property_id,
            item_id=item.id,
            container_id=payload.to_container_id,
            quantity=take,
            unit_id=source.unit_id or item.unit_id,
            production_date=source.production_date,
            expiry_date=source.expiry_date,
            opened_at=source.opened_at,
            opened_expiry_date=source.opened_expiry_date,
            status="active",
            note=source.note,
            created_by=user.id,
            updated_by=user.id,
        )
        db.add(target)
        await db.flush()
        tx = _tx(
            item=item,
            user=user,
            tx_type="move",
            delta=Decimal("0"),
            quantity_after=target.quantity,
            batch_id=target.id,
            container_id=payload.to_container_id,
            unit_id=target.unit_id,
            reason=payload.reason
            or f"从容器 {payload.from_container_id} 移动到 {payload.to_container_id}",
        )
        db.add(tx)
        transactions.append(tx)
        remaining -= take

    if remaining > 0:
        raise BadRequestError("源容器库存不足")
    await _recalculate(db, item)
    await db.commit()
    for tx in transactions:
        await db.refresh(tx)
    return transactions


async def adjust_stock(
    db: AsyncSession, item: Item, user: User, payload: StockAdjustRequest
) -> InventoryTransaction:
    if not item.track_inventory:
        raise BadRequestError("该物品未开启库存管理")
    batch = await db.scalar(
        select(ItemBatch).where(
            ItemBatch.id == payload.batch_id, ItemBatch.item_id == item.id
        )
    )
    if not batch:
        raise NotFoundError("批次不存在")

    old_quantity = Decimal(batch.quantity)
    delta = payload.new_quantity - old_quantity
    batch.quantity = payload.new_quantity
    batch.updated_by = user.id
    if payload.new_quantity == 0:
        batch.status = "discarded"
    elif batch.status in {"consumed", "discarded", "moved"}:
        batch.status = "active"

    tx = _tx(
        item=item,
        user=user,
        tx_type="adjust",
        delta=delta,
        quantity_after=payload.new_quantity,
        batch_id=batch.id,
        container_id=batch.container_id,
        unit_id=batch.unit_id,
        reason=payload.reason or "库存调整",
    )
    db.add(tx)
    await _recalculate(db, item)
    await db.commit()
    await db.refresh(tx)
    return tx
