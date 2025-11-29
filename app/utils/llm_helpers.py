"""
LLM响应处理工具函数
"""
from typing import Dict, Any
from app.adapters.base import ChatCompletionResponse
from app.exceptions import LLMServiceException
from app.utils.logger import logger


def extract_response_content(response: ChatCompletionResponse) -> str:
    """
    从LLM响应中提取内容
    
    Args:
        response: LLM响应对象
        
    Returns:
        响应内容文本
        
    Raises:
        LLMServiceException: 当响应无效或内容为空时
    """
    if not response.choices or len(response.choices) == 0:
        logger.error("LLM响应中没有choices字段")
        raise LLMServiceException("LLM未返回有效响应")
    
    content = response.choices[0].get("message", {}).get("content", "")
    if not content:
        logger.error("LLM响应内容为空")
        raise LLMServiceException("LLM返回内容为空")
    
    return content


def extract_usage_info(response: ChatCompletionResponse) -> Dict[str, int]:
    """
    从LLM响应中提取usage信息
    
    Args:
        response: LLM响应对象
        
    Returns:
        usage字典，包含prompt_tokens, completion_tokens, total_tokens
    """
    if not response.usage:
        return {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0
        }
    
    if isinstance(response.usage, dict):
        return {
            "prompt_tokens": response.usage.get("prompt_tokens", 0),
            "completion_tokens": response.usage.get("completion_tokens", 0),
            "total_tokens": response.usage.get("total_tokens", 0)
        }
    
    # 如果usage是对象
    return {
        "prompt_tokens": getattr(response.usage, "prompt_tokens", 0),
        "completion_tokens": getattr(response.usage, "completion_tokens", 0),
        "total_tokens": getattr(response.usage, "total_tokens", 0)
    }

