# 会话上下文管理设计方案

## 📋 方案概述

实现服务端会话管理，支持：
1. **创建新会话**：每次对话可以创建独立的会话
2. **自动上下文管理**：通过 `session_id` 自动加载历史消息
3. **会话列表**：用户可以查看和管理所有会话
4. **向后兼容**：不提供 `session_id` 时保持原有行为

---

## 🗄️ 数据库设计

### 1. conversations 表（会话表）
```sql
CREATE TABLE IF NOT EXISTS conversations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    api_key_id INT NOT NULL,
    title VARCHAR(255),  -- 会话标题（自动生成或手动设置）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (api_key_id) REFERENCES api_keys(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_api_key_id (api_key_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
```

### 2. conversation_messages 表（会话消息表）
```sql
CREATE TABLE IF NOT EXISTS conversation_messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    conversation_id INT NOT NULL,
    role VARCHAR(20) NOT NULL,  -- 'user', 'assistant', 'system'
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
    INDEX idx_conversation_id (conversation_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
```

---

## 🔌 API 接口设计

### 1. 创建新会话
**POST** `/api/v1/conversations`

**请求体：**
```json
{
  "title": "可选，会话标题，如果不提供则自动生成"
}
```

**响应：**
```json
{
  "conversation_id": 123,
  "title": "新对话",
  "created_at": "2024-01-01T00:00:00Z"
}
```

### 2. 获取会话列表
**GET** `/api/v1/conversations`

**查询参数：**
- `limit`: 返回数量（默认20）
- `offset`: 偏移量（默认0）

**响应：**
```json
{
  "conversations": [
    {
      "conversation_id": 123,
      "title": "对话标题",
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T01:00:00Z",
      "message_count": 10
    }
  ],
  "total": 50
}
```

### 3. 获取单个会话详情
**GET** `/api/v1/conversations/{conversation_id}`

**响应：**
```json
{
  "conversation_id": 123,
  "title": "对话标题",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T01:00:00Z",
  "messages": [
    {
      "role": "user",
      "content": "你好",
      "created_at": "2024-01-01T00:00:00Z"
    },
    {
      "role": "assistant",
      "content": "你好！有什么可以帮助你的吗？",
      "created_at": "2024-01-01T00:00:01Z"
    }
  ]
}
```

### 4. 删除会话
**DELETE** `/api/v1/conversations/{conversation_id}`

**响应：**
```json
{
  "success": true,
  "message": "会话已删除"
}
```

### 5. 更新会话标题
**PATCH** `/api/v1/conversations/{conversation_id}`

**请求体：**
```json
{
  "title": "新标题"
}
```

---

## 💬 聊天接口增强

### POST `/api/v1/chat/completions`（增强版）

**新增可选参数：**
- `conversation_id` (可选): 会话ID，如果提供则自动加载历史消息

**工作流程：**
1. 如果提供了 `conversation_id`：
   - 验证会话属于当前用户
   - 从数据库加载该会话的所有历史消息
   - 将历史消息与请求中的 `messages` 合并（请求中的消息追加到历史消息后面）
   - 调用 LLM
   - 保存用户消息和助手回复到数据库
   - 更新会话的 `updated_at` 时间

2. 如果没有提供 `conversation_id`：
   - 保持原有行为（独立请求，不保存历史）

**示例请求：**
```json
{
  "model": "deepseek-chat",
  "conversation_id": 123,  // 新增：会话ID
  "messages": [
    {
      "role": "user",
      "content": "继续刚才的话题"
    }
  ]
}
```

---

## 🔄 使用流程

### 场景1：创建新对话
```bash
# 1. 创建新会话
POST /api/v1/conversations
Response: { "conversation_id": 123 }

# 2. 发送第一条消息（带conversation_id）
POST /api/v1/chat/completions
{
  "conversation_id": 123,
  "messages": [{"role": "user", "content": "你好"}]
}

# 3. 继续对话（自动包含历史上下文）
POST /api/v1/chat/completions
{
  "conversation_id": 123,
  "messages": [{"role": "user", "content": "介绍一下Python"}]
}
```

### 场景2：独立请求（向后兼容）
```bash
# 不提供conversation_id，保持原有行为
POST /api/v1/chat/completions
{
  "messages": [{"role": "user", "content": "你好"}]
}
```

### 场景3：切换对话
```bash
# 创建新会话，开始新的对话上下文
POST /api/v1/conversations
Response: { "conversation_id": 456 }

# 使用新的conversation_id，上下文从新开始
POST /api/v1/chat/completions
{
  "conversation_id": 456,
  "messages": [{"role": "user", "content": "新话题"}]
}
```

---

## 🔒 安全考虑

1. **权限验证**：确保用户只能访问自己的会话
2. **会话归属**：通过 `api_key_id` 和 `user_id` 双重验证
3. **消息限制**：考虑限制单个会话的最大消息数量（防止token超限）

---

## 📝 实现步骤

1. ✅ 更新数据库模型和初始化脚本
2. ✅ 实现会话管理数据库操作函数
3. ✅ 创建会话管理路由
4. ✅ 修改聊天路由支持 `conversation_id`
5. ✅ 更新API文档

---

## ✨ 特性总结

- ✅ **自动上下文管理**：通过 `conversation_id` 自动加载历史
- ✅ **新开对话**：创建新的 `conversation_id` 即可
- ✅ **向后兼容**：不提供 `conversation_id` 时保持原行为
- ✅ **会话管理**：列表、查看、删除、重命名
- ✅ **安全隔离**：用户只能访问自己的会话

