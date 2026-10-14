from datetime import datetime

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_property_access, require_property_write
from app.core.database import get_db
from app.core.exceptions import BadRequestError, NotFoundError
from app.models import (
    Container,
    Item,
    ItemBatch,
    PropertyMember,
    Reminder,
    ReminderRecipient,
    User,
)
from app.schemas import (
    Message,
    ReminderActionRequest,
    ReminderCreate,
    ReminderOut,
    ReminderUpdate,
)

router = APIRouter(tags=["提醒"])


async def _get_reminder(
    db: AsyncSession, reminder_id: str, user: User, write: bool = False
) -> Reminder:
    reminder = await db.get(Reminder, reminder_id)
    if not reminder:
        raise NotFoundError("提醒不存在")
    if write:
        await require_property_write(db, reminder.property_id, user)
    else:
        await get_property_access(db, reminder.property_id, user)
    return reminder


@router.get(
    "/properties/{property_id}/reminders",
    response_model=list[ReminderOut],
    summary="提醒列表",
)
async def list_reminders(
    property_id: str,
    status: str | None = Query(default=None),
    type: str | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ReminderOut]:
    await get_property_access(db, property_id, user)
    conditions = [Reminder.property_id == property_id]
    if status:
        conditions.append(Reminder.status == status)
    if type:
        conditions.append(Reminder.type == type)
    rows = await db.scalars(
        select(Reminder).where(*conditions).order_by(Reminder.trigger_at.asc())
    )
    return [ReminderOut.model_validate(row) for row in rows.all()]


@router.post(
    "/properties/{property_id}/reminders",
    response_model=ReminderOut,
    status_code=status.HTTP_201_CREATED,
    summary="创建提醒",
)
async def create_reminder(
    property_id: str,
    payload: ReminderCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReminderOut:
    await require_property_write(db, property_id, user)

    if payload.item_id:
        item = await db.get(Item, payload.item_id)
        if not item or item.deleted_at is not None or item.property_id != property_id:
            raise BadRequestError("物品不属于当前房屋")
    if payload.batch_id:
        batch = await db.get(ItemBatch, payload.batch_id)
        if not batch or batch.property_id != property_id:
            raise BadRequestError("批次不属于当前房屋")
    if payload.container_id:
        container = await db.get(Container, payload.container_id)
        if (
            not container
            or container.deleted_at is not None
            or container.property_id != property_id
        ):
            raise BadRequestError("容器不属于当前房屋")

    dedupe_key = payload.dedupe_key or (
        f"{payload.type}:{payload.item_id or ''}:{payload.batch_id or ''}:"
        f"{int(payload.trigger_at.timestamp())}"
    )
    existing = await db.scalar(
        select(Reminder).where(
            Reminder.property_id == property_id,
            Reminder.dedupe_key == dedupe_key,
        )
    )
    if existing:
        raise BadRequestError("相同提醒已存在")

    reminder = Reminder(
        property_id=property_id,
        type=payload.type,
        item_id=payload.item_id,
        batch_id=payload.batch_id,
        container_id=payload.container_id,
        trigger_at=payload.trigger_at,
        threshold=payload.threshold,
        message=payload.message,
        dedupe_key=dedupe_key,
        created_by=user.id,
    )
    db.add(reminder)
    await db.flush()

    member_ids = set(
        (
            await db.scalars(
                select(PropertyMember.user_id).where(
                    PropertyMember.property_id == property_id,
                    PropertyMember.status == "active",
                )
            )
        ).all()
    )
    member_ids.add(user.id)
    for member_id in member_ids:
        db.add(ReminderRecipient(reminder_id=reminder.id, user_id=member_id))

    await db.commit()
    await db.refresh(reminder)
    return ReminderOut.model_validate(reminder)


@router.patch("/reminders/{reminder_id}", response_model=ReminderOut, summary="更新提醒")
async def update_reminder(
    reminder_id: str,
    payload: ReminderUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReminderOut:
    reminder = await _get_reminder(db, reminder_id, user, write=True)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(reminder, key, value)
    await db.commit()
    await db.refresh(reminder)
    return ReminderOut.model_validate(reminder)


@router.delete("/reminders/{reminder_id}", response_model=Message, summary="删除提醒")
async def delete_reminder(
    reminder_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Message:
    reminder = await _get_reminder(db, reminder_id, user, write=True)
    await db.delete(reminder)
    await db.commit()
    return Message(message="提醒已删除")


@router.get("/reminders/my", response_model=list[ReminderOut], summary="我的提醒")
async def my_reminders(
    status: str | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ReminderOut]:
    conditions = [ReminderRecipient.user_id == user.id]
    if status:
        conditions.append(ReminderRecipient.status == status)
    rows = await db.scalars(
        select(Reminder)
        .join(ReminderRecipient, ReminderRecipient.reminder_id == Reminder.id)
        .where(*conditions)
        .order_by(Reminder.trigger_at.asc())
    )
    return [ReminderOut.model_validate(row) for row in rows.all()]


@router.post("/reminders/{reminder_id}/actions", response_model=Message, summary="处理提醒")
async def reminder_action(
    reminder_id: str,
    payload: ReminderActionRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Message:
    reminder = await db.get(Reminder, reminder_id)
    if not reminder:
        raise NotFoundError("提醒不存在")
    await get_property_access(db, reminder.property_id, user)

    recipient = await db.scalar(
        select(ReminderRecipient).where(
            ReminderRecipient.reminder_id == reminder_id,
            ReminderRecipient.user_id == user.id,
        )
    )
    now = datetime.utcnow()
    if payload.action == "read":
        if recipient:
            recipient.status = "read"
            recipient.read_at = now
    elif payload.action in {"done", "dismiss"}:
        if recipient:
            recipient.status = payload.action
            recipient.done_at = now
        reminder.status = payload.action
    elif payload.action == "snooze":
        if not payload.snooze_until:
            raise BadRequestError("稍后提醒必须提供 snooze_until")
        if recipient:
            recipient.status = "snoozed"
            recipient.snoozed_until = payload.snooze_until
        reminder.status = "snoozed"
        reminder.snooze_until = payload.snooze_until

    await db.commit()
    return Message(message="提醒状态已更新")
