from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_user,
    get_property_access,
    require_property_write,
    write_audit_log,
)
from app.core.database import get_db
from app.core.exceptions import BadRequestError, NotFoundError
from app.models import Category, Container, Item, ItemBatch, ItemTag, Tag, Unit, User
from app.schemas import (
    BatchOut,
    ItemCreate,
    ItemDetailOut,
    ItemOut,
    ItemUpdate,
    Message,
    PageResult,
    TagOut,
    TagSetRequest,
)

router = APIRouter(tags=["物品"])


async def _get_item_access(
    db: AsyncSession, item_id: str, user: User, write: bool = False
) -> Item:
    item = await db.get(Item, item_id)
    if not item or item.deleted_at is not None:
        raise NotFoundError("物品不存在")
    if write:
        await require_property_write(db, item.property_id, user)
    else:
        await get_property_access(db, item.property_id, user)
    return item


async def _validate_reference(
    db: AsyncSession,
    model: type[Category] | type[Unit] | type[Container],
    ref_id: str | None,
    property_id: str,
) -> None:
    if not ref_id:
        return
    ref = await db.get(model, ref_id)
    if not ref:
        raise NotFoundError("关联数据不存在")
    if model is Container:
        if ref.deleted_at is not None or ref.property_id != property_id:
            raise BadRequestError("容器不属于当前房屋")
        return
    if getattr(ref, "deleted_at", None) is not None:
        raise NotFoundError("关联数据不存在")
    if getattr(ref, "property_id", None) not in (None, property_id):
        raise BadRequestError("关联数据不属于当前房屋")
    if hasattr(ref, "review_status") and getattr(ref, "is_public", False):
        if ref.review_status != "approved":
            raise BadRequestError("公共数据尚未审核通过")


@router.get(
    "/properties/{property_id}/items",
    response_model=PageResult[ItemOut],
    summary="物品列表",
)
async def list_items(
    property_id: str,
    q: str | None = Query(default=None, max_length=200),
    category_id: str | None = None,
    container_id: str | None = None,
    low_stock: bool | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PageResult[ItemOut]:
    await get_property_access(db, property_id, user)
    conditions = [Item.property_id == property_id, Item.deleted_at.is_(None)]
    if q:
        like = f"%{q}%"
        conditions.append(
            or_(
                Item.name.like(like),
                Item.brand.like(like),
                Item.model.like(like),
                Item.barcode.like(like),
            )
        )
    if category_id:
        conditions.append(Item.category_id == category_id)
    if container_id:
        conditions.append(Item.default_container_id == container_id)
    if low_stock:
        conditions.append(Item.low_stock_threshold.is_not(None))
        conditions.append(Item.current_quantity <= Item.low_stock_threshold)

    total = await db.scalar(select(func.count()).select_from(Item).where(*conditions))
    rows = await db.scalars(
        select(Item)
        .where(*conditions)
        .order_by(Item.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return PageResult[ItemOut](
        items=[ItemOut.model_validate(row) for row in rows.all()],
        total=int(total or 0),
        page=page,
        page_size=page_size,
    )


@router.post(
    "/properties/{property_id}/items",
    response_model=ItemOut,
    status_code=status.HTTP_201_CREATED,
    summary="创建物品",
)
async def create_item(
    property_id: str,
    payload: ItemCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ItemOut:
    await require_property_write(db, property_id, user)
    await _validate_reference(db, Category, payload.category_id, property_id)
    await _validate_reference(db, Unit, payload.unit_id, property_id)
    await _validate_reference(db, Container, payload.default_container_id, property_id)

    item = Item(
        property_id=property_id,
        **payload.model_dump(),
        current_quantity=Decimal("0"),
        created_by=user.id,
        updated_by=user.id,
    )
    db.add(item)
    await db.flush()
    await write_audit_log(
        db,
        user,
        action="create",
        entity_type="item",
        entity_id=item.id,
        property_id=property_id,
        after_data={"name": item.name},
    )
    await db.commit()
    await db.refresh(item)
    return ItemOut.model_validate(item)


@router.get("/items/{item_id}", response_model=ItemDetailOut, summary="物品详情")
async def get_item(
    item_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ItemDetailOut:
    item = await _get_item_access(db, item_id, user)
    detail = ItemDetailOut.model_validate(item)

    tag_rows = await db.scalars(
        select(Tag)
        .join(ItemTag, ItemTag.tag_id == Tag.id)
        .where(ItemTag.item_id == item.id, Tag.deleted_at.is_(None))
    )
    detail.tags = [TagOut.model_validate(row) for row in tag_rows.all()]

    batch_rows = await db.scalars(
        select(ItemBatch)
        .where(ItemBatch.item_id == item.id)
        .order_by(ItemBatch.created_at.desc())
    )
    detail.batches = [BatchOut.model_validate(row) for row in batch_rows.all()]
    return detail


@router.patch("/items/{item_id}", response_model=ItemOut, summary="更新物品")
async def update_item(
    item_id: str,
    payload: ItemUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ItemOut:
    item = await _get_item_access(db, item_id, user, write=True)
    data = payload.model_dump(exclude_unset=True)
    await _validate_reference(db, Category, data.get("category_id"), item.property_id)
    await _validate_reference(db, Unit, data.get("unit_id"), item.property_id)
    await _validate_reference(db, Container, data.get("default_container_id"), item.property_id)

    for key, value in data.items():
        setattr(item, key, value)
    item.updated_by = user.id
    await write_audit_log(
        db,
        user,
        action="update",
        entity_type="item",
        entity_id=item.id,
        property_id=item.property_id,
        after_data=data,
    )
    await db.commit()
    await db.refresh(item)
    return ItemOut.model_validate(item)


@router.delete("/items/{item_id}", response_model=Message, summary="删除物品")
async def delete_item(
    item_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Message:
    item = await _get_item_access(db, item_id, user, write=True)
    item.deleted_at = datetime.utcnow()
    item.updated_by = user.id
    await write_audit_log(
        db,
        user,
        action="delete",
        entity_type="item",
        entity_id=item.id,
        property_id=item.property_id,
    )
    await db.commit()
    return Message(message="物品已删除")


@router.put("/items/{item_id}/tags", response_model=ItemDetailOut, summary="设置物品标签")
async def set_item_tags(
    item_id: str,
    payload: TagSetRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ItemDetailOut:
    item = await _get_item_access(db, item_id, user, write=True)

    tags = []
    for tag_id in set(payload.tag_ids):
        tag = await db.get(Tag, tag_id)
        if not tag or tag.deleted_at is not None:
            raise NotFoundError(f"标签不存在：{tag_id}")
        if tag.property_id not in (None, item.property_id):
            raise BadRequestError("标签不属于当前房屋")
        tags.append(tag)

    await db.execute(delete(ItemTag).where(ItemTag.item_id == item.id))
    for tag in tags:
        db.add(ItemTag(item_id=item.id, tag_id=tag.id))
    await db.commit()

    detail = ItemDetailOut.model_validate(item)
    detail.tags = [TagOut.model_validate(tag) for tag in tags]
    return detail
