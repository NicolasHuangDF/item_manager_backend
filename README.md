# 家庭物品收纳管理后端服务

项目根目录：`D:\project\FastApiProject\item_manager_backend`

基于 FastAPI + SQLAlchemy 2.0 Async + MySQL 8.0 的家庭物品收纳管理后端。
对应数据库重建脚本中的 21 张表，支持认证、房屋成员、基础数据、容器、物品、批次库存、
库存流水、提醒、通知、附件、配置、审计日志和看板统计。

## 快速开始

```bat
cd D:\project\FastApiProject\item_manager_backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
REM 修改 .env 中的数据库连接

REM 方式一：使用 ORM 自动建表
python -m scripts.init_data

REM 方式二：先执行你原有的完整 21 表 SQL，再初始化数据
REM mysql -u root -p < sql\schema.sql
REM python -m scripts.init_data

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## ID 列规范与迁移

所有主键/外键列统一为 `CHAR(32)`，存放 `32 位、无连字符、全大写` 十六进制字符串。
长度常量定义在 `app/models/base.py`（`ID_LENGTH = 32`），取值由 `new_uuid()` 生成。
涉及的列包括：`id`、以 `_id` 结尾的列、以 `_by` 结尾的列，共 **87** 个。

### 1. 列类型迁移（CHAR(36) → CHAR(32)）

老库中这些列是 `CHAR(36)`，需要执行结构迁移：

```bat
cd D:\project\FastApiProject\item_manager_backend
conda activate item_manager
python -m scripts.migrate_ids_to_char32 --dry-run   REM 先审查将要执行的 DDL
python -m scripts.migrate_ids_to_char32             REM 确认后实际执行
```

脚本从 `information_schema` 动态读取全部外键，按**原名称与原级联规则**删除后重建，
并保留原有的列注释与默认值，因此可安全重复执行（已是 `CHAR(32)` 的列会自动跳过）。

两点需要注意：

- MySQL 不允许直接修改被外键引用的列，所以脚本必须走「删外键 → 改列 → 重建外键」；
- DDL 在 MySQL 中会隐式提交，无法整体回滚，请事先备份并在低峰期执行。

### 2. 列值格式迁移（带连字符 → 无连字符）

如果历史数据里存的是 `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` 形式，需要再做一次值转换：

```bat
python -m scripts.migrate_ids_to_32
```

也可以直接在 MySQL 中执行：

```sql
USE item_manager;
SOURCE D:/project/FastApiProject/item_manager_backend/sql/convert_ids_to_32.sql;
```

迁移完成后，旧 JWT 令牌中的 `jti` 仍是旧格式，需要让用户重新登录。

## 时间列规范

所有时间列统一使用 `app/models/base.py` 中的 `DateTimeMS`，它在 MySQL 下生成
`DATETIME(3)`（毫秒精度），与库中的 `datetime(3)` 完全一致。

注意**不要写成 `DateTime(3)`**：`DateTime` 的第一个位置参数是 `timezone` 而不是精度，
它只会生成 `DATETIME`（无小数秒），与 `server_default=CURRENT_TIMESTAMP(3)` 组合属于
非法 DDL，MySQL 会直接报 `1067 Invalid default value`，导致 `python -m scripts.init_db`
在空库上无法建表。

启动后访问：

- Swagger：`http://127.0.0.1:8000/docs`
- ReDoc：`http://127.0.0.1:8000/redoc`
- 健康检查：`http://127.0.0.1:8000/health`

默认管理员：

- 邮箱：`admin@example.com`
- 密码：`Admin123!`

生产环境请修改 `SECRET_KEY`、默认管理员密码，并将 `DEBUG` 设为 `false`。
