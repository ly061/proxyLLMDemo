"""
日志中间件
"""
from typing import Callable
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from app.utils.logger import logger


class LoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """记录请求和响应信息"""
        start_time = time.time()
        
        # 记录请求信息
        client_ip = request.client.host
        method = request.method
        path = request.url.path
        query_params = str(request.query_params) if request.query_params else ""
        
        logger.info(f"请求开始: {method} {path}?{query_params} from {client_ip}")
        
        try:
            # 处理请求
            response = await call_next(request)
            
            # 计算处理时间
            process_time = time.time() - start_time
            
            # 记录响应信息
            logger.info(
                f"请求完成: {method} {path} - "
                f"状态码: {response.status_code} - "
                f"耗时: {process_time:.3f}s"
            )
            
            # 添加响应头
            response.headers["X-Process-Time"] = str(process_time)
            
            return response
        
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"请求失败: {method} {path} - "
                f"错误: {str(e)} - "
                f"耗时: {process_time:.3f}s"
            )
            raise

