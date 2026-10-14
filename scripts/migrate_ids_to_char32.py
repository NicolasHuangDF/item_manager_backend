"""将 item_manager 库中所有主键/外键列从 36 位改造为 CHAR(32)。

背景
----
`new_uuid()` 生成的是 32 位无连字符大写十六进制串，ORM 侧已统一声明为
`CHAR(ID_LENGTH)`（ID_LENGTH = 32，见 app/models/base.py）。但由于
`Base.metadata.create_all()` 不会修改已存在的表结构，历史库里这些列仍然是
`VARCHAR(36)`，需要本脚本做一次结构迁移。

为什么不能直接 MODIFY
---------------------
MySQL 不允许修改正被外键引用的列（会报 "Cannot change column: used in a
foreign key constraint"）。因此执行顺序为：

    1. SET FOREIGN_KEY_CHECKS = 0
    2. 读取并删除全部外键约束（记录名称、列、引用目标、级联规则）
    3. ALTER TABLE ... MODIFY COLUMN ... CHAR(32)
    4. 按原名称与原规则重建外键
    5. 恢复 FOREIGN_KEY_CHECKS 并校验

外键信息全部从 information_schema 动态读取，不硬编码，因此可安全重复执行。

执行方式
--------
    cd D:\\project\\FastApiProject\\item_manager_backend
    conda activate item_manager
    python -m scripts.migrate_ids_to_char32            # 实际执行迁移
    python -m scripts.migrate_ids_to_char32 --dry-run  # 仅打印 DDL，不改动数据库

注意
----
DDL 在 MySQL 中会隐式提交，无法整体回滚。虽然脚本会在失败时尽力补回外键，
仍建议在业务低峰期执行，并事先备份。
"""

from __future__ import annotations

import re
import sys

from sqlalchemy import create_engine, text

from app.core.config import settings
from app.models import Base
from app.models.base import ID_LENGTH

#: 目标列类型（小写，用于与 information_schema 的 COLUMN_TYPE 比较）
TARGET_TYPE = f"char({ID_LENGTH})"

#: 36 位带连字符的 UUID，例如 00000000-0000-0000-0000-000000000000
UUID_36_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}"
    r"-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


def _sync_url() -> str:
    """把异步驱动换成同步驱动，供 DDL 脚本使用。"""
    return (
        settings.DATABASE_URL.replace("+aiomysql", "+pymysql")
        .replace("+asyncmy", "+pymysql")
    )


def _quote(value: object) -> str:
    """生成 SQL 字符串字面量。"""
    escaped = str(value).replace("\\", "\\\\").replace("'", "''")
    return f"'{escaped}'"


def _target_columns() -> list[tuple[str, str]]:
    """从 ORM 元数据挑出全部主键/外键列。

    判定规则与项目约定一致：列名为 id、或以 _id / _by 结尾。
    """
    targets: list[tuple[str, str]] = []
    for table in Base.metadata.sorted_tables:
        for column in table.columns:
            name = column.name
            if name == "id" or name.endswith("_id") or name.endswith("_by"):
                targets.append((table.name, name))
    return targets


def _load_column_defs(conn) -> dict[tuple[str, str], dict]:
    """读取当前库全部列的完整定义。"""
    rows = (
        conn.execute(
            text(
                """
                SELECT TABLE_NAME        AS table_name,
                       COLUMN_NAME       AS column_name,
                       COLUMN_TYPE       AS column_type,
                       IS_NULLABLE       AS is_nullable,
                       COLUMN_DEFAULT    AS column_default,
                       EXTRA             AS extra,
                       COLUMN_COMMENT    AS column_comment
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                """
            )
        )
        .mappings()
        .all()
    )
    return {(r["table_name"], r["column_name"]): dict(r) for r in rows}


