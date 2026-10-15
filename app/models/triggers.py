"""建表脚本定义的数据库触发器。

``sql/item_manager_create.sql`` 用两个 BEFORE INSERT/UPDATE 触发器实现
**公共单位重名规则**（units 表既没有 name_public_unique 生成列，也没有唯一索引）：

* 通用单位（``category_id`` 为空）名称在公共单位中全局唯一；
* 分类单位不得与通用单位同名，且在同一分类内唯一（不同分类允许重名）。

SQLAlchemy 的 ``create_all`` 不建模触发器，所以这里在应用侧补齐，
使「导入 SQL 脚本」与「``init_db()`` 自动建表」两条路径得到相同的数据库约束。
语句与建表脚本逐字一致，避免两边规则漂移。
"""

from __future__ import annotations

from sqlalchemy.engine import Connection

#: 触发器名，供测试与排查使用。
TRIGGER_NAMES: tuple[str, ...] = (
    "trg_units_public_unique_before_insert",
    "trg_units_public_unique_before_update",
)

#: MySQL 的 CREATE TRIGGER 不支持 IF NOT EXISTS（那是 MariaDB 的扩展），
#: 因此与建表脚本一样，先 DROP 再 CREATE，保证可重复执行。
TRIGGER_STATEMENTS: tuple[str, ...] = (
    "DROP TRIGGER IF EXISTS `trg_units_public_unique_before_insert`",
    """
    CREATE TRIGGER `trg_units_public_unique_before_insert`
    BEFORE INSERT ON `units`
    FOR EACH ROW
    BEGIN
      IF NEW.`is_public` = 1 AND NEW.`deleted_at` IS NULL THEN
        IF NEW.`category_id` IS NULL THEN
          IF EXISTS (SELECT 1 FROM `units` WHERE `name` = NEW.`name` AND `is_public` = 1 AND `deleted_at` IS NULL) THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '通用单位名称必须全局唯一';
          END IF;
        ELSE
          IF EXISTS (SELECT 1 FROM `units` WHERE `name` = NEW.`name` AND `is_public` = 1 AND `deleted_at` IS NULL AND `category_id` IS NULL) THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '不能与通用单位同名';
          END IF;
          IF EXISTS (SELECT 1 FROM `units` WHERE `name` = NEW.`name` AND `is_public` = 1 AND `deleted_at` IS NULL AND `category_id` = NEW.`category_id`) THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '该分类下已存在同名公共单位';
          END IF;
        END IF;
      END IF;
    END
    """,
    "DROP TRIGGER IF EXISTS `trg_units_public_unique_before_update`",
    """
    CREATE TRIGGER `trg_units_public_unique_before_update`
    BEFORE UPDATE ON `units`
    FOR EACH ROW
    BEGIN
      IF NEW.`is_public` = 1 AND NEW.`deleted_at` IS NULL THEN
        IF NEW.`category_id` IS NULL THEN
          IF EXISTS (SELECT 1 FROM `units` WHERE `name` = NEW.`name` AND `is_public` = 1 AND `deleted_at` IS NULL AND `id` <> NEW.`id`) THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '通用单位名称必须全局唯一';
          END IF;
        ELSE
          IF EXISTS (SELECT 1 FROM `units` WHERE `name` = NEW.`name` AND `is_public` = 1 AND `deleted_at` IS NULL AND `category_id` IS NULL AND `id` <> NEW.`id`) THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '不能与通用单位同名';
          END IF;
          IF EXISTS (SELECT 1 FROM `units` WHERE `name` = NEW.`name` AND `is_public` = 1 AND `deleted_at` IS NULL AND `category_id` = NEW.`category_id` AND `id` <> NEW.`id`) THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '该分类下已存在同名公共单位';
          END IF;
        END IF;
      END IF;
    END
    """,
)


def install_triggers(connection: Connection) -> None:
    """安装（或重建）触发器。需在表已创建之后调用，可重复执行。

    用 ``exec_driver_sql`` 直接下发原始 DDL：触发器体里含分号，
    不能走 SQLAlchemy 的 ``text()`` 参数解析。
    """
    for statement in TRIGGER_STATEMENTS:
        connection.exec_driver_sql(statement)


def drop_triggers(connection: Connection) -> None:
    """删除触发器（建表脚本 DROP TABLE 时不会自动清理同名触发器时会用到）。"""
    for name in TRIGGER_NAMES:
        connection.exec_driver_sql(f"DROP TRIGGER IF EXISTS `{name}`")
