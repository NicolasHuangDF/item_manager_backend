from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_property_access, require_property_write
from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.models import InventoryTransaction, Item, ItemBatch, User
from app.schemas import (
    BatchOut,
    PageResult,
    StockAdjustRequest,
    StockInRequest,
    StockMoveRequest,
    StockOutRequest,
    TransactionOut,
)
from app.services.inventory_service import (
    add_stock,
    adjust_stock,
    consume_stock,
    move_stock,
)

router = APIRouter(tags=["库存"])


async def _get_item_for_stock(db: AsyncSession, item_id: str, user: User) -> Item:
    item = await db.get(Item, item_id)
    if not item or item.deleted_at is not None:
        raise NotFoundError("物品不存在")
    await require_property_write(db, item.property_id, user)
    return item


@router.get("/items/{item_id}/batches", response_model=list[BatchOut], summary="物品批次列表")
async def list_batches(
    item_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[BatchOut]:
    item = await db.get(Item, item_id)
    if not item or item.deleted_at is not None:
        raise NotFoundError("物品不存在")
    await get_property_access(db, item.property_id, user)
    rows = await db.scalars(
        select(ItemBatch)
        .where(ItemBatch.item_id == item.id)
        .order_by(ItemBatch.created_at.desc())
    )
    return [BatchOut.model_validate(row) for row in rows.all()]


@router.post("/items/{item_id}/stock/in", response_model=BatchOut, summary="入库")
async def stock_in(
    item_id: str,
    payload: StockInRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BatchOut:
    item = await _get_item_for_stock(db, item_id, user)
    batch = await add_stock(db, item, user, payload)
    return BatchOut.model_validate(batch)


@router.post(
    "/items/{item_id}/stock/out",
    response_model=list[TransactionOut],
    summary="出库/消耗（未指定批次时按到期日 FIFO）",
)
async def stock_out(
    item_id: str,
    payload: StockOutRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[TransactionOut]:
    item = await _get_item_for_stock(db, item_id, user)
    transactions = await consume_stock(db, item, user, payload)
    return [TransactionOut.model_validate(tx) for tx in transactions]


@router.post("/items/{item_id}/stock/move", response_model=list[TransactionOut], summary="库存移库")
async def stock_move(
    item_id: str,
    payload: StockMoveRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[TransactionOut]:
    item = await _get_item_for_stock(db, item_id, user)
    transactions = await move_stock(db, item, user, payload)
    return [TransactionOut.model_validate(tx) for tx in transactions]


@router.post("/items/{item_id}/stock/adjust", response_model=TransactionOut, summary="库存调整")
async def stock_adjust(
    item_id: str,
    payload: StockAdjustRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TransactionOut:
    item = await _get_item_for_stock(db, item_id, user)
    transaction = await adjust_stock(db, item, user, payload)
    return TransactionOut.model_validate(transaction)


@router.get(
    "/properties/{property_id}/transactions",
    response_model=PageResult[TransactionOut],
    summary="库存流水",
)
async def list_transactions(
    property_id: str,
    item_id: str | None = None,
    batch_id: str | None = None,
    type: str | None = None,
    start_at: datetime | None = None,
    end_at: datetime | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PageResult[TransactionOut]:
    await get_property_access(db, property_id, user)
    conditions = [InventoryTransaction.property_id == property_id]
    if item_id:
        conditions.append(InventoryTransaction.item_id == item_id)
    if batch_id:
        conditions.append(InventoryTransaction.batch_id == batch_id)
    if type:
        conditions.append(InventoryTransaction.type == type)
    if start_at:
        conditions.append(InventoryTransaction.created_at >= start_at)
    if end_at:
        conditions.append(InventoryTransaction.created_at <= end_at)

    total = await db.scalar(
        select(func.count()).select_from(InventoryTransaction).where(*conditions)
    )
    rows = await db.scalars(
        select(InventoryTransaction)
        .where(*conditions)
        .order_by(InventoryTransaction.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return PageResult[TransactionOut](
        items=[TransactionOut.model_validate(row) for row in rows.all()],
        total=int(total or 0),
        page=page,
        page_size=page_size,
    )
