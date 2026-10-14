import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_user,
    get_property_access,
    require_property_admin,
    write_audit_log,
)
from app.core.database import get_db
from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.models import Property, PropertyInvitation, PropertyMember, User
from app.schemas import (
    InvitationOut,
    MemberInviteRequest,
    MemberUpdateRequest,
    Message,
    PropertyCreate,
    PropertyMemberOut,
    PropertyOut,
    PropertyUpdate,
    UserOut,
)

router = APIRouter(prefix="/properties", tags=["房屋"])
invitation_router = APIRouter(prefix="/invitations", tags=["房屋邀请"])


def _property_out(prop: Property, role: str | None = None) -> PropertyOut:
    out = PropertyOut.model_validate(prop)
    out.role = role
    return out


@router.get("", response_model=list[PropertyOut], summary="我参与的房屋")
async def list_properties(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[PropertyOut]:
    member_rows = (
        await db.execute(
            select(PropertyMember.property_id, PropertyMember.role).where(
                PropertyMember.user_id == user.id,
                PropertyMember.status == "active",
            )
        )
    ).all()
    role_map = {row.property_id: row.role for row in member_rows}
    prop_ids = set(role_map.keys())

    conditions = [Property.deleted_at.is_(None)]
    if prop_ids:
        conditions.append(
            or_(Property.id.in_(list(prop_ids)), Property.created_by == user.id)
        )
    else:
        conditions.append(Property.created_by == user.id)

    props = list(
        (
            await db.scalars(
                select(Property)
                .where(*conditions)
                .order_by(Property.sort_order, Property.created_at)
            )
        ).all()
    )
    return [
        _property_out(
            prop,
            role_map.get(prop.id, "admin" if prop.created_by == user.id else None),
        )
        for prop in props
    ]


@router.post(
    "",
    response_model=PropertyOut,
    status_code=status.HTTP_201_CREATED,
    summary="创建房屋",
)
async def create_property(
    payload: PropertyCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PropertyOut:
    prop = Property(**payload.model_dump(), created_by=user.id)
    db.add(prop)
    await db.flush()
    db.add(
        PropertyMember(
            property_id=prop.id,
            user_id=user.id,
            role="admin",
            status="active",
            joined_at=datetime.utcnow(),
            invited_by=None,
        )
    )
    await write_audit_log(
        db,
        user,
        action="create",
        entity_type="property",
        entity_id=prop.id,
        property_id=prop.id,
        after_data={"name": prop.name},
    )
    await db.commit()
    await db.refresh(prop)
    return _property_out(prop, "admin")


@router.get("/{property_id}", response_model=PropertyOut, summary="房屋详情")
async def get_property(
    property_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PropertyOut:
    prop, role = await get_property_access(db, property_id, user)
    return _property_out(prop, role)


@router.patch("/{property_id}", response_model=PropertyOut, summary="更新房屋")
async def update_property(
    property_id: str,
    payload: PropertyUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PropertyOut:
    prop, role = await require_property_admin(db, property_id, user)
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(prop, key, value)
    await write_audit_log(
        db,
        user,
        action="update",
        entity_type="property",
        entity_id=prop.id,
        property_id=prop.id,
        after_data=data,
    )
    await db.commit()
    await db.refresh(prop)
    return _property_out(prop, role)


@router.delete("/{property_id}", response_model=Message, summary="删除房屋（软删除）")
async def delete_property(
    property_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Message:
    prop, _ = await require_property_admin(db, property_id, user)
    prop.deleted_at = datetime.utcnow()
    await write_audit_log(
        db,
        user,
        action="delete",
        entity_type="property",
        entity_id=prop.id,
        property_id=prop.id,
    )
    await db.commit()
    return Message(message="房屋已删除")


@router.get(
    "/{property_id}/members",
    response_model=list[PropertyMemberOut],
    summary="房屋成员列表",
)
async def list_members(
    property_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[PropertyMemberOut]:
    await get_property_access(db, property_id, user)
    rows = (
        await db.execute(
            select(PropertyMember, User)
            .join(User, User.id == PropertyMember.user_id)
            .where(PropertyMember.property_id == property_id)
            .order_by(PropertyMember.created_at)
        )
    ).all()
    result = []
    for member, member_user in rows:
        out = PropertyMemberOut.model_validate(member)
        out.user = UserOut.model_validate(member_user)
        result.append(out)
    return result


@router.post(
    "/{property_id}/invitations",
    response_model=InvitationOut,
    status_code=status.HTTP_201_CREATED,
    summary="邀请成员",
)
async def invite_member(
    property_id: str,
    payload: MemberInviteRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InvitationOut:
    await require_property_admin(db, property_id, user)

    existing = await db.scalar(
        select(PropertyInvitation).where(
            PropertyInvitation.property_id == property_id,
            PropertyInvitation.status == "pending",
            or_(
                PropertyInvitation.invitee_email
                == (str(payload.email) if payload.email else None),
                PropertyInvitation.invitee_phone == payload.phone,
            ),
        )
    )
    if existing and existing.expires_at > datetime.utcnow():
        raise ConflictError("该联系人已有待处理的邀请")

    invitation = PropertyInvitation(
        property_id=property_id,
        inviter_user_id=user.id,
        invitee_email=str(payload.email) if payload.email else None,
        invitee_phone=payload.phone,
        token=secrets.token_urlsafe(32),
        role=payload.role,
        status="pending",
        expires_at=datetime.utcnow() + timedelta(days=7),
    )
    db.add(invitation)
    await db.flush()
    await write_audit_log(
        db,
        user,
        action="invite",
        entity_type="property_invitation",
        entity_id=invitation.id,
        property_id=property_id,
        after_data={
            "email": invitation.invitee_email,
            "phone": invitation.invitee_phone,
            "role": payload.role,
        },
    )
    await db.commit()
    await db.refresh(invitation)
    return InvitationOut.model_validate(invitation)


@router.get(
    "/{property_id}/invitations",
    response_model=list[InvitationOut],
    summary="房屋邀请列表",
)
async def list_invitations(
    property_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[InvitationOut]:
    await require_property_admin(db, property_id, user)
    rows = await db.scalars(
        select(PropertyInvitation)
        .where(PropertyInvitation.property_id == property_id)
        .order_by(PropertyInvitation.created_at.desc())
    )
    return [InvitationOut.model_validate(row) for row in rows.all()]


@router.patch(
    "/{property_id}/members/{member_id}",
    response_model=PropertyMemberOut,
    summary="更新成员角色/状态",
)
async def update_member(
    property_id: str,
    member_id: str,
    payload: MemberUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PropertyMemberOut:
    await require_property_admin(db, property_id, user)
    member = await db.get(PropertyMember, member_id)
    if not member or member.property_id != property_id:
        raise NotFoundError("成员不存在")
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(member, key, value)
    if member.status == "removed":
        member.joined_at = None
    await write_audit_log(
        db,
        user,
        action="update_member",
        entity_type="property_member",
        entity_id=member.id,
        property_id=property_id,
        after_data=data,
    )
    await db.commit()
    await db.refresh(member)
    return PropertyMemberOut.model_validate(member)


@router.delete(
    "/{property_id}/members/{member_id}",
    response_model=Message,
    summary="移除成员",
)
async def remove_member(
    property_id: str,
    member_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Message:
    await require_property_admin(db, property_id, user)
    member = await db.get(PropertyMember, member_id)
    if not member or member.property_id != property_id:
        raise NotFoundError("成员不存在")
    member.status = "removed"
    member.joined_at = None
    await write_audit_log(
        db,
        user,
        action="remove_member",
        entity_type="property_member",
        entity_id=member.id,
        property_id=property_id,
    )
    await db.commit()
    return Message(message="成员已移除")


@invitation_router.get("/my", response_model=list[InvitationOut], summary="我收到的邀请")
async def my_invitations(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[InvitationOut]:
    conditions = [PropertyInvitation.status == "pending"]
    if user.email or user.phone:
        conditions.append(
            or_(
                PropertyInvitation.invitee_email == user.email,
                PropertyInvitation.invitee_phone == user.phone,
            )
        )
    else:
        return []

    rows = await db.scalars(
        select(PropertyInvitation)
        .where(*conditions)
        .order_by(PropertyInvitation.created_at.desc())
    )
    return [InvitationOut.model_validate(row) for row in rows.all()]


@invitation_router.post(
    "/{token}/accept",
    response_model=PropertyOut,
    summary="接受房屋邀请",
)
async def accept_invitation(
    token: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PropertyOut:
    invitation = await db.scalar(
        select(PropertyInvitation).where(PropertyInvitation.token == token)
    )
    if not invitation:
        raise NotFoundError("邀请不存在")
    if invitation.status != "pending":
        raise BadRequestError("邀请已失效")
    if invitation.expires_at < datetime.utcnow():
        invitation.status = "expired"
        await db.commit()
        raise BadRequestError("邀请已过期")

    invitation.status = "accepted"
    invitation.accepted_by = user.id
    invitation.accepted_at = datetime.utcnow()

    member = await db.scalar(
        select(PropertyMember).where(
            PropertyMember.property_id == invitation.property_id,
            PropertyMember.user_id == user.id,
        )
    )
    if member:
        member.role = invitation.role
        member.status = "active"
        member.joined_at = datetime.utcnow()
    else:
        member = PropertyMember(
            property_id=invitation.property_id,
            user_id=user.id,
            role=invitation.role,
            status="active",
            joined_at=datetime.utcnow(),
            invited_by=invitation.inviter_user_id,
        )
        db.add(member)

    prop = await db.get(Property, invitation.property_id)
    if not prop or prop.deleted_at is not None:
        raise NotFoundError("房屋不存在")

    await write_audit_log(
        db,
        user,
        action="accept_invitation",
        entity_type="property_invitation",
        entity_id=invitation.id,
        property_id=prop.id,
    )
    await db.commit()
    await db.refresh(prop)
    return _property_out(prop, invitation.role)
