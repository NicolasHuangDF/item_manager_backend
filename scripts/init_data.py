import asyncio
import sys
from datetime import datetime
from pathlib import Path

# 以脚本方式直接运行（python scripts/init_data.py）时，Python 把 sys.path[0]
# 设为脚本所在目录 scripts/，项目根目录不在其中，`import app` 会失败。
# 这里显式把项目根目录加入 sys.path，与 run.py 的做法保持一致，
# 使 `python scripts/init_data.py` 和 `python -m scripts.init_data` 都能工作。
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import select  # noqa: E402

from app.core.database import AsyncSessionLocal, engine, init_db  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models import Unit, User  # noqa: E402

DEFAULT_UNITS = [
    ("个", "个", 0),
    ("条", "条", 0),
    ("顶", "顶", 0),
    ("双", "双", 0),
    ("只", "只", 0),
    ("枚", "枚", 0),
    ("把", "把", 0),
    ("口", "口", 0),
    ("张", "张", 0),
    ("台", "台", 0),
    ("件", "件", 0),
    ("瓶", "瓶", 0),
    ("包", "包", 0),
    ("盒", "盒", 0),
    ("箱", "箱", 0),
    ("支", "支", 0),
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
    # 必须显式释放连接池：否则 asyncio.run() 关闭事件循环后，
    # 残留的 aiomysql 连接会在 __del__ 中操作已关闭的循环，
    # 抛出 "RuntimeError: Event loop is closed" 并让脚本以退出码 1 结束。
    await engine.dispose()
    print("初始化数据完成。")


if __name__ == "__main__":
    asyncio.run(main())
