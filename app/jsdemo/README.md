# CodeceptJS 自定义 LLM 集成示例

这个目录包含了如何在 CodeceptJS 中使用自定义 LLM API 的示例代码。

## 功能特性

- ✅ 封装了自定义 LLM API 调用（LLMHelper）
- ✅ **CodeceptJS 内置 AI 功能支持**（pause 模式、页面对象生成、自愈测试）
- ✅ 支持生成测试数据
- ✅ 支持生成测试步骤
- ✅ 支持智能选择器建议
- ✅ 完全兼容 OpenAI API 格式
- ✅ 支持两种认证方式：`X-API-Key` 和 `Authorization: Bearer`

## 安装

1. 安装依赖：

```bash
npm install
```

或者手动安装：

```bash
npm install --save-dev codeceptjs playwright
npm install axios
```

## 配置

### 1. LLM Helper 配置（自定义 Helper）

编辑 `codecept.conf.js`，配置 LLM Helper：

```javascript
helpers: {
  Playwright: {
    // ... Playwright 配置
  },
  LLMHelper: {
    require: './helpers/llm_helper.js',
    baseUrl: 'http://127.0.0.1:8000',  // 你的 LLM API 地址
    apiKey: 'your-api-key-here',        // 你的 API Key
    model: 'deepseek-chat',             // 默认模型
    timeout: 60000                      // 超时时间（毫秒）
  }
}
```

### 2. CodeceptJS AI 功能配置（内置 AI）

CodeceptJS 提供了内置的 AI 功能，已在 `codecept.conf.js` 中配置：

```javascript
ai: {
  provider: 'openai',
  baseURL: 'http://127.0.0.1:8000/api/v1',
  apiKey: 'your-api-key-here'
}
```

**注意**：CodeceptJS AI 功能使用 OpenAI SDK，会自动使用 `Authorization: Bearer` 头部。我们的 API 已支持这种认证方式。

详细使用说明请查看 [AI_USAGE.md](./AI_USAGE.md)。

### 3. 获取 API Key：

如果你还没有 API Key，可以使用项目提供的脚本生成：

```bash
cd ..
python generate_api_key.py
```

## 使用方法

### 1. 生成测试数据

```javascript
const testData = await llmHelper.generateTestData(
  '生成一个用户注册信息，包含：用户名、邮箱、密码'
);
console.log(testData);
// 输出: { username: "...", email: "...", password: "..." }
```

### 2. 生成测试步骤

```javascript
const testSteps = await llmHelper.generateTestSteps(
  '测试用户登录功能：打开登录页面，输入用户名和密码，点击登录按钮'
);
console.log(testSteps);
// 输出: 生成的 CodeceptJS 测试代码
```

### 3. 直接调用 LLM

```javascript
const response = await llmHelper.generateText('你好，请介绍一下你自己');
console.log(response);
```

### 4. 使用消息数组

```javascript
const response = await llmHelper.generateText([
  { role: 'system', content: '你是一个测试助手' },
  { role: 'user', content: '请生成一个测试用例' }
]);
```

### 5. 建议选择器

```javascript
const selector = await llmHelper.suggestSelector('登录按钮');
console.log(selector);
// 输出: button[type="submit"] 或 #login-button 等
```

## 运行测试

```bash
# 运行所有测试
npm test

# 运行测试并显示步骤
npm run test:headed

# 调试模式
npm run test:debug

# 详细输出
npm run test:verbose
```

## 示例测试

查看 `tests/llm_integration_test.js` 了解完整的使用示例。

## API 参考

### LLMHelper 方法

#### `generateText(messages, options)`

生成文本内容。

**参数：**
- `messages` (string|Array): 消息内容或消息数组
- `options` (Object): 可选参数
  - `model` (string): 模型名称
  - `temperature` (number): 温度参数（0-2）
  - `maxTokens` (number): 最大 token 数

**返回：** Promise<string>

#### `generateTestData(description, options)`

生成测试数据（JSON 格式）。

**参数：**
- `description` (string): 数据描述
- `options` (Object): 可选参数

**返回：** Promise<Object>

#### `generateTestSteps(scenario, options)`

生成测试步骤代码。

**参数：**
- `scenario` (string): 测试场景描述
- `options` (Object): 可选参数

**返回：** Promise<string>

#### `suggestSelector(description, options)`

建议页面元素选择器。

**参数：**
- `description` (string): 元素描述
- `options` (Object): 可选参数

**返回：** Promise<string>

## 注意事项

1. **API Key 安全**：不要将 API Key 提交到版本控制系统。建议使用环境变量：

```javascript
LLMHelper: {
  require: './helpers/llm_helper.js',
  apiKey: process.env.LLM_API_KEY,
  // ...
}
```

2. **网络连接**：确保测试环境可以访问 LLM API 服务。

3. **错误处理**：LLM API 调用可能会失败，建议在测试中添加适当的错误处理。

4. **成本控制**：注意 LLM API 调用的成本，避免在测试中过度使用。

## 故障排除

### API Key 错误

如果遇到 "API Key is required" 错误，请检查 `codecept.conf.js` 中的配置。

### 连接超时

如果遇到连接超时，请检查：
1. LLM API 服务是否正在运行
2. `baseUrl` 配置是否正确
3. 网络连接是否正常

### 响应解析错误

如果遇到 JSON 解析错误，可能是 LLM 返回的格式不符合预期。可以：
1. 调整 prompt 使其更明确
2. 增加错误处理逻辑
3. 使用 `generateText` 方法手动处理响应

## 更多信息

- [CodeceptJS 文档](https://codecept.io/)
- [Playwright 文档](https://playwright.dev/)
- 项目主 README: `../../README.md`

