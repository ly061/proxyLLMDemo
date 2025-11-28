# 数据库迁移指南 - SQLite 到 MySQL

## 概述

项目已从 SQLite 迁移到 MySQL，以下是迁移步骤和注意事项。

## 数据库配置

在 `.env` 文件中添加以下配置：

```env
# MySQL配置
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=12345678
MYSQL_DATABASE=sonic
MYSQL_CHARSET=utf8mb4
MYSQL_POOL_SIZE=10
MYSQL_MAX_OVERFLOW=20
```

## 迁移步骤

### 1. 创建数据库

```sql
CREATE DATABASE IF NOT EXISTS sonic CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 2. 运行应用初始化

应用启动时会自动创建表结构：

```bash
python run.py
```

或手动初始化：

```python
from app.database.db import init_db
import asyncio

asyncio.run(init_db())
```

### 3. 数据迁移（可选）

如果有现有 SQLite 数据需要迁移，可以使用以下脚本：

```python
import sqlite3
import aiomysql
import asyncio
from app.config import settings

async def migrate_data():
    # 连接 SQLite
    sqlite_conn = sqlite3.connect('data/api_keys.db')
    sqlite_cursor = sqlite_conn.cursor()
    
    # 连接 MySQL
    mysql_pool = await aiomysql.create_pool(
        host=settings.MYSQL_HOST,
        port=settings.MYSQL_PORT,
        user=settings.MYSQL_USER,
        password=settings.MYSQL_PASSWORD,
        db=settings.MYSQL_DATABASE,
        charset=settings.MYSQL_CHARSET
    )
    
    async with mysql_pool.acquire() as mysql_conn:
        async with mysql_conn.cursor() as mysql_cursor:
            # 迁移用户数据
            sqlite_cursor.execute("SELECT * FROM users")
            users = sqlite_cursor.fetchall()
            for user in users:
                await mysql_cursor.execute(
                    "INSERT INTO users (id, username, email, created_at, updated_at, is_active) VALUES (%s, %s, %s, %s, %s, %s)",
                    user
                )
            
            # 迁移 API Key 数据
            sqlite_cursor.execute("SELECT * FROM api_keys")
            api_keys = sqlite_cursor.fetchall()
            for key in api_keys:
                await mysql_cursor.execute(
                    "INSERT INTO api_keys (id, user_id, api_key, key_name, created_at, last_used_at, expires_at, is_active) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                    key
                )
            
            # 迁移请求记录
            sqlite_cursor.execute("SELECT * FROM api_requests")
            requests = sqlite_cursor.fetchall()
            for req in requests:
                await mysql_cursor.execute(
                    "INSERT INTO api_requests (id, api_key_id, user_id, model, user_query, prompt_tokens, completion_tokens, total_tokens, request_time) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    req
                )
            
            await mysql_conn.commit()
    
    sqlite_conn.close()
    mysql_pool.close()
    await mysql_pool.wait_closed()
    print("数据迁移完成")

if __name__ == "__main__":
    asyncio.run(migrate_data())
```

## 主要变更

### 1. 数据库连接

- **之前**: 使用 `aiosqlite`，每次请求创建新连接
- **现在**: 使用 `aiomysql`，连接池管理

### 2. SQL 语法

- **之前**: SQLite 语法 (`?` 占位符)
- **现在**: MySQL 语法 (`%s` 占位符)

### 3. 数据类型

- **之前**: SQLite 的 `BOOLEAN` (0/1)
- **现在**: MySQL 的 `BOOLEAN` (TRUE/FALSE)

### 4. 异常处理

- **之前**: `aiosqlite.IntegrityError`
- **现在**: `aiomysql.IntegrityError`

## 性能优化

1. **连接池**: 使用连接池减少连接开销
2. **索引**: 已添加必要的索引优化查询性能
3. **异步操作**: 所有数据库操作都是异步的

## 注意事项

1. 确保 MySQL 服务正在运行
2. 确保数据库用户有足够的权限
3. 生产环境建议使用更强的密码
4. 建议配置 MySQL 的 `max_connections` 参数

## 回滚方案

如果需要回滚到 SQLite：

1. 恢复 `app/database/db.py` 的旧版本
2. 恢复 `app/routers/admin.py` 的旧版本
3. 更新 `requirements.txt` 移除 `aiomysql`
4. 恢复配置中的 `DATABASE_PATH`


