"""
数据库模型
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


class User(BaseModel):
    """用户模型"""
    id: Optional[int] = None
    username: str
    email: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    is_active: bool = True


class APIKey(BaseModel):
    """API Key模型"""
    id: Optional[int] = None
    user_id: int
    api_key: str
    key_name: Optional[str] = None
    created_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    is_active: bool = True


class UserCreate(BaseModel):
    """创建用户请求模型"""
    username: str
    email: Optional[str] = None


class APIKeyCreate(BaseModel):
    """创建API Key请求模型"""
    user_id: int
    key_name: Optional[str] = None
    expires_at: Optional[datetime] = None


class APIKeyResponse(BaseModel):
    """API Key响应模型"""
    id: int
    user_id: int
    api_key: str
    key_name: Optional[str] = None
    created_at: datetime
    expires_at: Optional[datetime] = None
    is_active: bool