def _load_foreign_keys(conn) -> list[dict]:
    """读取当前库全部外键，按约束聚合（支持复合外键）。"""
    rows = (
        conn.execute(
            text(
                """
                SELECT k.CONSTRAINT_NAME       AS name,
                       k.TABLE_NAME            AS table_name,
                       k.COLUMN_NAME           AS column_name,
                       k.REFERENCED_TABLE_NAME AS ref_table,
                       k.REFERENCED_COLUMN_NAME AS ref_column,
                       r.DELETE_RULE           AS delete_rule,
                       r.UPDATE_RULE           AS update_rule
                FROM information_schema.KEY_COLUMN_USAGE k
                JOIN information_schema.REFERENTIAL_CONSTRAINTS r
                  ON r.CONSTRAINT_SCHEMA = k.CONSTRAINT_SCHEMA
                 AND r.CONSTRAINT_NAME = k.CONSTRAINT_NAME
                 AND r.TABLE_NAME = k.TABLE_NAME
                WHERE k.TABLE_SCHEMA = DATABASE()
                  AND k.REFERENCED_TABLE_NAME IS NOT NULL
                ORDER BY k.TABLE_NAME, k.CONSTRAINT_NAME, k.ORDINAL_POSITION
                """
            )
        )
        .mappings()
        .all()
    )

    grouped: dict[tuple[str, str], dict] = {}
    for row in rows:
        key = (row["table_name"], row["name"])
        fk = grouped.setdefault(
            key,
            {
                "table": row["table_name"],
                "name": row["name"],
                "columns": [],
                "ref_table": row["ref_table"],
                "ref_columns": [],
                "delete_rule": row["delete_rule"],
                "update_rule": row["update_rule"],
            },
        )
        fk["columns"].append(row["column_name"])
        fk["ref_columns"].append(row["ref_column"])
    return list(grouped.values())


def _default_clause(col: dict) -> str | None:
    """还原默认值表达式，返回形如 DEFAULT xxx 的片段。

    MySQL 8 会把表达式默认值（如 uuid()）原样放进 COLUMN_DEFAULT，并在 EXTRA
    中标记 DEFAULT_GENERATED。这类值**不能加引号**，否则函数会退化成字符串常量
    （DEFAULT (uuid()) 被写成 DEFAULT 'uuid()'）。

    另外，uuid() 产出的是 36 位带连字符的小写串，直接作为 CHAR(32) 的默认值会
    触发 "Data too long"（实测 1406），因此统一改写为与 new_uuid() 一致的
    32 位大写无连字符形式。
    """
    raw = col["column_default"]
    if raw is None:
        return None

    text_value = str(raw)
    extra = (col.get("extra") or "").upper()

    if "DEFAULT_GENERATED" in extra:
        if UUID_36_RE.match(text_value.strip()):
            return f"DEFAULT ('{text_value.strip().replace('-', '').upper()}')"
        if "uuid()" in text_value.lower():
            return "DEFAULT (REPLACE(UPPER(uuid()),'-',''))"
        return f"DEFAULT ({text_value})"

    if UUID_36_RE.match(text_value):
        text_value = text_value.replace("-", "").upper()
    return f"DEFAULT {_quote(text_value)}"


def _new_definition(col: dict) -> str:
    """按原列定义生成 CHAR(ID_LENGTH) 版本（保留 NULL / DEFAULT / COMMENT）。"""
    parts = [f"CHAR({ID_LENGTH})"]

    parts.append("NULL" if col["is_nullable"] == "YES" else "NOT NULL")

    default = _default_clause(col)
    if default:
        parts.append(default)

    if col["column_comment"]:
        parts.append(f"COMMENT {_quote(col['column_comment'])}")

    return " ".join(parts)


def _drop_fk_sql(fk: dict) -> str:
    return f"ALTER TABLE `{fk['table']}` DROP FOREIGN KEY `{fk['name']}`"


def _add_fk_sql(fk: dict) -> str:
    columns = ", ".join(f"`{c}`" for c in fk["columns"])
    ref_columns = ", ".join(f"`{c}`" for c in fk["ref_columns"])
    sql = (
        f"ALTER TABLE `{fk['table']}` ADD CONSTRAINT `{fk['name']}` "
        f"FOREIGN KEY ({columns}) REFERENCES `{fk['ref_table']}` ({ref_columns})"
    )
    # RESTRICT / NO ACTION 是 MySQL 默认行为，无需显式写出
    if fk["delete_rule"] not in {"NO ACTION", "RESTRICT"}:
        sql += f" ON DELETE {fk['delete_rule']}"
    if fk["update_rule"] not in {"NO ACTION", "RESTRICT"}:
        sql += f" ON UPDATE {fk['update_rule']}"
    return sql


