#!/usr/bin/env python3
"""
流式响应测试脚本
使用方法: python3 test_stream.py [提示词]
"""
import requests
import json
import sys

API_KEY = "1LtJU5J8KxkjryJtuRfdf1BIriTDV2DE"
API_URL = "http://127.0.0.1:8000/api/v1/chat/completions"

def test_stream(prompt="请用一句话介绍人工智能"):
    """测试流式响应"""
    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "stream": True,
        "temperature": 0.7
    }
    
    print("🧪 流式响应测试")
    print("=" * 50)
    print(f"提示词: {prompt}")
    print("=" * 50)
    print()
    
    try:
        response = requests.post(
            API_URL,
            headers=headers,
            json=data,
            stream=True  # 启用流式响应
        )
        
        response.raise_for_status()
        
        # 逐行读取SSE数据
        for line in response.iter_lines():
            if line:
                line_text = line.decode('utf-8')
                if line_text.startswith('data: '):
                    data_str = line_text[6:]  # 移除 'data: ' 前缀
                    if data_str.strip() == '[DONE]':
                        print("\n✅ 流式响应完成")
                        break
                    try:
                        chunk = json.loads(data_str)
                        if 'choices' in chunk and len(chunk['choices']) > 0:
                            delta = chunk['choices'][0].get('delta', {})
                            content = delta.get('content', '')
                            if content:
                                print(content, end='', flush=True)
                    except json.JSONDecodeError:
                        pass
        
        print("\n" + "=" * 50)
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    prompt = sys.argv[1] if len(sys.argv) > 1 else "请用一句话介绍人工智能"
    test_stream(prompt)

