# LangGraph 中使用自定义 LLM 详细指南

本指南详细介绍如何在 LangGraph 中使用自定义的 LLM（大语言模型），特别是如何集成你自己的 API 服务。

## 目录

1. [为什么需要自定义 LLM](#为什么需要自定义-llm)
2. [实现原理](#实现原理)
3. [步骤一：创建自定义 ChatModel](#步骤一创建自定义-chatmodel)
4. [步骤二：在 LangGraph 中使用](#步骤二在-langgraph-中使用)
5. [完整示例](#完整示例)
6. [高级用法](#高级用法)
7. [常见问题](#常见问题)
8. [最佳实践](#最佳实践)

---

## 为什么需要自定义 LLM

在某些场景下，你可能需要：

1. **使用自己的 API 服务**：你开发了自己的 LLM API，想要在 LangGraph 中使用
2. **统一接口**：将不同的 LLM 提供商统一到一个接口
3. **添加自定义逻辑**：在调用 LLM 前后添加日志、缓存、监控等逻辑
4. **成本控制**：使用自己的模型服务来控制成本

---

## 实现原理

LangGraph 基于 LangChain，而 LangChain 使用 `BaseChatModel` 作为所有聊天模型的基类。要创建自定义 LLM，你需要：

1. **继承 `BaseChatModel`**：实现 LangChain 的接口
2. **实现核心方法**：`_generate()` 和 `_agenerate()`（同步和异步）
3. **消息格式转换**：将 LangChain 的消息格式转换为你的 API 格式
4. **响应格式转换**：将 API 响应转换回 LangChain 格式

```
LangGraph Agent
    ↓
LangChain BaseChatModel (接口)
    ↓
你的自定义 ChatModel (实现)
    ↓
你的 API 服务
```

---

## 步骤一：创建自定义 ChatModel

### 1. 基本结构

创建一个继承自 `BaseChatModel` 的类：

```python
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from typing import Any, List, Optional
from pydantic import Field
import httpx

class CustomChatModel(BaseChatModel):
    """自定义 ChatModel，使用我们的 API 服务"""
    
    # 定义配置字段
    api_key: str = Field(..., description="API Key for authentication")
    base_url: str = Field(default="http://127.0.0.1:8000", description="API base URL")
    model: str = Field(default="deepseek-chat", description="Model name")
    temperature: float = Field(default=0.7, description="Temperature parameter")
    max_tokens: Optional[int] = Field(default=None, description="Max tokens")
    timeout: float = Field(default=60.0, description="Request timeout")
    
    @property
    def _llm_type(self) -> str:
        """返回 LLM 类型标识"""
        return "custom_api"
```

### 2. 实现消息格式转换

将 LangChain 的消息格式转换为你的 API 格式：

```python
def _convert_message_to_dict(self, message: BaseMessage) -> dict:
    """将 LangChain 消息转换为 API 格式"""
    if isinstance(message, HumanMessage):
        return {"role": "user", "content": message.content}
    elif isinstance(message, AIMessage):
        return {"role": "assistant", "content": message.content}
    elif isinstance(message, SystemMessage):
        return {"role": "system", "content": message.content}
    else:
        # 默认处理
        return {"role": "user", "content": str(message.content)}
```

### 3. 实现同步生成方法

实现 `_generate()` 方法用于同步调用：

```python
def _generate(
    self,
    messages: List[BaseMessage],
    stop: Optional[List[str]] = None,
    run_manager: Optional[Any] = None,
    **kwargs: Any,
) -> ChatResult:
    """同步生成响应"""
    # 1. 转换消息格式
    api_messages = [self._convert_message_to_dict(msg) for msg in messages]
    
    # 2. 构建请求参数
    request_data = {
        "model": self.model,
        "messages": api_messages,
        "temperature": kwargs.get("temperature", self.temperature),
    }
    
    if self.max_tokens:
        request_data["max_tokens"] = self.max_tokens
    
    # 3. 构建请求头
    headers = {
        "X-API-Key": self.api_key,
        "Content-Type": "application/json",
    }
    
    # 4. 发送 HTTP 请求
    try:
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{self.base_url}/api/v1/chat/completions",
                json=request_data,
                headers=headers,
            )
            response.raise_for_status()
            result = response.json()
            
            # 5. 提取响应内容
            if "choices" in result and len(result["choices"]) > 0:
                choice = result["choices"][0]
                message_content = choice.get("message", {}).get("content", "")
                
                # 6. 创建 LangChain 格式的响应
                ai_message = AIMessage(content=message_content)
                generation = ChatGeneration(message=ai_message)
                return ChatResult(generations=[generation])
            else:
                raise ValueError("API 响应格式错误")
                
    except httpx.HTTPStatusError as e:
        raise Exception(f"API 请求失败: {e.response.status_code}")
```

### 4. 实现异步生成方法

实现 `_agenerate()` 方法用于异步调用：

```python
async def _agenerate(
    self,
    messages: List[BaseMessage],
    stop: Optional[List[str]] = None,
    run_manager: Optional[Any] = None,
    **kwargs: Any,
) -> ChatResult:
    """异步生成响应"""
    # 与同步方法类似，但使用异步 HTTP 客户端
    api_messages = [self._convert_message_to_dict(msg) for msg in messages]
    
    request_data = {
        "model": self.model,
        "messages": api_messages,
        "temperature": kwargs.get("temperature", self.temperature),
    }
    
    headers = {
        "X-API-Key": self.api_key,
        "Content-Type": "application/json",
    }
    
    try:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/v1/chat/completions",
                json=request_data,
                headers=headers,
            )
            response.raise_for_status()
            result = response.json()
            
            if "choices" in result and len(result["choices"]) > 0:
                choice = result["choices"][0]
                message_content = choice.get("message", {}).get("content", "")
                
                ai_message = AIMessage(content=message_content)
                generation = ChatGeneration(message=ai_message)
                return ChatResult(generations=[generation])
            else:
                raise ValueError("API 响应格式错误")
                
    except httpx.HTTPStatusError as e:
        raise Exception(f"API 请求失败: {e.response.status_code}")
```

### 5. 实现标识参数

```python
@property
def _identifying_params(self) -> dict:
    """返回用于标识此模型的参数"""
    return {
        "base_url": self.base_url,
        "model": self.model,
        "temperature": self.temperature,
    }
```

---

## 步骤二：在 LangGraph 中使用

### 1. 创建 Agent（使用预构建函数）

最简单的方式是使用 `create_react_agent`：

```python
from langgraph.prebuilt import create_react_agent
from app.agents.custom_chat_model import CustomChatModel

# 创建自定义 ChatModel
llm = CustomChatModel(
    api_key="your-api-key",
    base_url="http://127.0.0.1:8000",
    model="deepseek-chat",
    temperature=0.7,
)

# 定义工具
@tool
def get_weather(city: str) -> str:
    """获取城市天气"""
    return f"{city} 的天气是晴天"

# 创建 Agent
agent = create_react_agent(
    model=llm,
    tools=[get_weather],
)
```

### 2. 使用 Agent

```python
from langchain_core.messages import HumanMessage

# 调用 Agent
result = agent.invoke({
    "messages": [HumanMessage(content="北京的天气怎么样？")]
})

# 获取响应
print(result['messages'][-1].content)
```

### 3. 流式输出

```python
# 流式调用
for chunk in agent.stream({
    "messages": [HumanMessage(content="你好")]
}):
    print(chunk)
```

---

## 完整示例

### 示例 1：基本使用

```python
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent
from app.agents.custom_chat_model import CustomChatModel

# 创建自定义 LLM
llm = CustomChatModel(
    api_key="your-api-key",
    base_url="http://127.0.0.1:8000",
    model="deepseek-chat",
)

# 创建 Agent
agent = create_react_agent(model=llm, tools=[])

# 使用
result = agent.invoke({
    "messages": [HumanMessage(content="你好")]
})

print(result['messages'][-1].content)
```

### 示例 2：带工具的 Agent

```python
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent
from app.agents.custom_chat_model import CustomChatModel

# 定义工具
@tool
def calculate(expression: str) -> str:
    """计算数学表达式"""
    try:
        result = eval(expression)
        return f"计算结果: {result}"
    except Exception as e:
        return f"计算错误: {str(e)}"

# 创建 LLM
llm = CustomChatModel(
    api_key="your-api-key",
    base_url="http://127.0.0.1:8000",
    model="deepseek-chat",
)

# 创建带工具的 Agent
agent = create_react_agent(
    model=llm,
    tools=[calculate],
)

# 使用
result = agent.invoke({
    "messages": [HumanMessage(content="帮我计算 123 * 456")]
})

print(result['messages'][-1].content)
```

### 示例 3：自定义状态管理

如果需要更复杂的控制，可以直接使用 LangGraph 的底层 API：

```python
from typing import Annotated, Sequence, TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from app.agents.custom_chat_model import CustomChatModel

# 定义状态
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

# 创建 LLM
llm = CustomChatModel(
    api_key="your-api-key",
    base_url="http://127.0.0.1:8000",
    model="deepseek-chat",
)

# 绑定工具
llm_with_tools = llm.bind_tools([calculate])

# 定义 Agent 节点
def agent_node(state: AgentState):
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}

# 创建图
workflow = StateGraph(AgentState)
workflow.add_node("agent", agent_node)
workflow.add_node("tools", ToolNode([calculate]))

workflow.set_entry_point("agent")
workflow.add_conditional_edges(
    "agent",
    tools_condition,
    {
        "continue": "tools",
        "end": END,
    }
)
workflow.add_edge("tools", "agent")

# 编译图
graph = workflow.compile()

# 使用
result = graph.invoke({
    "messages": [HumanMessage(content="计算 100 + 200")]
})
```

---

## 高级用法

### 1. 添加重试机制

```python
from tenacity import retry, stop_after_attempt, wait_exponential

class CustomChatModel(BaseChatModel):
    # ... 其他代码 ...
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def _generate(self, messages, **kwargs):
        # 实现重试逻辑
        pass
```

### 2. 添加缓存

```python
from functools import lru_cache
import hashlib
import json

class CustomChatModel(BaseChatModel):
    # ... 其他代码 ...
    
    def _generate(self, messages, **kwargs):
        # 生成缓存键
        cache_key = self._generate_cache_key(messages, kwargs)
        
        # 检查缓存
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        # 调用 API
        result = self._call_api(messages, **kwargs)
        
        # 保存到缓存
        cache.set(cache_key, result)
        return result
    
    def _generate_cache_key(self, messages, kwargs):
        data = {
            "messages": [self._convert_message_to_dict(m) for m in messages],
            **kwargs
        }
        return hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()
```

### 3. 添加日志和监控

```python
import time
from app.utils.logger import logger

class CustomChatModel(BaseChatModel):
    # ... 其他代码 ...
    
    def _generate(self, messages, **kwargs):
        start_time = time.time()
        
        try:
            logger.info(f"调用 LLM API: model={self.model}, messages_count={len(messages)}")
            result = self._call_api(messages, **kwargs)
            
            elapsed_time = time.time() - start_time
            logger.info(f"LLM API 调用成功: elapsed={elapsed_time:.2f}s")
            
            return result
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(f"LLM API 调用失败: elapsed={elapsed_time:.2f}s, error={str(e)}")
            raise
```

### 4. 支持流式输出

如果需要支持流式输出，需要实现 `_stream()` 和 `_astream()` 方法：

```python
from typing import Iterator, AsyncIterator
from langchain_core.outputs import ChatGenerationChunk

def _stream(
    self,
    messages: List[BaseMessage],
    stop: Optional[List[str]] = None,
    run_manager: Optional[Any] = None,
    **kwargs: Any,
) -> Iterator[ChatGenerationChunk]:
    """流式生成响应"""
    # 实现流式逻辑
    # 注意：需要你的 API 支持流式响应
    pass

async def _astream(
    self,
    messages: List[BaseMessage],
    stop: Optional[List[str]] = None,
    run_manager: Optional[Any] = None,
    **kwargs: Any,
) -> AsyncIterator[ChatGenerationChunk]:
    """异步流式生成响应"""
    # 实现异步流式逻辑
    pass
```

---

## 常见问题

### Q1: 如何处理不同的消息格式？

如果你的 API 使用不同的消息格式，可以在 `_convert_message_to_dict()` 方法中自定义转换逻辑：

```python
def _convert_message_to_dict(self, message: BaseMessage) -> dict:
    """自定义消息格式转换"""
    # 根据你的 API 格式进行调整
    if isinstance(message, HumanMessage):
        return {
            "type": "user",
            "text": message.content,
            # 添加其他字段
        }
    # ... 其他类型
```

### Q2: 如何处理工具调用？

如果你的 API 支持工具调用，需要在响应处理中提取工具调用信息：

```python
# 在 _generate 方法中
if "tool_calls" in choice:
    tool_calls = choice["tool_calls"]
    ai_message = AIMessage(
        content=message_content,
        tool_calls=tool_calls  # 添加工具调用
    )
```

### Q3: 如何处理错误和重试？

```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TimeoutException))
)
def _generate(self, messages, **kwargs):
    # 实现带重试的逻辑
    pass
```

### Q4: 如何支持多个模型？

可以在创建 ChatModel 时指定不同的模型：

```python
# 模型 1
llm1 = CustomChatModel(
    api_key="key1",
    model="model-1",
)

# 模型 2
llm2 = CustomChatModel(
    api_key="key2",
    model="model-2",
)
```

---

## 最佳实践

### 1. 错误处理

- 始终捕获并处理 HTTP 错误
- 提供有意义的错误消息
- 记录错误日志以便调试

### 2. 性能优化

- 使用连接池（httpx.AsyncClient）
- 实现请求缓存
- 使用异步方法提高并发性能

### 3. 安全性

- 不要在代码中硬编码 API Key
- 使用环境变量或配置文件
- 验证 API Key 的有效性

### 4. 可维护性

- 将配置参数化
- 添加详细的文档字符串
- 使用类型注解提高代码可读性

### 5. 测试

- 编写单元测试
- 使用 Mock 对象测试 API 调用
- 测试错误处理逻辑

---

## 总结

在 LangGraph 中使用自定义 LLM 的关键步骤：

1. ✅ **继承 `BaseChatModel`**：实现 LangChain 的接口
2. ✅ **实现核心方法**：`_generate()` 和 `_agenerate()`
3. ✅ **消息格式转换**：在 LangChain 格式和你的 API 格式之间转换
4. ✅ **创建 Agent**：使用 `create_react_agent` 或自定义图
5. ✅ **使用 Agent**：调用 `invoke()` 或 `stream()` 方法

通过这种方式，你可以轻松地将任何 LLM API 集成到 LangGraph 中，享受 LangGraph 提供的强大功能，如工具调用、状态管理、流式输出等。

---

## 参考资源

- [LangGraph 官方文档](https://langchain-ai.github.io/langgraph/)
- [LangChain BaseChatModel 文档](https://python.langchain.com/docs/modules/model_io/chat/custom_chat_model)
- [完整示例代码](../app/agents/custom_chat_model.py)
- [使用示例](../examples/langgraph_agent_example.py)

