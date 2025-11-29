#!/usr/bin/env python3
"""
全面测试脚本 - 测试 plan 和 chat 的流式和非流式响应
使用方法: python3 test_all.py
"""
import requests
import json
import sys
import time
from typing import Dict, Any

API_KEY = "1LtJU5J8KxkjryJtuRfdf1BIriTDV2DE"
API_URL = "http://127.0.0.1:8000"

# 颜色输出
class Colors:
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    RED = '\033[0;31m'
    NC = '\033[0m'  # No Color

def print_header(title: str):
    """打印测试标题"""
    print(f"\n{Colors.BLUE}{title}{Colors.NC}")
    print("-" * 50)

def test_plan_non_stream():
    """测试 Plan 非流式响应"""
    print_header("测试1: Plan 非流式响应")
    
    url = f"{API_URL}/api/v1/plan"
    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }
    data = {
        "task": "开发一个简单的待办事项应用",
        "model": "deepseek-chat",
        "max_steps": 5,
        "temperature": 0.7,
        "stream": False
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        print(f"✅ 请求成功")
        print(f"任务: {result.get('task', '')}")
        print(f"步骤数: {result.get('total_steps', 0)}")
        print(f"模型: {result.get('model', '')}")
        if result.get('steps'):
            print(f"前3个步骤:")
            for step in result['steps'][:3]:
                print(f"  {step.get('step_number')}. {step.get('title')}")
        return True
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return False

def test_plan_stream():
    """测试 Plan 流式响应"""
    print_header("测试2: Plan 流式响应")
    
    url = f"{API_URL}/api/v1/plan"
    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }
    data = {
        "task": "学习Python编程",
        "max_steps": 4,
        "stream": True
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, stream=True, timeout=30)
        response.raise_for_status()
        
        print("✅ 流式响应开始:")
        chunk_count = 0
        for line in response.iter_lines():
            if line:
                line_text = line.decode('utf-8')
                if line_text.startswith('data: '):
                    data_str = line_text[6:]
                    if data_str.strip() == '[DONE]':
                        print(f"\n✅ 流式响应完成（共 {chunk_count} 个chunk）")
                        break
                    try:
                        chunk = json.loads(data_str)
                        chunk_count += 1
                        if chunk_count <= 5:  # 只显示前5个chunk
                            if 'choices' in chunk:
                                content = chunk['choices'][0].get('delta', {}).get('content', '')
                                if content:
                                    print(content, end='', flush=True)
                    except json.JSONDecodeError:
                        pass
        return True
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return False

def test_chat_non_stream():
    """测试 Chat 非流式响应"""
    print_header("测试3: Chat 非流式响应")
    
    url = f"{API_URL}/api/v1/chat/completions"
    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }
    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "user", "content": "用一句话介绍人工智能"}
        ],
        "temperature": 0.7,
        "stream": False
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        print(f"✅ 请求成功")
        if result.get('choices'):
            content = result['choices'][0].get('message', {}).get('content', '')
            print(f"回复: {content[:100]}...")
        if result.get('usage'):
            usage = result['usage']
            print(f"Token使用: {usage.get('total_tokens', 0)} tokens")
        return True
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return False

def test_chat_stream():
    """测试 Chat 流式响应"""
    print_header("测试4: Chat 流式响应")
    
    url = f"{API_URL}/api/v1/chat/completions"
    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }
    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "user", "content": "写一首关于春天的短诗"}
        ],
        "stream": True,
        "temperature": 0.7
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, stream=True, timeout=30)
        response.raise_for_status()
        
        print("✅ 流式响应开始:")
        full_content = ""
        chunk_count = 0
        for line in response.iter_lines():
            if line:
                line_text = line.decode('utf-8')
                if line_text.startswith('data: '):
                    data_str = line_text[6:]
                    if data_str.strip() == '[DONE]':
                        print(f"\n✅ 流式响应完成（共 {chunk_count} 个chunk）")
                        print(f"完整内容长度: {len(full_content)} 字符")
                        break
                    try:
                        chunk = json.loads(data_str)
                        chunk_count += 1
                        if 'choices' in chunk:
                            content = chunk['choices'][0].get('delta', {}).get('content', '')
                            if content:
                                full_content += content
                                print(content, end='', flush=True)
                    except json.JSONDecodeError:
                        pass
        return True
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return False

