"""
模型列表路由
"""
from typing import List
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.auth.api_key import verify_api_key
from app.config import settings
from app.utils.logger import logger
from app.utils.adapter_factory import get_adapter
from app.exceptions import LLMServiceException


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
            try:
                deepseek_adapter = get_adapter("deepseek-chat")
                deepseek_models = await deepseek_adapter.list_models()
                for model_id in deepseek_models:
                    models.append({
                        "id": model_id,
                        "object": "model",
                        "created": 0,
                        "owned_by": "deepseek"
                    })
            except Exception as e:
                logger.warning(f"获取DeepSeek模型列表失败: {str(e)}")
        
        # OpenAI模型
        if settings.OPENAI_API_KEY:
            try:
                openai_adapter = get_adapter("gpt-3.5-turbo")
                openai_models = await openai_adapter.list_models()
                for model_id in openai_models:
                    models.append({
                        "id": model_id,
                        "object": "model",
                        "created": 0,
                        "owned_by": "openai"
                    })
            except Exception as e:
                logger.warning(f"获取OpenAI模型列表失败: {str(e)}")
        
        logger.info(f"返回模型列表: {len(models)} 个模型")
        
        return {
            "object": "list",
            "data": models
        }
    
    except Exception as e:
        logger.error(f"获取模型列表失败: {str(e)}", exc_info=True)
        raise LLMServiceException(f"获取模型列表时发生错误: {str(e)}")

