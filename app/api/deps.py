from collections.abc import Callable
from datetime import datetime

from fastapi import Depends, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import (
    NotFoundError,
    PermissionDeniedError,
    UnauthorizedError,
)
from app.core.security import decode_token
from app.models import AuditLog, AuthToken, Property, PropertyMember, User

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None or not credentials.credentials:
        raise UnauthorizedError()

    try:
        payload = decode_token(credentials.credentials)
    except ValueError as exc:
        raise UnauthorizedError(str(exc)) from exc

    if payload.get("type") != "access":
        raise UnauthorizedError("令牌类型错误")

    token_id = payload.get("jti")
    user_id = payload.get("sub")
    if not token_id or not user_id:
        raise UnauthorizedError("令牌缺少必要信息")

    token = await db.get(AuthToken, token_id)
    now = datetime.utcnow()
    if (
        not token
        or token.type != "access"
        or token.revoked_at is not None
        or (token.expires_at is not None and token.expires_at < now)
    ):
        raise UnauthorizedError("令牌已失效，请重新登录")

    user = await db.get(User, user_id)
    if not user or user.deleted_at is not None:
        raise UnauthorizedError("用户不存在或已注销")
    if user.status != "active":
        raise PermissionDeniedError("账号已被禁用")

    token.last_used_at = now
    return user


def get_pagination(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict[str, int]:
    return {"page": page, "page_size": page_size, "offset": (page - 1) * page_size}


async def get_property_access(
    db: AsyncSession,
    property_id: str,
    user: User,
    allowed_roles: set[str] | None = None,
) -> tuple[Property, str]:
    """校验用户对房屋的访问权限，返回房屋和当前角色。"""
    prop = await db.get(Property, property_id)
    if not prop or prop.deleted_at is not None:
        raise NotFoundError("房屋不存在")

    member = await db.scalar(
        select(PropertyMember).where(
            PropertyMember.property_id == property_id,
            PropertyMember.user_id == user.id,
            PropertyMember.status == "active",
        )
    )
    role = member.role if member else None
    if role is None and prop.created_by == user.id:
        role = "admin"

    if role is None:
        raise PermissionDeniedError("不是该房屋成员")

    if allowed_roles is not None and role not in allowed_roles:
        raise PermissionDeniedError("当前角色无权执行该操作")

    return prop, role


async def require_property_admin(
    db: AsyncSession,
    property_id: str,
    user: User,
) -> tuple[Property, str]:
    return await get_property_access(db, property_id, user, {"admin"})


async def require_property_write(
    db: AsyncSession,
    property_id: str,
    user: User,
) -> tuple[Property, str]:
    return await get_property_access(db, property_id, user, {"admin", "member"})


def require_property_roles(*roles: str) -> Callable:
    async def dependency(
        property_id: str,
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> tuple[Property, str]:
        return await get_property_access(db, property_id, user, set(roles))

    return dependency


async def write_audit_log(
    db: AsyncSession,
    user: User | None,
    action: str,
    entity_type: str,
    entity_id: str | None = None,
    property_id: str | None = None,
    before_data: dict | None = None,
    after_data: dict | None = None,
    request: Request | None = None,
) -> AuditLog:
    log = AuditLog(
        property_id=property_id,
        user_id=user.id if user else None,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before_data=jsonable_encoder(before_data) if before_data is not None else None,
        after_data=jsonable_encoder(after_data) if after_data is not None else None,
        ip=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent") if request else None,
    )
    db.add(log)
    return log
