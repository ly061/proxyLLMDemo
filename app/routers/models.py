"""
模型列表路由
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from app.adapters.deepseek_adapter import DeepSeekAdapter
from app.adapters.openai_adapter import OpenAIAdapter
from app.auth.api_key import verify_api_key
from app.config import settings
from app.utils.logger import logger


router = APIRouter(prefix="/api/v1", tags=["models"])


class ModelInfo(BaseModel):
    """模型信息"""
    id: str
    object: str = "model"
    created: int = 0
    owned_by: str = ""


@router.get("/models", response_model=dict)
async def list_models(api_key: str = Depends(verify_api_key)):
    """
    获取可用模型列表
    """
    try:
        models = []
        
        # DeepSeek模型
        if settings.DEEPSEEK_API_KEY:
            deepseek_adapter = DeepSeekAdapter(
                api_key=settings.DEEPSEEK_API_KEY,
                base_url=settings.DEEPSEEK_BASE_URL,
                default_model=settings.DEEPSEEK_MODEL
            )
            deepseek_models = await deepseek_adapter.list_models()
            for model_id in deepseek_models:
                models.append({
                    "id": model_id,
                    "object": "model",
                    "created": 0,
                    "owned_by": "deepseek"
                })
        
        # OpenAI模型
        if settings.OPENAI_API_KEY:
            openai_adapter = OpenAIAdapter(
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_BASE_URL,
                default_model=settings.OPENAI_MODEL
            )
            openai_models = await openai_adapter.list_models()
            for model_id in openai_models:
                models.append({
                    "id": model_id,
                    "object": "model",
                    "created": 0,
                    "owned_by": "openai"
                })
        
        logger.info(f"返回模型列表: {len(models)} 个模型")
        
        return {
            "object": "list",
            "data": models
        }
    
    except Exception as e:
        logger.error(f"获取模型列表失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取模型列表时发生错误: {str(e)}"
        )

