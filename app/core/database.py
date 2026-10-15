from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DB_ECHO,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """开发环境使用：按 ORM 模型自动建表，并补齐建表脚本里的触发器。

    create_all 只建表，不会创建 sql/item_manager_create.sql 中定义的
    公共单位重名触发器（trg_units_public_unique_before_insert/_update）。
    若不补上，用这条路径初始化的库会缺失该约束，因此这里一并安装。

    生产环境建议直接执行 sql/item_manager_create.sql，由 DBA 控制 DDL。
    """
    from app.models import Base
    from app.models.triggers import install_triggers

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(install_triggers)
