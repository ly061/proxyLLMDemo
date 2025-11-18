"""
DeepSeek LLM适配器
"""
import httpx
import time
from typing import List, Optional
from app.adapters.base import BaseLLMAdapter, ChatMessage, ChatCompletionResponse
from app.utils.logger import logger


class DeepSeekAdapter(BaseLLMAdapter):
    """DeepSeek适配器实现"""
    
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
        发送聊天完成请求到DeepSeek API
        """
        if not self.api_key:
            raise ValueError("DeepSeek API Key未配置")
        
        model = model or self.default_model
        url = f"{self.base_url}/chat/completions"
        
        # 构建请求体
        payload = {
            "model": model,
            "messages": [{"role": msg.role, "content": msg.content} for msg in messages],
            "temperature": temperature,
        }
        
        if max_tokens:
            payload["max_tokens"] = max_tokens
        
        if stream:
            payload["stream"] = stream
        
        # 添加其他参数
        if "top_p" in kwargs:
            payload["top_p"] = kwargs["top_p"]
        if "frequency_penalty" in kwargs:
            payload["frequency_penalty"] = kwargs["frequency_penalty"]
        if "presence_penalty" in kwargs:
            payload["presence_penalty"] = kwargs["presence_penalty"]
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            logger.info(f"发送请求到DeepSeek: model={model}, messages_count={len(messages)}")
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                
                result = response.json()
                
                # 处理usage字段，只保留简单的整数键值对
                usage = result.get("usage")
                if usage and isinstance(usage, dict):
                    # 只保留值为整数的字段，忽略嵌套对象
                    clean_usage = {
                        k: v for k, v in usage.items() 
                        if isinstance(v, (int, float))
                    }
                    usage = clean_usage if clean_usage else None
                
                # 转换为统一格式
                return ChatCompletionResponse(
                    id=result.get("id", f"deepseek-{int(time.time())}"),
                    created=result.get("created", int(time.time())),
                    model=result.get("model", model),
                    choices=result.get("choices", []),
                    usage=usage
                )
        
        except httpx.HTTPStatusError as e:
            logger.error(f"DeepSeek API错误: {e.response.status_code} - {e.response.text}")
            raise Exception(f"DeepSeek API错误: {e.response.status_code}")
        except Exception as e:
            logger.error(f"DeepSeek请求失败: {str(e)}")
            raise
    
    async def list_models(self) -> List[str]:
        """获取DeepSeek可用模型列表"""
        return [
            "deepseek-chat",
            "deepseek-coder",
        ]

