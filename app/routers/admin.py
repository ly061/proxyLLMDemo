"""
API Key管理路由
"""
import secrets
import string
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from app.database.db import get_db, init_db
from app.database.models import UserCreate, APIKeyCreate, APIKeyResponse
from app.utils.logger import logger
import aiosqlite

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


def generate_api_key(length: int = 32) -> str:
    """生成安全的随机API Key"""
    alphabet = string.ascii_letters + string.digits + "-_"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


@router.post("/users", status_code=status.HTTP_201_CREATED)
async def create_user(user_data: UserCreate):
    """
    创建新用户
    """
    async for db in get_db():
        try:
            cursor = await db.execute("""
                INSERT INTO users (username, email)
                VALUES (?, ?)
            """, (user_data.username, user_data.email))
            await db.commit()
            user_id = cursor.lastrowid
            logger.info(f"创建用户成功: {user_data.username} (ID: {user_id})")
            return {
                "id": user_id,
                "username": user_data.username,
                "email": user_data.email,
                "message": "用户创建成功"
            }
        except aiosqlite.IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户名已存在"
            )


@router.get("/users")
async def list_users():
    """
    获取所有用户列表
    """
    async for db in get_db():
        cursor = await db.execute("""
            SELECT id, username, email, created_at, is_active
            FROM users
            ORDER BY created_at DESC
        """)
        rows = await cursor.fetchall()
        return [
            {
                "id": row["id"],
                "username": row["username"],
                "email": row["email"],
                "created_at": row["created_at"],
                "is_active": bool(row["is_active"])
            }
            for row in rows
        ]


@router.post("/api-keys", status_code=status.HTTP_201_CREATED)
async def create_api_key(key_data: APIKeyCreate):
    """
    为用户创建API Key
    """
    # 生成API Key
    api_key = generate_api_key()
    
    async for db in get_db():
        # 检查用户是否存在
        cursor = await db.execute("SELECT id, is_active FROM users WHERE id = ?", (key_data.user_id,))
        user = await cursor.fetchone()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
        if not user["is_active"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户已被禁用"
            )
        
        # 插入API Key
        expires_at_str = key_data.expires_at.isoformat() if key_data.expires_at else None
        cursor = await db.execute("""
            INSERT INTO api_keys (user_id, api_key, key_name, expires_at)
            VALUES (?, ?, ?, ?)
        """, (key_data.user_id, api_key, key_data.key_name, expires_at_str))
        await db.commit()
        key_id = cursor.lastrowid
        
        logger.info(f"创建API Key成功: 用户ID={key_data.user_id}, Key ID={key_id}")
        
        return {
            "id": key_id,
            "user_id": key_data.user_id,
            "api_key": api_key,
            "key_name": key_data.key_name,
            "expires_at": expires_at_str,
            "message": "API Key创建成功，请妥善保管"
        }


@router.get("/api-keys")
async def list_api_keys(user_id: Optional[int] = None):
    """
    获取API Key列表
    """
    async for db in get_db():
        if user_id:
            cursor = await db.execute("""
                SELECT ak.id, ak.user_id, ak.api_key, ak.key_name, 
                       ak.created_at, ak.last_used_at, ak.expires_at, ak.is_active,
                       u.username
                FROM api_keys ak
                JOIN users u ON ak.user_id = u.id
                WHERE ak.user_id = ?
                ORDER BY ak.created_at DESC
            """, (user_id,))
        else:
            cursor = await db.execute("""
                SELECT ak.id, ak.user_id, ak.api_key, ak.key_name,
                       ak.created_at, ak.last_used_at, ak.expires_at, ak.is_active,
                       u.username
                FROM api_keys ak
                JOIN users u ON ak.user_id = u.id
                ORDER BY ak.created_at DESC
            """)
        
        rows = await cursor.fetchall()
        return [
            {
                "id": row["id"],
                "user_id": row["user_id"],
                "username": row["username"],
                "api_key": row["api_key"][:10] + "..." if row["api_key"] else None,  # 只显示前10位
                "key_name": row["key_name"],
                "created_at": row["created_at"],
                "last_used_at": row["last_used_at"],
                "expires_at": row["expires_at"],
                "is_active": bool(row["is_active"])
            }
            for row in rows
        ]


@router.delete("/api-keys/{key_id}")
async def delete_api_key(key_id: int):
    """
    删除API Key（软删除，设置为非活跃状态）
    """
    async for db in get_db():
        cursor = await db.execute("""
            UPDATE api_keys SET is_active = 0 WHERE id = ?
        """, (key_id,))
        await db.commit()
        
        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API Key不存在"
            )
        
        logger.info(f"删除API Key成功: Key ID={key_id}")
        return {"message": "API Key已删除"}


@router.put("/api-keys/{key_id}/activate")
async def activate_api_key(key_id: int):
    """
    激活API Key
    """
    async for db in get_db():
        cursor = await db.execute("""
            UPDATE api_keys SET is_active = 1 WHERE id = ?
        """, (key_id,))
        await db.commit()
        
        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API Key不存在"
            )
        
        logger.info(f"激活API Key成功: Key ID={key_id}")
        return {"message": "API Key已激活"}


@router.get("/stats")
async def get_stats():
    """
    获取统计信息
    """
    async for db in get_db():
        # 用户统计
        cursor = await db.execute("SELECT COUNT(*) as total FROM users")
        total_users = (await cursor.fetchone())["total"]
        
        cursor = await db.execute("SELECT COUNT(*) as total FROM users WHERE is_active = 1")
        active_users = (await cursor.fetchone())["total"]
        
        # API Key统计
        cursor = await db.execute("SELECT COUNT(*) as total FROM api_keys")
        total_keys = (await cursor.fetchone())["total"]
        
        cursor = await db.execute("SELECT COUNT(*) as total FROM api_keys WHERE is_active = 1")
        active_keys = (await cursor.fetchone())["total"]
        
        return {
            "users": {
                "total": total_users,
                "active": active_users
            },
            "api_keys": {
                "total": total_keys,
                "active": active_keys
            }
        }

