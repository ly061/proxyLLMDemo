#!/usr/bin/env python3
"""
LangGraph Agent 测试脚本

快速测试 LangGraph Agent 是否正常工作
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from langchain_core.messages import HumanMessage
from app.agents.langgraph_agent import create_agent


def test_basic_agent():
    """测试基本的 Agent 功能"""
    print("=" * 70)
    print("测试 1: 基本 Agent 功能")
    print("=" * 70)
    
    # 配置参数（请替换为实际的 API Key）
    API_KEY = os.getenv("API_KEY", "your-api-key-here")
    BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
    
    if API_KEY == "your-api-key-here":
        print("⚠️  警告: 请设置 API_KEY 环境变量")
        print("   例如: export API_KEY='your-actual-api-key'")
        return False
    
    try:
        # 创建 agent
        agent = create_agent(
            api_key=API_KEY,
            base_url=BASE_URL,
            model="deepseek-chat",
            temperature=0.7,
        )
        
        # 测试简单查询
        result = agent.invoke({
            "messages": [
                HumanMessage(content="请用一句话介绍人工智能")
            ]
        })
        
        print(f"✅ Agent 创建成功")
        print(f"用户: 请用一句话介绍人工智能")
        print(f"助手: {result['messages'][-1].content}")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_agent_with_tools():
    """测试带工具的 Agent"""
    print("\n" + "=" * 70)
    print("测试 2: Agent 工具调用")
    print("=" * 70)
    
    API_KEY = os.getenv("API_KEY", "your-api-key-here")
    BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
    
    if API_KEY == "your-api-key-here":
        print("⚠️  跳过测试（需要 API_KEY）")
        return False
    
    try:
        # 创建带工具的 agent
        agent = create_agent(
            api_key=API_KEY,
            base_url=BASE_URL,
            model="deepseek-chat",
            temperature=0.7,
        )
        
        # 测试工具调用
        result = agent.invoke({
            "messages": [
                HumanMessage(content="北京的天气怎么样？")
            ]
        })
        
        print(f"✅ 工具调用测试成功")
        print(f"用户: 北京的天气怎么样？")
        print(f"助手: {result['messages'][-1].content}")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("\n🧪 LangGraph Agent 测试")
    print("=" * 70)
    
    results = []
    
    # 运行测试
    results.append(("基本功能", test_basic_agent()))
    results.append(("工具调用", test_agent_with_tools()))
    
    # 显示结果
    print("\n" + "=" * 70)
    print("测试结果汇总")
    print("=" * 70)
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{name}: {status}")
    
    total_passed = sum(1 for _, passed in results if passed)
    total_tests = len(results)
    
    print(f"\n总计: {total_passed}/{total_tests} 测试通过")
    
    if total_passed == total_tests:
        print("🎉 所有测试通过！")
        return 0
    else:
        print("⚠️  部分测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())

