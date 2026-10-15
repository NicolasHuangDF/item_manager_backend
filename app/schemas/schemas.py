from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

T = TypeVar("T")


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Message(BaseModel):
    message: str


class PageResult(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# 用户与认证
# ---------------------------------------------------------------------------
class UserOut(ORMModel):
    id: str
    username: str | None = None
    email: str | None = None
    phone: str | None = None
    display_name: str | None = None
    avatar_url: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime


class UserUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=100)
    avatar_url: str | None = None
    phone: str | None = Field(default=None, max_length=32)
    username: str | None = Field(default=None, min_length=3, max_length=64)
    email: EmailStr | None = None


class RegisterRequest(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=64)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, min_length=5, max_length=32)
    password: str = Field(min_length=8, max_length=128)
    display_name: str | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def ensure_identifier(self) -> "RegisterRequest":
        if not any([self.username, self.email, self.phone]):
            raise ValueError("用户名、邮箱、手机号至少填写一项")
        return self


class LoginRequest(BaseModel):
    account: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(min_length=8, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


# ---------------------------------------------------------------------------
# 房屋、成员与邀请
# ---------------------------------------------------------------------------
class PropertyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    address: str | None = None
    type: str | None = Field(default=None, max_length=50)
    sort_order: int = 0
    notes: str | None = None


class PropertyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    address: str | None = None
    type: str | None = Field(default=None, max_length=50)
    sort_order: int | None = None
    notes: str | None = None


class PropertyOut(ORMModel):
    id: str
    name: str
    address: str | None = None
    type: str | None = None
    sort_order: int
    notes: str | None = None
    created_by: str
    created_at: datetime
    updated_at: datetime
    role: str | None = None


class MemberInviteRequest(BaseModel):
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=32)
    role: Literal["admin", "member", "guest"] = "member"

    @model_validator(mode="after")
    def ensure_contact(self) -> "MemberInviteRequest":
        if not self.email and not self.phone:
            raise ValueError("邮箱或手机号至少填写一项")
        return self


class MemberUpdateRequest(BaseModel):
    role: Literal["admin", "member", "guest"] | None = None
    status: Literal["active", "invited", "removed"] | None = None


class PropertyMemberOut(ORMModel):
    id: str
    property_id: str
    user_id: str
    role: str
    status: str
    joined_at: datetime | None = None
    invited_by: str | None = None
    created_at: datetime
    user: UserOut | None = None


class InvitationOut(ORMModel):
    id: str
    property_id: str
    inviter_user_id: str
    invitee_email: str | None = None
    invitee_phone: str | None = None
    token: str
    role: str
    status: str
    expires_at: datetime
    accepted_by: str | None = None
    accepted_at: datetime | None = None
    created_at: datetime


# ---------------------------------------------------------------------------
# 单位、分类、标签
# ---------------------------------------------------------------------------
class UnitCreate(BaseModel):
    category_id: str | None = Field(default=None, description="关联分类ID；为空表示通用单位")
    name: str = Field(min_length=1, max_length=50)
    symbol: str | None = Field(default=None, max_length=20)
    decimal_places: int = Field(default=0, ge=0, le=6)
    is_public: bool = False


class UnitUpdate(BaseModel):
    category_id: str | None = Field(default=None, description="关联分类ID；显式传 null 表示改为通用单位")
    name: str | None = Field(default=None, min_length=1, max_length=50)
    symbol: str | None = Field(default=None, max_length=20)
    decimal_places: int | None = Field(default=None, ge=0, le=6)
    is_public: bool | None = None


class UnitOut(ORMModel):
    id: str
    property_id: str | None = None
    category_id: str | None = None
    name: str
    symbol: str | None = None
    decimal_places: int
    created_by: str | None = None
    is_public: bool
    review_status: str
    review_remark: str | None = None
    created_at: datetime
    updated_at: datetime


