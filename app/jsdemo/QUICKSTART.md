# CodeceptJS + 自定义 LLM 快速开始指南

## 5 分钟快速开始

### 1. 安装依赖

```bash
cd app/jsdemo
npm install
```

### 2. 配置 API Key

有两种方式配置 API Key：

**方式一：使用环境变量（推荐）**

```bash
export LLM_API_KEY="your-api-key-here"
export LLM_BASE_URL="http://127.0.0.1:8000"
```

**方式二：直接修改配置文件**

编辑 `codecept.conf.js`，找到 `LLMHelper` 配置部分，直接填写 API Key：

```javascript
LLMHelper: {
  require: './helpers/llm_helper.js',
  apiKey: 'your-api-key-here',  // 直接填写你的 API Key
  // ...
}
```

### 3. 获取 API Key

如果你还没有 API Key，在项目根目录运行：

```bash
cd ../..
python generate_api_key.py
```

### 4. 确保 LLM API 服务正在运行

确保你的 LLM API 服务正在运行（默认端口 8000）：

```bash
# 在项目根目录
python run.py
```

### 5. 运行示例测试

```bash
# 运行基础示例
npm test -- tests/basic_example_test.js

# 运行完整示例
npm test -- tests/llm_integration_test.js

# 运行所有测试
npm test
```

## 基本使用示例

### 在测试中使用 LLM Helper

```javascript
Feature('My Feature');

Scenario('使用 LLM 生成测试数据', async ({ I, llmHelper }) => {
  // 生成测试数据
  const userData = await llmHelper.generateTestData(
    '生成一个用户对象，包含 name 和 email'
  );
  
  console.log('生成的用户:', userData);
  
  // 使用生成的数据
  I.amOnPage('/register');
  I.fillField('name', userData.name);
  I.fillField('email', userData.email);
});
```

### 可用的方法

1. **`generateText(messages, options)`** - 生成文本
2. **`generateTestData(description, options)`** - 生成测试数据（JSON）
3. **`generateTestSteps(scenario, options)`** - 生成测试步骤代码
4. **`suggestSelector(description, options)`** - 建议页面元素选择器

## 常见问题

### Q: API Key 错误怎么办？

A: 检查以下几点：
1. API Key 是否正确配置
2. API Key 是否有效（可以通过 API 文档测试）
3. 环境变量是否正确设置

### Q: 连接超时怎么办？

A: 检查：
1. LLM API 服务是否正在运行
2. `baseUrl` 配置是否正确
3. 网络连接是否正常

### Q: 如何调试？

A: 使用调试模式运行：

```bash
npm run test:debug
```

## 下一步

- 查看 `tests/basic_example_test.js` 了解基础用法
- 查看 `tests/llm_integration_test.js` 了解高级用法
- 阅读 `README.md` 了解完整文档