def test_plan_cache():
    """测试 Plan 缓存功能"""
    print_header("测试5: Plan 缓存功能测试")
    
    url = f"{API_URL}/api/v1/plan"
    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }
    data = {
        "task": "测试缓存功能",
        "max_steps": 3,
        "stream": False
    }
    
    try:
        print("第一次请求（应该调用LLM）:")
        start_time = time.time()
        response1 = requests.post(url, headers=headers, json=data, timeout=30)
        response1.raise_for_status()
        time1 = time.time() - start_time
        print(f"✅ 完成，耗时: {time1:.2f}秒")
        
        print("\n第二次请求（应该从缓存返回）:")
        start_time = time.time()
        response2 = requests.post(url, headers=headers, json=data, timeout=30)
        response2.raise_for_status()
        time2 = time.time() - start_time
        print(f"✅ 完成，耗时: {time2:.2f}秒")
        
        if time2 < time1 * 0.5:  # 缓存应该至少快50%
            print(f"✅ 缓存生效！第二次请求快了 {((time1-time2)/time1*100):.1f}%")
        else:
            print(f"⚠️  缓存可能未生效（时间差异不明显）")
        
        return True
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return False

def test_chat_cache():
    """测试 Chat 缓存功能"""
    print_header("测试6: Chat 缓存功能测试")
    
    url = f"{API_URL}/api/v1/chat/completions"
    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }
    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "user", "content": "测试缓存"}
        ],
        "stream": False
    }
    
    try:
        print("第一次请求（应该调用LLM）:")
        start_time = time.time()
        response1 = requests.post(url, headers=headers, json=data, timeout=30)
        response1.raise_for_status()
        time1 = time.time() - start_time
        print(f"✅ 完成，耗时: {time1:.2f}秒")
        
        print("\n第二次请求（应该从缓存返回）:")
        start_time = time.time()
        response2 = requests.post(url, headers=headers, json=data, timeout=30)
        response2.raise_for_status()
        time2 = time.time() - start_time
        print(f"✅ 完成，耗时: {time2:.2f}秒")
        
        if time2 < time1 * 0.5:  # 缓存应该至少快50%
            print(f"✅ 缓存生效！第二次请求快了 {((time1-time2)/time1*100):.1f}%")
        else:
            print(f"⚠️  缓存可能未生效（时间差异不明显）")
        
        return True
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return False

def main():
    """主函数"""
    print(f"{Colors.GREEN}🧪 全面测试脚本{Colors.NC}")
    print("=" * 50)
    print(f"API地址: {API_URL}")
    print(f"API Key: {API_KEY[:10]}...")
    print("=" * 50)
    
    results = []
    
    # 运行所有测试
    results.append(("Plan 非流式", test_plan_non_stream()))
    results.append(("Plan 流式", test_plan_stream()))
    results.append(("Chat 非流式", test_chat_non_stream()))
    results.append(("Chat 流式", test_chat_stream()))
    results.append(("Plan 缓存", test_plan_cache()))
    results.append(("Chat 缓存", test_chat_cache()))
    
    # 打印总结
    print(f"\n{Colors.GREEN}{'='*50}{Colors.NC}")
    print(f"{Colors.GREEN}测试总结{Colors.NC}")
    print(f"{'='*50}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = f"{Colors.GREEN}✅ 通过{Colors.NC}" if result else f"{Colors.RED}❌ 失败{Colors.NC}"
        print(f"{name}: {status}")
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print(f"{Colors.GREEN}🎉 所有测试通过！{Colors.NC}")
        return 0
    else:
        print(f"{Colors.RED}⚠️  部分测试失败{Colors.NC}")
        return 1

if __name__ == "__main__":
    sys.exit(main())