class ReviewRequest(BaseModel):
    approve: bool
    remark: str | None = Field(default=None, max_length=500)


class CategoryCreate(BaseModel):
    parent_id: str | None = None
    name: str = Field(min_length=1, max_length=100)
    icon: str | None = Field(default=None, max_length=100)
    default_unit_id: str | None = None
    default_low_stock_threshold: Decimal | None = Field(default=None, ge=0)
    default_expiry_warning_days: int | None = Field(default=None, ge=0)
    sort_order: int = 0
    is_public: bool = False


class CategoryUpdate(BaseModel):
    parent_id: str | None = None
    name: str | None = Field(default=None, min_length=1, max_length=100)
    icon: str | None = Field(default=None, max_length=100)
    default_unit_id: str | None = None
    default_low_stock_threshold: Decimal | None = Field(default=None, ge=0)
    default_expiry_warning_days: int | None = Field(default=None, ge=0)
    sort_order: int | None = None
    is_public: bool | None = None


class CategoryOut(ORMModel):
    id: str
    property_id: str | None = None
    parent_id: str | None = None
    name: str
    icon: str | None = None
    default_unit_id: str | None = None
    default_low_stock_threshold: Decimal | None = None
    default_expiry_warning_days: int | None = None
    sort_order: int
    created_by: str | None = None
    is_public: bool
    review_status: str
    created_at: datetime
    updated_at: datetime


class TagCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    color: str | None = Field(default=None, max_length=20)
    is_public: bool = False


class TagUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    color: str | None = Field(default=None, max_length=20)
    is_public: bool | None = None


class TagOut(ORMModel):
    id: str
    property_id: str | None = None
    name: str
    color: str | None = None
    created_by: str | None = None
    is_public: bool
    review_status: str
    created_at: datetime
    updated_at: datetime


class TagSetRequest(BaseModel):
    tag_ids: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# 容器
# ---------------------------------------------------------------------------
class ContainerCreate(BaseModel):
    parent_id: str | None = None
    name: str = Field(min_length=1, max_length=100)
    type: str = Field(default="other", max_length=50)
    qr_code: str | None = Field(default=None, max_length=255)
    icon: str | None = Field(default=None, max_length=100)
    color: str | None = Field(default=None, max_length=20)
    sort_order: int = 0
    attributes: dict[str, Any] | None = None
    is_active: bool = True


class ContainerUpdate(BaseModel):
    parent_id: str | None = None
    name: str | None = Field(default=None, min_length=1, max_length=100)
    type: str | None = Field(default=None, max_length=50)
    qr_code: str | None = Field(default=None, max_length=255)
    icon: str | None = Field(default=None, max_length=100)
    color: str | None = Field(default=None, max_length=20)
    sort_order: int | None = None
    attributes: dict[str, Any] | None = None
    is_active: bool | None = None


class ContainerOut(ORMModel):
    id: str
    property_id: str
    parent_id: str | None = None
    name: str
    type: str
    qr_code: str | None = None
    icon: str | None = None
    color: str | None = None
    sort_order: int
    attributes: dict[str, Any] | None = None
    is_active: bool
    created_by: str
    updated_by: str | None = None
    created_at: datetime
    updated_at: datetime


class ContainerTreeOut(ContainerOut):
    children: list[ContainerTreeOut] = Field(default_factory=list)


ContainerTreeOut.model_rebuild()


# ---------------------------------------------------------------------------
# 物品与库存
# ---------------------------------------------------------------------------
class ItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    category_id: str | None = None
    brand: str | None = Field(default=None, max_length=100)
    model: str | None = Field(default=None, max_length=100)
    barcode: str | None = Field(default=None, max_length=100)
    unit_id: str | None = None
    default_container_id: str | None = None
    image_url: str | None = None
    notes: str | None = None
    track_inventory: bool = True
    track_expiry: bool = False
    is_consumable: bool = False
    low_stock_threshold: Decimal | None = Field(default=None, ge=0)
    expiry_warning_days: int | None = Field(default=None, ge=0)
    opened_expiry_days: int | None = Field(default=None, ge=0)
    default_shelf_life_days: int | None = Field(default=None, ge=0)
    attributes: dict[str, Any] | None = None


class ItemUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    category_id: str | None = None
    brand: str | None = Field(default=None, max_length=100)
    model: str | None = Field(default=None, max_length=100)
    barcode: str | None = Field(default=None, max_length=100)
    unit_id: str | None = None
    default_container_id: str | None = None
    image_url: str | None = None
    notes: str | None = None
    track_inventory: bool | None = None
    track_expiry: bool | None = None
    is_consumable: bool | None = None
    low_stock_threshold: Decimal | None = Field(default=None, ge=0)
    expiry_warning_days: int | None = Field(default=None, ge=0)
    opened_expiry_days: int | None = Field(default=None, ge=0)
    default_shelf_life_days: int | None = Field(default=None, ge=0)
    attributes: dict[str, Any] | None = None


class ItemOut(ORMModel):
    id: str
    property_id: str
    name: str
    category_id: str | None = None
    brand: str | None = None
    model: str | None = None
    barcode: str | None = None
    unit_id: str | None = None
    default_container_id: str | None = None
    image_url: str | None = None
    notes: str | None = None
    track_inventory: bool
    track_expiry: bool
    is_consumable: bool
    low_stock_threshold: Decimal | None = None
    expiry_warning_days: int | None = None
    opened_expiry_days: int | None = None
    default_shelf_life_days: int | None = None
    attributes: dict[str, Any] | None = None
    current_quantity: Decimal
    created_by: str
    updated_by: str | None = None
    created_at: datetime
    updated_at: datetime


class BatchOut(ORMModel):
    id: str
    property_id: str
    item_id: str
    container_id: str
    quantity: Decimal
    unit_id: str | None = None
    production_date: date | None = None
    expiry_date: date | None = None
    opened_at: datetime | None = None
    opened_expiry_date: date | None = None
    status: str
    note: str | None = None
    created_by: str
    created_at: datetime
    updated_at: datetime


class ItemDetailOut(ItemOut):
    tags: list[TagOut] = Field(default_factory=list)
    batches: list[BatchOut] = Field(default_factory=list)


class StockInRequest(BaseModel):
    container_id: str
    quantity: Decimal = Field(gt=0)
    unit_id: str | None = None
    production_date: date | None = None
    expiry_date: date | None = None
    note: str | None = None


class StockOutRequest(BaseModel):
    quantity: Decimal = Field(gt=0)
    batch_id: str | None = None
    container_id: str | None = None
    reason: str | None = None


class StockMoveRequest(BaseModel):
    from_container_id: str
    to_container_id: str
    quantity: Decimal = Field(gt=0)
    batch_id: str | None = None
    reason: str | None = None


class StockAdjustRequest(BaseModel):
    batch_id: str
    new_quantity: Decimal = Field(ge=0)
    reason: str | None = None


class TransactionOut(ORMModel):
    id: str
    property_id: str
    item_id: str
    batch_id: str | None = None
    container_id: str | None = None
    type: str
    quantity_delta: Decimal
    quantity_after: Decimal | None = None
    unit_id: str | None = None
    reason: str | None = None
    created_by: str
    created_at: datetime


# ---------------------------------------------------------------------------
# 提醒
# ---------------------------------------------------------------------------
class ReminderCreate(BaseModel):
    type: Literal["expiry", "opened_expiry", "low_stock", "custom"]
    item_id: str | None = None
    batch_id: str | None = None
    container_id: str | None = None
    trigger_at: datetime
    threshold: Decimal | None = Field(default=None, ge=0)
    message: str | None = None
    dedupe_key: str | None = Field(default=None, max_length=255)


