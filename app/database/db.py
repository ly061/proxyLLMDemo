"""
数据库连接和初始化
"""
import sqlite3
import aiosqlite
from pathlib import Path
from typing import AsyncGenerator
from app.config import settings
from app.utils.logger import logger


# 数据库文件路径
DB_PATH = Path(settings.DATABASE_PATH) if hasattr(settings, 'DATABASE_PATH') and settings.DATABASE_PATH else Path("data/api_keys.db")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    """
    获取数据库连接
    
    Yields:
        数据库连接
    """
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        yield db


async def init_db():
    """
    初始化数据库，创建表结构
    """
    async with aiosqlite.connect(str(DB_PATH)) as db:
        # 创建用户表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        """)
        
        # 创建API Key表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                api_key TEXT UNIQUE NOT NULL,
                key_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used_at TIMESTAMP,
                expires_at TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        
        # 创建索引
        await db.execute("CREATE INDEX IF NOT EXISTS idx_api_key ON api_keys(api_key)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON api_keys(user_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_api_key_active ON api_keys(api_key, is_active)")
        
        await db.commit()
        logger.info(f"数据库初始化完成: {DB_PATH}")


async def check_api_key(api_key: str) -> dict:
    """
    检查API Key是否有效
    
    Args:
        api_key: 要检查的API Key
        
    Returns:
        包含用户信息的字典，如果无效返回None
    """
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT 
                ak.id,
                ak.user_id,
                ak.api_key,
                ak.key_name,
                ak.last_used_at,
                ak.expires_at,
                ak.is_active,
                u.username,
                u.email,
                u.is_active as user_is_active
            FROM api_keys ak
            JOIN users u ON ak.user_id = u.id
            WHERE ak.api_key = ? AND ak.is_active = 1 AND u.is_active = 1
        """, (api_key,))
        
        row = await cursor.fetchone()
        if row:
            # 检查是否过期
            if row['expires_at']:
                from datetime import datetime
                try:
                    expires_at = datetime.fromisoformat(row['expires_at'].replace('Z', '+00:00'))
                    if datetime.now(expires_at.tzinfo) > expires_at:
                        return None
                except (ValueError, AttributeError):
                    # 如果日期格式不正确，忽略过期检查
                    pass
            
            # 更新最后使用时间
            await db.execute("""
                UPDATE api_keys 
                SET last_used_at = CURRENT_TIMESTAMP 
                WHERE id = ?
            """, (row['id'],))
            await db.commit()
            
            return {
                'id': row['id'],
                'user_id': row['user_id'],
                'username': row['username'],
                'email': row['email'],
                'key_name': row['key_name'],
                'api_key': row['api_key']
            }
        return None

