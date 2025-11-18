"""
限流中间件
"""
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Callable
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from app.config import settings
from app.utils.logger import logger


class RateLimitMiddleware(BaseHTTPMiddleware):
    """限流中间件"""
    
    def __init__(self, app):
        super().__init__(app)
        self.rate_limit_enabled = settings.RATE_LIMIT_ENABLED
        self.requests_per_minute = settings.RATE_LIMIT_PER_MINUTE
        self.requests_per_hour = settings.RATE_LIMIT_PER_HOUR
        
        # 简单的内存存储（生产环境建议使用Redis）
        self.minute_requests: dict[str, list[datetime]] = defaultdict(list)
        self.hour_requests: dict[str, list[datetime]] = defaultdict(list)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求并应用限流"""
        if not self.rate_limit_enabled:
            return await call_next(request)
        
        # 获取客户端标识（优先使用API Key，否则使用IP）
        client_id = request.headers.get("X-API-Key", request.client.host)
        
        # 清理过期记录
        self._cleanup_old_requests(client_id)
        
        # 检查每分钟限流
        if len(self.minute_requests[client_id]) >= self.requests_per_minute:
            logger.warning(f"限流触发: {client_id} 超过每分钟限制 {self.requests_per_minute}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"请求过于频繁，每分钟最多 {self.requests_per_minute} 次请求"
            )
        
        # 检查每小时限流
        if len(self.hour_requests[client_id]) >= self.requests_per_hour:
            logger.warning(f"限流触发: {client_id} 超过每小时限制 {self.requests_per_hour}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"请求过于频繁，每小时最多 {self.requests_per_hour} 次请求"
            )
        
        # 记录请求时间
        now = datetime.now()
        self.minute_requests[client_id].append(now)
        self.hour_requests[client_id].append(now)
        
        # 继续处理请求
        response = await call_next(request)
        
        # 添加限流响应头
        response.headers["X-RateLimit-Limit-Minute"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Limit-Hour"] = str(self.requests_per_hour)
        response.headers["X-RateLimit-Remaining-Minute"] = str(
            max(0, self.requests_per_minute - len(self.minute_requests[client_id]))
        )
        response.headers["X-RateLimit-Remaining-Hour"] = str(
            max(0, self.requests_per_hour - len(self.hour_requests[client_id]))
        )
        
        return response
    
    def _cleanup_old_requests(self, client_id: str):
        """清理过期的请求记录"""
        now = datetime.now()
        
        # 清理1分钟前的记录
        cutoff_minute = now - timedelta(minutes=1)
        self.minute_requests[client_id] = [
            ts for ts in self.minute_requests[client_id] if ts > cutoff_minute
        ]
        
        # 清理1小时前的记录
        cutoff_hour = now - timedelta(hours=1)
        self.hour_requests[client_id] = [
            ts for ts in self.hour_requests[client_id] if ts > cutoff_hour
        ]

