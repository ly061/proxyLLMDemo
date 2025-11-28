# 更新日志

## [优化版本] - 2024-01-XX

### 重大变更

#### 1. 数据库迁移：SQLite → MySQL
- **BREAKING**: 数据库从 SQLite 迁移到 MySQL
- 需要配置 MySQL 连接信息（见 `MIGRATION_GUIDE.md`）
- 所有 SQL 语法从 SQLite 改为 MySQL（`?` → `%s`）
- 实现连接池管理，提升性能

#### 2. 代码重构：适配器工厂模式
- 创建统一的适配器工厂 `app/utils/adapter_factory.py`
- 消除 `chat.py` 和 `plan.py` 中的重复代码
- 所有路由统一使用适配器工厂

### 新增功能

#### 1. 流式响应支持
- 实现 Server-Sent Events (SSE) 流式响应
- 支持实时流式对话，改善用户体验
- 兼容 OpenAI API 格式

#### 2. Redis 限流支持
- 可选 Redis 后端限流（配置 `REDIS_URL`）
- 支持分布式限流，多实例部署
- 内存模式作为降级方案

#### 3. LRU 缓存
- 使用 `cachetools` 实现 LRU 缓存
- 添加缓存大小限制，防止内存泄漏
- 支持 TTL 过期策略

#### 4. 统一异常处理
- 创建自定义异常类体系
- 统一异常处理中间件
- 改善错误响应格式和日志记录

### 改进

#### 性能优化
- 数据库连接池减少连接开销
- LRU 缓存提升重复请求性能
- 限流后台清理任务防止内存泄漏

#### 代码质量
- 消除代码重复（约 100+ 行）
- 统一适配器创建逻辑
- 改进错误处理和日志记录

#### 可扩展性
- MySQL 支持高并发场景
- Redis 支持分布式限流
- 更好的连接管理

### 配置变更

#### 新增配置项
```env
# MySQL 配置
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=12345678
MYSQL_DATABASE=sonic
MYSQL_CHARSET=utf8mb4
MYSQL_POOL_SIZE=10
MYSQL_MAX_OVERFLOW=20

# 缓存配置
CACHE_MAX_SIZE=1000

# Redis 配置（可选）
REDIS_URL=redis://localhost:6379/0
```

### 依赖更新

#### 新增依赖
- `aiomysql==0.2.0` - MySQL 异步驱动
- `redis==5.0.1` - Redis 客户端
- `cachetools==5.3.2` - LRU 缓存实现

### 文档更新

- 新增 `OPTIMIZATION_SUMMARY.md` - 优化总结
- 新增 `MIGRATION_GUIDE.md` - 数据库迁移指南
- 新增 `CHANGELOG.md` - 更新日志

### 修复

- 修复限流中间件内存泄漏问题
- 修复缓存无限增长问题
- 修复数据库连接管理问题

### 迁移指南

如果从旧版本升级，请参考：
1. `MIGRATION_GUIDE.md` - 数据库迁移步骤
2. `OPTIMIZATION_SUMMARY.md` - 详细变更说明

### 注意事项

- ⚠️ **数据库迁移**: 需要先创建 MySQL 数据库并配置连接信息
- ⚠️ **Redis 可选**: Redis 是可选的，不配置会使用内存限流
- ⚠️ **生产环境**: 建议配置 Redis 和更强的 MySQL 密码

