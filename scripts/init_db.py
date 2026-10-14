import asyncio

from app.core.database import init_db


async def main() -> None:
    print("正在根据 ORM 模型创建数据库表...")
    await init_db()
    print("数据库表创建完成。生产环境请优先执行 sql/schema.sql。")


if __name__ == "__main__":
    asyncio.run(main())
