"""
FastAPI应用主入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.middleware.rate_limit import RateLimitMiddleware, start_rate_limit_cleanup_task, stop_rate_limit_cleanup_task
from app.middleware.logging import LoggingMiddleware
from app.middleware.exception_handler import ExceptionHandlerMiddleware
from app.routers import chat, models, admin, plan, conversations
from app.utils.logger import logger
from app.database.db import init_db, close_pool


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

# 添加自定义中间件（顺序很重要，异常处理应该在最外层）
# 注意：RateLimitMiddleware 必须在最后添加，以便在启动事件中可以访问实例
if settings.RATE_LIMIT_ENABLED:
    app.add_middleware(RateLimitMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(ExceptionHandlerMiddleware)


# 注册路由
app.include_router(chat.router)
app.include_router(models.router)
app.include_router(admin.router)
app.include_router(plan.router)
app.include_router(conversations.router)


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
    
    # 初始化数据库
    if settings.USE_DATABASE_AUTH:
        # 验证 MySQL 配置
        if not settings.MYSQL_USER or not settings.MYSQL_PASSWORD:
            logger.error(
                "错误: MySQL用户名和密码未配置。"
                "请设置 MYSQL_USER 和 MYSQL_PASSWORD 环境变量。"
            )
            raise ValueError("MySQL配置不完整，请检查环境变量")
        
        await init_db()
        logger.info("数据库认证已启用")
    else:
        logger.warning("警告: 使用环境变量认证（已废弃），建议启用数据库认证")
    
    # 启动限流清理任务
    if settings.RATE_LIMIT_ENABLED:
        await start_rate_limit_cleanup_task()
    
    # 检查配置
    if not settings.DEEPSEEK_API_KEY:
        logger.warning("警告: DeepSeek API Key未配置")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    logger.info(f"{settings.APP_NAME} 正在关闭...")
    
    # 停止限流清理任务
    if settings.RATE_LIMIT_ENABLED:
        await stop_rate_limit_cleanup_task()
    
    # 关闭数据库连接池
    await close_pool()
    logger.info("数据库连接池已关闭")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )

