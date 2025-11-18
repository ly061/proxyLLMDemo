"""
配置管理模块
"""
from typing import List, Optional
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """应用配置"""
    
    # 应用基础配置
    APP_NAME: str = "LLM Proxy Service"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # API认证配置
    API_KEYS: List[str] = Field(default_factory=list)  # 允许的API Key列表
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24  # 24小时
    
    # DeepSeek配置
    DEEPSEEK_API_KEY: Optional[str] = None
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-chat"
    
    # OpenAI配置（可选）
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-3.5-turbo"
    
    # Claude配置（可选）
    CLAUDE_API_KEY: Optional[str] = None
    CLAUDE_BASE_URL: str = "https://api.anthropic.com/v1"
    CLAUDE_MODEL: str = "claude-3-sonnet-20240229"
    
    # 限流配置
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 60  # 每分钟请求数
    RATE_LIMIT_PER_HOUR: int = 1000  # 每小时请求数
    REDIS_URL: Optional[str] = None  # Redis连接URL（可选，用于分布式限流）
    
    # 缓存配置
    CACHE_ENABLED: bool = True
    CACHE_TTL: int = 3600  # 缓存过期时间（秒）
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FILE: Optional[str] = None
    
    # 安全配置
    ALLOWED_IPS: List[str] = Field(default_factory=list)  # IP白名单（空列表表示不限制）
    ENABLE_CONTENT_FILTER: bool = False  # 是否启用内容过滤
    
    class Config:
        env_file = ".env"
        # env_file_encoding 在 pydantic-settings v1 中可能不支持，使用默认 UTF-8 编码
        case_sensitive = True


# 全局配置实例
settings = Settings()


