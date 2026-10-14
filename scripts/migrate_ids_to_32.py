"""将 item_manager 数据库中所有 UUID 字段转换为 32 位无连字符大写格式。

适用字段：
    - 名为 id 的列
    - 以 _id 结尾的列，例如 property_id、user_id
    - 以 _by 结尾的列，例如 created_by、updated_by
    - 长度 >= 32 的 char/varchar 列

执行方式：
    cd D:\\project\\FastApiProject\\item_manager_backend
    .venv\\Scripts\\activate
    python -m scripts.migrate_ids_to_32
"""

from sqlalchemy import create_engine, text

from app.core.config import settings


def _sync_url() -> str:
    return (
        settings.DATABASE_URL
        .replace("+aiomysql", "+pymysql")
        .replace("+asyncmy", "+pymysql")
    )


def main() -> None:
    engine = create_engine(_sync_url(), pool_pre_ping=True)

    with engine.connect() as conn:
        db_name = conn.exec_driver_sql("SELECT DATABASE()").scalar()
        print(f"当前数据库：{db_name}")

        columns = conn.execute(
            text(
                """
                SELECT TABLE_NAME, COLUMN_NAME
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = :schema
                  AND DATA_TYPE IN ('char', 'varchar')
                  AND CHARACTER_MAXIMUM_LENGTH >= 32
                  AND (
                        COLUMN_NAME = 'id'
                        OR RIGHT(COLUMN_NAME, 3) = '_id'
                        OR RIGHT(COLUMN_NAME, 3) = '_by'
                  )
                ORDER BY TABLE_NAME, COLUMN_NAME
                """
            ),
            {"schema": db_name},
        ).all()

        if not columns:
            print("没有找到需要转换的 UUID 字段。")
            return

        print(f"共找到 {len(columns)} 个 UUID 字段，开始转换...")

        try:
            conn.exec_driver_sql("SET FOREIGN_KEY_CHECKS = 0")
            total = 0
            for table_name, column_name in columns:
                result = conn.execute(
                    text(
                        f"UPDATE `{table_name}` "
                        f"SET `{column_name}` = UPPER(REPLACE(`{column_name}`, '-', '')) "
                        f"WHERE `{column_name}` IS NOT NULL"
                    )
                )
                affected = result.rowcount or 0
                total += affected
                print(f"{table_name}.{column_name}: {affected} 行")

            conn.commit()
            print(f"转换完成，共更新 {total} 行。")
        except Exception:
            conn.rollback()
            raise
        finally:
            try:
                conn.exec_driver_sql("SET FOREIGN_KEY_CHECKS = 1")
                conn.commit()
            except Exception:
                pass

        print("开始校验...")
        remaining = 0
        for table_name, column_name in columns:
            count = conn.execute(
                text(
                    f"SELECT COUNT(*) FROM `{table_name}` "
                    f"WHERE `{column_name}` IS NOT NULL "
                    f"AND (LENGTH(`{column_name}`) <> 32 "
                    f"OR BINARY `{column_name}` <> UPPER(`{column_name}`))"
                )
            ).scalar()
            remaining += int(count or 0)

        if remaining:
            print(f"校验未通过：仍有 {remaining} 个字段值不是 32 位大写格式。")
        else:
            print("校验通过：所有 UUID 字段均为 32 位无连字符大写格式。")


if __name__ == "__main__":
    main()
