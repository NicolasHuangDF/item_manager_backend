import uuid
from datetime import datetime

from sqlalchemy import CHAR, DateTime, MetaData, text
from sqlalchemy.dialects.mysql import DATETIME as MySQLDateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


#: 所有主键/外键列统一长度：32 位无连字符十六进制字符串。
ID_LENGTH = 32

#: 毫秒精度时间戳。MySQL 下生成 DATETIME(3)，与库中的 datetime(3) 完全一致。
#: 注意：DateTime(3) 是常见误用 —— DateTime 的第一个位置参数是 timezone 而不是精度，
#: 它只会生成 DATETIME，与 server_default=CURRENT_TIMESTAMP(3) 组合是非法 DDL
#: （MySQL 报 1067 Invalid default value）。
DateTimeMS = DateTime().with_variant(MySQLDateTime(fsp=3), "mysql")


def new_uuid() -> str:
    """生成 32 位、无连字符、全大写 UUID。"""
    return uuid.uuid4().hex.upper()


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class UUIDMixin:
    id: Mapped[str] = mapped_column(
        CHAR(ID_LENGTH),
        primary_key=True,
        default=new_uuid,
        server_default=text("(REPLACE(UPPER(uuid()),'-',''))"),
        comment="主键",
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTimeMS,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP(3)"),
        comment="创建时间",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTimeMS,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP(3)"),
        onupdate=text("CURRENT_TIMESTAMP(3)"),
        comment="更新时间",
    )


class SoftDeleteMixin:
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTimeMS,
        nullable=True,
        comment="软删除时间",
    )
