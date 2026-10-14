from fastapi import APIRouter, Depends
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.exceptions import BadRequestError, ConflictError
from app.core.security import hash_password, verify_password
from app.models import User
from app.schemas import ChangePasswordRequest, Message, UserOut, UserUpdate

router = APIRouter(prefix="/users", tags=["用户"])


@router.get("/me", response_model=UserOut, summary="获取个人资料")
async def get_me(user: User = Depends(get_current_user)) -> User:
    return user


@router.patch("/me", response_model=UserOut, summary="更新个人资料")
async def update_me(
    payload: UserUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    data = payload.model_dump(exclude_unset=True)
    if "email" in data and data["email"] is not None:
        data["email"] = str(data["email"])

    if any(key in data for key in ("username", "email", "phone")):
        conditions = []
        if data.get("username"):
            conditions.append(User.username == data["username"])
        if data.get("email"):
            conditions.append(User.email == data["email"])
        if data.get("phone"):
            conditions.append(User.phone == data["phone"])
        if conditions:
            existing = await db.scalar(
                select(User).where(or_(*conditions), User.id != user.id)
            )
            if existing:
                raise ConflictError("用户名、邮箱或手机号已被占用")

    for key, value in data.items():
        setattr(user, key, value)

    await db.commit()
    await db.refresh(user)
    return user


@router.post("/me/change-password", response_model=Message, summary="修改密码")
async def change_password(
    payload: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Message:
    if not verify_password(payload.old_password, user.password_hash):
        raise BadRequestError("原密码不正确")
    user.password_hash = hash_password(payload.new_password)
    await db.commit()
    return Message(message="密码修改成功")
