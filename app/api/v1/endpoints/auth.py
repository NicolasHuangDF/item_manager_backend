from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Request
from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import bearer_scheme, get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models import AuthToken, User
from app.schemas import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserOut,
)

router = APIRouter(prefix="/auth", tags=["认证"])


def _client_info(request: Request) -> tuple[dict, str | None]:
    return (
        {"user_agent": request.headers.get("user-agent")},
        request.client.host if request.client else None,
    )


def _naive_utc(expire: object) -> datetime:
    if isinstance(expire, datetime):
        return expire.replace(tzinfo=None)
    return datetime.utcfromtimestamp(float(expire))  # type: ignore[arg-type]


async def _save_token(
    db: AsyncSession,
    token: str,
    payload: dict,
    token_type: str,
    request: Request,
) -> AuthToken:
    device_info, ip = _client_info(request)
    record = AuthToken(
        id=payload["jti"],
        user_id=payload["sub"],
        token_hash=hash_token(token),
        type=token_type,
        expires_at=_naive_utc(payload["exp"]),
        device_info=device_info,
        ip=ip,
        last_used_at=datetime.utcnow(),
    )
    db.add(record)
    return record


async def _issue_tokens(db: AsyncSession, user: User, request: Request) -> TokenResponse:
    access_token, access_payload = create_access_token(user.id)
    refresh_token, refresh_payload = create_refresh_token(user.id)
    await _save_token(db, access_token, access_payload, "access", request)
    await _save_token(db, refresh_token, refresh_payload, "refresh", request)
    await db.commit()
    await db.refresh(user)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserOut.model_validate(user),
    )


@router.post("/register", response_model=TokenResponse, summary="注册并登录")
async def register(
    payload: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    conditions = []
    if payload.username:
        conditions.append(User.username == payload.username)
    if payload.email:
        conditions.append(User.email == str(payload.email))
    if payload.phone:
        conditions.append(User.phone == payload.phone)

    existing = await db.scalar(select(User).where(or_(*conditions))) if conditions else None
    if existing:
        raise ConflictError("用户名、邮箱或手机号已被占用")

    user = User(
        username=payload.username,
        email=str(payload.email) if payload.email else None,
        phone=payload.phone,
        password_hash=hash_password(payload.password),
        display_name=payload.display_name or payload.username or "新用户",
        status="active",
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return await _issue_tokens(db, user, request)


@router.post("/login", response_model=TokenResponse, summary="账号密码登录")
async def login(
    payload: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    account = payload.account.strip()
    user = await db.scalar(
        select(User).where(
            or_(
                User.username == account,
                User.email == account,
                User.phone == account,
            ),
            User.deleted_at.is_(None),
        )
    )
    if not user or not verify_password(payload.password, user.password_hash):
        raise UnauthorizedError("账号或密码错误")
    if user.status != "active":
        raise UnauthorizedError("账号已被禁用")
    return await _issue_tokens(db, user, request)


@router.post("/refresh", response_model=TokenResponse, summary="刷新令牌")
async def refresh_token(
    payload: RefreshRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    try:
        token_payload = decode_token(payload.refresh_token)
    except ValueError as exc:
        raise UnauthorizedError(str(exc)) from exc

    if token_payload.get("type") != "refresh":
        raise UnauthorizedError("刷新令牌类型错误")

    token_id = token_payload.get("jti")
    user_id = token_payload.get("sub")
    record = await db.get(AuthToken, token_id) if token_id else None
    now = datetime.utcnow()
    if (
        not record
        or record.type != "refresh"
        or record.revoked_at is not None
        or (record.expires_at is not None and record.expires_at < now)
    ):
        raise UnauthorizedError("刷新令牌已失效")

    user = await db.get(User, user_id)
    if not user or user.deleted_at is not None or user.status != "active":
        raise UnauthorizedError("用户不存在或不可用")

    record.revoked_at = now
    return await _issue_tokens(db, user, request)


@router.post("/logout", summary="退出当前会话")
async def logout(
    credentials=Depends(bearer_scheme),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if credentials and credentials.credentials:
        try:
            payload = decode_token(credentials.credentials)
            token = await db.get(AuthToken, payload.get("jti"))
            if token and token.user_id == user.id:
                token.revoked_at = datetime.utcnow()
        except ValueError:
            pass
    await db.commit()
    return {"message": "已退出登录"}


@router.post("/logout-all", summary="退出全部会话")
async def logout_all(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await db.execute(
        update(AuthToken)
        .where(AuthToken.user_id == user.id, AuthToken.revoked_at.is_(None))
        .values(revoked_at=datetime.utcnow())
    )
    await db.commit()
    return {"message": "已退出全部会话"}


@router.get("/me", response_model=UserOut, summary="当前用户信息")
async def me(user: User = Depends(get_current_user)) -> User:
    return user
