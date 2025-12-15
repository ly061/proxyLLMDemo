"""
自定义 LangChain ChatModel，使用我们的 API 服务
"""
from typing import Any, AsyncIterator, Iterator, List, Optional
import httpx
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    BaseMessage,
    AIMessage,
    HumanMessage,
    SystemMessage,
    ChatMessage,
)
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field
from app.utils.logger import logger


class CustomChatModel(BaseChatModel):
    """
    自定义 ChatModel，使用我们的 API 服务
    
    这个类实现了 LangChain 的 BaseChatModel 接口，
    允许 LangGraph 使用我们的 API 作为 LLM 提供者。
    """
    
    api_key: str = Field(..., description="API Key for authentication")
    base_url: str = Field(default="http://127.0.0.1:8000", description="API base URL")
    model: str = Field(default="deepseek-chat", description="Model name to use")
    temperature: float = Field(default=0.7, description="Temperature parameter")
    max_tokens: Optional[int] = Field(default=None, description="Max tokens")
    timeout: float = Field(default=60.0, description="Request timeout in seconds")
    
    def __init__(self, **kwargs):
        """初始化，允许存储绑定的工具"""
        super().__init__(**kwargs)
        # 使用 object.__setattr__ 绕过 Pydantic 的限制
        object.__setattr__(self, '_bound_tools', None)
    
    @property
    def _llm_type(self) -> str:
        """返回 LLM 类型标识"""
        return "custom_api"
    
    def _convert_message_to_dict(self, message: BaseMessage) -> dict:
        """将 LangChain 消息转换为 API 格式"""
        if isinstance(message, HumanMessage):
            return {"role": "user", "content": message.content}
        elif isinstance(message, AIMessage):
            return {"role": "assistant", "content": message.content}
        elif isinstance(message, SystemMessage):
            return {"role": "system", "content": message.content}
        elif isinstance(message, ChatMessage):
            return {"role": message.role, "content": message.content}
        else:
            # 默认处理
            return {"role": "user", "content": str(message.content)}
    
    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """
        同步生成响应
        
        Args:
            messages: 消息列表
            stop: 停止词列表
            run_manager: 回调管理器
            **kwargs: 其他参数
            
        Returns:
            ChatResult 对象
        """
        # 转换为 API 格式
        api_messages = [self._convert_message_to_dict(msg) for msg in messages]
        
        # 构建请求参数
        request_data = {
            "model": self.model,
            "messages": api_messages,
            "temperature": kwargs.get("temperature", self.temperature),
        }
        
        if self.max_tokens:
            request_data["max_tokens"] = self.max_tokens
        if kwargs.get("max_tokens"):
            request_data["max_tokens"] = kwargs["max_tokens"]
        
        # 构建请求头
        headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
        }
        
        # 发送请求
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.base_url}/api/v1/chat/completions",
                    json=request_data,
                    headers=headers,
                )
                response.raise_for_status()
                result = response.json()
                
                # 提取响应内容
                if "choices" in result and len(result["choices"]) > 0:
                    choice = result["choices"][0]
                    message_content = choice.get("message", {}).get("content", "")
                    
                    # 创建 AIMessage
                    ai_message = AIMessage(content=message_content)
                    
                    # 创建 ChatGeneration
                    generation = ChatGeneration(message=ai_message)
                    
                    # 创建 ChatResult
                    return ChatResult(generations=[generation])
                else:
                    raise ValueError("API 响应格式错误：未找到 choices 字段")
                    
        except httpx.HTTPStatusError as e:
            logger.error(f"API 请求失败: HTTP {e.response.status_code} - {e.response.text}")
            raise Exception(f"API 请求失败: {e.response.status_code}")
        except Exception as e:
            logger.error(f"生成响应时发生错误: {str(e)}")
            raise
    
    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """
        异步生成响应
        
        Args:
            messages: 消息列表
            stop: 停止词列表
            run_manager: 异步回调管理器
            **kwargs: 其他参数
            
        Returns:
            ChatResult 对象
        """
        # 转换为 API 格式
        api_messages = [self._convert_message_to_dict(msg) for msg in messages]
        
        # 构建请求参数
        request_data = {
            "model": self.model,
            "messages": api_messages,
            "temperature": kwargs.get("temperature", self.temperature),
        }
        
        if self.max_tokens:
            request_data["max_tokens"] = self.max_tokens
        if kwargs.get("max_tokens"):
            request_data["max_tokens"] = kwargs["max_tokens"]
        
        # 构建请求头
        headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
        }
        
        # 发送异步请求
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/chat/completions",
                    json=request_data,
                    headers=headers,
                )
                response.raise_for_status()
                result = response.json()
                
                # 提取响应内容
                if "choices" in result and len(result["choices"]) > 0:
                    choice = result["choices"][0]
                    message_content = choice.get("message", {}).get("content", "")
                    
                    # 创建 AIMessage
                    ai_message = AIMessage(content=message_content)
                    
                    # 创建 ChatGeneration
                    generation = ChatGeneration(message=ai_message)
                    
                    # 创建 ChatResult
                    return ChatResult(generations=[generation])
                else:
                    raise ValueError("API 响应格式错误：未找到 choices 字段")
                    
        except httpx.HTTPStatusError as e:
            logger.error(f"API 请求失败: HTTP {e.response.status_code} - {e.response.text}")
            raise Exception(f"API 请求失败: {e.response.status_code}")
        except Exception as e:
            logger.error(f"生成响应时发生错误: {str(e)}")
            raise
    
    def bind_tools(self, tools: List[Any], **kwargs: Any) -> "CustomChatModel":
        """
        绑定工具到模型
        
        Args:
            tools: 工具列表
            **kwargs: 其他参数
            
        Returns:
            绑定了工具的新模型实例
        """
        # 创建一个新实例，存储工具信息
        bound_model = CustomChatModel(
            api_key=self.api_key,
            base_url=self.base_url,
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            timeout=self.timeout,
        )
        # 存储工具信息（虽然我们的 API 可能不支持工具调用，但为了兼容性存储）
        object.__setattr__(bound_model, '_bound_tools', tools)
        return bound_model
    
    @property
    def _identifying_params(self) -> dict:
        """返回用于标识此模型的参数"""
        return {
            "base_url": self.base_url,
            "model": self.model,
            "temperature": self.temperature,
        }

