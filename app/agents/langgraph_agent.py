"""
LangGraph Agent 示例
使用我们的自定义 API 作为 LLM 提供者
"""
from typing import Any, List, Optional
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from app.agents.custom_chat_model import CustomChatModel
from app.utils.logger import logger


# 示例工具函数
@tool
def get_weather(location: str) -> str:
    """获取指定城市的天气信息
    
    Args:
        location: 城市名称，例如 "北京"、"上海"、"San Francisco"
        
    Returns:
        天气信息字符串
    """
    # 这里是一个示例实现，实际应用中应该调用真实的天气 API
    weather_data = {
        "北京": "北京今天晴天，温度 15-25°C，微风",
        "上海": "上海今天多云，温度 18-26°C，东南风",
        "深圳": "深圳今天晴天，温度 22-30°C，无风",
        "san francisco": "It's 60 degrees and foggy in San Francisco.",
        "sf": "It's 60 degrees and foggy in San Francisco.",
    }
    
    location_lower = location.lower()
    for city, weather in weather_data.items():
        if city.lower() in location_lower or location_lower in city.lower():
            return weather
    
    return f"抱歉，我无法获取 {location} 的天气信息。请尝试其他城市。"


@tool
def calculate(expression: str) -> str:
    """计算数学表达式
    
    Args:
        expression: 数学表达式，例如 "2 + 2"、"10 * 5"
        
    Returns:
        计算结果字符串
    """
    try:
        # 安全的数学表达式计算
        # 注意：在生产环境中应该使用更安全的评估方法
        result = eval(expression)
        return f"计算结果: {result}"
    except Exception as e:
        return f"计算错误: {str(e)}"


def create_agent(
    api_key: str,
    base_url: str = "http://127.0.0.1:8000",
    model: str = "deepseek-chat",
    temperature: float = 0.7,
    tools: Optional[List] = None,
    system_prompt: Optional[str] = None,
) -> Any:
    """
    创建 LangGraph ReAct Agent
    
    Args:
        api_key: API Key 用于认证
        base_url: API 基础 URL，默认为本地服务
        model: 模型名称
        temperature: 温度参数
        tools: 工具列表，如果为 None 则使用默认工具
        system_prompt: 系统提示词
        
    Returns:
        配置好的 LangGraph Agent
    """
    # 创建自定义 ChatModel
    llm = CustomChatModel(
        api_key=api_key,
        base_url=base_url,
        model=model,
        temperature=temperature,
    )
    
    # 如果没有提供工具，使用默认工具
    if tools is None:
        tools = [get_weather, calculate]
    
    # 创建 agent
    # 注意：旧版本的 langgraph (0.1.x) 不支持 prompt 参数
    # system_prompt 参数会被忽略，需要在调用时通过 SystemMessage 手动添加
    agent = create_react_agent(
        model=llm,
        tools=tools,
    )
    
    # 如果提供了 system_prompt，记录警告（因为旧版本不支持）
    if system_prompt:
        logger.warning(
            "system_prompt 参数已提供，但当前版本的 langgraph 不支持 prompt 参数。"
            "请在调用 agent.invoke() 时手动添加 SystemMessage。"
        )
    
    logger.info(f"LangGraph Agent 创建成功: model={model}, tools={len(tools)}")
    return agent


def run_agent_example():
    """
    运行 Agent 示例
    """
    # 配置参数（实际使用时应该从环境变量或配置文件读取）
    API_KEY = "your-api-key-here"  # 替换为实际的 API Key
    BASE_URL = "http://127.0.0.1:8000"
    MODEL = "deepseek-chat"
    
    # 创建 agent
    agent = create_agent(
        api_key=API_KEY,
        base_url=BASE_URL,
        model=MODEL,
        temperature=0.7,
        system_prompt="你是一个有用的 AI 助手，可以帮助用户查询天气和进行数学计算。",
    )
    
    # 运行 agent
    print("=" * 60)
    print("LangGraph Agent 示例")
    print("=" * 60)
    
    # 示例 1: 查询天气
    print("\n示例 1: 查询天气")
    print("-" * 60)
    result = agent.invoke(
        {
            "messages": [
                HumanMessage(content="北京的天气怎么样？")
            ]
        }
    )
    print(f"用户: 北京的天气怎么样？")
    print(f"助手: {result['messages'][-1].content}")
    
    # 示例 2: 数学计算
    print("\n示例 2: 数学计算")
    print("-" * 60)
    result = agent.invoke(
        {
            "messages": [
                HumanMessage(content="帮我计算 123 * 456 等于多少？")
            ]
        }
    )
    print(f"用户: 帮我计算 123 * 456 等于多少？")
    print(f"助手: {result['messages'][-1].content}")
    
    # 示例 3: 复杂查询
    print("\n示例 3: 复杂查询")
    print("-" * 60)
    result = agent.invoke(
        {
            "messages": [
                HumanMessage(content="如果北京的温度是 20 度，上海的温度是 25 度，那么温差是多少？")
            ]
        }
    )
    print(f"用户: 如果北京的温度是 20 度，上海的温度是 25 度，那么温差是多少？")
    print(f"助手: {result['messages'][-1].content}")
    
    print("\n" + "=" * 60)
    print("示例运行完成")
    print("=" * 60)


if __name__ == "__main__":
    run_agent_example()

