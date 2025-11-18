"""
OpenAI LLM适配器（使用官方SDK）
"""
from typing import List, Optional
from openai import AsyncOpenAI
from app.adapters.base import BaseLLMAdapter, ChatMessage, ChatCompletionResponse
from app.utils.logger import logger


class OpenAIAdapter(BaseLLMAdapter):
    """OpenAI适配器实现（使用官方SDK）"""
    
    def __init__(self, api_key: str, base_url: str, default_model: str):
        """
        初始化OpenAI适配器
        
        Args:
            api_key: OpenAI API密钥
            base_url: API基础URL
            default_model: 默认模型名称
        """
        super().__init__(api_key, base_url, default_model)
        # 初始化OpenAI客户端
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
        发送聊天完成请求到OpenAI API（使用官方SDK）
        """
        if not self.api_key:
            raise ValueError("OpenAI API Key未配置")
        
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
            logger.info(f"发送请求到OpenAI: model={model}, messages_count={len(messages)}")
            
            # 使用OpenAI SDK调用API
            response = await self.client.chat.completions.create(**request_params)
            
            # 处理流式响应
            if stream:
                # 流式响应需要特殊处理，这里先返回第一个chunk
                # 实际应用中可能需要返回生成器
                raise NotImplementedError("流式响应暂未实现，请设置 stream=False")
            
            # 处理usage字段，只保留简单的整数键值对
            usage = None
            if response.usage:
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }
            
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
            logger.error(f"OpenAI请求失败: {str(e)}")
            raise Exception(f"OpenAI API错误: {str(e)}")
    
    async def list_models(self) -> List[str]:
        """获取OpenAI可用模型列表"""
        return [
            "gpt-4",
            "gpt-4-turbo",
            "gpt-3.5-turbo",
        ]

