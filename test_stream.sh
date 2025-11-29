#!/bin/bash

# 流式响应测试脚本
# 使用方法: ./test_stream.sh

API_KEY="${API_KEY:-1LtJU5J8KxkjryJtuRfdf1BIriTDV2DE}"
API_URL="${API_URL:-http://127.0.0.1:8000/api/v1/chat/completions}"
PROMPT="${1:-请用一句话介绍人工智能}"

echo "🧪 流式响应测试"
echo "=========================================="
echo "API地址: $API_URL"
echo "提示词: $PROMPT"
echo "=========================================="
echo ""

curl -N -X POST "$API_URL" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"deepseek-chat\",
    \"messages\": [
      {\"role\": \"user\", \"content\": \"$PROMPT\"}
    ],
    \"stream\": true,
    \"temperature\": 0.7
  }" 2>&1 | grep -E "^data: " | sed 's/^data: //' | while read line; do
  if [ "$line" = "[DONE]" ]; then
    echo ""
    echo "✅ 流式响应完成"
    break
  fi
  # 提取并显示内容
  echo "$line" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('choices', [{}])[0].get('delta', {}).get('content', ''), end='', flush=True)" 2>/dev/null
done

echo ""
echo "=========================================="

