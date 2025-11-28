"""
统一异常处理中间件
"""
from typing import Callable
from fastapi import Request, status, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.exceptions import BaseServiceException
from app.utils.logger import logger


class ExceptionHandlerMiddleware(BaseHTTPMiddleware):
    """统一异常处理中间件"""
    
    async def dispatch(self, request: Request, call_next: Callable):
        """处理请求并捕获异常"""
        try:
            response = await call_next(request)
            return response
        except HTTPException as e:
            # FastAPI 的 HTTPException，直接返回
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "error": {
                        "message": e.detail,
                        "type": "HTTPException",
                        "status_code": e.status_code
                    }
                }
            )
        except BaseServiceException as e:
            # 自定义异常
            logger.warning(f"业务异常: {e.detail}")
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "error": {
                        "message": e.detail,
                        "type": e.__class__.__name__,
                        "status_code": e.status_code
                    }
                }
            )
        except Exception as e:
            # 未预期的异常
            logger.error(f"未预期的异常: {str(e)}", exc_info=True)
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": {
                        "message": "服务器内部错误",
                        "type": "InternalServerError",
                        "status_code": 500
                    }
                }
            )


