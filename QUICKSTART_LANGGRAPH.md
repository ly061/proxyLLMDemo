# LangGraph Agent 快速开始

## 简介

本项目已集成 LangGraph，可以使用我们开发的 API 服务来创建和运行 LangGraph Agent。

## 安装

```bash
# 安装依赖
pip install -r requirements.txt
```

主要新增依赖：
- `langgraph>=0.2.0`
- `langchain-core>=0.3.0`
- `langchain>=0.3.0`

## 快速示例

### 1. 最简单的使用

```python
from langchain_core.messages import HumanMessage
from app.agents.langgraph_agent import create_agent

# 创建 agent
agent = create_agent(
    api_key="your-api-key-here",
    base_url="http://127.0.0.1:8000",
    model="deepseek-chat",
)

# 运行
result = agent.invoke({
    "messages": [HumanMessage(content="你好")]
})

print(result['messages'][-1].content)
```

### 2. 使用自定义工具

```python
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from app.agents.langgraph_agent import create_agent

@tool
def get_weather(city: str) -> str:
    """获取城市天气"""
    return f"{city} 的天气是晴天"

agent = create_agent(
    api_key="your-api-key",
    base_url="http://127.0.0.1:8000",
    tools=[get_weather],
)

result = agent.invoke({
    "messages": [HumanMessage(content="北京天气怎么样？")]
})
```

## 运行示例

### 运行完整示例

```bash
export API_KEY="your-api-key-here"
python examples/langgraph_agent_example.py
```

### 运行测试

```bash
export API_KEY="your-api-key-here"
python test_langgraph_agent.py
```

## 文件结构

```
app/agents/
├── __init__.py              # 模块初始化
├── custom_chat_model.py     # 自定义 ChatModel 实现
└── langgraph_agent.py       # Agent 创建函数和示例

examples/
└── langgraph_agent_example.py  # 完整使用示例

test_langgraph_agent.py      # 测试脚本
LANGGRAPH_AGENT_GUIDE.md     # 详细使用指南
QUICKSTART_LANGGRAPH.md      # 本文件
```

## 核心组件

### CustomChatModel

位于 `app/agents/custom_chat_model.py`，实现了 LangChain 的 `BaseChatModel` 接口：

- 将 LangChain 消息格式转换为我们的 API 格式
- 通过 HTTP 调用我们的 API 服务
- 将 API 响应转换回 LangChain 格式

### create_agent 函数

位于 `app/agents/langgraph_agent.py`，提供便捷的 Agent 创建：

```python
agent = create_agent(
    api_key="your-key",
    base_url="http://127.0.0.1:8000",
    model="deepseek-chat",
    temperature=0.7,
    tools=[...],  # 可选
    system_prompt="...",  # 可选
)
```

## 配置

### 环境变量

```bash
export API_KEY="your-api-key-here"
export API_BASE_URL="http://127.0.0.1:8000"
export MODEL="deepseek-chat"
```

### 代码配置

```python
from app.agents.custom_chat_model import CustomChatModel

llm = CustomChatModel(
    api_key="your-key",
    base_url="http://127.0.0.1:8000",
    model="deepseek-chat",
    temperature=0.7,
    max_tokens=2000,
    timeout=60.0,
)
```

## 更多信息

详细文档请参考：
- [LANGGRAPH_AGENT_GUIDE.md](./LANGGRAPH_AGENT_GUIDE.md) - 完整使用指南
- [LangGraph 官方文档](https://langchain-ai.github.io/langgraph/)

## 常见问题

**Q: 如何获取 API Key？**  
A: 使用 `generate_api_key.py` 脚本生成，或通过数据库查询。

**Q: API 服务需要运行吗？**  
A: 是的，需要先启动 API 服务（`python run.py`）。

**Q: 支持流式输出吗？**  
A: 当前版本支持非流式输出。流式输出需要额外实现。

**Q: 如何添加更多工具？**  
A: 使用 `@tool` 装饰器定义工具函数，然后传递给 `create_agent`。

