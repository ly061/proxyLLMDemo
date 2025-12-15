# LangGraph Agent 使用指南

本指南介绍如何使用我们开发的 API 服务来创建和运行 LangGraph Agent。

## 概述

LangGraph 是一个用于构建状态化、多智能体应用的框架。我们创建了一个自定义的 ChatModel 实现，允许 LangGraph 使用我们的 API 服务作为 LLM 提供者。

## 安装依赖

首先，确保安装了所有必要的依赖：

```bash
pip install -r requirements.txt
```

主要依赖包括：
- `langgraph>=0.2.0` - LangGraph 核心库
- `langchain-core>=0.3.0` - LangChain 核心库
- `langchain>=0.3.0` - LangChain 完整库
- `httpx>=0.25.1` - HTTP 客户端（已包含）

## 快速开始

### 1. 基本使用

```python
from langchain_core.messages import HumanMessage
from app.agents.langgraph_agent import create_agent

# 创建 agent
agent = create_agent(
    api_key="your-api-key-here",
    base_url="http://127.0.0.1:8000",
    model="deepseek-chat",
    temperature=0.7,
)

# 运行 agent
result = agent.invoke({
    "messages": [
        HumanMessage(content="你好，请介绍一下你自己")
    ]
})

print(result['messages'][-1].content)
```

### 2. 使用自定义工具

```python
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from app.agents.langgraph_agent import create_agent

# 定义自定义工具
@tool
def get_weather(city: str) -> str:
    """获取指定城市的天气信息"""
    # 实现你的天气查询逻辑
    return f"{city} 的天气是晴天，温度 20-25°C"

# 创建带工具的 agent
agent = create_agent(
    api_key="your-api-key-here",
    base_url="http://127.0.0.1:8000",
    model="deepseek-chat",
    tools=[get_weather],
    system_prompt="你是一个天气助手，可以帮助用户查询天气。",
)

# 运行 agent
result = agent.invoke({
    "messages": [
        HumanMessage(content="北京的天气怎么样？")
    ]
})

print(result['messages'][-1].content)
```

### 3. 运行示例

我们提供了一个完整的示例文件：

```bash
# 设置环境变量
export API_KEY="your-api-key-here"
export API_BASE_URL="http://127.0.0.1:8000"
export MODEL="deepseek-chat"

# 运行示例
python examples/langgraph_agent_example.py
```

## 架构说明

### CustomChatModel

`CustomChatModel` 类位于 `app/agents/custom_chat_model.py`，它实现了 LangChain 的 `BaseChatModel` 接口。主要功能：

1. **消息转换**: 将 LangChain 的消息格式转换为我们的 API 格式
2. **API 调用**: 通过 HTTP 请求调用我们的 API 服务
3. **响应处理**: 将 API 响应转换回 LangChain 格式

### LangGraph Agent

`langgraph_agent.py` 提供了便捷的函数来创建 LangGraph ReAct Agent：

- `create_agent()`: 创建配置好的 agent
- `run_agent_example()`: 运行示例代码

## 配置参数

### CustomChatModel 参数

- `api_key` (必需): API Key 用于认证
- `base_url` (可选): API 基础 URL，默认 `http://127.0.0.1:8000`
- `model` (可选): 模型名称，默认 `deepseek-chat`
- `temperature` (可选): 温度参数，默认 `0.7`
- `max_tokens` (可选): 最大 token 数
- `timeout` (可选): 请求超时时间（秒），默认 `60.0`

### create_agent 参数

- `api_key` (必需): API Key
- `base_url` (可选): API 基础 URL
- `model` (可选): 模型名称
- `temperature` (可选): 温度参数
- `tools` (可选): 工具列表，如果为 None 则使用默认工具
- `system_prompt` (可选): 系统提示词

## 工具开发

### 定义工具

使用 `@tool` 装饰器定义工具：

```python
from langchain_core.tools import tool

@tool
def my_tool(param1: str, param2: int) -> str:
    """工具描述
    
    Args:
        param1: 参数1的描述
        param2: 参数2的描述
        
    Returns:
        返回值的描述
    """
    # 实现工具逻辑
    return "结果"
```

### 工具要求

1. **类型注解**: 所有参数和返回值必须有类型注解
2. **文档字符串**: 必须提供详细的文档字符串，包括参数和返回值说明
3. **返回值**: 工具必须返回字符串类型

## 高级用法

### 流式输出

LangGraph Agent 支持流式输出：

```python
# 流式调用
for chunk in agent.stream({
    "messages": [HumanMessage(content="你好")]
}):
    print(chunk)
```

### 自定义状态管理

如果需要更复杂的状态管理，可以直接使用 LangGraph 的底层 API：

```python
from langgraph.graph import StateGraph
from app.agents.custom_chat_model import CustomChatModel

# 创建自定义图
# ... 实现你的自定义逻辑
```

### 错误处理

```python
try:
    result = agent.invoke({
        "messages": [HumanMessage(content="你的查询")]
    })
except Exception as e:
    print(f"错误: {e}")
    # 处理错误
```

## 常见问题

### 1. API Key 认证失败

确保：
- API Key 正确
- API 服务正在运行
- `base_url` 配置正确

### 2. 工具调用失败

检查：
- 工具函数是否有正确的类型注解
- 工具函数是否有文档字符串
- 工具函数的返回值是否为字符串

### 3. 超时错误

如果遇到超时，可以增加 `timeout` 参数：

```python
llm = CustomChatModel(
    api_key="your-key",
    timeout=120.0,  # 增加到 120 秒
)
```

## 示例代码

完整示例请参考：
- `examples/langgraph_agent_example.py` - 基本使用示例
- `app/agents/langgraph_agent.py` - Agent 实现和示例

## 参考资源

- [LangGraph 官方文档](https://langchain-ai.github.io/langgraph/)
- [LangChain 官方文档](https://python.langchain.com/)
- [我们的 API 文档](./README.md)

## 更新日志

- 2024-01-XX: 初始版本，支持基本的 LangGraph Agent 功能

