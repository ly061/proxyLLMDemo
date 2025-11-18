"""
聊天完成路由
"""
from typing import Optional, List, Union
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from app.adapters.base import ChatMessage, ChatCompletionResponse, BaseLLMAdapter
from app.adapters.deepseek_adapter import DeepSeekAdapter
from app.adapters.openai_adapter import OpenAIAdapter
from app.auth.api_key import verify_api_key
from app.config import settings
from app.utils.cache import cache, cache_key_generator
from app.utils.logger import logger


router = APIRouter(prefix="/api/v1", tags=["chat"])


class ChatCompletionRequest(BaseModel):
    """聊天完成请求"""
    model: Optional[str] = Field(None, description="模型名称，如果不指定则使用默认模型")
    messages: List[dict] = Field(..., description="消息列表")
    temperature: Optional[float] = Field(0.7, ge=0, le=2, description="温度参数")
    max_tokens: Optional[int] = Field(None, gt=0, description="最大token数")
    stream: Optional[bool] = Field(False, description="是否流式返回")
    top_p: Optional[float] = Field(None, ge=0, le=1, description="Top-p采样")
    frequency_penalty: Optional[float] = Field(None, ge=-2, le=2, description="频率惩罚")
    presence_penalty: Optional[float] = Field(None, ge=-2, le=2, description="存在惩罚")


def get_adapter(model: Optional[str] = None) -> BaseLLMAdapter:
    """
    根据模型名称获取对应的适配器
    
    Args:
        model: 模型名称
        
    Returns:
        LLM适配器实例
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


@router.post("/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(
    request: ChatCompletionRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    聊天完成接口（兼容OpenAI格式）
    
    支持DeepSeek和其他LLM提供商
    """
    try:
        # 转换消息格式
        messages = [
            ChatMessage(role=msg["role"], content=msg["content"])
            for msg in request.messages
        ]
        
        # 获取适配器
        adapter = get_adapter(request.model)
        
        # 生成缓存键（如果启用缓存）
        cache_key = None
        if settings.CACHE_ENABLED and not request.stream:
            cache_key = f"chat:{cache_key_generator(request.model, request.messages, request.temperature)}"
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.info("返回缓存结果")
                return cached_result
        
        # 调用LLM
        response = await adapter.chat_completion(
            messages=messages,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stream=request.stream,
            top_p=request.top_p,
            frequency_penalty=request.frequency_penalty,
            presence_penalty=request.presence_penalty
        )
        
        # 缓存结果
        if cache_key:
            cache.set(cache_key, response)
        
        logger.info(f"聊天完成: model={response.model}, choices={len(response.choices)}")
        return response
    
    except Exception as e:
        logger.error(f"聊天完成失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"处理请求时发生错误: {str(e)}"
        )

