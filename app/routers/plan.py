"""
任务规划路由 - 将任务拆分成步骤
"""
import json
import re
from typing import Optional, List, Any, Dict
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from app.adapters.base import ChatMessage
from app.auth.api_key import get_user_info
from app.config import settings
from app.utils.logger import logger
from app.utils.adapter_factory import get_adapter
from app.utils.cache import cache, cache_key_generator
from app.utils.llm_helpers import extract_response_content, extract_usage_info
from app.database.db import record_request
from app.exceptions import LLMServiceException, ValidationException


router = APIRouter(prefix="/api/v1", tags=["plan"])


class PlanRequest(BaseModel):
    """任务规划请求"""
    task: str = Field(
        ..., 
        description="要拆分的任务描述",
        min_length=1,
        max_length=settings.PLAN_TASK_MAX_LENGTH
    )
    model: Optional[str] = Field(None, description="模型名称，如果不指定则使用默认模型")
    temperature: Optional[float] = Field(0.7, ge=0, le=2, description="温度参数")
    max_steps: Optional[int] = Field(
        settings.PLAN_DEFAULT_MAX_STEPS, 
        ge=settings.PLAN_MIN_STEPS, 
        le=settings.PLAN_MAX_STEPS, 
        description="最大步骤数"
    )
    stream: Optional[bool] = Field(False, description="是否启用流式响应")


class PlanStep(BaseModel):
    """计划步骤"""
    step_number: int = Field(..., description="步骤序号")
    title: str = Field(..., description="步骤标题")
    description: str = Field(..., description="步骤详细描述")
    estimated_time: Optional[str] = Field(None, description="预估时间")


class PlanResponse(BaseModel):
    """任务规划响应"""
    task: str = Field(..., description="原始任务")
    steps: List[PlanStep] = Field(..., description="拆分后的步骤列表")
    total_steps: int = Field(..., description="总步骤数")
    model: str = Field(..., description="使用的模型")


def build_plan_system_prompt(max_steps: int) -> str:
    """
    构建任务规划的系统提示词
    
    Args:
        max_steps: 最大步骤数
        
    Returns:
        系统提示词
    """
    return f"""你是一个专业的任务规划助手。你的任务是将用户给出的任务拆分成清晰的步骤。

请按照以下要求：
1. 将任务拆分成{settings.PLAN_MIN_STEPS}-{max_steps}个具体的步骤
2. 每个步骤应该有清晰的标题和描述
3. 步骤应该按照逻辑顺序排列
4. 如果可能，为每个步骤提供预估时间

请以JSON格式返回，格式如下：
{{
  "steps": [
    {{
      "step_number": 1,
      "title": "步骤标题",
      "description": "步骤详细描述",
      "estimated_time": "预估时间（可选）"
    }}
  ]
}}

如果无法返回JSON格式，也可以使用文本格式，每行一个步骤，格式：步骤序号. 步骤标题: 步骤描述"""


def extract_json_from_markdown(text: str) -> Optional[str]:
    """
    从markdown代码块中提取JSON文本
    
    Args:
        text: 包含JSON的文本
        
    Returns:
        提取的JSON文本，如果未找到则返回None
    """
    # 尝试提取 ```json ... ``` 格式
    json_match = re.search(r'```json\s*\n(.*?)\n```', text, re.DOTALL)
    if json_match:
        return json_match.group(1).strip()
    
    # 尝试提取 ``` ... ``` 格式
    code_match = re.search(r'```\s*\n(.*?)\n```', text, re.DOTALL)
    if code_match:
        return code_match.group(1).strip()
    
    return None


def parse_json_steps(data: Any, max_steps: int) -> List[PlanStep]:
    """
    解析JSON格式的步骤数据
    
    Args:
        data: JSON解析后的数据
        max_steps: 最大步骤数
        
    Returns:
        解析后的步骤列表
    """
    steps = []
    
    # 如果返回的是字典，尝试获取steps字段
    if isinstance(data, dict):
        if "steps" in data:
            steps_data = data["steps"]
        elif "plan" in data:
            steps_data = data["plan"]
        else:
            # 如果字典本身可能就是步骤数据
            steps_data = [data] if data else []
    elif isinstance(data, list):
        steps_data = data
    else:
        logger.warning(f"无法解析的数据类型: {type(data)}")
        return []
    
    # 转换为PlanStep列表
    if isinstance(steps_data, list):
        for idx, step in enumerate(steps_data[:max_steps], 1):
            if isinstance(step, dict):
                steps.append(PlanStep(
                    step_number=step.get("step_number", idx),
                    title=step.get("title", step.get("name", f"步骤{idx}")),
                    description=step.get("description", step.get("content", "")),
                    estimated_time=step.get("estimated_time", step.get("time"))
                ))
            elif isinstance(step, str):
                steps.append(PlanStep(
                    step_number=idx,
                    title=f"步骤{idx}",
                    description=step
                ))
    
    return steps


