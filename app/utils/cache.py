"""
缓存工具模块 - 使用LRU缓存
"""
import hashlib
import json
import time
from typing import Optional, Any
from functools import wraps
from cachetools import LRUCache, TTLCache
from app.config import settings


class LRUCacheWrapper:
    """LRU缓存包装器，支持TTL和大小限制"""
    
    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        """
        初始化缓存
        
        Args:
            max_size: 最大缓存条目数
            ttl: 缓存过期时间（秒）
        """
        # 使用TTLCache结合LRU策略
        self._cache = TTLCache(maxsize=max_size, ttl=ttl)
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        if not settings.CACHE_ENABLED:
            return None
        
        try:
            return self._cache.get(key)
        except KeyError:
            return None
    
    def set(self, key: str, value: Any):
        """设置缓存"""
        if not settings.CACHE_ENABLED:
            return
        
        try:
            self._cache[key] = value
        except Exception as e:
            # 如果缓存已满，LRU会自动淘汰最久未使用的项
            pass
    
    def clear(self):
        """清空缓存"""
        self._cache.clear()
    
    def size(self) -> int:
        """获取当前缓存大小"""
        return len(self._cache)


# 全局缓存实例
cache = LRUCacheWrapper(
    max_size=settings.CACHE_MAX_SIZE,
    ttl=settings.CACHE_TTL
)


def cache_key_generator(*args, **kwargs) -> str:
    """生成缓存键"""
    key_data = {
        "args": args,
        "kwargs": kwargs
    }
    key_str = json.dumps(key_data, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(key_str.encode()).hexdigest()


def cached(ttl: Optional[int] = None):
    """缓存装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            key = f"{func.__name__}:{cache_key_generator(*args, **kwargs)}"
            
            # 尝试从缓存获取
            cached_result = cache.get(key)
            if cached_result is not None:
                return cached_result
            
            # 执行函数
            result = await func(*args, **kwargs)
            
            # 存入缓存
            cache.set(key, result)
            
            return result
        return wrapper
    return decorator
