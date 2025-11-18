"""
LLM适配器基类
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel


class ChatMessage(BaseModel):
    """聊天消息模型"""
    role: str  # system, user, assistant
    content: str


class ChatCompletionRequest(BaseModel):
    """聊天完成请求模型"""
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    stream: Optional[bool] = False
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None


class ChatCompletionResponse(BaseModel):
    """聊天完成响应模型"""
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Dict[str, Any]]
    usage: Optional[Any] = None  # 使用Any类型以支持各种usage格式（包括嵌套对象）
    
    class Config:
        # 允许任意类型，避免严格验证导致的错误
        arbitrary_types_allowed = True


class BaseLLMAdapter(ABC):
    """LLM适配器基类"""
    
    def __init__(self, api_key: str, base_url: str, default_model: str):
        """
        初始化适配器
        
        Args:
            api_key: API密钥
            base_url: API基础URL
            default_model: 默认模型名称
        """
        self.api_key = api_key
        self.base_url = base_url
        self.default_model = default_model
    
    @abstractmethod
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
        发送聊天完成请求
        
        Args:
            messages: 消息列表
            model: 模型名称（如果为None则使用默认模型）
            temperature: 温度参数
            max_tokens: 最大token数
            stream: 是否流式返回
            **kwargs: 其他参数
            
        Returns:
            聊天完成响应
        """
        pass
    
    @abstractmethod
    async def list_models(self) -> List[str]:
        """
        获取可用模型列表
        
        Returns:
            模型名称列表
        """
        pass
    
    def get_default_model(self) -> str:
        """获取默认模型"""
        return self.default_model