def _verify(conn) -> int:
    """校验所有目标列都已是 CHAR(ID_LENGTH)，返回异常列数。"""
    defs = _load_column_defs(conn)
    bad = [
        (table, column, defs[(table, column)]["column_type"])
        for table, column in _target_columns()
        if (table, column) in defs
        and defs[(table, column)]["column_type"].lower() != TARGET_TYPE
    ]

    fk_count = len(_load_foreign_keys(conn))
    print(f"  外键约束数量：{fk_count}")

    if bad:
        print(f"  以下 {len(bad)} 列仍未达到 CHAR({ID_LENGTH})：")
        for table, column, col_type in bad:
            print(f"    {table}.{column} = {col_type}")
        return len(bad)

    print(f"  校验通过：所有主键/外键列均为 CHAR({ID_LENGTH})。")
    return 0


def main() -> None:
    dry_run = "--dry-run" in sys.argv

    engine = create_engine(
        _sync_url(), pool_pre_ping=True, isolation_level="AUTOCOMMIT"
    )

    with engine.connect() as conn:
        db_name = conn.exec_driver_sql("SELECT DATABASE()").scalar()
        print(f"当前数据库：{db_name}")
        print(f"目标列类型：CHAR({ID_LENGTH})")
        if dry_run:
            print("模式：DRY-RUN（只打印 DDL，不执行）")
        print()

        defs = _load_column_defs(conn)
        all_targets = _target_columns()

        missing = [t for t in all_targets if t not in defs]
        if missing:
            print(f"警告：ORM 中存在但数据库里找不到的列（已跳过）：{missing}")

        todo = [
            (table, column, defs[(table, column)]["column_type"])
            for table, column in all_targets
            if (table, column) in defs
            and defs[(table, column)]["column_type"].lower() != TARGET_TYPE
        ]

        print(f"主键/外键列总数：{len(all_targets)}")
        print(f"需要迁移的列数：{len(todo)}")

        if not todo:
            print("\n所有列已是目标类型，无需迁移。")
            print("\n-- 校验 --")
            _verify(conn)
            return

        fks = _load_foreign_keys(conn)
        print(f"涉及外键约束：{len(fks)} 个（将先删除、后按原规则重建）")

        if dry_run:
            print("\n-- 将执行以下 DDL --")
            for fk in fks:
                print(_drop_fk_sql(fk) + ";")
            for table, column, _ in todo:
                print(
                    f"ALTER TABLE `{table}` MODIFY COLUMN `{column}` "
                    f"{_new_definition(defs[(table, column)])};"
                )
            for fk in fks:
                print(_add_fk_sql(fk) + ";")
            print("\nDRY-RUN 结束，数据库未被改动。")
            return

        dropped: list[dict] = []
        restored: set[str] = set()
        failure: Exception | None = None

        try:
            conn.exec_driver_sql("SET FOREIGN_KEY_CHECKS = 0")

            print("\n-- 1/3 删除外键 --")
            for fk in fks:
                conn.exec_driver_sql(_drop_fk_sql(fk))
                dropped.append(fk)
            print(f"  已删除 {len(dropped)} 个外键")

            print("\n-- 2/3 修改列类型 --")
            for table, column, old_type in todo:
                conn.exec_driver_sql(
                    f"ALTER TABLE `{table}` MODIFY COLUMN `{column}` "
                    f"{_new_definition(defs[(table, column)])}"
                )
                print(f"  {table}.{column}: {old_type} -> {TARGET_TYPE}")
        except Exception as exc:  # noqa: BLE001 - 需要兜底重建外键
            failure = exc
            print(f"\n迁移中断：{type(exc).__name__}: {exc}")
        finally:
            print("\n-- 3/3 重建外键 --")
            for fk in dropped:
                if fk["name"] in restored:
                    continue
                try:
                    conn.exec_driver_sql(_add_fk_sql(fk))
                    restored.add(fk["name"])
                except Exception as exc:  # noqa: BLE001 - 尽量补回全部外键
                    print(f"  重建失败 {fk['name']}: {exc}")
            print(f"  已重建 {len(restored)} / {len(dropped)} 个外键")
            try:
                conn.exec_driver_sql("SET FOREIGN_KEY_CHECKS = 1")
            except Exception:  # noqa: BLE001
                pass

        print("\n-- 校验 --")
        bad = _verify(conn)

        if failure is not None:
            raise SystemExit(f"迁移未完成：{failure}")
        if bad:
            raise SystemExit(f"迁移后仍有 {bad} 列不符合预期，请人工检查。")


if __name__ == "__main__":
    main()
