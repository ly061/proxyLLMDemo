"""
聊天完成路由
"""
from typing import Optional, List, Union
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from app.adapters.base import ChatMessage, ChatCompletionResponse
from app.auth.api_key import verify_api_key, get_user_info
from app.config import settings
from app.utils.cache import cache, cache_key_generator
from app.utils.logger import logger
from app.utils.adapter_factory import get_adapter
from app.database.db import record_request


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


@router.post("/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    user_info: dict = Depends(get_user_info)
):
    """
    聊天完成接口（兼容OpenAI格式）
    
    支持DeepSeek和其他LLM提供商
    支持流式响应（SSE）
    """
    # 流式响应处理
    if request.stream:
        from fastapi.responses import StreamingResponse
        from app.utils.streaming import stream_chat_completion
        
        return StreamingResponse(
            stream_chat_completion(request, user_info),
            media_type="text/event-stream"
        )
    
    # 非流式响应
    try:
        # 转换消息格式
        messages = [
            ChatMessage(role=msg["role"], content=msg["content"])
            for msg in request.messages
        ]
        
        # 获取适配器
        adapter = get_adapter(request.model)
        
        # 生成缓存键（如果启用缓存）
        # 包含用户标识符（api_key_id）以确保不同用户的缓存隔离
        cache_key = None
        if settings.CACHE_ENABLED and not request.stream:
            api_key_id = user_info.get('api_key_id', 'anonymous')
            cache_key = f"chat:{cache_key_generator(request.model, request.messages, request.temperature, api_key_id)}"
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.info("返回缓存结果")
                # 即使从缓存返回，也要记录请求到数据库（用于审计跟踪）
                if user_info.get('api_key_id') is not None and user_info.get('user_id') is not None:
                    try:
                        # 提取用户的问题（取最后一条user角色的消息）
                        user_query = None
                        if request.messages:
                            # 从后往前查找最后一条user消息
                            for msg in reversed(request.messages):
                                if msg.get('role') == 'user':
                                    user_query = msg.get('content', '')
                                    break
                            # 如果没找到user消息，取第一条消息的内容
                            if not user_query and request.messages:
                                user_query = request.messages[0].get('content', '')
                        
                        await record_request(
                            api_key_id=user_info['api_key_id'],
                            user_id=user_info['user_id'],
                            model=cached_result.model if hasattr(cached_result, 'model') else request.model,
                            user_query=user_query,
                            prompt_tokens=0,  # 缓存命中，无token消耗
                            completion_tokens=0,
                            total_tokens=0
                        )
                        logger.debug("缓存命中请求已记录到数据库（token=0）")
                    except Exception as e:
                        logger.error(f"记录缓存命中请求失败: {str(e)}", exc_info=True)
                return cached_result
        
        # 调用LLM（非流式）
        response = await adapter.chat_completion(
            messages=messages,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stream=False,  # 非流式响应
            top_p=request.top_p,
            frequency_penalty=request.frequency_penalty,
            presence_penalty=request.presence_penalty
        )
        
        # 缓存结果
        if cache_key:
            cache.set(cache_key, response)
        
        # 记录token消耗情况
        if user_info.get('api_key_id') is not None and user_info.get('user_id') is not None and response.usage:
            try:
                usage = response.usage
                if isinstance(usage, dict):
                    # 提取用户的问题（取最后一条user角色的消息）
                    user_query = None
                    if request.messages:
                        # 从后往前查找最后一条user消息
                        for msg in reversed(request.messages):
                            if msg.get('role') == 'user':
                                user_query = msg.get('content', '')
                                break
                        # 如果没找到user消息，取第一条消息的内容
                        if not user_query and request.messages:
                            user_query = request.messages[0].get('content', '')
                    
                    await record_request(
                        api_key_id=user_info['api_key_id'],
                        user_id=user_info['user_id'],
                        model=response.model,
                        user_query=user_query,
                        prompt_tokens=usage.get('prompt_tokens', 0),
                        completion_tokens=usage.get('completion_tokens', 0),
                        total_tokens=usage.get('total_tokens', 0)
                    )
            except Exception as e:
                logger.error(f"记录token消耗失败: {str(e)}")
        
        logger.info(f"聊天完成: model={response.model}, choices={len(response.choices)}")
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"聊天完成失败: {str(e)}", exc_info=True)
        from app.exceptions import LLMServiceException
        raise LLMServiceException(f"处理请求时发生错误: {str(e)}")

