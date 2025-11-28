"""
自定义异常类
"""
from fastapi import HTTPException, status
from typing import Optional


class BaseServiceException(HTTPException):
    """基础服务异常"""
    def __init__(self, detail: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR):
        super().__init__(status_code=status_code, detail=detail)


class LLMServiceException(BaseServiceException):
    """LLM服务异常"""
    def __init__(self, detail: str):
        super().__init__(detail=detail, status_code=status.HTTP_502_BAD_GATEWAY)


class AuthenticationException(BaseServiceException):
    """认证异常"""
    def __init__(self, detail: str = "认证失败"):
        super().__init__(detail=detail, status_code=status.HTTP_401_UNAUTHORIZED)


class RateLimitException(BaseServiceException):
    """限流异常"""
    def __init__(self, detail: str = "请求过于频繁"):
        super().__init__(detail=detail, status_code=status.HTTP_429_TOO_MANY_REQUESTS)


class ValidationException(BaseServiceException):
    """验证异常"""
    def __init__(self, detail: str = "请求参数验证失败"):
        super().__init__(detail=detail, status_code=status.HTTP_400_BAD_REQUEST)


class NotFoundException(BaseServiceException):
    """资源未找到异常"""
    def __init__(self, detail: str = "资源未找到"):
        super().__init__(detail=detail, status_code=status.HTTP_404_NOT_FOUND)


