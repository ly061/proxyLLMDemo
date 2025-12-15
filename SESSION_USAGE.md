# 会话上下文管理使用指南

## 📖 概述

现在服务支持会话上下文管理功能！你可以创建会话，并在会话中建立上下文记忆。

## 🚀 快速开始

### 1. 创建新会话

```bash
POST /api/v1/conversations
Authorization: Bearer YOUR_API_KEY
Content-Type: application/json

{
  "title": "我的第一个对话"  // 可选，不提供则默认为"新对话"
}
```

**响应：**
```json
{
  "conversation_id": 123,
  "title": "我的第一个对话",
  "created_at": "2024-01-01T00:00:00",
  "updated_at": null
}
```

### 2. 使用会话进行对话（自动上下文）

```bash
POST /api/v1/chat/completions
Authorization: Bearer YOUR_API_KEY
Content-Type: application/json

{
  "conversation_id": 123,  // 使用刚才创建的会话ID
  "model": "deepseek-chat",
  "messages": [
    {
      "role": "user",
      "content": "你好，我叫张三"
    }
  ]
}
```

**响应：**
```json
{
  "id": "...",
  "model": "deepseek-chat",
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": "你好张三！很高兴认识你。"
      }
    }
  ]
}
```

### 3. 继续对话（自动包含历史上下文）

```bash
POST /api/v1/chat/completions
Authorization: Bearer YOUR_API_KEY
Content-Type: application/json

{
  "conversation_id": 123,  // 同一个会话ID
  "messages": [
    {
      "role": "user",
      "content": "你还记得我的名字吗？"
    }
  ]
}
```

**响应：**
```json
{
  "choices": [
    {
      "message": {
        "content": "当然记得！你叫张三。"
      }
    }
  ]
}
```

✅ **服务会自动加载会话123的所有历史消息，AI会记住之前的对话！**

### 4. 新开一个对话

只需要创建新的会话ID即可：

```bash
POST /api/v1/conversations
# 返回新的 conversation_id: 456

POST /api/v1/chat/completions
{
  "conversation_id": 456,  // 新的会话ID，上下文从新开始
  "messages": [{"role": "user", "content": "新话题"}]
}
```

## 📋 API 接口列表

### 会话管理接口

#### 1. 创建会话
- **POST** `/api/v1/conversations`
- 请求体：`{"title": "可选标题"}`
- 返回：会话信息（包含 `conversation_id`）

#### 2. 获取会话列表
- **GET** `/api/v1/conversations?limit=20&offset=0`
- 返回：会话列表和总数

#### 3. 获取会话详情
- **GET** `/api/v1/conversations/{conversation_id}`
- 返回：会话信息和所有消息历史

#### 4. 更新会话标题
- **PATCH** `/api/v1/conversations/{conversation_id}`
- 请求体：`{"title": "新标题"}`

#### 5. 删除会话
- **DELETE** `/api/v1/conversations/{conversation_id}`
- 返回：删除确认

### 聊天接口（增强）

#### POST `/api/v1/chat/completions`

**新增可选参数：**
- `conversation_id` (可选): 会话ID

**使用方式：**
- **带会话ID**：自动加载历史，建立上下文
- **不带会话ID**：独立请求，不保存历史（向后兼容）

## 💡 使用场景示例

### 场景1：多轮对话

```python
import requests

api_key = "YOUR_API_KEY"
headers = {"Authorization": f"Bearer {api_key}"}

# 1. 创建会话
response = requests.post(
    "http://localhost:8000/api/v1/conversations",
    headers=headers,
    json={"title": "Python学习"}
)
conv_id = response.json()["conversation_id"]

# 2. 第一轮对话
response = requests.post(
    "http://localhost:8000/api/v1/chat/completions",
    headers=headers,
    json={
        "conversation_id": conv_id,
        "messages": [{"role": "user", "content": "什么是Python？"}]
    }
)
print(response.json()["choices"][0]["message"]["content"])

# 3. 第二轮对话（AI记得之前的对话）
response = requests.post(
    "http://localhost:8000/api/v1/chat/completions",
    headers=headers,
    json={
        "conversation_id": conv_id,
        "messages": [{"role": "user", "content": "它有什么优势？"}]
    }
)
print(response.json()["choices"][0]["message"]["content"])
```

### 场景2：独立请求（不使用会话）

```python
# 不提供conversation_id，保持原有行为
response = requests.post(
    "http://localhost:8000/api/v1/chat/completions",
    headers=headers,
    json={
        "messages": [{"role": "user", "content": "你好"}]
    }
)
```

### 场景3：切换话题

```python
# 创建新会话，开始新话题
conv_id_2 = requests.post(
    "http://localhost:8000/api/v1/conversations",
    headers=headers
).json()["conversation_id"]

# 使用新会话ID，上下文从新开始
response = requests.post(
    "http://localhost:8000/api/v1/chat/completions",
    headers=headers,
    json={
        "conversation_id": conv_id_2,
        "messages": [{"role": "user", "content": "新话题"}]
    }
)
```

## 🔒 安全特性

1. **权限隔离**：用户只能访问自己的会话
2. **双重验证**：通过 `user_id` 和 `api_key_id` 双重验证
3. **自动清理**：删除会话时自动删除所有相关消息

## ⚠️ 注意事项

1. **缓存机制**：使用 `conversation_id` 时，缓存会被禁用（因为每次对话上下文都在变化）
2. **消息限制**：建议单个会话不要超过太多消息，避免token超限
3. **向后兼容**：不提供 `conversation_id` 时，完全保持原有行为

## 🎯 总结

- ✅ **创建会话** → 获取 `conversation_id`
- ✅ **使用会话ID聊天** → 自动建立上下文
- ✅ **新开对话** → 创建新的 `conversation_id`
- ✅ **向后兼容** → 不提供会话ID时保持原行为

现在你的服务支持完整的会话上下文管理了！🎉

