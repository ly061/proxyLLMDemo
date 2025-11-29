"""
流式响应处理
"""
import json
from typing import AsyncGenerator
from app.adapters.base import ChatMessage
from app.utils.adapter_factory import get_adapter
from app.utils.logger import logger
from app.routers.chat import ChatCompletionRequest


async def stream_chat_completion(
    request: ChatCompletionRequest,
    user_info: dict
) -> AsyncGenerator[str, None]:
    """
    流式聊天完成响应生成器
    
    Args:
        request: 聊天完成请求
        user_info: 用户信息
        
    Yields:
        SSE格式的数据块
    """
    try:
        # 转换消息格式（转换为字典格式，因为OpenAI SDK需要字典而不是Pydantic模型）
        messages = [
            {"role": msg["role"], "content": msg["content"]}
            for msg in request.messages
        ]
        
        # 获取适配器
        adapter = get_adapter(request.model)
        
        # 调用LLM的流式接口
        logger.info(f"开始流式响应: model={request.model}")
        
        # 构建请求参数
        request_params = {
            "model": request.model,
            "messages": messages,
            "temperature": request.temperature,
            "stream": True,
        }
        
        if request.max_tokens:
            request_params["max_tokens"] = request.max_tokens
        if request.top_p:
            request_params["top_p"] = request.top_p
        if request.frequency_penalty:
            request_params["frequency_penalty"] = request.frequency_penalty
        if request.presence_penalty:
            request_params["presence_penalty"] = request.presence_penalty
        
        # 调用适配器的流式接口
        if hasattr(adapter, 'client') and hasattr(adapter.client, 'chat') and hasattr(adapter.client.chat, 'completions'):
            stream = await adapter.client.chat.completions.create(**request_params)
            
            # 发送流式数据（使用异步迭代）
            full_content = ""
            async for chunk in stream:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if delta and delta.content:
                        content = delta.content
                        full_content += content
                        
                        # 发送SSE格式数据
                        data = {
                            "id": chunk.id if hasattr(chunk, 'id') else "",
                            "object": "chat.completion.chunk",
                            "created": chunk.created if hasattr(chunk, 'created') else 0,
                            "model": chunk.model if hasattr(chunk, 'model') else request.model,
                            "choices": [{
                                "index": chunk.choices[0].index if hasattr(chunk.choices[0], 'index') else 0,
                                "delta": {"content": content},
                                "finish_reason": chunk.choices[0].finish_reason if hasattr(chunk.choices[0], 'finish_reason') else None
                            }]
                        }
                        yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
            
            # 发送结束标记
            yield "data: [DONE]\n\n"
            logger.info(f"流式响应完成: model={request.model}, total_length={len(full_content)}")
        else:
            # 如果不支持流式，返回错误
            error_data = {
                "error": {
                    "message": "该适配器不支持流式响应",
                    "type": "stream_not_supported"
                }
            }
            yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
            
    except Exception as e:
        logger.error(f"流式响应错误: {str(e)}", exc_info=True)
        error_data = {
            "error": {
                "message": f"流式响应处理失败: {str(e)}",
                "type": "stream_error"
            }
        }
        yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"

