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
    """生成 32 位、无连字符的小写 UUID。

    与建表脚本 sql/item_manager_create.sql 中的
    ``DEFAULT (REPLACE(uuid(), '-', ''))`` 保持一致：MySQL 的 uuid() 返回小写，
    因此 Python 侧也生成小写，避免同一列混入两种大小写形式。
    （列排序规则为 utf8mb4_unicode_ci，比较本身不区分大小写。）
    """
    return uuid.uuid4().hex


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class UUIDMixin:
    # sort_order 为负值，保证 id 排在业务列之前，
    # 与建表脚本中 `id` 紧跟表定义首行的顺序一致。
    id: Mapped[str] = mapped_column(
        CHAR(ID_LENGTH),
        primary_key=True,
        default=new_uuid,
        server_default=text("(REPLACE(uuid(),'-',''))"),
        sort_order=-100,
        comment="主键",
    )


class TimestampMixin:
    # sort_order 为正值，保证 created_at/updated_at 排在业务列之后，
    # 与建表脚本的列顺序一致。
    created_at: Mapped[datetime] = mapped_column(
        DateTimeMS,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP(3)"),
        sort_order=100,
        comment="创建时间",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTimeMS,
        nullable=False,
        # 注意：SQLAlchemy 的 server_onupdate 不会写进 MySQL 的建表 DDL，
        # 必须把 ON UPDATE 子句并入 server_default，才能生成
        # `DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3)`，
        # 与建表脚本一致（绕过 ORM 的直接 SQL 更新也会自动刷新该列）。
        server_default=text("CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3)"),
        # onupdate 作用于 ORM 发出的 UPDATE 语句。
        onupdate=text("CURRENT_TIMESTAMP(3)"),
        sort_order=101,
        comment="更新时间",
    )


class SoftDeleteMixin:
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTimeMS,
        nullable=True,
        sort_order=102,
        comment="软删除时间",
    )
