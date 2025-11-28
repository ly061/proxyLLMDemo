# Bug 修复记录

## Bug 1: RateLimitMiddleware 初始化时创建异步任务 ✅

### 问题描述
`RateLimitMiddleware.__init__()` 方法中调用 `asyncio.create_task()` 创建后台清理任务，但中间件初始化是在事件循环启动之前同步执行的，导致 `RuntimeError: no running event loop`。

### 修复方案
- 移除了 `__init__()` 中的 `asyncio.create_task()` 调用
- 创建了 `start_rate_limit_cleanup_task()` 和 `stop_rate_limit_cleanup_task()` 函数
- 在应用的 `startup_event` 中启动清理任务
- 在应用的 `shutdown_event` 中停止清理任务

### 修改文件
- `app/middleware/rate_limit.py` - 移除初始化时的任务创建，添加启动/停止函数
- `app/main.py` - 在启动和关闭事件中调用清理任务函数

### 验证
- ✅ 清理任务现在在事件循环启动后正确启动
- ✅ 应用关闭时正确停止清理任务
- ✅ 不再出现 `RuntimeError: no running event loop` 错误

---

## Bug 2: MySQL 密码硬编码 ✅

### 问题描述
MySQL 密码 `"12345678"` 硬编码在配置文件中，存在安全风险。敏感信息不应该硬编码在源代码中。

### 修复方案
- 将 `MYSQL_USER` 和 `MYSQL_PASSWORD` 的默认值改为 `None`
- 添加配置验证，确保这些值必须通过环境变量提供
- 在数据库连接和启动时验证配置完整性

### 修改文件
- `app/config.py` - 移除硬编码的密码，改为 `Optional[str] = None`
- `app/database/db.py` - 添加配置验证
- `app/main.py` - 在启动时验证 MySQL 配置

### 使用方式
现在必须通过环境变量配置：
```bash
export MYSQL_USER=root
export MYSQL_PASSWORD=your-secure-password
```

或在 `.env` 文件中：
```env
MYSQL_USER=root
MYSQL_PASSWORD=your-secure-password
```

### 验证
- ✅ 密码不再硬编码在源代码中
- ✅ 启动时会验证配置完整性
- ✅ 如果未配置会给出清晰的错误提示

---

## Bug 3: ID 检查使用 truthiness 而非显式 None 检查 ✅

### 问题描述
代码使用 `if user_info.get('api_key_id') and user_info.get('user_id')` 检查，如果 ID 值为 0（虽然自增 ID 通常从 1 开始，但理论上可能为 0），会被误判为 False。

### 修复方案
将检查改为显式的 `is not None` 检查：
```python
# 修复前
if user_info.get('api_key_id') and user_info.get('user_id') and response.usage:

# 修复后
if user_info.get('api_key_id') is not None and user_info.get('user_id') is not None and response.usage:
```

### 修改文件
- `app/routers/chat.py` - 修复 ID 检查逻辑
- `app/routers/plan.py` - 修复 ID 检查逻辑

### 验证
- ✅ 现在正确检查 ID 是否为 None，而不是依赖 truthiness
- ✅ 如果 ID 为 0（虽然不太可能），也能正确处理
- ✅ 代码意图更清晰明确

---

## 总结

所有三个 bug 都已修复：

1. ✅ **异步任务启动问题** - 清理任务现在在正确的事件循环中启动
2. ✅ **安全漏洞** - 敏感信息不再硬编码，必须通过环境变量提供
3. ✅ **逻辑错误** - ID 检查现在使用显式的 None 检查

这些修复提高了代码的：
- **安全性** - 敏感信息不再硬编码
- **可靠性** - 异步任务正确启动和停止
- **正确性** - ID 检查逻辑更准确

