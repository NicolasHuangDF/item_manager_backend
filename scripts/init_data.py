import asyncio
from datetime import datetime

from sqlalchemy import select

from app.core.database import AsyncSessionLocal, init_db
from app.core.security import hash_password
from app.models import Unit, User

DEFAULT_UNITS = [
    ("个", "个", 0),
    ("件", "件", 0),
    ("瓶", "瓶", 0),
    ("包", "包", 0),
    ("盒", "盒", 0),
    ("袋", "袋", 0),
    ("罐", "罐", 0),
    ("千克", "kg", 3),
    ("克", "g", 3),
    ("升", "L", 3),
    ("毫升", "mL", 3),
    ("米", "m", 2),
]


async def main() -> None:
    await init_db()
    async with AsyncSessionLocal() as db:
        admin = await db.scalar(select(User).where(User.username == "admin"))
        if not admin:
            admin = User(
                username="admin",
                email="admin@example.com",
                password_hash=hash_password("Admin123!"),
                display_name="系统管理员",
                status="active",
            )
            db.add(admin)
            await db.flush()
            print("已创建管理员：admin@example.com / Admin123!")
        else:
            print("管理员已存在，跳过创建。")

        for name, symbol, decimal_places in DEFAULT_UNITS:
            exists = await db.scalar(
                select(Unit).where(
                    Unit.name == name,
                    Unit.is_public.is_(True),
                    Unit.deleted_at.is_(None),
                )
            )
            if exists:
                continue
            db.add(
                Unit(
                    property_id=None,
                    name=name,
                    symbol=symbol,
                    decimal_places=decimal_places,
                    created_by=None,
                    is_public=True,
                    review_status="approved",
                    published_at=datetime.utcnow(),
                    reviewed_at=datetime.utcnow(),
                    review_remark="系统预置单位",
                )
            )
        await db.commit()
    print("初始化数据完成。")


if __name__ == "__main__":
    asyncio.run(main())
