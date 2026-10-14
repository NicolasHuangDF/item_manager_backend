from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_user,
    get_property_access,
    require_property_admin,
    require_property_write,
)
from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import BadRequestError, NotFoundError, PermissionDeniedError
from app.models import Attachment, AuditLog, Setting, User
from app.schemas import (
    AttachmentOut,
    AuditLogOut,
    Message,
    PageResult,
    SettingOut,
    SettingUpsert,
)

router = APIRouter(tags=["系统"])


def _is_system_admin(user: User) -> bool:
    username = (user.username or "").lower()
    email = (user.email or "").lower()
    return username in {"admin", "administrator"} or email.startswith("admin@")


@router.post(
    "/properties/{property_id}/attachments",
    response_model=AttachmentOut,
    status_code=status.HTTP_201_CREATED,
    summary="上传附件",
)
async def upload_attachment(
    property_id: str,
    owner_type: str = Form(..., max_length=30),
    owner_id: str = Form(...),
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AttachmentOut:
    await require_property_write(db, property_id, user)

    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise BadRequestError(
            f"文件大小不能超过 {settings.MAX_UPLOAD_SIZE // 1024 // 1024}MB"
        )

    safe_name = Path(file.filename or "file").name
    target_dir = Path(settings.UPLOAD_DIR) / property_id
    target_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}_{safe_name}"
    target_path = target_dir / stored_name
    target_path.write_bytes(content)

    attachment = Attachment(
        property_id=property_id,
        owner_type=owner_type,
        owner_id=owner_id,
        file_path=str(target_path),
        file_name=safe_name,
        mime_type=file.content_type,
        file_size=len(content),
        uploaded_by=user.id,
    )
    db.add(attachment)
    await db.commit()
    await db.refresh(attachment)
    return AttachmentOut.model_validate(attachment)


@router.get(
    "/properties/{property_id}/attachments",
    response_model=list[AttachmentOut],
    summary="附件列表",
)
async def list_attachments(
    property_id: str,
    owner_type: str | None = None,
    owner_id: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AttachmentOut]:
    await get_property_access(db, property_id, user)
    conditions = [Attachment.property_id == property_id]
    if owner_type:
        conditions.append(Attachment.owner_type == owner_type)
    if owner_id:
        conditions.append(Attachment.owner_id == owner_id)
    rows = await db.scalars(
        select(Attachment)
        .where(*conditions)
        .order_by(Attachment.created_at.desc())
    )
    return [AttachmentOut.model_validate(row) for row in rows.all()]


@router.get(
    "/attachments/{attachment_id}/download",
    response_class=FileResponse,
    response_model=None,
    summary="下载附件",
)
async def download_attachment(
    attachment_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    attachment = await db.get(Attachment, attachment_id)
    if not attachment:
        raise NotFoundError("附件不存在")
    await get_property_access(db, attachment.property_id, user)
    path = Path(attachment.file_path)
    if not path.exists():
        raise NotFoundError("附件文件不存在")
    return FileResponse(
        path=path,
        filename=attachment.file_name or path.name,
        media_type=attachment.mime_type or "application/octet-stream",
    )


@router.delete("/attachments/{attachment_id}", response_model=Message, summary="删除附件")
async def delete_attachment(
    attachment_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Message:
    attachment = await db.get(Attachment, attachment_id)
    if not attachment:
        raise NotFoundError("附件不存在")
    await require_property_write(db, attachment.property_id, user)
    try:
        Path(attachment.file_path).unlink(missing_ok=True)
    except OSError:
        pass
    await db.delete(attachment)
    await db.commit()
    return Message(message="附件已删除")


@router.get("/settings", response_model=list[SettingOut], summary="配置列表")
async def list_settings(
    scope: str | None = None,
    owner_id: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[SettingOut]:
    if not scope:
        conditions = [Setting.scope == "user", Setting.owner_id == user.id]
    elif scope == "user":
        if owner_id and owner_id != user.id:
            raise PermissionDeniedError("不能查看其他用户配置")
        conditions = [Setting.scope == "user", Setting.owner_id == user.id]
    elif scope == "property":
        if not owner_id:
            return []
        await get_property_access(db, owner_id, user)
        conditions = [Setting.scope == "property", Setting.owner_id == owner_id]
    elif scope == "system":
        if not _is_system_admin(user):
            raise PermissionDeniedError("仅系统管理员可查看系统配置")
        conditions = [Setting.scope == "system"]
    else:
        return []

    rows = await db.scalars(
        select(Setting).where(*conditions).order_by(Setting.scope, Setting.key)
    )
    return [SettingOut.model_validate(row) for row in rows.all()]


@router.get(
    "/settings/{scope}/{owner_id}/{key}", response_model=SettingOut, summary="读取单个配置"
)
async def get_setting(
    scope: str,
    owner_id: str,
    key: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SettingOut:
    if scope == "user" and owner_id != user.id:
        raise PermissionDeniedError("不能查看其他用户配置")
    if scope == "system" and not _is_system_admin(user):
        raise PermissionDeniedError("仅系统管理员可查看系统配置")
    if scope == "property":
        await get_property_access(db, owner_id, user)

    setting = await db.scalar(
        select(Setting).where(
            Setting.scope == scope,
            Setting.owner_id == owner_id,
            Setting.key == key,
        )
    )
    if not setting:
        raise NotFoundError("配置不存在")
    return SettingOut.model_validate(setting)


@router.put("/settings", response_model=SettingOut, summary="新增/更新配置")
async def upsert_setting(
    payload: SettingUpsert,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SettingOut:
    if payload.scope == "system":
        if not _is_system_admin(user):
            raise PermissionDeniedError("仅系统管理员可修改系统配置")
    elif payload.scope == "user":
        if payload.owner_id != user.id:
            raise PermissionDeniedError("只能修改自己的配置")
    elif payload.scope == "property":
        await require_property_admin(db, payload.owner_id, user)

    setting = await db.scalar(
        select(Setting).where(
            Setting.scope == payload.scope,
            Setting.owner_id == payload.owner_id,
            Setting.key == payload.key,
        )
    )
    if setting:
        setting.value = payload.value
        setting.updated_by = user.id
    else:
        setting = Setting(
            scope=payload.scope,
            owner_id=payload.owner_id,
            key=payload.key,
            value=payload.value,
            updated_by=user.id,
        )
        db.add(setting)
    await db.commit()
    await db.refresh(setting)
    return SettingOut.model_validate(setting)


@router.get(
    "/properties/{property_id}/audit-logs",
    response_model=PageResult[AuditLogOut],
    summary="审计日志",
)
async def list_audit_logs(
    property_id: str,
    action: str | None = None,
    entity_type: str | None = None,
    start_at: datetime | None = None,
    end_at: datetime | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PageResult[AuditLogOut]:
    await require_property_admin(db, property_id, user)
    conditions = [AuditLog.property_id == property_id]
    if action:
        conditions.append(AuditLog.action == action)
    if entity_type:
        conditions.append(AuditLog.entity_type == entity_type)
    if start_at:
        conditions.append(AuditLog.created_at >= start_at)
    if end_at:
        conditions.append(AuditLog.created_at <= end_at)

    total = await db.scalar(
        select(func.count()).select_from(AuditLog).where(*conditions)
    )
    rows = await db.scalars(
        select(AuditLog)
        .where(*conditions)
        .order_by(AuditLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return PageResult[AuditLogOut](
        items=[AuditLogOut.model_validate(row) for row in rows.all()],
        total=int(total or 0),
        page=page,
        page_size=page_size,
    )
