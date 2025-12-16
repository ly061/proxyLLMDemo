"""
API Key认证模块
"""
from typing import Optional
from fastapi import Security, HTTPException, status, Request
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials
from app.config import settings
from app.utils.logger import logger
from app.database.db import check_api_key

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


async def _extract_api_key(request: Request) -> Optional[str]:
    """
    从请求中提取 API Key
    支持两种方式：
    1. X-API-Key 头部
    2. Authorization: Bearer <token> 头部（兼容 CodeceptJS AI）
    """
    # 方式1: X-API-Key 头部
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return api_key
    
    # 方式2: Authorization: Bearer <token> 头部
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:]  # 移除 "Bearer " 前缀
    
    return None


async def get_user_info_from_request(request: Request) -> dict:
    """
    从 Request 对象中提取并验证 API Key
    用于支持 Authorization: Bearer 头部（CodeceptJS AI）
    """
    extracted_key = await _extract_api_key(request)
    if not extracted_key:
        logger.warning("请求缺少API Key")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少API Key，请在请求头中添加 X-API-Key 或 Authorization: Bearer <token>"
        )
    return await _validate_api_key(extracted_key)


async def _validate_api_key(extracted_key: str) -> dict:
    """
    验证 API Key 并返回用户信息
    """
    # 使用数据库验证API Key
    if settings.USE_DATABASE_AUTH:
        user_info = await check_api_key(extracted_key)
        if not user_info:
            logger.warning(f"无效的API Key尝试: {extracted_key[:10]}...")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的API Key或Key已过期"
            )
        logger.info(f"API Key验证成功: 用户={user_info['username']}, Key={extracted_key[:10]}...")
        return user_info
    
    # 兼容旧的环境变量配置方式（已废弃）
    if settings.API_KEYS and extracted_key not in settings.API_KEYS:
        logger.warning(f"无效的API Key尝试: {extracted_key[:10]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的API Key"
        )
    
    # 如果没有配置API_KEYS列表，则允许任何非空的API Key
    if not settings.API_KEYS:
        logger.warning("警告: 未配置API_KEYS列表，允许所有请求")
    
    logger.info(f"API Key验证成功: {extracted_key[:10]}...")
    # 返回一个默认的用户信息结构（兼容旧方式）
    return {
        'api_key_id': None,
        'user_id': None,
        'username': 'anonymous',
        'api_key': extracted_key
    }


async def get_user_info(
    api_key: Optional[str] = Security(api_key_header),
    bearer: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme)
) -> dict:
    """
    获取API Key对应的用户信息
    
    支持两种认证方式：
    1. X-API-Key 头部
    2. Authorization: Bearer <token> 头部（兼容 CodeceptJS AI）
    
    Args:
        api_key: 从 X-API-Key 头部获取的API Key
        bearer: 从 Authorization 头部获取的 Bearer token
        
    Returns:
        包含用户信息的字典
        
    Raises:
        HTTPException: API Key无效时抛出401错误
    """
    # 提取 API Key（优先使用 X-API-Key，否则使用 Bearer token）
    extracted_key = api_key
    if not extracted_key and bearer:
        extracted_key = bearer.credentials
    
    if not extracted_key:
        logger.warning("请求缺少API Key")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少API Key，请在请求头中添加 X-API-Key 或 Authorization: Bearer <token>"
        )
    
    return await _validate_api_key(extracted_key)


async def verify_api_key(api_key: Optional[str] = Security(api_key_header)) -> str:
    """
    验证API Key（兼容旧接口）
    
    Args:
        api_key: 从请求头获取的API Key
        
    Returns:
        验证通过的API Key
        
    Raises:
        HTTPException: API Key无效时抛出401错误
    """
    user_info = await get_user_info(api_key)
    return user_info.get('api_key', api_key)
