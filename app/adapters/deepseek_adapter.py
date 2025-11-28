"""
DeepSeek LLM适配器（使用OpenAI SDK）
"""
from typing import List, Optional
from openai import AsyncOpenAI
from app.adapters.base import BaseLLMAdapter, ChatMessage, ChatCompletionResponse
from app.utils.logger import logger


class DeepSeekAdapter(BaseLLMAdapter):
    """DeepSeek适配器实现（使用OpenAI SDK，DeepSeek API兼容OpenAI格式）"""
    
    def __init__(self, api_key: str, base_url: str, default_model: str):
        """
        初始化DeepSeek适配器
        
        Args:
            api_key: DeepSeek API密钥
            base_url: API基础URL
            default_model: 默认模型名称
        """
        super().__init__(api_key, base_url, default_model)
        # 初始化OpenAI客户端（DeepSeek API兼容OpenAI格式）
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
    
    async def chat_completion(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        temperature: Optional[float] = 0.7,
        max_tokens: Optional[int] = None,
        stream: Optional[bool] = False,
        **kwargs
    ) -> ChatCompletionResponse:
        """
        发送聊天完成请求到DeepSeek API（使用OpenAI SDK）
        """
        if not self.api_key:
            raise ValueError("DeepSeek API Key未配置")
        
        model = model or self.default_model
        
        # 构建请求参数
        request_params = {
            "model": model,
            "messages": [{"role": msg.role, "content": msg.content} for msg in messages],
            "temperature": temperature,
        }
        
        if max_tokens:
            request_params["max_tokens"] = max_tokens
        if stream:
            request_params["stream"] = stream
        if "top_p" in kwargs:
            request_params["top_p"] = kwargs["top_p"]
        if "frequency_penalty" in kwargs:
            request_params["frequency_penalty"] = kwargs["frequency_penalty"]
        if "presence_penalty" in kwargs:
            request_params["presence_penalty"] = kwargs["presence_penalty"]
        
        try:
            logger.info(f"发送请求到DeepSeek: model={model}, messages_count={len(messages)}")
            
            # 使用OpenAI SDK调用API（DeepSeek API兼容OpenAI格式）
            response = await self.client.chat.completions.create(**request_params)
            
            # 流式响应由调用方处理，这里不处理
            if stream:
                # 流式响应应该使用 streaming.py 中的函数处理
                # 这里不应该被调用
                raise ValueError("流式响应应该使用 streaming 模块处理")
            
            # 处理usage字段，只保留简单的整数键值对
            usage = None
            if response.usage:
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }
                # DeepSeek可能返回额外的usage字段，如果存在也包含进去
                if hasattr(response.usage, 'prompt_cache_hit_tokens'):
                    usage["prompt_cache_hit_tokens"] = response.usage.prompt_cache_hit_tokens
                if hasattr(response.usage, 'prompt_cache_miss_tokens'):
                    usage["prompt_cache_miss_tokens"] = response.usage.prompt_cache_miss_tokens
            
            # 转换为统一格式
            return ChatCompletionResponse(
                id=response.id,
                created=response.created,
                model=response.model,
                choices=[
                    {
                        "index": choice.index,
                        "message": {
                            "role": choice.message.role,
                            "content": choice.message.content
                        },
                        "finish_reason": choice.finish_reason
                    }
                    for choice in response.choices
                ],
                usage=usage
            )
        
        except Exception as e:
            logger.error(f"DeepSeek请求失败: {str(e)}")
            raise Exception(f"DeepSeek API错误: {str(e)}")
    
    async def list_models(self) -> List[str]:
        """获取DeepSeek可用模型列表"""
        return [
            "deepseek-chat",
            "deepseek-coder",
        ]

