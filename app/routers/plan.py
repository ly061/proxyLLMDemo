"""
任务规划路由 - 将任务拆分成步骤
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from app.adapters.base import ChatMessage
from app.auth.api_key import get_user_info
from app.config import settings
from app.utils.logger import logger
from app.utils.adapter_factory import get_adapter
from app.database.db import record_request
import json


router = APIRouter(prefix="/api/v1", tags=["plan"])


class PlanRequest(BaseModel):
    """任务规划请求"""
    task: str = Field(..., description="要拆分的任务描述")
    model: Optional[str] = Field(None, description="模型名称，如果不指定则使用默认模型")
    temperature: Optional[float] = Field(0.7, ge=0, le=2, description="温度参数")
    max_steps: Optional[int] = Field(10, ge=1, le=50, description="最大步骤数")


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


def parse_plan_response(response_text: str, max_steps: int) -> List[PlanStep]:
    """
    解析LLM返回的计划步骤
    
    Args:
        response_text: LLM返回的文本
        max_steps: 最大步骤数
        
    Returns:
        解析后的步骤列表
    """
    steps = []
    
    # 尝试解析JSON格式
    try:
        # 查找JSON部分（可能在markdown代码块中）
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            json_text = response_text[json_start:json_end].strip()
        elif "```" in response_text:
            json_start = response_text.find("```") + 3
            json_end = response_text.find("```", json_start)
            json_text = response_text[json_start:json_end].strip()
        else:
            json_text = response_text.strip()
        
        # 尝试解析JSON
        data = json.loads(json_text)
        
        # 如果返回的是字典，尝试获取steps字段
        if isinstance(data, dict):
            if "steps" in data:
                steps_data = data["steps"]
            elif "plan" in data:
                steps_data = data["plan"]
            else:
                steps_data = data
        else:
            steps_data = data
        
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
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.warning(f"JSON解析失败，尝试文本解析: {str(e)}")
        # 如果JSON解析失败，尝试文本解析
        lines = response_text.split('\n')
        step_number = 1
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 匹配步骤格式：1. 标题 或 Step 1: 标题 或 步骤1：标题
            if any(marker in line for marker in ['1.', '2.', '3.', '4.', '5.', 'Step', '步骤', 'STEP']):
                # 提取步骤内容
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
    
    # 如果仍然没有解析到步骤，创建一个默认步骤
    if not steps:
        steps.append(PlanStep(
            step_number=1,
            title="任务分析",
            description=response_text[:500] if len(response_text) > 500 else response_text
        ))
    
    return steps[:max_steps]


@router.post("/plan", response_model=PlanResponse)
async def create_plan(
    request: PlanRequest,
    user_info: dict = Depends(get_user_info)
):
    """
    任务规划接口 - 将任务拆分成步骤
    
    接收一个任务描述，使用LLM将其拆分成可执行的步骤列表
    """
    try:
        # 获取适配器
        adapter = get_adapter(request.model)
        model_name = request.model or adapter.default_model
        
        # 构建提示词
        system_prompt = """你是一个专业的任务规划助手。你的任务是将用户给出的任务拆分成清晰的步骤。

请按照以下要求：
1. 将任务拆分成3-10个具体的步骤
2. 每个步骤应该有清晰的标题和描述
3. 步骤应该按照逻辑顺序排列
4. 如果可能，为每个步骤提供预估时间

请以JSON格式返回，格式如下：
{
  "steps": [
    {
      "step_number": 1,
      "title": "步骤标题",
      "description": "步骤详细描述",
      "estimated_time": "预估时间（可选）"
    }
  ]
}

如果无法返回JSON格式，也可以使用文本格式，每行一个步骤，格式：步骤序号. 步骤标题: 步骤描述"""
        
        user_prompt = f"请将以下任务拆分成步骤：\n\n{request.task}"
        
        # 构建消息
        messages = [
            ChatMessage(role="system", content=system_prompt),
            ChatMessage(role="user", content=user_prompt)
        ]
        
        # 调用LLM
        logger.info(f"开始规划任务: {request.task[:50]}...")
        response = await adapter.chat_completion(
            messages=messages,
            model=model_name,
            temperature=request.temperature,
            max_tokens=2000  # 规划任务通常需要更多token
        )
        
        # 提取响应内容
        if not response.choices or len(response.choices) == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="LLM未返回有效响应"
            )
        
        response_text = response.choices[0].get("message", {}).get("content", "")
        if not response_text:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="LLM返回内容为空"
            )
        
        # 解析步骤
        steps = parse_plan_response(response_text, request.max_steps)
        
        # 记录token消耗情况
        if user_info.get('api_key_id') is not None and user_info.get('user_id') is not None and response.usage:
            try:
                usage = response.usage
                if isinstance(usage, dict):
                    await record_request(
                        api_key_id=user_info['api_key_id'],
                        user_id=user_info['user_id'],
                        model=response.model,
                        user_query=f"规划任务: {request.task}",
                        prompt_tokens=usage.get('prompt_tokens', 0),
                        completion_tokens=usage.get('completion_tokens', 0),
                        total_tokens=usage.get('total_tokens', 0)
                    )
            except Exception as e:
                logger.error(f"记录token消耗失败: {str(e)}")
        
        logger.info(f"任务规划完成: {len(steps)}个步骤")
        
        return PlanResponse(
            task=request.task,
            steps=steps,
            total_steps=len(steps),
            model=response.model
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"任务规划失败: {str(e)}", exc_info=True)
        from app.exceptions import LLMServiceException
        raise LLMServiceException(f"处理请求时发生错误: {str(e)}")