def parse_text_steps(text: str, max_steps: int) -> List[PlanStep]:
    """
    使用正则表达式解析文本格式的步骤
    
    Args:
        text: 包含步骤的文本
        max_steps: 最大步骤数
        
    Returns:
        解析后的步骤列表
    """
    steps = []
    step_number = 1
    
    # 定义多种步骤格式的正则表达式
    patterns = [
        # 格式1: 1. 标题: 描述 或 1. 标题
        (r'^\s*(\d+)\.\s+(.+?)(?::\s*(.+))?$', lambda m: {
            'number': int(m.group(1)),
            'title': m.group(2).strip(),
            'description': m.group(3).strip() if m.group(3) else ''
        }),
        # 格式2: Step 1: 标题: 描述 或 Step 1: 标题
        (r'^\s*[Ss]tep\s+(\d+)[:：]\s*(.+?)(?::\s*(.+))?$', lambda m: {
            'number': int(m.group(1)),
            'title': m.group(2).strip(),
            'description': m.group(3).strip() if m.group(3) else ''
        }),
        # 格式3: 步骤1：标题: 描述 或 步骤1：标题
        (r'^\s*步骤\s*(\d+)[:：]\s*(.+?)(?::\s*(.+))?$', lambda m: {
            'number': int(m.group(1)),
            'title': m.group(2).strip(),
            'description': m.group(3).strip() if m.group(3) else ''
        }),
    ]
    
    for line in text.split('\n'):
        line = line.strip()
        if not line:
            continue
        
        matched = False
        for pattern, extractor in patterns:
            match = re.match(pattern, line)
            if match:
                try:
                    step_data = extractor(match)
                    step_num = step_data['number']
                    title = step_data['title']
                    description = step_data['description'] if step_data['description'] else title
                    
                    steps.append(PlanStep(
                        step_number=step_num,
                        title=title,
                        description=description
                    ))
                    matched = True
                    step_number = max(step_number, step_num) + 1
                    break
                except (ValueError, IndexError) as e:
                    logger.debug(f"解析步骤失败: {line}, 错误: {str(e)}")
                    continue
        
        if not matched and step_number <= max_steps:
            # 如果没有匹配到格式，但行看起来像步骤，尝试简单解析
            if re.match(r'^\s*\d+', line):
                parts = line.split(':', 1) if ':' in line else line.split('.', 1)
                if len(parts) >= 2:
                    title = parts[0].strip()
                    description = parts[1].strip()
                else:
                    title = f"步骤{step_number}"
                    description = line
                
                steps.append(PlanStep(
                    step_number=step_number,
                    title=title,
                    description=description
                ))
                step_number += 1
        
        if step_number > max_steps:
            break
    
    return steps


