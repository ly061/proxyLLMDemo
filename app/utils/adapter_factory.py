"""
适配器工厂 - 统一管理 LLM 适配器创建
"""
from typing import Optional
from fastapi import HTTPException, status
from app.adapters.base import BaseLLMAdapter
from app.adapters.deepseek_adapter import DeepSeekAdapter
from app.adapters.openai_adapter import OpenAIAdapter
from app.config import settings


def get_adapter(model: Optional[str] = None) -> BaseLLMAdapter:
    """
    根据模型名称获取对应的适配器
    
    Args:
        model: 模型名称
        
    Returns:
        LLM适配器实例
        
    Raises:
        HTTPException: 当模型不支持或 API Key 未配置时
    """
    # 默认使用DeepSeek
    if not model or model.startswith("deepseek"):
        if not settings.DEEPSEEK_API_KEY:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="DeepSeek API Key未配置"
            )
        return DeepSeekAdapter(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
            default_model=settings.DEEPSEEK_MODEL
        )
    elif model.startswith("gpt") or model.startswith("openai"):
        if not settings.OPENAI_API_KEY:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="OpenAI API Key未配置"
            )
        return OpenAIAdapter(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
            default_model=settings.OPENAI_MODEL
        )
    else:
        # 默认使用DeepSeek
        if not settings.DEEPSEEK_API_KEY:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="DeepSeek API Key未配置"
            )
        return DeepSeekAdapter(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
            default_model=settings.DEEPSEEK_MODEL
        )


