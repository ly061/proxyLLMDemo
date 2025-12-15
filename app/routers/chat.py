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
from app.database.db import (
    record_request,
    get_conversation,
    get_conversation_messages,
    add_message_to_conversation,
    create_conversation
)


router = APIRouter(prefix="/api/v1", tags=["chat"])


class ChatCompletionRequest(BaseModel):
    """聊天完成请求"""
    model: Optional[str] = Field(None, description="模型名称，如果不指定则使用默认模型")
    messages: List[dict] = Field(..., description="消息列表")
    conversation_id: Optional[int] = Field(None, description="会话ID，如果提供则自动加载历史消息并建立上下文")
    temperature: Optional[float] = Field(0.7, ge=0, le=2, description="温度参数")
    max_tokens: Optional[int] = Field(None, gt=0, description="最大token数")
    stream: Optional[bool] = Field(False, description="是否流式返回（已禁用，默认非流式）")
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
    默认使用非流式响应
    
    如果提供了conversation_id，会自动加载历史消息并建立上下文
    """
    # 强制使用非流式响应（忽略 stream 参数）
    request.stream = False
    
    # 非流式响应
    try:
        conversation_id = request.conversation_id
        all_messages = list(request.messages)  # 当前请求的消息
        auto_created_conversation = False  # 标记是否自动创建了会话
        
        # 如果没有提供conversation_id，自动创建一个新会话
        if not conversation_id:
            user_id = user_info.get('user_id')
            api_key_id = user_info.get('api_key_id')
            
            if user_id and api_key_id:
                try:
                    # 自动生成会话标题（使用第一条用户消息的前50个字符）
                    title = "新对话"
                    if request.messages:
                        for msg in request.messages:
                            if msg.get('role') == 'user':
                                content = msg.get('content', '')
                                if content:
                                    title = content[:50] + ("..." if len(content) > 50 else "")
                                    break
                    
                    conversation_id = await create_conversation(
                        user_id=user_id,
                        api_key_id=api_key_id,
                        title=title
                    )
                    auto_created_conversation = True
                    logger.info(f"自动创建新会话: conversation_id={conversation_id}, user_id={user_id}")
                except Exception as e:
                    logger.error(f"自动创建会话失败: {str(e)}", exc_info=True)
                    # 如果创建失败，继续执行但不保存消息
        
        # 如果提供了conversation_id，加载历史消息
        if conversation_id:
            user_id = user_info.get('user_id')
            api_key_id = user_info.get('api_key_id')
            
            if not user_id or not api_key_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="用户信息不完整，无法使用会话功能"
                )
            
            # 如果不是自动创建的会话，需要验证会话属于当前用户
            if not auto_created_conversation:
                conversation = await get_conversation(
                    conversation_id=conversation_id,
                    user_id=user_id,
                    api_key_id=api_key_id
                )
                
                if not conversation:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="会话不存在或无权访问"
                    )
            
            # 加载历史消息（如果是新创建的会话，历史消息为空）
            history_messages = await get_conversation_messages(conversation_id)
            
            # 将历史消息转换为字典格式，并合并到当前消息前面
            history_dicts = [
                {"role": msg["role"], "content": msg["content"]}
                for msg in history_messages
            ]
            
            # 合并历史消息和当前消息
            all_messages = history_dicts + all_messages
            
            logger.info(f"加载会话历史: conversation_id={conversation_id}, history_count={len(history_dicts)}, new_messages={len(request.messages)}")
        
        # 转换消息格式
        messages = [
            ChatMessage(role=msg["role"], content=msg["content"])
            for msg in all_messages
        ]
        
        # 获取适配器
        adapter = get_adapter(request.model)
        
        # 生成缓存键（如果启用缓存）
        # 包含用户标识符（api_key_id）以确保不同用户的缓存隔离
        # 注意：如果使用了conversation_id，不启用缓存（因为每次对话上下文都在变化）
        cache_key = None
        if settings.CACHE_ENABLED and not conversation_id:
            api_key_id = user_info.get('api_key_id', 'anonymous')
            cache_key = f"chat:{cache_key_generator(request.model, all_messages, request.temperature, api_key_id)}"
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.info("返回缓存结果")
                # 即使从缓存返回，也要记录请求到数据库（用于审计跟踪）
                if user_info.get('api_key_id') is not None and user_info.get('user_id') is not None:
                    try:
                        # 提取用户的问题（取最后一条user角色的消息）
                        user_query = None
                        if all_messages:
                            # 从后往前查找最后一条user消息
                            for msg in reversed(all_messages):
                                if msg.get('role') == 'user':
                                    user_query = msg.get('content', '')
                                    break
                            # 如果没找到user消息，取第一条消息的内容
                            if not user_query and all_messages:
                                user_query = all_messages[0].get('content', '')
                        
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
                    if all_messages:
                        # 从后往前查找最后一条user消息
                        for msg in reversed(all_messages):
                            if msg.get('role') == 'user':
                                user_query = msg.get('content', '')
                                break
                        # 如果没找到user消息，取第一条消息的内容
                        if not user_query and all_messages:
                            user_query = all_messages[0].get('content', '')
                    
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
        
        # 如果使用了conversation_id，保存消息到数据库
        if conversation_id:
            try:
                user_id = user_info.get('user_id')
                if user_id:
                    # 保存用户消息（只保存当前请求中的新消息）
                    for msg in request.messages:
                        if msg.get('role') in ['user', 'system']:
                            await add_message_to_conversation(
                                conversation_id=conversation_id,
                                role=msg['role'],
                                content=msg['content']
                            )
                    
                    # 保存助手回复
                    if response.choices and len(response.choices) > 0:
                        assistant_message = response.choices[0].get('message', {})
                        if assistant_message.get('content'):
                            await add_message_to_conversation(
                                conversation_id=conversation_id,
                                role='assistant',
                                content=assistant_message['content']
                            )
                    
                    logger.info(f"消息已保存到会话: conversation_id={conversation_id}")
            except Exception as e:
                logger.error(f"保存消息到会话失败: {str(e)}", exc_info=True)
                # 不抛出异常，因为主要功能（聊天）已经完成
        
        # 将响应转换为字典，添加conversation_id字段
        # Pydantic模型支持dict()和model_dump()方法
        try:
            if hasattr(response, 'model_dump'):
                response_dict = response.model_dump()
            elif hasattr(response, 'dict'):
                response_dict = response.dict()
            else:
                # 如果不是Pydantic模型，尝试直接转换
                response_dict = {
                    'id': getattr(response, 'id', ''),
                    'object': getattr(response, 'object', 'chat.completion'),
                    'created': getattr(response, 'created', 0),
                    'model': getattr(response, 'model', ''),
                    'choices': getattr(response, 'choices', []),
                    'usage': getattr(response, 'usage', None)
                }
        except Exception as e:
            logger.error(f"转换响应为字典失败: {str(e)}", exc_info=True)
            response_dict = {
                'id': getattr(response, 'id', ''),
                'object': 'chat.completion',
                'created': getattr(response, 'created', 0),
                'model': getattr(response, 'model', ''),
                'choices': getattr(response, 'choices', []),
                'usage': getattr(response, 'usage', None)
            }
        
        # 如果创建了会话或使用了会话，在响应中添加conversation_id
        if conversation_id:
            response_dict['conversation_id'] = conversation_id
        
        logger.info(f"聊天完成: model={response.model}, choices={len(response.choices)}, conversation_id={conversation_id or 'none'}")
        return response_dict
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"聊天完成失败: {str(e)}", exc_info=True)
        from app.exceptions import LLMServiceException
        raise LLMServiceException(f"处理请求时发生错误: {str(e)}")