def parse_plan_response(response_text: str, max_steps: int) -> List[PlanStep]:
    """
    解析LLM返回的计划步骤（主解析函数）
    
    按优先级尝试不同解析方式：
    1. JSON格式解析（优先）
    2. 文本格式解析（降级）
    3. 默认步骤（最后）
    
    Args:
        response_text: LLM返回的文本
        max_steps: 最大步骤数
        
    Returns:
        解析后的步骤列表
    """
    logger.info(f"开始解析规划响应，长度: {len(response_text)}")
    steps = []
    
    # 第一步：尝试JSON解析
    try:
        logger.debug("尝试JSON解析...")
        
        # 先尝试从markdown代码块中提取JSON
        json_text = extract_json_from_markdown(response_text)
        if json_text is None:
            json_text = response_text.strip()
        
        # 解析JSON
        data = json.loads(json_text)
        steps = parse_json_steps(data, max_steps)
        
        if steps:
            logger.info(f"JSON解析成功，找到 {len(steps)} 个步骤")
            return steps[:max_steps]
        else:
            logger.warning("JSON解析成功但未找到步骤数据")
    
    except json.JSONDecodeError as e:
        logger.warning(f"JSON解析失败，尝试文本解析: {str(e)}")
    except (KeyError, TypeError, ValueError) as e:
        logger.warning(f"JSON数据格式错误，尝试文本解析: {str(e)}")
    
    # 第二步：如果JSON解析失败，尝试文本解析
    if not steps:
        try:
            logger.debug("尝试文本解析...")
            steps = parse_text_steps(response_text, max_steps)
            if steps:
                logger.info(f"文本解析成功，找到 {len(steps)} 个步骤")
                return steps[:max_steps]
        except Exception as e:
            logger.warning(f"文本解析失败: {str(e)}")
    
    # 第三步：如果仍然没有解析到步骤，创建一个默认步骤
    if not steps:
        logger.warning("所有解析方式都失败，创建默认步骤")
        steps.append(PlanStep(
            step_number=1,
            title="任务分析",
            description=response_text[:500] if len(response_text) > 500 else response_text
        ))
    
    return steps[:max_steps]


async def stream_plan_completion(request: PlanRequest, user_info: Dict[str, Any]):
    """
    流式规划响应生成器
    
    Args:
        request: 规划请求
        user_info: 用户信息
        
    Yields:
        SSE格式的数据块
    """
    import json as json_module
    
    try:
        # 获取适配器
        adapter = get_adapter(request.model)
        model_name = request.model or adapter.default_model
        
        # 构建提示词
        system_prompt = build_plan_system_prompt(request.max_steps)
        user_prompt = f"请将以下任务拆分成步骤：\n\n{request.task}"
        
        # 构建消息（转换为字典格式，因为OpenAI SDK需要字典而不是Pydantic模型）
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # 构建请求参数
        request_params = {
            "model": model_name,
            "messages": messages,
            "temperature": request.temperature,
            "stream": True,
            "max_tokens": settings.PLAN_MAX_TOKENS
        }
        
        logger.info(f"开始流式规划任务: {request.task[:50]}...")
        
        # 调用适配器的流式接口
        if hasattr(adapter, 'client') and hasattr(adapter.client, 'chat') and hasattr(adapter.client.chat, 'completions'):
            stream = await adapter.client.chat.completions.create(**request_params)
            
            full_content = ""
            steps = []  # 初始化steps变量，避免NameError
            async for chunk in stream:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if delta and delta.content:
                        content = delta.content
                        full_content += content
                        
                        # 发送SSE格式数据
                        data = {
                            "id": chunk.id if hasattr(chunk, 'id') else "",
                            "object": "plan.completion.chunk",
                            "created": chunk.created if hasattr(chunk, 'created') else 0,
                            "model": chunk.model if hasattr(chunk, 'model') else model_name,
                            "choices": [{
                                "index": chunk.choices[0].index if hasattr(chunk.choices[0], 'index') else 0,
                                "delta": {"content": content},
                                "finish_reason": chunk.choices[0].finish_reason if hasattr(chunk.choices[0], 'finish_reason') else None
                            }]
                        }
                        yield f"data: {json_module.dumps(data, ensure_ascii=False)}\n\n"
            
            # 流式响应完成后，解析并发送最终结果
            if full_content:
                steps = parse_plan_response(full_content, request.max_steps)
                final_data = {
                    "object": "plan.completion.final",
                    "steps": [step.dict() for step in steps],
                    "total_steps": len(steps)
                }
                yield f"data: {json_module.dumps(final_data, ensure_ascii=False)}\n\n"
            
            yield "data: [DONE]\n\n"
            logger.info(f"流式规划完成: {len(steps)}个步骤")
        else:
            error_data = {
                "error": {
                    "message": "该适配器不支持流式响应",
                    "type": "stream_not_supported"
                }
            }
            yield f"data: {json_module.dumps(error_data, ensure_ascii=False)}\n\n"
            
    except Exception as e:
        logger.error(f"流式规划错误: {str(e)}", exc_info=True)
        error_data = {
            "error": {
                "message": f"流式规划处理失败: {str(e)}",
                "type": "stream_error"
            }
        }
        yield f"data: {json_module.dumps(error_data, ensure_ascii=False)}\n\n"


