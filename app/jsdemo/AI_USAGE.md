# CodeceptJS AI 功能使用指南

根据 [CodeceptJS AI 文档](https://codecept.io/ai)，CodeceptJS 提供了内置的 AI 功能，可以与我们的自定义 LLM API 集成。

## 配置说明

已在 `codecept.conf.js` 中配置了 AI 功能：

```javascript
ai: {
  provider: 'openai',
  baseURL: 'http://127.0.0.1:8000/api/v1',
  apiKey: 'your-api-key-here'
}
```

## AI 功能

### 1. 辅助编写测试（在 pause() 模式下）

在交互式 pause 模式下，可以使用自然语言与 AI 交互：

```bash
# 运行测试并进入 pause 模式
npx codeceptjs run --pause
```

在 pause 模式下，你可以：
- 输入自然语言指令，AI 会帮助你编写测试代码
- 例如：`"generate test for login form"`
- AI 会分析当前页面并生成相应的测试代码

### 2. 生成页面对象

AI 可以分析页面并自动生成页面对象：

```bash
# 在 pause 模式下
npx codeceptjs run --pause

# 然后输入：
"generate PageObject for this page"
```

AI 会：
- 分析当前页面的 HTML 结构
- 识别表单、按钮、链接等元素
- 生成对应的页面对象代码

### 3. 自愈失败的测试

AI 可以自动修复失败的测试：

```javascript
// 在 codecept.conf.js 中已启用
plugins: {
  retryFailedStep: {
    enabled: true
  }
}
```

当测试失败时，AI 会：
1. 分析失败原因
2. 修改选择器或等待策略
3. 重新运行测试

### 4. 从测试页面发送提示

在测试执行过程中，可以从任何页面发送提示到 AI：

```javascript
Scenario('使用 AI 分析页面', async ({ I }) => {
  I.amOnPage('/some-page');
  
  // 在 pause 模式下，可以发送提示
  // AI 会分析页面内容并给出建议
});
```

## 使用示例

### 示例 1：生成登录测试

```bash
# 1. 启动测试并进入 pause 模式
npx codeceptjs run --pause

# 2. 访问登录页面
I.amOnPage('/login')

# 3. 在 pause 模式下输入：
"generate test for login with username and password"

# 4. AI 会生成测试代码
```

### 示例 2：修复失败的测试

```javascript
Scenario('测试登录功能', async ({ I }) => {
  I.amOnPage('/login');
  I.fillField('#username', 'testuser');
  I.fillField('#password', 'password');
  I.click('Login');
  I.see('Welcome');
});
```

如果测试失败（例如选择器不正确），AI 会自动：
1. 分析页面结构
2. 找到正确的选择器
3. 更新测试代码
4. 重新运行

### 示例 3：生成页面对象

```bash
# 在 pause 模式下
npx codeceptjs run --pause

# 访问页面
I.amOnPage('/products')

# 输入指令
"generate PageObject for products page"

# AI 会生成类似这样的代码：
# class ProductsPage {
#   constructor() {
#     this.productList = '.product-list';
#     this.addToCartButton = 'button.add-to-cart';
#   }
# }
```

## API 兼容性

我们的自定义 LLM API 完全兼容 OpenAI 格式：

- **端点**: `/api/v1/chat/completions`
- **认证**: `X-API-Key` 头部
- **格式**: OpenAI Chat Completions API 格式

CodeceptJS 的 AI 功能使用 OpenAI SDK，会自动：
- 在 baseURL 后添加 `/chat/completions`
- 使用正确的请求格式
- 处理响应

## 注意事项

1. **API Key 安全**: 不要将 API Key 提交到版本控制系统
2. **网络连接**: 确保测试环境可以访问 LLM API 服务
3. **成本控制**: AI 功能会消耗 API 调用，注意控制成本
4. **pause 模式**: AI 的主要功能在 pause 模式下使用

## 故障排除

### AI 功能不工作

1. 检查 API 服务是否运行：
```bash
curl http://127.0.0.1:8000/health
```

2. 检查 API Key 是否正确：
```bash
curl -H "X-API-Key: your-key" http://127.0.0.1:8000/api/v1/chat/completions
```

3. 检查 baseURL 配置：
   - baseURL 应该是 `http://127.0.0.1:8000/api/v1`
   - CodeceptJS 会自动添加 `/chat/completions`

### pause 模式无法进入

确保使用正确的命令：
```bash
npx codeceptjs run --pause
```

## 更多信息

- [CodeceptJS AI 文档](https://codecept.io/ai)
- [CodeceptJS 文档](https://codecept.io/)
- 项目主 README: `../../README.md`

