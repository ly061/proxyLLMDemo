"""
日志工具模块
"""
import sys
from loguru import logger
from app.config import settings


def setup_logger():
    """配置日志"""
    logger.remove()  # 移除默认处理器
    
    # 控制台输出
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=settings.LOG_LEVEL,
        colorize=True
    )
    
    # 文件输出（如果配置了日志文件）
    if settings.LOG_FILE:
        logger.add(
            settings.LOG_FILE,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            level=settings.LOG_LEVEL,
            rotation="100 MB",
            retention="7 days",
            compression="zip"
        )
    
    return logger


# 初始化日志
setup_logger()


