from datetime import datetime

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_property_access
from app.core.database import get_db
from app.core.exceptions import BadRequestError, NotFoundError
from app.models import (
    Notification,
    NotificationChannel,
    NotificationPreference,
    User,
)
from app.schemas import (
    ChannelCreate,
    ChannelOut,
    ChannelUpdate,
    Message,
    NotificationOut,
    PreferenceCreate,
    PreferenceOut,
    PreferenceUpdate,
)

router = APIRouter(tags=["通知"])


@router.get("/notification-channels", response_model=list[ChannelOut], summary="我的通知渠道")
async def list_channels(
    property_id: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ChannelOut]:
    conditions = [NotificationChannel.user_id == user.id]
    if property_id:
        conditions.append(NotificationChannel.property_id == property_id)
    rows = await db.scalars(
        select(NotificationChannel)
        .where(*conditions)
        .order_by(NotificationChannel.created_at.desc())
    )
    return [ChannelOut.model_validate(row) for row in rows.all()]


@router.post(
    "/notification-channels",
    response_model=ChannelOut,
    status_code=status.HTTP_201_CREATED,
    summary="创建通知渠道",
)
async def create_channel(
    payload: ChannelCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChannelOut:
    if payload.property_id:
        await get_property_access(db, payload.property_id, user)
    channel = NotificationChannel(user_id=user.id, **payload.model_dump())
    db.add(channel)
    await db.commit()
    await db.refresh(channel)
    return ChannelOut.model_validate(channel)


@router.patch(
    "/notification-channels/{channel_id}", response_model=ChannelOut, summary="更新通知渠道"
)
async def update_channel(
    channel_id: str,
    payload: ChannelUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChannelOut:
    channel = await db.get(NotificationChannel, channel_id)
    if not channel or channel.user_id != user.id:
        raise NotFoundError("通知渠道不存在")
    data = payload.model_dump(exclude_unset=True)
    if data.get("property_id"):
        await get_property_access(db, data["property_id"], user)
    for key, value in data.items():
        setattr(channel, key, value)
    await db.commit()
    await db.refresh(channel)
    return ChannelOut.model_validate(channel)


@router.delete(
    "/notification-channels/{channel_id}", response_model=Message, summary="删除通知渠道"
)
async def delete_channel(
    channel_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Message:
    channel = await db.get(NotificationChannel, channel_id)
    if not channel or channel.user_id != user.id:
        raise NotFoundError("通知渠道不存在")
    await db.delete(channel)
    await db.commit()
    return Message(message="通知渠道已删除")


@router.get(
    "/notification-preferences",
    response_model=list[PreferenceOut],
    summary="我的通知偏好",
)
async def list_preferences(
    property_id: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[PreferenceOut]:
    conditions = [NotificationPreference.user_id == user.id]
    if property_id:
        conditions.append(NotificationPreference.property_id == property_id)
    rows = await db.scalars(
        select(NotificationPreference)
        .where(*conditions)
        .order_by(NotificationPreference.created_at.desc())
    )
    return [PreferenceOut.model_validate(row) for row in rows.all()]


@router.post(
    "/notification-preferences",
    response_model=PreferenceOut,
    status_code=status.HTTP_201_CREATED,
    summary="创建通知偏好",
)
async def create_preference(
    payload: PreferenceCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PreferenceOut:
    if payload.property_id:
        await get_property_access(db, payload.property_id, user)
    if payload.channel_id:
        channel = await db.get(NotificationChannel, payload.channel_id)
        if not channel or channel.user_id != user.id:
            raise BadRequestError("通知渠道不存在或不属于当前用户")
    preference = NotificationPreference(user_id=user.id, **payload.model_dump())
    db.add(preference)
    await db.commit()
    await db.refresh(preference)
    return PreferenceOut.model_validate(preference)


@router.patch(
    "/notification-preferences/{preference_id}",
    response_model=PreferenceOut,
    summary="更新通知偏好",
)
async def update_preference(
    preference_id: str,
    payload: PreferenceUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PreferenceOut:
    preference = await db.get(NotificationPreference, preference_id)
    if not preference or preference.user_id != user.id:
        raise NotFoundError("通知偏好不存在")
    data = payload.model_dump(exclude_unset=True)
    if data.get("channel_id"):
        channel = await db.get(NotificationChannel, data["channel_id"])
        if not channel or channel.user_id != user.id:
            raise BadRequestError("通知渠道不存在或不属于当前用户")
    for key, value in data.items():
        setattr(preference, key, value)
    await db.commit()
    await db.refresh(preference)
    return PreferenceOut.model_validate(preference)


@router.delete(
    "/notification-preferences/{preference_id}",
    response_model=Message,
    summary="删除通知偏好",
)
async def delete_preference(
    preference_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Message:
    preference = await db.get(NotificationPreference, preference_id)
    if not preference or preference.user_id != user.id:
        raise NotFoundError("通知偏好不存在")
    await db.delete(preference)
    await db.commit()
    return Message(message="通知偏好已删除")


@router.get("/notifications", response_model=list[NotificationOut], summary="我的通知记录")
async def list_notifications(
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[NotificationOut]:
    conditions = [Notification.user_id == user.id]
    if status:
        conditions.append(Notification.status == status)
    rows = await db.scalars(
        select(Notification)
        .where(*conditions)
        .order_by(Notification.created_at.desc())
        .limit(limit)
    )
    return [NotificationOut.model_validate(row) for row in rows.all()]


@router.post(
    "/notifications/{notification_id}/read", response_model=Message, summary="标记通知已读"
)
async def mark_notification_read(
    notification_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Message:
    notification = await db.get(Notification, notification_id)
    if not notification or notification.user_id != user.id:
        raise NotFoundError("通知不存在")
    notification.status = "read"
    notification.read_at = datetime.utcnow()
    await db.commit()
    return Message(message="通知已标记为已读")


@router.post("/notifications/read-all", response_model=Message, summary="全部标记已读")
async def mark_all_read(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Message:
    await db.execute(
        update(Notification)
        .where(Notification.user_id == user.id, Notification.status != "read")
        .values(status="read", read_at=datetime.utcnow())
    )
    await db.commit()
    return Message(message="全部通知已标记为已读")
