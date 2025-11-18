"""
FastAPI应用主入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.logging import LoggingMiddleware
from app.routers import chat, models
from app.utils.logger import logger


# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="LLM代理服务 - 统一的大模型访问接口",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加自定义中间件
app.add_middleware(LoggingMiddleware)
if settings.RATE_LIMIT_ENABLED:
    app.add_middleware(RateLimitMiddleware)


# 注册路由
app.include_router(chat.router)
app.include_router(models.router)


@app.get("/")
async def root():
    """根路径"""
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": settings.APP_NAME
    }


@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    logger.info(f"{settings.APP_NAME} v{settings.APP_VERSION} 启动成功")
    logger.info(f"服务器运行在 http://{settings.HOST}:{settings.PORT}")
    
    # 检查配置
    if not settings.DEEPSEEK_API_KEY:
        logger.warning("警告: DeepSeek API Key未配置")
    if not settings.API_KEYS:
        logger.warning("警告: 未配置API_KEYS列表，所有请求将被允许")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    logger.info(f"{settings.APP_NAME} 正在关闭...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )

