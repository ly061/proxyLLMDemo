#!/bin/bash

# 全面测试脚本 - 测试 plan 和 chat 的流式和非流式响应
# 使用方法: ./test_all.sh

API_KEY="${API_KEY:-1LtJU5J8KxkjryJtuRfdf1BIriTDV2DE}"
API_URL="${API_URL:-http://127.0.0.1:8000}"
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "🧪 全面测试脚本"
echo "=========================================="
echo ""

# 测试1: Plan 非流式
echo -e "${BLUE}测试1: Plan 非流式响应${NC}"
echo "----------------------------------------"
curl -s -X POST "${API_URL}/api/v1/plan" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "task": "开发一个简单的待办事项应用",
    "model": "deepseek-chat",
    "max_steps": 5,
    "temperature": 0.7,
    "stream": false
  }' | python3 -m json.tool 2>/dev/null | head -30 || echo "请求失败"
echo ""
echo ""

# 测试2: Plan 流式响应
echo -e "${BLUE}测试2: Plan 流式响应${NC}"
echo "----------------------------------------"
echo "流式数据（前20行）:"
curl -N -s -X POST "${API_URL}/api/v1/plan" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "task": "学习Python编程",
    "max_steps": 4,
    "stream": true
  }' 2>&1 | head -20
echo ""
echo ""

# 测试3: Chat 非流式
echo -e "${BLUE}测试3: Chat 非流式响应${NC}"
echo "----------------------------------------"
curl -s -X POST "${API_URL}/api/v1/chat/completions" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-chat",
    "messages": [
      {"role": "user", "content": "用一句话介绍人工智能"}
    ],
    "temperature": 0.7,
    "stream": false
  }' | python3 -m json.tool 2>/dev/null | head -25 || echo "请求失败"
echo ""
echo ""

# 测试4: Chat 流式响应
echo -e "${BLUE}测试4: Chat 流式响应${NC}"
echo "----------------------------------------"
echo "流式数据（前20行）:"
curl -N -s -X POST "${API_URL}/api/v1/chat/completions" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-chat",
    "messages": [
      {"role": "user", "content": "写一首关于春天的短诗"}
    ],
    "stream": true,
    "temperature": 0.7
  }' 2>&1 | head -20
echo ""
echo ""

# 测试5: Plan 缓存测试
echo -e "${BLUE}测试5: Plan 缓存功能测试${NC}"
echo "----------------------------------------"
echo "第一次请求（应该调用LLM）:"
time curl -s -X POST "${API_URL}/api/v1/plan" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "task": "测试缓存功能",
    "max_steps": 3,
    "stream": false
  }' > /dev/null 2>&1
echo "完成"

echo ""
echo "第二次请求（应该从缓存返回）:"
time curl -s -X POST "${API_URL}/api/v1/plan" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "task": "测试缓存功能",
    "max_steps": 3,
    "stream": false
  }' > /dev/null 2>&1
echo "完成（应该更快）"
echo ""
echo ""

# 测试6: Chat 缓存测试
echo -e "${BLUE}测试6: Chat 缓存功能测试${NC}"
echo "----------------------------------------"
echo "第一次请求（应该调用LLM）:"
time curl -s -X POST "${API_URL}/api/v1/chat/completions" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-chat",
    "messages": [
      {"role": "user", "content": "测试缓存"}
    ],
    "stream": false
  }' > /dev/null 2>&1
echo "完成"

echo ""
echo "第二次请求（应该从缓存返回）:"
time curl -s -X POST "${API_URL}/api/v1/chat/completions" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-chat",
    "messages": [
      {"role": "user", "content": "测试缓存"}
    ],
    "stream": false
  }' > /dev/null 2>&1
echo "完成（应该更快）"
echo ""
echo ""

echo -e "${GREEN}✅ 所有测试完成！${NC}"
echo "=========================================="

