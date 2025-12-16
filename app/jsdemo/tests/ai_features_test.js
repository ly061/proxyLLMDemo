/**
 * CodeceptJS AI 功能测试示例
 * 
 * 根据 CodeceptJS AI 文档：https://codecept.io/ai
 * 
 * AI 功能包括：
 * 1. 在 pause() 模式下辅助编写测试
 * 2. 生成页面对象
 * 3. 自愈失败的测试
 * 4. 从测试页面发送提示到 AI
 */

Feature('CodeceptJS AI Features');

Scenario('测试 AI 辅助功能 - 生成页面对象', async ({ I }) => {
  // 注意：AI 功能主要在 pause() 模式下使用
  // 这里展示如何通过代码使用 AI 功能
  
  // 访问一个页面
  I.amOnPage('https://www.baidu.com');
  pause();
  
  // 在 pause() 模式下，可以使用自然语言与 AI 交互
  // 例如：输入 "generate PageObject for this page"
  // AI 会分析页面并生成页面对象代码
  
  console.log('AI 功能已配置，可以在 pause() 模式下使用');
  console.log('运行测试时使用 --pause 参数进入交互模式');
  console.log('然后在交互模式中输入自然语言指令，AI 会帮助你编写测试');
});

