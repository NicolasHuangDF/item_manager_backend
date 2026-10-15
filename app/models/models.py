"""与 MySQL 重建脚本 sql/item_manager_create.sql 完全对应的 SQLAlchemy ORM 模型。

外键名、索引名、唯一约束名与建表脚本逐字一致，使 ``Base.metadata.create_all``
产出的结构与该脚本等价，模型与线上表结构不会出现漂移。
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CHAR,
    Computed,
    Date,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import (
    Base,
    DateTimeMS,
    ID_LENGTH,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDMixin,
    new_uuid,
)


class User(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "users"

    username: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="用户名，唯一")
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="邮箱，唯一")
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="手机号，唯一")
    password_hash: Mapped[str] = mapped_column(Text, nullable=False, comment="密码哈希")
    display_name: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="显示名称")
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True, comment="头像URL")
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'active'"),
        comment="状态：active/disabled/deleted",
    )

    __table_args__ = (
        UniqueConstraint("username", name="uk_users_username"),
        UniqueConstraint("email", name="uk_users_email"),
        UniqueConstraint("phone", name="uk_users_phone"),
    )


class AuthToken(UUIDMixin, Base):
    __tablename__ = "auth_tokens"

    user_id: Mapped[str] = mapped_column(
        CHAR(ID_LENGTH),
        ForeignKey("users.id", name="fk_auth_tokens_user", ondelete="CASCADE"),
        nullable=False,
        comment="用户ID",
    )
    token_hash: Mapped[str] = mapped_column(Text, nullable=False, comment="令牌哈希")
    type: Mapped[str] = mapped_column(String(20), nullable=False, comment="类型：access/refresh/session/api_key")
    expires_at: Mapped[datetime | None] = mapped_column(DateTimeMS, nullable=True, comment="过期时间")
    revoked_at: Mapped[datetime | None] = mapped_column(DateTimeMS, nullable=True, comment="撤销时间")
    device_info: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="设备信息JSON")
    ip: Mapped[str | None] = mapped_column(String(45), nullable=True, comment="IP地址")
    created_at: Mapped[datetime] = mapped_column(
        DateTimeMS,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP(3)"),
        comment="创建时间",
    )
    last_used_at: Mapped[datetime | None] = mapped_column(DateTimeMS, nullable=True, comment="最后使用时间")

    __table_args__ = (
        Index("idx_auth_tokens_user", "user_id"),
        Index("idx_auth_tokens_expires", "expires_at"),
    )


class Property(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "properties"

    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="房屋名称")
    address: Mapped[str | None] = mapped_column(Text, nullable=True, comment="地址")
    type: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="房屋类型")
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0"),
        comment="排序",
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")
    created_by: Mapped[str] = mapped_column(
        CHAR(ID_LENGTH),
        ForeignKey("users.id", name="fk_properties_created_by", ondelete="RESTRICT"),
        nullable=False,
        comment="创建人用户ID",
    )

    __table_args__ = (Index("idx_properties_created_by", "created_by"),)


class Setting(UUIDMixin, Base):
    __tablename__ = "settings"

    scope: Mapped[str] = mapped_column(String(20), nullable=False, comment="范围：system/user/property")
    owner_id: Mapped[str] = mapped_column(
        CHAR(ID_LENGTH),
        nullable=False,
        server_default=text("'00000000000000000000000000000000'"),
        comment="所有者ID：system为全零UUID，user为users.id，property为properties.id",
    )
    key: Mapped[str] = mapped_column("key", String(100), nullable=False, comment="配置键")
    value: Mapped[Any | None] = mapped_column(JSON, nullable=True, comment="配置值JSON")
    updated_by: Mapped[str | None] = mapped_column(
        CHAR(ID_LENGTH),
        ForeignKey("users.id", name="fk_settings_updated_by", ondelete="RESTRICT"),
        nullable=True,
        comment="更新人用户ID",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTimeMS,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3)"),
        onupdate=text("CURRENT_TIMESTAMP(3)"),
        comment="更新时间",
    )

    __table_args__ = (
        UniqueConstraint("scope", "owner_id", "key", name="uk_settings_scope_owner_key"),
        Index("fk_settings_updated_by", "updated_by"),
    )


class PropertyMember(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "property_members"

    property_id: Mapped[str] = mapped_column(
        CHAR(ID_LENGTH),
        ForeignKey("properties.id", name="fk_pm_property", ondelete="CASCADE"),
        nullable=False,
        comment="房屋ID",
    )
    user_id: Mapped[str] = mapped_column(
        CHAR(ID_LENGTH),
        ForeignKey("users.id", name="fk_pm_user", ondelete="CASCADE"),
        nullable=False,
        comment="用户ID",
    )
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'member'"),
        comment="角色：admin/member/guest",
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'active'"),
        comment="状态：active/invited/removed",
    )
    joined_at: Mapped[datetime | None] = mapped_column(DateTimeMS, nullable=True, comment="加入时间")
    invited_by: Mapped[str | None] = mapped_column(
        CHAR(ID_LENGTH),
        ForeignKey("users.id", name="fk_pm_invited_by", ondelete="RESTRICT"),
        nullable=True,
        comment="邀请人用户ID",
    )

    __table_args__ = (
        UniqueConstraint("property_id", "user_id", name="uk_property_members"),
        Index("idx_property_members_user", "user_id"),
        Index("idx_property_members_role", "property_id", "role"),
        Index("fk_pm_invited_by", "invited_by"),
    )


class PropertyInvitation(UUIDMixin, Base):
    __tablename__ = "property_invitations"

    property_id: Mapped[str] = mapped_column(
        CHAR(ID_LENGTH),
        ForeignKey("properties.id", name="fk_pi_property", ondelete="CASCADE"),
        nullable=False,
        comment="房屋ID",
    )
    inviter_user_id: Mapped[str] = mapped_column(
        CHAR(ID_LENGTH),
        ForeignKey("users.id", name="fk_pi_inviter", ondelete="RESTRICT"),
        nullable=False,
        comment="邀请人用户ID",
    )
    invitee_email: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="被邀请人邮箱")
    invitee_phone: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="被邀请人手机号")
    token: Mapped[str] = mapped_column(String(255), nullable=False, comment="邀请令牌")
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'member'"),
        comment="邀请角色：admin/member/guest",
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'pending'"),
        comment="状态：pending/accepted/expired/cancelled",
    )
    expires_at: Mapped[datetime] = mapped_column(DateTimeMS, nullable=False, comment="过期时间")
    accepted_by: Mapped[str | None] = mapped_column(
        CHAR(ID_LENGTH),
        ForeignKey("users.id", name="fk_pi_accepted_by", ondelete="RESTRICT"),
        nullable=True,
        comment="接受人用户ID",
    )
    accepted_at: Mapped[datetime | None] = mapped_column(DateTimeMS, nullable=True, comment="接受时间")
    created_at: Mapped[datetime] = mapped_column(
        DateTimeMS,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP(3)"),
        comment="创建时间",
    )

    __table_args__ = (
        UniqueConstraint("token", name="uk_property_invitations_token"),
        Index("idx_pi_property", "property_id"),
        Index("idx_pi_status", "status", "expires_at"),
        Index("fk_pi_inviter", "inviter_user_id"),
        Index("fk_pi_accepted_by", "accepted_by"),
    )


class Unit(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "units"

    property_id: Mapped[str | None] = mapped_column(
        CHAR(ID_LENGTH),
        ForeignKey("properties.id", name="fk_units_property", ondelete="SET NULL"),
        nullable=True,
        comment="来源房屋ID，仅用于追踪，审核通过后可为空，建议is_public=0时保留",
    )
    category_id: Mapped[str | None] = mapped_column(
        CHAR(ID_LENGTH),
        ForeignKey("categories.id", name="fk_units_category", ondelete="SET NULL"),
        nullable=True,
        comment="关联物品分类ID；NULL 表示通用单位，非 NULL 表示仅限该分类使用",
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False, comment="单位名称")
    symbol: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="单位符号")
    decimal_places: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0"),
        comment="小数位数",
    )
    created_by: Mapped[str | None] = mapped_column(
        CHAR(ID_LENGTH),
        ForeignKey("users.id", name="fk_units_created_by", ondelete="SET NULL"),
        nullable=True,
        comment="创建人用户ID，系统预置可为空",
    )
    is_public: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("0"),
        comment="是否公共：0私有1公共",
    )
    review_status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'pending'"),
        comment="审核状态：pending/approved/rejected",
    )
    reviewed_by: Mapped[str | None] = mapped_column(
        CHAR(ID_LENGTH),
        ForeignKey("users.id", name="fk_units_reviewed_by", ondelete="SET NULL"),
        nullable=True,
        comment="审核人用户ID",
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTimeMS, nullable=True, comment="审核时间")
    review_remark: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="审核备注")
    published_at: Mapped[datetime | None] = mapped_column(DateTimeMS, nullable=True, comment="转为公共的时间")
    # 注意：units 表**没有** name_public_unique 生成列，也没有 uk_units_public_name 唯一索引。
    # 公共单位的重名规则改为由数据库触发器
    # trg_units_public_unique_before_insert / _before_update 强制：
    #   * 通用单位（category_id 为空）名称全局唯一；
    #   * 分类单位不得与通用单位同名，且在同一分类内唯一（不同分类可重名）。
    # 因此这里不能声明该列，否则查询会拼出不存在的字段
    # （Unknown column 'units.name_public_unique'）。

    __table_args__ = (
        Index("idx_units_review", "review_status", "is_public"),
        Index("idx_units_created_by", "created_by"),
        Index("idx_units_public", "is_public", "deleted_at"),
        Index("idx_units_scope", "is_public", "category_id", "property_id"),
        Index("fk_units_property", "property_id"),
        Index("fk_units_reviewed_by", "reviewed_by"),
        Index("fk_units_category", "category_id"),
    )


class Category(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "categories"

    property_id: Mapped[str | None] = mapped_column(
        CHAR(ID_LENGTH),
        ForeignKey("properties.id", name="fk_categories_property", ondelete="SET NULL"),
        nullable=True,
        comment="来源房屋ID，仅用于追踪，审核通过后可为空",
    )
    parent_id: Mapped[str | None] = mapped_column(
        CHAR(ID_LENGTH),
        ForeignKey("categories.id", name="fk_categories_parent", ondelete="SET NULL"),
        nullable=True,
        comment="父分类ID",
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="分类名称")
    icon: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="图标")
    default_unit_id: Mapped[str | None] = mapped_column(
        CHAR(ID_LENGTH),
        ForeignKey("units.id", name="fk_categories_unit", ondelete="SET NULL"),
        nullable=True,
        comment="默认单位ID",
    )
    default_low_stock_threshold: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 3), nullable=True,
        comment="默认低库存阈值",
    )
    default_expiry_warning_days: Mapped[int | None] = mapped_column(
        Integer, nullable=True,
        comment="默认过期提前提醒天数",
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0"),
        comment="排序",
    )
    created_by: Mapped[str | None] = mapped_column(
        CHAR(ID_LENGTH),
        ForeignKey("users.id", name="fk_categories_created_by", ondelete="SET NULL"),
        nullable=True,
        comment="创建人用户ID，系统预置可为空",
    )
    is_public: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("0"),
        comment="是否公共：0私有1公共",
    )
    review_status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'pending'"),
        comment="审核状态：pending/approved/rejected",
    )
    reviewed_by: Mapped[str | None] = mapped_column(
        CHAR(ID_LENGTH),
        ForeignKey("users.id", name="fk_categories_reviewed_by", ondelete="SET NULL"),
        nullable=True,
        comment="审核人用户ID",
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTimeMS, nullable=True, comment="审核时间")
    review_remark: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="审核备注")
    published_at: Mapped[datetime | None] = mapped_column(DateTimeMS, nullable=True, comment="转为公共的时间")
    name_public_unique: Mapped[str | None] = mapped_column(
        String(100),
        Computed(
            "(CASE WHEN is_public = 1 AND deleted_at IS NULL THEN name ELSE NULL END)",
            persisted=True,
        ),
        nullable=True,
        sort_order=200,
        comment="公共命名唯一键，仅公共记录参与唯一约束",
    )

    __table_args__ = (
        UniqueConstraint("name_public_unique", name="uk_categories_public_name"),
        Index("idx_categories_property_parent", "property_id", "parent_id"),
        Index("idx_categories_review", "review_status", "is_public"),
        Index("idx_categories_created_by", "created_by"),
        Index("idx_categories_public", "is_public", "deleted_at"),
        Index("fk_categories_parent", "parent_id"),
        Index("fk_categories_unit", "default_unit_id"),
        Index("fk_categories_reviewed_by", "reviewed_by"),
    )


class Container(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "containers"

    property_id: Mapped[str] = mapped_column(
        CHAR(ID_LENGTH),
        ForeignKey("properties.id", name="fk_containers_property", ondelete="CASCADE"),
        nullable=False,
        comment="所属房屋ID",
    )
    parent_id: Mapped[str | None] = mapped_column(
        CHAR(ID_LENGTH),
        ForeignKey("containers.id", name="fk_containers_parent", ondelete="CASCADE"),
        nullable=True,
        comment="父容器ID",
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="容器名称")
    type: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default=text("'other'"),
        comment="容器类型：room/cabinet/drawer/shelf/grid/box/fridge/freezer/appliance/other",
    )
    qr_code: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="二维码")
    icon: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="图标")
    color: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="颜色")
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0"),
        comment="排序",
    )
    attributes: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="扩展属性JSON")
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("1"),
        comment="是否启用：0否1是",
    )
    created_by: Mapped[str] = mapped_column(
        CHAR(ID_LENGTH),
        ForeignKey("users.id", name="fk_containers_created_by", ondelete="RESTRICT"),
        nullable=False,
        comment="创建人用户ID",
    )
    updated_by: Mapped[str | None] = mapped_column(
        CHAR(ID_LENGTH),
        ForeignKey("users.id", name="fk_containers_updated_by", ondelete="RESTRICT"),
        nullable=True,
        comment="更新人用户ID",
    )

    __table_args__ = (
        Index("idx_containers_property_parent", "property_id", "parent_id"),
        Index("idx_containers_property_type", "property_id", "type"),
        Index("idx_containers_qr_code", "qr_code"),
        Index("fk_containers_parent", "parent_id"),
        Index("fk_containers_created_by", "created_by"),
        Index("fk_containers_updated_by", "updated_by"),
    )


class Item(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "items"

    property_id: Mapped[str] = mapped_column(
        CHAR(ID_LENGTH),
        ForeignKey("properties.id", name="fk_items_property", ondelete="CASCADE"),
        nullable=False,
        comment="所属房屋ID",
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False, comment="物品名称")
    category_id: Mapped[str | None] = mapped_column(
        CHAR(ID_LENGTH),
        ForeignKey("categories.id", name="fk_items_category", ondelete="SET NULL"),
        nullable=True,
        comment="分类ID",
    )
    brand: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="品牌")
    model: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="型号/规格")
    barcode: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="条码")
    unit_id: Mapped[str | None] = mapped_column(
        CHAR(ID_LENGTH),
        ForeignKey("units.id", name="fk_items_unit", ondelete="SET NULL"),
        nullable=True,
        comment="单位ID",
    )
    default_container_id: Mapped[str | None] = mapped_column(
        CHAR(ID_LENGTH),
        ForeignKey("containers.id", name="fk_items_default_container", ondelete="SET NULL"),
        nullable=True,
        comment="默认容器ID",
    )
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True, comment="图片URL")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")
    track_inventory: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("1"),
        comment="是否管理库存：0否1是",
    )
    track_expiry: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("0"),
        comment="是否管理过期：0否1是",
    )
    is_consumable: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("0"),
        comment="是否消耗品：0否1是",
    )
    low_stock_threshold: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 3), nullable=True,
        comment="低库存阈值",
    )
    expiry_warning_days: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="过期提前提醒天数")
    opened_expiry_days: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="开封后可用天数")
    default_shelf_life_days: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="默认保质期天数")
    attributes: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="扩展属性JSON")
    current_quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 3), nullable=False, server_default=text("0"),
        comment="当前总库存（冗余字段）",
    )
    created_by: Mapped[str] = mapped_column(
        CHAR(ID_LENGTH),
        ForeignKey("users.id", name="fk_items_created_by", ondelete="RESTRICT"),
        nullable=False,
        comment="创建人用户ID",
    )
    updated_by: Mapped[str | None] = mapped_column(
        CHAR(ID_LENGTH),
        ForeignKey("users.id", name="fk_items_updated_by", ondelete="RESTRICT"),
        nullable=True,
        comment="更新人用户ID",
    )

    __table_args__ = (
        Index("idx_items_property", "property_id"),
        Index("idx_items_property_category", "property_id", "category_id"),
        Index("idx_items_property_name", "property_id", "name"),
        Index("idx_items_barcode", "property_id", "barcode"),
        Index("fk_items_category", "category_id"),
        Index("fk_items_unit", "unit_id"),
        Index("fk_items_default_container", "default_container_id"),
        Index("fk_items_created_by", "created_by"),
        Index("fk_items_updated_by", "updated_by"),
    )


class ItemBatch(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "item_batches"

    property_id: Mapped[str] = mapped_column(
        CHAR(ID_LENGTH),
        ForeignKey("properties.id", name="fk_batches_property", ondelete="CASCADE"),
        nullable=False,
        comment="所属房屋ID",
    )
    item_id: Mapped[str] = mapped_column(
        CHAR(ID_LENGTH),
        ForeignKey("items.id", name="fk_batches_item", ondelete="CASCADE"),
        nullable=False,
        comment="物品ID",
    )
    container_id: Mapped[str] = mapped_column(
        CHAR(ID_LENGTH),
        ForeignKey("containers.id", name="fk_batches_container", ondelete="RESTRICT"),
        nullable=False,
        comment="容器ID",
    )
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 3), nullable=False, server_default=text("0"),
        comment="当前数量",
    )
    unit_id: Mapped[str | None] = mapped_column(
        CHAR(ID_LENGTH),
        ForeignKey("units.id", name="fk_batches_unit", ondelete="SET NULL"),
        nullable=True,
        comment="单位ID",
    )
    production_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="生产日期")
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="过期日期")
    opened_at: Mapped[datetime | None] = mapped_column(DateTimeMS, nullable=True, comment="开封时间")
    opened_expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="开封后过期日期")
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'active'"),
        comment="状态：active/consumed/expired/discarded/moved",
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")
    created_by: Mapped[str] = mapped_column(
        CHAR(ID_LENGTH),
        ForeignKey("users.id", name="fk_batches_created_by", ondelete="RESTRICT"),
        nullable=False,
        comment="创建人用户ID",
    )
    updated_by: Mapped[str | None] = mapped_column(
        CHAR(ID_LENGTH),
        ForeignKey("users.id", name="fk_batches_updated_by", ondelete="RESTRICT"),
        nullable=True,
        comment="更新人用户ID",
    )

    __table_args__ = (
        Index("idx_batches_property_item", "property_id", "item_id"),
        Index("idx_batches_property_container", "property_id", "container_id"),
        Index("idx_batches_expiry", "expiry_date"),
        Index("idx_batches_opened_expiry", "opened_expiry_date"),
        Index("idx_batches_status", "property_id", "status"),
        Index("fk_batches_item", "item_id"),
        Index("fk_batches_container", "container_id"),
        Index("fk_batches_unit", "unit_id"),
        Index("fk_batches_created_by", "created_by"),
        Index("fk_batches_updated_by", "updated_by"),
    )


class InventoryTransaction(UUIDMixin, Base):
    __tablename__ = "inventory_transactions"

    property_id: Mapped[str] = mapped_column(
        CHAR(ID_LENGTH),
        ForeignKey("properties.id", name="fk_transactions_property", ondelete="CASCADE"),
        nullable=False,
        comment="所属房屋ID",
    )
    item_id: Mapped[str] = mapped_column(
        CHAR(ID_LENGTH),
        ForeignKey("items.id", name="fk_transactions_item", ondelete="CASCADE"),
        nullable=False,
        comment="物品ID",
    )
    batch_id: Mapped[str | None] = mapped_column(
        CHAR(ID_LENGTH),
        ForeignKey("item_batches.id", name="fk_transactions_batch", ondelete="SET NULL"),
        nullable=True,
        comment="批次ID",
    )
    container_id: Mapped[str | None] = mapped_column(
        CHAR(ID_LENGTH),
        ForeignKey("containers.id", name="fk_transactions_container", ondelete="SET NULL"),
        nullable=True,
        comment="容器ID",
    )
    type: Mapped[str] = mapped_column(String(20), nullable=False, comment="类型：in/out/consume/move/adjust/discard/return")
    quantity_delta: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False, comment="数量变化")
    quantity_after: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True, comment="变化后数量")
    unit_id: Mapped[str | None] = mapped_column(
        CHAR(ID_LENGTH),
        ForeignKey("units.id", name="fk_transactions_unit", ondelete="SET NULL"),
        nullable=True,
        comment="单位ID",
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True, comment="原因")
    created_by: Mapped[str] = mapped_column(
        CHAR(ID_LENGTH),
        ForeignKey("users.id", name="fk_transactions_created_by", ondelete="RESTRICT"),
        nullable=False,
        comment="创建人用户ID",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTimeMS,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP(3)"),
        comment="创建时间",
    )

    __table_args__ = (
        Index("idx_transactions_property_item", "property_id", "item_id"),
        Index("idx_transactions_property_batch", "property_id", "batch_id"),
        Index("idx_transactions_created_at", "created_at"),
        Index("fk_transactions_item", "item_id"),
        Index("fk_transactions_batch", "batch_id"),
        Index("fk_transactions_container", "container_id"),
        Index("fk_transactions_unit", "unit_id"),
        Index("fk_transactions_created_by", "created_by"),
    )


class Reminder(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "reminders"

    property_id: Mapped[str] = mapped_column(
        CHAR(ID_LENGTH),
        ForeignKey("properties.id", name="fk_reminders_property", ondelete="CASCADE"),
        nullable=False,
        comment="所属房屋ID",
    )
    type: Mapped[str] = mapped_column(String(30), nullable=False, comment="类型：expiry/opened_expiry/low_stock/custom")
    item_id: Mapped[str | None] = mapped_column(
        CHAR(ID_LENGTH),
        ForeignKey("items.id", name="fk_reminders_item", ondelete="CASCADE"),
        nullable=True,
        comment="物品ID",
    )
    batch_id: Mapped[str | None] = mapped_column(
        CHAR(ID_LENGTH),
        ForeignKey("item_batches.id", name="fk_reminders_batch", ondelete="CASCADE"),
        nullable=True,
        comment="批次ID",
    )
    container_id: Mapped[str | None] = mapped_column(
        CHAR(ID_LENGTH),
        ForeignKey("containers.id", name="fk_reminders_container", ondelete="SET NULL"),
        nullable=True,
        comment="容器ID",
    )
    trigger_at: Mapped[datetime] = mapped_column(DateTimeMS, nullable=False, comment="触发时间")
    threshold: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True, comment="阈值")
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'pending'"),
        comment="状态：pending/done/snoozed/dismissed",
    )
    snooze_until: Mapped[datetime | None] = mapped_column(DateTimeMS, nullable=True, comment="稍后提醒时间")
    last_notified_at: Mapped[datetime | None] = mapped_column(DateTimeMS, nullable=True, comment="上次通知时间")
    message: Mapped[str | None] = mapped_column(Text, nullable=True, comment="提醒内容")
    dedupe_key: Mapped[str] = mapped_column(String(255), nullable=False, comment="去重键")
    created_by: Mapped[str | None] = mapped_column(
        CHAR(ID_LENGTH),
        ForeignKey("users.id", name="fk_reminders_created_by", ondelete="RESTRICT"),
        nullable=True,
        comment="创建人用户ID",
    )

    __table_args__ = (
        UniqueConstraint("property_id", "dedupe_key", name="uk_reminders_dedupe"),
        Index(
            "idx_reminders_property_status_trigger",
            "property_id",
            "status",
            "trigger_at",
        ),
        Index("idx_reminders_item", "item_id"),
        Index("idx_reminders_batch", "batch_id"),
        Index("fk_reminders_container", "container_id"),
        Index("fk_reminders_created_by", "created_by"),
    )


class ReminderRecipient(UUIDMixin, Base):
    __tablename__ = "reminder_recipients"

    reminder_id: Mapped[str] = mapped_column(
        CHAR(ID_LENGTH),
        ForeignKey("reminders.id", name="fk_rr_reminder", ondelete="CASCADE"),
        nullable=False,
        comment="提醒ID",
    )
    user_id: Mapped[str] = mapped_column(
        CHAR(ID_LENGTH),
        ForeignKey("users.id", name="fk_rr_user", ondelete="CASCADE"),
        nullable=False,
        comment="用户ID",
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'pending'"),
        comment="状态：pending/read/done/snoozed/dismissed",
    )
    read_at: Mapped[datetime | None] = mapped_column(DateTimeMS, nullable=True, comment="阅读时间")
    done_at: Mapped[datetime | None] = mapped_column(DateTimeMS, nullable=True, comment="完成时间")
    snoozed_until: Mapped[datetime | None] = mapped_column(DateTimeMS, nullable=True, comment="稍后提醒时间")
    created_at: Mapped[datetime] = mapped_column(
        DateTimeMS,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP(3)"),
        comment="创建时间",
    )

    __table_args__ = (
        UniqueConstraint("reminder_id", "user_id", name="uk_reminder_recipients"),
        Index("idx_reminder_recipients_user", "user_id", "status"),
    )


class Tag(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "tags"

    property_id: Mapped[str | None] = mapped_column(
        CHAR(ID_LENGTH),
        ForeignKey("properties.id", name="fk_tags_property", ondelete="SET NULL"),
        nullable=True,
        comment="来源房屋ID，仅用于追踪，审核通过后可为空",
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False, comment="标签名称")
    color: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="颜色")
    created_by: Mapped[str | None] = mapped_column(
        CHAR(ID_LENGTH),
        ForeignKey("users.id", name="fk_tags_created_by", ondelete="SET NULL"),
        nullable=True,
        comment="创建人用户ID，系统预置可为空",
    )
    is_public: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("0"),
        comment="是否公共：0私有1公共",
    )
    review_status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'pending'"),
        comment="审核状态：pending/approved/rejected",
    )
    reviewed_by: Mapped[str | None] = mapped_column(
        CHAR(ID_LENGTH),
        ForeignKey("users.id", name="fk_tags_reviewed_by", ondelete="SET NULL"),
        nullable=True,
        comment="审核人用户ID",
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTimeMS, nullable=True, comment="审核时间")
    review_remark: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="审核备注")
    published_at: Mapped[datetime | None] = mapped_column(DateTimeMS, nullable=True, comment="转为公共的时间")
    name_public_unique: Mapped[str | None] = mapped_column(
        String(50),
        Computed(
            "(CASE WHEN is_public = 1 AND deleted_at IS NULL THEN name ELSE NULL END)",
            persisted=True,
        ),
        nullable=True,
        sort_order=200,
        comment="公共命名唯一键",
    )

    __table_args__ = (
        UniqueConstraint("name_public_unique", name="uk_tags_public_name"),
        Index("idx_tags_review", "review_status", "is_public"),
        Index("idx_tags_created_by", "created_by"),
        Index("idx_tags_public", "is_public", "deleted_at"),
        Index("fk_tags_property", "property_id"),
        Index("fk_tags_reviewed_by", "reviewed_by"),
    )


class ItemTag(Base):
    __tablename__ = "item_tags"

    item_id: Mapped[str] = mapped_column(
        CHAR(ID_LENGTH),
        ForeignKey("items.id", name="fk_item_tags_item", ondelete="CASCADE"),
        primary_key=True,
        comment="物品ID",
    )
    tag_id: Mapped[str] = mapped_column(
        CHAR(ID_LENGTH),
        ForeignKey("tags.id", name="fk_item_tags_tag", ondelete="CASCADE"),
        primary_key=True,
        comment="标签ID",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTimeMS,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP(3)"),
        comment="创建时间",
    )

    __table_args__ = (Index("idx_item_tags_tag", "tag_id"),)


class Attachment(UUIDMixin, Base):
    __tablename__ = "attachments"

    property_id: Mapped[str] = mapped_column(
        CHAR(ID_LENGTH),
        ForeignKey("properties.id", name="fk_attachments_property", ondelete="CASCADE"),
        nullable=False,
        comment="所属房屋ID",
    )
    owner_type: Mapped[str] = mapped_column(String(30), nullable=False, comment="所属类型：item/item_batch/container/property/reminder")
    owner_id: Mapped[str] = mapped_column(CHAR(ID_LENGTH), nullable=False, comment="所属对象ID")
    file_path: Mapped[str] = mapped_column(Text, nullable=False, comment="文件路径")
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="文件名")
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="MIME类型")
    file_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="文件大小")
    uploaded_by: Mapped[str] = mapped_column(
        CHAR(ID_LENGTH),
        ForeignKey("users.id", name="fk_attachments_uploaded_by", ondelete="RESTRICT"),
        nullable=False,
        comment="上传人用户ID",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTimeMS,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP(3)"),
        comment="创建时间",
    )

    __table_args__ = (
        Index("idx_attachments_property", "property_id"),
        Index("idx_attachments_owner", "owner_type", "owner_id"),
        Index("fk_attachments_uploaded_by", "uploaded_by"),
    )


class NotificationChannel(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "notification_channels"

    user_id: Mapped[str] = mapped_column(
        CHAR(ID_LENGTH),
        ForeignKey("users.id", name="fk_nc_user", ondelete="CASCADE"),
        nullable=False,
        comment="用户ID",
    )
    property_id: Mapped[str | None] = mapped_column(
        CHAR(ID_LENGTH),
        ForeignKey("properties.id", name="fk_nc_property", ondelete="CASCADE"),
        nullable=True,
        comment="房屋ID（可空）",
    )
    type: Mapped[str] = mapped_column(String(30), nullable=False, comment="类型：email/push/bark/telegram/webhook")
    config: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="配置JSON")
    is_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("1"),
        comment="是否启用：0否1是",
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTimeMS, nullable=True, comment="验证时间")

    __table_args__ = (
        Index("idx_nc_user", "user_id"),
        Index("idx_nc_property", "property_id"),
    )


class NotificationPreference(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "notification_preferences"

    user_id: Mapped[str] = mapped_column(
        CHAR(ID_LENGTH),
        ForeignKey("users.id", name="fk_np_user", ondelete="CASCADE"),
        nullable=False,
        comment="用户ID",
    )
    property_id: Mapped[str | None] = mapped_column(
        CHAR(ID_LENGTH),
        ForeignKey("properties.id", name="fk_np_property", ondelete="CASCADE"),
        nullable=True,
        comment="房屋ID（可空）",
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, comment="事件类型")
    channel_id: Mapped[str | None] = mapped_column(
        CHAR(ID_LENGTH),
        ForeignKey("notification_channels.id", name="fk_np_channel", ondelete="CASCADE"),
        nullable=True,
        comment="渠道ID",
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("1"),
        comment="是否启用：0否1是",
    )
    advance_days: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="提前天数")
    quiet_hours: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="免打扰时段JSON")

    __table_args__ = (
        Index("idx_np_user", "user_id"),
        Index("idx_np_property", "property_id"),
        Index("fk_np_channel", "channel_id"),
    )


class Notification(UUIDMixin, Base):
    __tablename__ = "notifications"

    property_id: Mapped[str | None] = mapped_column(
        CHAR(ID_LENGTH),
        ForeignKey("properties.id", name="fk_notifications_property", ondelete="CASCADE"),
        nullable=True,
        comment="房屋ID（可空）",
    )
    user_id: Mapped[str] = mapped_column(
        CHAR(ID_LENGTH),
        ForeignKey("users.id", name="fk_notifications_user", ondelete="CASCADE"),
        nullable=False,
        comment="用户ID",
    )
    reminder_id: Mapped[str | None] = mapped_column(
        CHAR(ID_LENGTH),
        ForeignKey("reminders.id", name="fk_notifications_reminder", ondelete="SET NULL"),
        nullable=True,
        comment="提醒ID",
    )
    channel_id: Mapped[str | None] = mapped_column(
        CHAR(ID_LENGTH),
        ForeignKey("notification_channels.id", name="fk_notifications_channel", ondelete="SET NULL"),
        nullable=True,
        comment="渠道ID",
    )
    title: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="标题")
    body: Mapped[str | None] = mapped_column(Text, nullable=True, comment="内容")
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="负载JSON")
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'pending'"),
        comment="状态：pending/sent/failed/read",
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTimeMS, nullable=True, comment="发送时间")
    read_at: Mapped[datetime | None] = mapped_column(DateTimeMS, nullable=True, comment="阅读时间")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, comment="错误信息")
    created_at: Mapped[datetime] = mapped_column(
        DateTimeMS,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP(3)"),
        comment="创建时间",
    )

    __table_args__ = (
        Index("idx_notifications_user_status", "user_id", "status"),
        Index("idx_notifications_property", "property_id"),
        Index("idx_notifications_created_at", "created_at"),
        Index("fk_notifications_reminder", "reminder_id"),
        Index("fk_notifications_channel", "channel_id"),
    )


class AuditLog(UUIDMixin, Base):
    __tablename__ = "audit_logs"

    property_id: Mapped[str | None] = mapped_column(
        CHAR(ID_LENGTH),
        ForeignKey("properties.id", name="fk_audit_property", ondelete="SET NULL"),
        nullable=True,
        comment="房屋ID（可空）",
    )
    user_id: Mapped[str | None] = mapped_column(
        CHAR(ID_LENGTH),
        ForeignKey("users.id", name="fk_audit_user", ondelete="SET NULL"),
        nullable=True,
        comment="用户ID（可空）",
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False, comment="操作")
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, comment="实体类型")
    entity_id: Mapped[str | None] = mapped_column(CHAR(ID_LENGTH), nullable=True, comment="实体ID")
    before_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="变更前数据JSON")
    after_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="变更后数据JSON")
    ip: Mapped[str | None] = mapped_column(String(45), nullable=True, comment="IP地址")
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True, comment="用户代理")
    created_at: Mapped[datetime] = mapped_column(
        DateTimeMS,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP(3)"),
        comment="创建时间",
    )

    __table_args__ = (
        Index("idx_audit_logs_property_created", "property_id", "created_at"),
        Index("idx_audit_logs_user_created", "user_id", "created_at"),
        Index("idx_audit_logs_entity", "entity_type", "entity_id"),
    )
