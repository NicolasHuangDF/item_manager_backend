from datetime import datetime

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_user,
    get_property_access,
    require_property_write,
    write_audit_log,
)
from app.core.database import get_db
from app.core.exceptions import BadRequestError, NotFoundError
from app.models import Container, User
from app.schemas import (
    ContainerCreate,
    ContainerOut,
    ContainerTreeOut,
    ContainerUpdate,
    Message,
)

router = APIRouter(tags=["容器"])


async def _get_container(db: AsyncSession, container_id: str) -> Container:
    container = await db.get(Container, container_id)
    if not container or container.deleted_at is not None:
        raise NotFoundError("容器不存在")
    return container


@router.get(
    "/properties/{property_id}/containers",
    response_model=None,
    summary="容器列表/树",
)
async def list_containers(
    property_id: str,
    tree: bool = Query(default=True, description="是否返回树形结构"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_property_access(db, property_id, user)
    rows = list(
        (
            await db.scalars(
                select(Container)
                .where(
                    Container.property_id == property_id,
                    Container.deleted_at.is_(None),
                )
                .order_by(Container.sort_order, Container.created_at)
            )
        ).all()
    )
    if not tree:
        return [ContainerOut.model_validate(row) for row in rows]

    nodes: dict[str, ContainerTreeOut] = {}
    for row in rows:
        nodes[row.id] = ContainerTreeOut.model_validate(row)
    roots: list[ContainerTreeOut] = []
    for row in rows:
        node = nodes[row.id]
        if row.parent_id and row.parent_id in nodes:
            nodes[row.parent_id].children.append(node)
        else:
            roots.append(node)
    return roots


@router.post(
    "/properties/{property_id}/containers",
    response_model=ContainerOut,
    status_code=status.HTTP_201_CREATED,
    summary="创建容器",
)
async def create_container(
    property_id: str,
    payload: ContainerCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ContainerOut:
    await require_property_write(db, property_id, user)
    if payload.parent_id:
        parent = await _get_container(db, payload.parent_id)
        if parent.property_id != property_id:
            raise BadRequestError("父容器不属于当前房屋")

    container = Container(
        property_id=property_id,
        **payload.model_dump(),
        created_by=user.id,
        updated_by=user.id,
    )
    db.add(container)
    await db.flush()
    await write_audit_log(
        db,
        user,
        action="create",
        entity_type="container",
        entity_id=container.id,
        property_id=property_id,
        after_data={"name": container.name, "type": container.type},
    )
    await db.commit()
    await db.refresh(container)
    return ContainerOut.model_validate(container)


@router.get("/containers/qr/{qr_code}", response_model=ContainerOut, summary="二维码查容器")
async def get_by_qr_code(
    qr_code: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ContainerOut:
    container = await db.scalar(
        select(Container).where(
            Container.qr_code == qr_code,
            Container.deleted_at.is_(None),
        )
    )
    if not container:
        raise NotFoundError("未找到二维码对应的容器")
    await get_property_access(db, container.property_id, user)
    return ContainerOut.model_validate(container)


@router.get("/containers/{container_id}", response_model=ContainerOut, summary="容器详情")
async def get_container(
    container_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ContainerOut:
    container = await _get_container(db, container_id)
    await get_property_access(db, container.property_id, user)
    return ContainerOut.model_validate(container)


@router.patch("/containers/{container_id}", response_model=ContainerOut, summary="更新容器")
async def update_container(
    container_id: str,
    payload: ContainerUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ContainerOut:
    container = await _get_container(db, container_id)
    await require_property_write(db, container.property_id, user)

    data = payload.model_dump(exclude_unset=True)
    if data.get("parent_id"):
        if data["parent_id"] == container.id:
            raise BadRequestError("父容器不能是自己")
        parent = await _get_container(db, data["parent_id"])
        if parent.property_id != container.property_id:
            raise BadRequestError("父容器不属于当前房屋")

    for key, value in data.items():
        setattr(container, key, value)
    container.updated_by = user.id

    await write_audit_log(
        db,
        user,
        action="update",
        entity_type="container",
        entity_id=container.id,
        property_id=container.property_id,
        after_data=data,
    )
    await db.commit()
    await db.refresh(container)
    return ContainerOut.model_validate(container)


@router.delete("/containers/{container_id}", response_model=Message, summary="删除容器")
async def delete_container(
    container_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Message:
    container = await _get_container(db, container_id)
    await require_property_write(db, container.property_id, user)
    container.deleted_at = datetime.utcnow()
    container.updated_by = user.id
    await write_audit_log(
        db,
        user,
        action="delete",
        entity_type="container",
        entity_id=container.id,
        property_id=container.property_id,
    )
    await db.commit()
    return Message(message="容器已删除")
