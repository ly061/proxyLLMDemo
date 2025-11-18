"""
API Key认证模块
"""
from typing import Optional
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
from app.config import settings
from app.utils.logger import logger

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: Optional[str] = Security(api_key_header)) -> str:
    """
    验证API Key
    
    Args:
        api_key: 从请求头获取的API Key
        
    Returns:
        验证通过的API Key
        
    Raises:
        HTTPException: API Key无效时抛出401错误
    """
    if not api_key:
        logger.warning("请求缺少API Key")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少API Key，请在请求头中添加 X-API-Key"
        )
    
    # 检查API Key是否在允许列表中
    if settings.API_KEYS and api_key not in settings.API_KEYS:
        logger.warning(f"无效的API Key尝试: {api_key[:10]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的API Key"
        )
    
    # 如果没有配置API_KEYS列表，则允许任何非空的API Key
    # 这在开发环境中可能有用，但生产环境应该配置API_KEYS
    if not settings.API_KEYS:
        logger.warning("警告: 未配置API_KEYS列表，允许所有请求")
    
    logger.info(f"API Key验证成功: {api_key[:10]}...")
    return api_key
