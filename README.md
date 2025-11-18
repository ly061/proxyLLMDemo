# LLM代理服务

一个统一的大模型访问接口服务，支持DeepSeek、OpenAI等多个LLM提供商。

## 功能特性

- ✅ **统一接口**: 兼容OpenAI API格式，屏蔽底层LLM差异
- ✅ **多LLM支持**: 支持DeepSeek、OpenAI等主流LLM提供商
- ✅ **安全认证**: API Key认证机制，保护服务安全
- ✅ **限流控制**: 防止滥用，支持每分钟和每小时限流
- ✅ **请求缓存**: 相同请求结果缓存，降低成本和延迟
- ✅ **日志监控**: 完整的请求日志和错误追踪
- ✅ **异步高性能**: 基于FastAPI的异步架构

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并填写配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件，至少需要配置：

```env
# DeepSeek API Key（必需）
DEEPSEEK_API_KEY=your-deepseek-api-key

# API认证密钥（必需）
API_KEYS=your-api-key-1,your-api-key-2
```

**生成 API Key**：

你可以使用项目提供的工具脚本生成安全的 API Key：

```bash
# 生成单个 API Key
python generate_api_key.py

# 生成多个 API Key
python generate_api_key.py --count 3

# 直接输出为环境变量格式
python generate_api_key.py --count 2 --format env

# 生成更长的 API Key（64字符）
python generate_api_key.py --length 64
```

生成的 API Key 会自动使用加密安全的随机数生成器，确保安全性。

### 3. 启动服务

**方式一：使用启动脚本（推荐）**

```bash
# Linux/Mac
./run.sh

# 或使用Python脚本（跨平台）
python3 run.py
```

启动脚本会自动：
- 检查Python环境
- 检查并安装依赖
- 检查配置文件
- 启动服务

**方式二：手动启动**

```bash
python -m app.main
```

或者使用uvicorn：

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

服务启动后，访问 http://localhost:8000/docs 查看API文档。

## API使用示例

### 1. 聊天完成接口

```bash
curl -X POST "http://localhost:8000/api/v1/chat/completions" \
  -H "X-API-Key: your-api-key-1" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-chat",
    "messages": [
      {"role": "user", "content": "你好，请介绍一下你自己"}
    ],
    "temperature": 0.7
  }'
```

### 2. 获取模型列表

```bash
curl -X GET "http://localhost:8000/api/v1/models" \
  -H "X-API-Key: your-api-key-1"
```

### 3. Python客户端示例

```python
import httpx

async def chat_completion():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/chat/completions",
            headers={
                "X-API-Key": "your-api-key-1",
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek-chat",
                "messages": [
                    {"role": "user", "content": "你好"}
                ],
                "temperature": 0.7
            }
        )
        print(response.json())

# 运行
import asyncio
asyncio.run(chat_completion())
```

## 支持的模型

### DeepSeek
- `deepseek-chat` - 通用对话模型
- `deepseek-coder` - 代码生成模型

### OpenAI（可选）
- `gpt-4`
- `gpt-4-turbo`
- `gpt-3.5-turbo`

## 配置说明

### 必需配置

- `DEEPSEEK_API_KEY`: DeepSeek API密钥
- `API_KEYS`: 允许访问服务的API Key列表（逗号分隔）

### 可选配置

- `RATE_LIMIT_ENABLED`: 是否启用限流（默认：True）
- `RATE_LIMIT_PER_MINUTE`: 每分钟请求限制（默认：60）
- `RATE_LIMIT_PER_HOUR`: 每小时请求限制（默认：1000）
- `CACHE_ENABLED`: 是否启用缓存（默认：True）
- `CACHE_TTL`: 缓存过期时间（秒，默认：3600）

## 项目结构

```
AI Services/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI应用入口
│   ├── config.py               # 配置管理
│   ├── auth/                   # 认证模块
│   │   ├── api_key.py          # API Key验证
│   │   └── jwt_handler.py      # JWT处理（可选）
│   ├── middleware/             # 中间件
│   │   ├── rate_limit.py       # 限流中间件
│   │   └── logging.py          # 日志中间件
│   ├── adapters/               # LLM适配器
│   │   ├── base.py             # 适配器基类
│   │   ├── deepseek_adapter.py # DeepSeek适配器
│   │   └── openai_adapter.py   # OpenAI适配器
│   ├── routers/                # 路由
│   │   ├── chat.py             # 聊天路由
│   │   └── models.py           # 模型路由
│   └── utils/                  # 工具模块
│       ├── logger.py           # 日志工具
│       └── cache.py            # 缓存工具
├── requirements.txt
├── .env.example
└── README.md
```

## 安全建议

1. **生产环境配置**:
   - 修改 `JWT_SECRET_KEY` 为强随机密钥
   - 配置 `API_KEYS` 列表，不要留空
   - 使用HTTPS部署
   - 配置IP白名单（如需要）

2. **限流策略**:
   - 根据实际需求调整限流参数
   - 高并发场景建议使用Redis实现分布式限流

3. **监控告警**:
   - 配置日志文件路径
   - 监控错误率和响应时间
   - 设置API Key使用量告警

## 开发

### 添加新的LLM适配器

1. 在 `app/adapters/` 目录下创建新的适配器文件
2. 继承 `BaseLLMAdapter` 类
3. 实现 `chat_completion` 和 `list_models` 方法
4. 在 `app/routers/chat.py` 的 `get_adapter` 函数中添加路由逻辑

## 许可证

MIT License

