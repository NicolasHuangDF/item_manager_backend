from datetime import datetime

from fastapi import APIRouter, Depends, status
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_user,
    get_property_access,
    require_property_write,
    write_audit_log,
)
from app.core.database import get_db
from app.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from app.models import Category, Tag, Unit, User
from app.schemas import (
    CategoryCreate,
    CategoryOut,
    CategoryUpdate,
    Message,
    ReviewRequest,
    TagCreate,
    TagOut,
    TagUpdate,
    UnitCreate,
    UnitOut,
    UnitUpdate,
)

router = APIRouter(tags=["基础数据"])


def _ensure_reviewer(user: User) -> None:
    username = (user.username or "").lower()
    email = (user.email or "").lower()
    if username in {"admin", "administrator"} or email.startswith("admin@"):
        return
    raise PermissionDeniedError("仅系统管理员可审核公共基础数据")


async def _check_public_name(
    db: AsyncSession,
    model: type[Unit] | type[Category] | type[Tag],
    name: str,
    exclude_id: str | None = None,
) -> None:
    stmt = select(model).where(
        model.name == name,
        model.is_public.is_(True),
        model.deleted_at.is_(None),
    )
    if exclude_id:
        stmt = stmt.where(model.id != exclude_id)
    if await db.scalar(stmt):
        raise ConflictError(f"公共{model.__name__}名称已存在")


