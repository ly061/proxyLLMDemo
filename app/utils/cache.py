"""
缓存工具模块
"""
import hashlib
import json
from typing import Optional, Any
from functools import wraps
from app.config import settings


class SimpleCache:
    """简单的内存缓存实现"""
    
    def __init__(self):
        self._cache: dict[str, tuple[Any, float]] = {}
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        if not settings.CACHE_ENABLED:
            return None
        
        if key in self._cache:
            value, timestamp = self._cache[key]
            import time
            if time.time() - timestamp < settings.CACHE_TTL:
                return value
            else:
                del self._cache[key]
        return None
    
    def set(self, key: str, value: Any):
        """设置缓存"""
        if not settings.CACHE_ENABLED:
            return
        
        import time
        self._cache[key] = (value, time.time())
    
    def clear(self):
        """清空缓存"""
        self._cache.clear()


# 全局缓存实例
cache = SimpleCache()


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