@router.post("/plan", response_model=PlanResponse)
async def create_plan(
    request: PlanRequest,
    user_info: dict = Depends(get_user_info)
):
    """
    任务规划接口 - 将任务拆分成步骤
    
    接收一个任务描述，使用LLM将其拆分成可执行的步骤列表
    支持流式响应（stream=True）
    """
    # 流式响应处理
    if request.stream:
        return StreamingResponse(
            stream_plan_completion(request, user_info),
            media_type="text/event-stream"
        )
    
    try:
        # 获取适配器
        adapter = get_adapter(request.model)
        model_name = request.model or adapter.default_model
        
        # 生成缓存键（如果启用缓存）
        # 注意：使用 model_name 而不是 request.model，确保缓存键与实际使用的模型一致
        # 包含用户标识符（api_key_id）以确保不同用户的缓存隔离
        cache_key = None
        if settings.CACHE_ENABLED:
            api_key_id = user_info.get('api_key_id', 'anonymous')
            cache_key = f"plan:{cache_key_generator(request.task, model_name, request.max_steps, request.temperature, api_key_id)}"
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.info("返回缓存的规划结果")
                # 即使从缓存返回，也要记录请求到数据库（用于审计跟踪）
                if user_info.get('api_key_id') is not None and user_info.get('user_id') is not None:
                    try:
                        await record_request(
                            api_key_id=user_info['api_key_id'],
                            user_id=user_info['user_id'],
                            model=cached_result.model if hasattr(cached_result, 'model') else model_name,
                            user_query=f"规划任务: {request.task[:100]}",
                            prompt_tokens=0,  # 缓存命中，无token消耗
                            completion_tokens=0,
                            total_tokens=0
                        )
                        logger.debug("缓存命中请求已记录到数据库（token=0）")
                    except Exception as e:
                        logger.error(f"记录缓存命中请求失败: {str(e)}", exc_info=True)
                return cached_result
        
        # 构建提示词
        system_prompt = build_plan_system_prompt(request.max_steps)
        user_prompt = f"请将以下任务拆分成步骤：\n\n{request.task}"
        
        # 构建消息
        messages = [
            ChatMessage(role="system", content=system_prompt),
            ChatMessage(role="user", content=user_prompt)
        ]
        
        # 调用LLM
        logger.info(f"开始规划任务: {request.task[:50]}... (model={model_name}, max_steps={request.max_steps})")
        response = await adapter.chat_completion(
            messages=messages,
            model=model_name,
            temperature=request.temperature,
            max_tokens=settings.PLAN_MAX_TOKENS
        )
        
        # 提取响应内容（使用工具函数）
        response_text = extract_response_content(response)
        logger.debug(f"LLM响应内容长度: {len(response_text)}")
        
        # 解析步骤
        steps = parse_plan_response(response_text, request.max_steps)
        logger.info(f"任务规划完成: {len(steps)}个步骤")
        
        # 构建响应
        plan_response = PlanResponse(
            task=request.task,
            steps=steps,
            total_steps=len(steps),
            model=response.model
        )
        
        # 缓存结果
        if cache_key:
            cache.set(cache_key, plan_response)
            logger.debug(f"规划结果已缓存: {cache_key[:20]}...")
        
        # 记录token消耗情况
        if user_info.get('api_key_id') is not None and user_info.get('user_id') is not None:
            try:
                usage = extract_usage_info(response)
                await record_request(
                    api_key_id=user_info['api_key_id'],
                    user_id=user_info['user_id'],
                    model=response.model,
                    user_query=f"规划任务: {request.task[:100]}",
                    prompt_tokens=usage.get('prompt_tokens', 0),
                    completion_tokens=usage.get('completion_tokens', 0),
                    total_tokens=usage.get('total_tokens', 0)
                )
                logger.debug(f"Token消耗已记录: {usage.get('total_tokens', 0)} tokens")
            except Exception as e:
                logger.error(f"记录token消耗失败: {str(e)}", exc_info=True)
        
        return plan_response
    
    except LLMServiceException:
        raise
    except ValidationException:
        raise
    except Exception as e:
        logger.error(f"任务规划失败: {str(e)}", exc_info=True)
        raise LLMServiceException(f"处理请求时发生错误: {str(e)}")
