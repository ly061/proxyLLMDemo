#!/usr/bin/env python3
"""
LangGraph Agent 使用示例

这个示例展示了如何使用我们开发的 API 来创建和运行 LangGraph Agent。

使用方法:
    python examples/langgraph_agent_example.py
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from app.agents.langgraph_agent import create_agent


# 定义自定义工具
@tool
def search_web(query: str) -> str:
    """搜索网络信息
    
    Args:
        query: 搜索查询字符串
        
    Returns:
        搜索结果（示例）
    """
    # 这是一个示例实现，实际应用中应该调用真实的搜索 API
    return f"关于 '{query}' 的搜索结果：这是一个示例结果。在实际应用中，这里应该返回真实的搜索结果。"


@tool
def get_time() -> str:
    """获取当前时间
    
    Returns:
        当前时间字符串
    """
    from datetime import datetime
    return f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"


def main():
    """主函数"""
    # 配置参数
    # 注意：实际使用时应该从环境变量或配置文件读取
    API_KEY = "1LtJU5J8KxkjryJtuRfdf1BIriTDV2DE"
    BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
    MODEL = os.getenv("MODEL", "deepseek-chat")
    
    if API_KEY == "your-api-key-here":
        print("⚠️  警告: 请设置 API_KEY 环境变量或修改代码中的 API_KEY")
        print("   例如: export API_KEY='your-actual-api-key'")
        print()
    
    print("=" * 70)
    print("LangGraph Agent 使用示例")
    print("=" * 70)
    print(f"API URL: {BASE_URL}")
    print(f"模型: {MODEL}")
    print("=" * 70)
    print()
    
    # 创建 agent，使用自定义工具
    print("正在创建 Agent...")
    agent = create_agent(
        api_key=API_KEY,
        base_url=BASE_URL,
        model=MODEL,
        temperature=0.7,
        tools=[search_web, get_time],
        system_prompt="你是一个有用的 AI 助手，可以帮助用户搜索信息和查询时间。",
    )
    print("✅ Agent 创建成功")
    print()
    
    # 示例查询
    examples = [
        "现在几点了？",
        "帮我搜索一下 Python 编程语言的最新信息",
        "请告诉我当前时间，然后搜索一下人工智能的发展历史",
    ]
    
    for i, query in enumerate(examples, 1):
        print(f"\n{'=' * 70}")
        print(f"示例 {i}: {query}")
        print("-" * 70)
        
        try:
            # 运行 agent
            # 手动添加 SystemMessage（因为旧版本 langgraph 不支持 prompt 参数）
            messages = [SystemMessage(content="你是一个有用的 AI 助手，可以帮助用户搜索信息和查询时间。"), 
                       HumanMessage(content=query)]
            
            result = agent.invoke(
                {
                    "messages": messages
                }
            )
            
            # 显示结果
            assistant_message = result['messages'][-1]
            print(f"用户: {query}")
            print(f"助手: {assistant_message.content}")
            
            # 如果有工具调用，显示工具调用信息
            if hasattr(assistant_message, 'tool_calls') and assistant_message.tool_calls:
                print("\n工具调用:")
                for tool_call in assistant_message.tool_calls:
                    print(f"  - {tool_call.get('name', 'unknown')}: {tool_call.get('args', {})}")
        
        except Exception as e:
            print(f"❌ 错误: {str(e)}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 70)
    print("示例运行完成")
    print("=" * 70)


if __name__ == "__main__":
    main()

