"""
OpenAI LLM适配器（可选）
"""
import httpx
import time
from typing import List, Optional
from app.adapters.base import BaseLLMAdapter, ChatMessage, ChatCompletionResponse
from app.utils.logger import logger


class OpenAIAdapter(BaseLLMAdapter):
    """OpenAI适配器实现"""
    
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
        发送聊天完成请求到OpenAI API
        """
        if not self.api_key:
            raise ValueError("OpenAI API Key未配置")
        
        model = model or self.default_model
        url = f"{self.base_url}/chat/completions"
        
        payload = {
            "model": model,
            "messages": [{"role": msg.role, "content": msg.content} for msg in messages],
            "temperature": temperature,
        }
        
        if max_tokens:
            payload["max_tokens"] = max_tokens
        if stream:
            payload["stream"] = stream
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
            logger.info(f"发送请求到OpenAI: model={model}, messages_count={len(messages)}")
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                
                result = response.json()
                
                return ChatCompletionResponse(
                    id=result.get("id", f"openai-{int(time.time())}"),
                    created=result.get("created", int(time.time())),
                    model=result.get("model", model),
                    choices=result.get("choices", []),
                    usage=result.get("usage")
                )
        
        except httpx.HTTPStatusError as e:
            logger.error(f"OpenAI API错误: {e.response.status_code} - {e.response.text}")
            raise Exception(f"OpenAI API错误: {e.response.status_code}")
        except Exception as e:
            logger.error(f"OpenAI请求失败: {str(e)}")
            raise
    
    async def list_models(self) -> List[str]:
        """获取OpenAI可用模型列表"""
        return [
            "gpt-4",
            "gpt-4-turbo",
            "gpt-3.5-turbo",
        ]

