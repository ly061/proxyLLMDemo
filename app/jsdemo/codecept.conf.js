/**
 * CodeceptJS 配置文件
 * 配置了 Playwright 作为测试驱动
 */
exports.config = {
  tests: './tests/**/*_test.js',
  output: './output',
  helpers: {
    Playwright: {
      url: 'http://localhost',
      show: true,
      browser: 'chromium',
      waitForTimeout: 5000,
      waitForAction: 1000,
    }
  },
  include: {
    I: './steps_file.js'
  },
  bootstrap: null,
  mocha: {},
  name: 'codeceptjs-tests',
  plugins: {
    pauseOnFail: {},
    retryFailedStep: {
      enabled: true
    },
    tryTo: {
      enabled: true
    },
    screenshotOnFail: {
      enabled: true
    }
  },
  // CodeceptJS AI 功能配置
  // 根据文档：https://codecept.io/ai
  // 使用自定义 request 函数直接调用我们的 LLM API
  ai: {
    request: async (messages) => {
      const axios = require('axios');
      const baseURL = process.env.LLM_BASE_URL || 'http://127.0.0.1:8000';
      const apiKey = process.env.LLM_API_KEY || '1LtJU5J8KxkjryJtuRfdf1BIriTDV2DE';
      const model = process.env.LLM_MODEL || 'deepseek-chat';
      
      try {
        const response = await axios.post(
          `${baseURL}/api/v1/chat/completions`,
          {
            model: model,
            messages: messages,
            temperature: 0.7
          },
          {
            headers: {
              'Content-Type': 'application/json',
              'X-API-Key': apiKey
            },
            timeout: 60000
          }
        );
        
        // 返回消息内容
        if (response.data && response.data.choices && response.data.choices.length > 0) {
          return response.data.choices[0].message.content;
        }
        throw new Error('Invalid response format from LLM API');
      } catch (error) {
        if (error.response) {
          throw new Error(`LLM API Error: ${error.response.status} - ${error.response.data?.detail || error.response.statusText}`);
        }
        throw error;
      }
    }
  }
};