class ReminderUpdate(BaseModel):
    trigger_at: datetime | None = None
    status: Literal["pending", "done", "snoozed", "dismissed"] | None = None
    snooze_until: datetime | None = None
    message: str | None = None
    threshold: Decimal | None = Field(default=None, ge=0)


class ReminderOut(ORMModel):
    id: str
    property_id: str
    type: str
    item_id: str | None = None
    batch_id: str | None = None
    container_id: str | None = None
    trigger_at: datetime
    threshold: Decimal | None = None
    status: str
    snooze_until: datetime | None = None
    last_notified_at: datetime | None = None
    message: str | None = None
    dedupe_key: str
    created_by: str | None = None
    created_at: datetime
    updated_at: datetime


class ReminderActionRequest(BaseModel):
    action: Literal["read", "done", "snooze", "dismiss"]
    snooze_until: datetime | None = None


# ---------------------------------------------------------------------------
# 通知
# ---------------------------------------------------------------------------
class ChannelCreate(BaseModel):
    property_id: str | None = None
    type: Literal["email", "push", "bark", "telegram", "webhook"]
    config: dict[str, Any] | None = None
    is_enabled: bool = True


class ChannelUpdate(BaseModel):
    config: dict[str, Any] | None = None
    is_enabled: bool | None = None
    property_id: str | None = None


class ChannelOut(ORMModel):
    id: str
    user_id: str
    property_id: str | None = None
    type: str
    config: dict[str, Any] | None = None
    is_enabled: bool
    verified_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class PreferenceCreate(BaseModel):
    property_id: str | None = None
    event_type: str = Field(min_length=1, max_length=50)
    channel_id: str | None = None
    enabled: bool = True
    advance_days: int | None = Field(default=None, ge=0)
    quiet_hours: dict[str, Any] | None = None


class PreferenceUpdate(BaseModel):
    event_type: str | None = Field(default=None, max_length=50)
    channel_id: str | None = None
    enabled: bool | None = None
    advance_days: int | None = Field(default=None, ge=0)
    quiet_hours: dict[str, Any] | None = None


class PreferenceOut(ORMModel):
    id: str
    user_id: str
    property_id: str | None = None
    event_type: str
    channel_id: str | None = None
    enabled: bool
    advance_days: int | None = None
    quiet_hours: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


class NotificationOut(ORMModel):
    id: str
    property_id: str | None = None
    user_id: str
    reminder_id: str | None = None
    channel_id: str | None = None
    title: str | None = None
    body: str | None = None
    payload: dict[str, Any] | None = None
    status: str
    sent_at: datetime | None = None
    read_at: datetime | None = None
    error_message: str | None = None
    created_at: datetime


# ---------------------------------------------------------------------------
# 附件、配置、审计、看板
# ---------------------------------------------------------------------------
class AttachmentOut(ORMModel):
    id: str
    property_id: str
    owner_type: str
    owner_id: str
    file_path: str
    file_name: str | None = None
    mime_type: str | None = None
    file_size: int | None = None
    uploaded_by: str
    created_at: datetime


class SettingUpsert(BaseModel):
    scope: Literal["system", "user", "property"]
    owner_id: str
    key: str = Field(min_length=1, max_length=100)
    value: Any = None


class SettingOut(ORMModel):
    id: str
    scope: str
    owner_id: str
    key: str
    value: Any = None
    updated_by: str | None = None
    updated_at: datetime


class AuditLogOut(ORMModel):
    id: str
    property_id: str | None = None
    user_id: str | None = None
    action: str
    entity_type: str
    entity_id: str | None = None
    before_data: dict[str, Any] | None = None
    after_data: dict[str, Any] | None = None
    ip: str | None = None
    user_agent: str | None = None
    created_at: datetime


class DashboardSummary(BaseModel):
    property_id: str
    item_count: int
    container_count: int
    member_count: int
    low_stock_count: int
    expiring_count: int
    pending_reminder_count: int
    total_quantity: Decimal