@router.get("/properties/{property_id}/units", response_model=list[UnitOut], summary="单位列表")
async def list_units(
    property_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[UnitOut]:
    await get_property_access(db, property_id, user)
    rows = await db.scalars(
        select(Unit)
        .where(
            Unit.deleted_at.is_(None),
            or_(
                and_(Unit.is_public.is_(True), Unit.review_status == "approved"),
                Unit.property_id == property_id,
            ),
        )
        .order_by(Unit.is_public.desc(), Unit.name)
    )
    return [UnitOut.model_validate(row) for row in rows.all()]


@router.get("/units/public", response_model=list[UnitOut], summary="公共单位")
async def list_public_units(db: AsyncSession = Depends(get_db)) -> list[UnitOut]:
    rows = await db.scalars(
        select(Unit)
        .where(
            Unit.is_public.is_(True),
            Unit.review_status == "approved",
            Unit.deleted_at.is_(None),
        )
        .order_by(Unit.name)
    )
    return [UnitOut.model_validate(row) for row in rows.all()]


@router.post(
    "/properties/{property_id}/units",
    response_model=UnitOut,
    status_code=status.HTTP_201_CREATED,
    summary="创建单位",
)
async def create_unit(
    property_id: str,
    payload: UnitCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UnitOut:
    await require_property_write(db, property_id, user)
    if payload.is_public:
        await _check_public_name(db, Unit, payload.name)
    unit = Unit(
        property_id=property_id,
        name=payload.name,
        symbol=payload.symbol,
        decimal_places=payload.decimal_places,
        created_by=user.id,
        is_public=payload.is_public,
        review_status="pending" if payload.is_public else "approved",
    )
    db.add(unit)
    await db.flush()
    await write_audit_log(
        db,
        user,
        action="create",
        entity_type="unit",
        entity_id=unit.id,
        property_id=property_id,
        after_data={"name": unit.name, "is_public": unit.is_public},
    )
    await db.commit()
    await db.refresh(unit)
    return UnitOut.model_validate(unit)


@router.patch("/units/{unit_id}", response_model=UnitOut, summary="更新单位")
async def update_unit(
    unit_id: str,
    payload: UnitUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UnitOut:
    unit = await db.get(Unit, unit_id)
    if not unit or unit.deleted_at is not None:
        raise NotFoundError("单位不存在")
    if not unit.property_id:
        _ensure_reviewer(user)
    else:
        await require_property_write(db, unit.property_id, user)
    data = payload.model_dump(exclude_unset=True)
    if data.get("name") and data.get("is_public", unit.is_public):
        await _check_public_name(db, Unit, data["name"], unit.id)
    for key, value in data.items():
        setattr(unit, key, value)
    if data.get("is_public") is True:
        unit.review_status = "pending"
    await db.commit()
    await db.refresh(unit)
    return UnitOut.model_validate(unit)


@router.delete("/units/{unit_id}", response_model=Message, summary="删除单位")
async def delete_unit(
    unit_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Message:
    unit = await db.get(Unit, unit_id)
    if not unit or unit.deleted_at is not None:
        raise NotFoundError("单位不存在")
    if not unit.property_id:
        _ensure_reviewer(user)
    else:
        await require_property_write(db, unit.property_id, user)
    unit.deleted_at = datetime.utcnow()
    await db.commit()
    return Message(message="单位已删除")


@router.post("/units/{unit_id}/submit-review", response_model=UnitOut, summary="提交公共单位审核")
async def submit_unit_review(
    unit_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UnitOut:
    unit = await db.get(Unit, unit_id)
    if not unit or unit.deleted_at is not None:
        raise NotFoundError("单位不存在")
    if not unit.property_id:
        raise PermissionDeniedError("该单位已转为公共数据")
    await require_property_write(db, unit.property_id, user)
    await _check_public_name(db, Unit, unit.name, unit.id)
    unit.is_public = True
    unit.review_status = "pending"
    unit.review_remark = None
    await db.commit()
    await db.refresh(unit)
    return UnitOut.model_validate(unit)


@router.post("/units/{unit_id}/review", response_model=UnitOut, summary="审核公共单位")
async def review_unit(
    unit_id: str,
    payload: ReviewRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UnitOut:
    _ensure_reviewer(user)
    unit = await db.get(Unit, unit_id)
    if not unit or unit.deleted_at is not None:
        raise NotFoundError("单位不存在")
    unit.review_status = "approved" if payload.approve else "rejected"
    unit.reviewed_by = user.id
    unit.reviewed_at = datetime.utcnow()
    unit.review_remark = payload.remark
    if payload.approve:
        unit.is_public = True
        unit.published_at = datetime.utcnow()
        unit.property_id = None
    else:
        unit.is_public = False
    await db.commit()
    await db.refresh(unit)
    return UnitOut.model_validate(unit)


@router.get(
    "/properties/{property_id}/categories",
    response_model=list[CategoryOut],
    summary="分类列表",
)
async def list_categories(
    property_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[CategoryOut]:
    await get_property_access(db, property_id, user)
    rows = await db.scalars(
        select(Category)
        .where(
            Category.deleted_at.is_(None),
            or_(
                and_(Category.is_public.is_(True), Category.review_status == "approved"),
                Category.property_id == property_id,
            ),
        )
        .order_by(Category.sort_order, Category.name)
    )
    return [CategoryOut.model_validate(row) for row in rows.all()]


@router.post(
    "/properties/{property_id}/categories",
    response_model=CategoryOut,
    status_code=status.HTTP_201_CREATED,
    summary="创建分类",
)
async def create_category(
    property_id: str,
    payload: CategoryCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CategoryOut:
    await require_property_write(db, property_id, user)
    if payload.parent_id:
        parent = await db.get(Category, payload.parent_id)
        if not parent or parent.deleted_at is not None:
            raise NotFoundError("父分类不存在")
    if payload.is_public:
        await _check_public_name(db, Category, payload.name)
    category = Category(
        property_id=property_id,
        **payload.model_dump(exclude={"is_public"}),
        is_public=payload.is_public,
        created_by=user.id,
        review_status="pending" if payload.is_public else "approved",
    )
    db.add(category)
    await db.flush()
    await write_audit_log(
        db,
        user,
        action="create",
        entity_type="category",
        entity_id=category.id,
        property_id=property_id,
        after_data={"name": category.name},
    )
    await db.commit()
    await db.refresh(category)
    return CategoryOut.model_validate(category)


@router.patch("/categories/{category_id}", response_model=CategoryOut, summary="更新分类")
async def update_category(
    category_id: str,
    payload: CategoryUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CategoryOut:
    category = await db.get(Category, category_id)
    if not category or category.deleted_at is not None:
        raise NotFoundError("分类不存在")
    if not category.property_id:
        _ensure_reviewer(user)
    else:
        await require_property_write(db, category.property_id, user)
    data = payload.model_dump(exclude_unset=True)
    if data.get("name") and data.get("is_public", category.is_public):
        await _check_public_name(db, Category, data["name"], category.id)
    for key, value in data.items():
        setattr(category, key, value)
    if data.get("is_public") is True:
        category.review_status = "pending"
    await db.commit()
    await db.refresh(category)
    return CategoryOut.model_validate(category)


@router.delete("/categories/{category_id}", response_model=Message, summary="删除分类")
async def delete_category(
    category_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Message:
    category = await db.get(Category, category_id)
    if not category or category.deleted_at is not None:
        raise NotFoundError("分类不存在")
    if not category.property_id:
        _ensure_reviewer(user)
    else:
        await require_property_write(db, category.property_id, user)
    category.deleted_at = datetime.utcnow()
    await db.commit()
    return Message(message="分类已删除")


@router.post(
    "/categories/{category_id}/submit-review",
    response_model=CategoryOut,
    summary="提交分类审核",
)
async def submit_category_review(
    category_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CategoryOut:
    category = await db.get(Category, category_id)
    if not category or category.deleted_at is not None:
        raise NotFoundError("分类不存在")
    if not category.property_id:
        raise PermissionDeniedError("该分类已转为公共数据")
    await require_property_write(db, category.property_id, user)
    await _check_public_name(db, Category, category.name, category.id)
    category.is_public = True
    category.review_status = "pending"
    await db.commit()
    await db.refresh(category)
    return CategoryOut.model_validate(category)


@router.post("/categories/{category_id}/review", response_model=CategoryOut, summary="审核分类")
async def review_category(
    category_id: str,
    payload: ReviewRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CategoryOut:
    _ensure_reviewer(user)
    category = await db.get(Category, category_id)
    if not category or category.deleted_at is not None:
        raise NotFoundError("分类不存在")
    category.review_status = "approved" if payload.approve else "rejected"
    category.reviewed_by = user.id
    category.reviewed_at = datetime.utcnow()
    category.review_remark = payload.remark
    if payload.approve:
        category.is_public = True
        category.published_at = datetime.utcnow()
        category.property_id = None
    else:
        category.is_public = False
    await db.commit()
    await db.refresh(category)
    return CategoryOut.model_validate(category)


@router.get("/properties/{property_id}/tags", response_model=list[TagOut], summary="标签列表")
async def list_tags(
    property_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[TagOut]:
    await get_property_access(db, property_id, user)
    rows = await db.scalars(
        select(Tag)
        .where(
            Tag.deleted_at.is_(None),
            or_(
                and_(Tag.is_public.is_(True), Tag.review_status == "approved"),
                Tag.property_id == property_id,
            ),
        )
        .order_by(Tag.name)
    )
    return [TagOut.model_validate(row) for row in rows.all()]


@router.post(
    "/properties/{property_id}/tags",
    response_model=TagOut,
    status_code=status.HTTP_201_CREATED,
    summary="创建标签",
)
async def create_tag(
    property_id: str,
    payload: TagCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TagOut:
    await require_property_write(db, property_id, user)
    if payload.is_public:
        await _check_public_name(db, Tag, payload.name)
    tag = Tag(
        property_id=property_id,
        name=payload.name,
        color=payload.color,
        created_by=user.id,
        is_public=payload.is_public,
        review_status="pending" if payload.is_public else "approved",
    )
    db.add(tag)
    await db.flush()
    await db.commit()
    await db.refresh(tag)
    return TagOut.model_validate(tag)


@router.patch("/tags/{tag_id}", response_model=TagOut, summary="更新标签")
async def update_tag(
    tag_id: str,
    payload: TagUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TagOut:
    tag = await db.get(Tag, tag_id)
    if not tag or tag.deleted_at is not None:
        raise NotFoundError("标签不存在")
    if not tag.property_id:
        _ensure_reviewer(user)
    else:
        await require_property_write(db, tag.property_id, user)
    data = payload.model_dump(exclude_unset=True)
    if data.get("name") and data.get("is_public", tag.is_public):
        await _check_public_name(db, Tag, data["name"], tag.id)
    for key, value in data.items():
        setattr(tag, key, value)
    if data.get("is_public") is True:
        tag.review_status = "pending"
    await db.commit()
    await db.refresh(tag)
    return TagOut.model_validate(tag)


@router.delete("/tags/{tag_id}", response_model=Message, summary="删除标签")
async def delete_tag(
    tag_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Message:
    tag = await db.get(Tag, tag_id)
    if not tag or tag.deleted_at is not None:
        raise NotFoundError("标签不存在")
    if not tag.property_id:
        _ensure_reviewer(user)
    else:
        await require_property_write(db, tag.property_id, user)
    tag.deleted_at = datetime.utcnow()
    await db.commit()
    return Message(message="标签已删除")


@router.post("/tags/{tag_id}/submit-review", response_model=TagOut, summary="提交标签审核")
async def submit_tag_review(
    tag_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TagOut:
    tag = await db.get(Tag, tag_id)
    if not tag or tag.deleted_at is not None:
        raise NotFoundError("标签不存在")
    if not tag.property_id:
        raise PermissionDeniedError("该标签已转为公共数据")
    await require_property_write(db, tag.property_id, user)
    await _check_public_name(db, Tag, tag.name, tag.id)
    tag.is_public = True
    tag.review_status = "pending"
    await db.commit()
    await db.refresh(tag)
    return TagOut.model_validate(tag)


@router.post("/tags/{tag_id}/review", response_model=TagOut, summary="审核标签")
async def review_tag(
    tag_id: str,
    payload: ReviewRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TagOut:
    _ensure_reviewer(user)
    tag = await db.get(Tag, tag_id)
    if not tag or tag.deleted_at is not None:
        raise NotFoundError("标签不存在")
    tag.review_status = "approved" if payload.approve else "rejected"
    tag.reviewed_by = user.id
    tag.reviewed_at = datetime.utcnow()
    tag.review_remark = payload.remark
    if payload.approve:
        tag.is_public = True
        tag.published_at = datetime.utcnow()
        tag.property_id = None
    else:
        tag.is_public = False
    await db.commit()
    await db.refresh(tag)
    return TagOut.model_validate(tag)
