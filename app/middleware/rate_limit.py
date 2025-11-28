"""
限流中间件 - 支持Redis和内存两种模式
"""
import asyncio
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Callable, Optional, Any
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from app.config import settings
from app.utils.logger import logger
from app.exceptions import RateLimitException

# Redis客户端（可选）
_redis_client: Optional[Any] = None


async def get_redis_client():
    """获取Redis客户端"""
    global _redis_client
    if _redis_client is None and settings.REDIS_URL:
        try:
            import redis.asyncio as redis
            _redis_client = await redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            logger.info("Redis连接成功，使用Redis限流")
        except Exception as e:
            logger.warning(f"Redis连接失败，使用内存限流: {str(e)}")
            _redis_client = None
    return _redis_client


# 全局清理任务引用（用于启动和停止）
_cleanup_task: Optional[asyncio.Task] = None
_middleware_instance: Optional['RateLimitMiddleware'] = None


class RateLimitMiddleware(BaseHTTPMiddleware):
    """限流中间件"""
    
    def __init__(self, app):
        super().__init__(app)
        self.rate_limit_enabled = settings.RATE_LIMIT_ENABLED
        self.requests_per_minute = settings.RATE_LIMIT_PER_MINUTE
        self.requests_per_hour = settings.RATE_LIMIT_PER_HOUR
        
        # 内存存储（当Redis不可用时使用）
        self.minute_requests: dict[str, list[datetime]] = defaultdict(list)
        self.hour_requests: dict[str, list[datetime]] = defaultdict(list)
        
        # 保存实例引用以便在启动时启动清理任务
        global _middleware_instance
        _middleware_instance = self
    
    async def _cleanup_task(self):
        """后台清理过期数据任务"""
        while True:
            try:
                await asyncio.sleep(60)  # 每分钟清理一次
                await self._cleanup_old_requests_all()
            except asyncio.CancelledError:
                logger.info("限流清理任务已取消")
                break
            except Exception as e:
                logger.error(f"清理限流数据失败: {str(e)}")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求并应用限流"""
        # 确保清理任务已启动（延迟启动）
        global _cleanup_task, _middleware_instance
        if _middleware_instance == self and _cleanup_task is None and self.rate_limit_enabled:
            try:
                loop = asyncio.get_event_loop()
                _cleanup_task = loop.create_task(self._cleanup_task())
                logger.info("限流清理任务已启动（延迟启动）")
            except Exception as e:
                logger.warning(f"延迟启动清理任务失败: {str(e)}")
        
        if not self.rate_limit_enabled:
            return await call_next(request)
        
        # 获取客户端标识（优先使用API Key，否则使用IP）
        client_id = request.headers.get("X-API-Key", request.client.host)
        
        # 检查限流
        redis_client = await get_redis_client()
        if redis_client:
            # 使用Redis限流
            if not await self._check_rate_limit_redis(redis_client, client_id):
                raise RateLimitException(
                    f"请求过于频繁，每分钟最多 {self.requests_per_minute} 次请求"
                )
        else:
            # 使用内存限流
            if not await self._check_rate_limit_memory(client_id):
                raise RateLimitException(
                    f"请求过于频繁，每分钟最多 {self.requests_per_minute} 次请求"
                )
        
        # 继续处理请求
        response = await call_next(request)
        
        # 添加限流响应头
        remaining_minute = max(0, self.requests_per_minute - len(self.minute_requests.get(client_id, [])))
        remaining_hour = max(0, self.requests_per_hour - len(self.hour_requests.get(client_id, [])))
        
        response.headers["X-RateLimit-Limit-Minute"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Limit-Hour"] = str(self.requests_per_hour)
        response.headers["X-RateLimit-Remaining-Minute"] = str(remaining_minute)
        response.headers["X-RateLimit-Remaining-Hour"] = str(remaining_hour)
        
        return response
    
    async def _check_rate_limit_redis(self, redis_client, client_id: str) -> bool:
        """使用Redis检查限流"""
        try:
            now = datetime.now()
            minute_key = f"rate_limit:minute:{client_id}"
            hour_key = f"rate_limit:hour:{client_id}"
            
            # 使用滑动窗口
            pipe = redis_client.pipeline()
            pipe.zremrangebyscore(minute_key, 0, (now - timedelta(minutes=1)).timestamp())
            pipe.zremrangebyscore(hour_key, 0, (now - timedelta(hours=1)).timestamp())
            pipe.zcard(minute_key)
            pipe.zcard(hour_key)
            pipe.zadd(minute_key, {str(now.timestamp()): now.timestamp()})
            pipe.zadd(hour_key, {str(now.timestamp()): now.timestamp()})
            pipe.expire(minute_key, 60)
            pipe.expire(hour_key, 3600)
            
            results = await pipe.execute()
            minute_count = results[2]
            hour_count = results[3]
            
            if minute_count >= self.requests_per_minute or hour_count >= self.requests_per_hour:
                return False
            
            return True
        except Exception as e:
            logger.error(f"Redis限流检查失败: {str(e)}")
            # Redis失败时回退到内存限流
            return await self._check_rate_limit_memory(client_id)
    
    async def _check_rate_limit_memory(self, client_id: str) -> bool:
        """使用内存检查限流"""
        # 清理过期记录
        self._cleanup_old_requests(client_id)
        
        # 检查每分钟限流
        if len(self.minute_requests[client_id]) >= self.requests_per_minute:
            logger.warning(f"限流触发: {client_id} 超过每分钟限制 {self.requests_per_minute}")
            return False
        
        # 检查每小时限流
        if len(self.hour_requests[client_id]) >= self.requests_per_hour:
            logger.warning(f"限流触发: {client_id} 超过每小时限制 {self.requests_per_hour}")
            return False
        
        # 记录请求时间
        now = datetime.now()
        self.minute_requests[client_id].append(now)
        self.hour_requests[client_id].append(now)
        
        return True
    
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
    
    async def _cleanup_old_requests_all(self):
        """清理所有客户端的过期记录"""
        now = datetime.now()
        cutoff_minute = now - timedelta(minutes=1)
        cutoff_hour = now - timedelta(hours=1)
        
        # 清理分钟级记录
        for client_id in list(self.minute_requests.keys()):
            self.minute_requests[client_id] = [
                ts for ts in self.minute_requests[client_id] if ts > cutoff_minute
            ]
            if not self.minute_requests[client_id]:
                del self.minute_requests[client_id]
        
        # 清理小时级记录
        for client_id in list(self.hour_requests.keys()):
            self.hour_requests[client_id] = [
                ts for ts in self.hour_requests[client_id] if ts > cutoff_hour
            ]
            if not self.hour_requests[client_id]:
                del self.hour_requests[client_id]


async def start_rate_limit_cleanup_task():
    """启动限流清理任务（在应用启动时调用）"""
    global _cleanup_task, _middleware_instance
    
    # 如果中间件实例还没有设置，尝试从应用状态获取
    if _middleware_instance is None:
        try:
            from app.main import app
            # 查找 RateLimitMiddleware 实例
            for middleware in app.user_middleware:
                if middleware.cls == RateLimitMiddleware:
                    # 中间件实例会在第一次请求时创建，这里先跳过
                    logger.warning("限流中间件实例尚未创建，清理任务将在第一次请求后启动")
                    return
        except Exception:
            pass
    
    if _middleware_instance and _middleware_instance.rate_limit_enabled:
        try:
            loop = asyncio.get_event_loop()
            _cleanup_task = loop.create_task(_middleware_instance._cleanup_task())
            logger.info("限流清理任务已启动")
        except Exception as e:
            logger.error(f"启动限流清理任务失败: {str(e)}")
    else:
        logger.warning("限流中间件未启用或实例不存在，跳过清理任务启动")


async def stop_rate_limit_cleanup_task():
    """停止限流清理任务（在应用关闭时调用）"""
    global _cleanup_task
    if _cleanup_task and not _cleanup_task.done():
        _cleanup_task.cancel()
        try:
            await _cleanup_task
        except asyncio.CancelledError:
            pass
        logger.info("限流清理任务已停止")
