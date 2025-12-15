"""
会话管理路由
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from app.auth.api_key import get_user_info
from app.database.db import (
    create_conversation,
    get_conversation,
    get_conversation_messages,
    update_conversation_title,
    delete_conversation,
    list_conversations
)
from app.utils.logger import logger


router = APIRouter(prefix="/api/v1", tags=["conversations"])


class CreateConversationRequest(BaseModel):
    """创建会话请求"""
    title: Optional[str] = Field(None, description="会话标题，如果不提供则自动生成")


class ConversationResponse(BaseModel):
    """会话响应"""
    conversation_id: int
    title: str
    created_at: str
    updated_at: Optional[str] = None


class ConversationDetailResponse(BaseModel):
    """会话详情响应"""
    conversation_id: int
    title: str
    created_at: str
    updated_at: str
    messages: List[dict]


class ConversationListResponse(BaseModel):
    """会话列表响应"""
    conversations: List[dict]
    total: int


class UpdateConversationRequest(BaseModel):
    """更新会话请求"""
    title: str = Field(..., description="新标题")


class DeleteConversationResponse(BaseModel):
    """删除会话响应"""
    success: bool
    message: str


@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation_endpoint(
    request: CreateConversationRequest,
    user_info: dict = Depends(get_user_info)
):
    """
    创建新会话
    """
    try:
        user_id = user_info.get('user_id')
        api_key_id = user_info.get('api_key_id')
        
        if not user_id or not api_key_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户信息不完整"
            )
        
        # 如果没有提供标题，使用默认标题
        title = request.title or "新对话"
        
        conversation_id = await create_conversation(
            user_id=user_id,
            api_key_id=api_key_id,
            title=title
        )
        
        # 获取创建的会话信息
        conversation = await get_conversation(conversation_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="创建会话失败"
            )
        
        logger.info(f"创建会话成功: conversation_id={conversation_id}, user_id={user_id}")
        
        return ConversationResponse(
            conversation_id=conversation['id'],
            title=conversation['title'],
            created_at=conversation['created_at'].isoformat() if conversation['created_at'] else "",
            updated_at=conversation['updated_at'].isoformat() if conversation.get('updated_at') else None
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建会话失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建会话失败: {str(e)}"
        )


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations_endpoint(
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    user_info: dict = Depends(get_user_info)
):
    """
    获取会话列表
    """
    try:
        user_id = user_info.get('user_id')
        api_key_id = user_info.get('api_key_id')
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户信息不完整"
            )
        
        conversations, total = await list_conversations(
            user_id=user_id,
            api_key_id=api_key_id,
            limit=limit,
            offset=offset
        )
        
        # 格式化响应
        formatted_conversations = []
        for conv in conversations:
            formatted_conversations.append({
                "conversation_id": conv['conversation_id'],
                "title": conv['title'],
                "created_at": conv['created_at'].isoformat() if conv['created_at'] else "",
                "updated_at": conv['updated_at'].isoformat() if conv.get('updated_at') else "",
                "message_count": conv['message_count']
            })
        
        return ConversationListResponse(
            conversations=formatted_conversations,
            total=total
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取会话列表失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取会话列表失败: {str(e)}"
        )


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation_endpoint(
    conversation_id: int,
    user_info: dict = Depends(get_user_info)
):
    """
    获取会话详情（包含所有消息）
    """
    try:
        user_id = user_info.get('user_id')
        api_key_id = user_info.get('api_key_id')
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户信息不完整"
            )
        
        # 获取会话信息（带权限验证）
        conversation = await get_conversation(
            conversation_id=conversation_id,
            user_id=user_id,
            api_key_id=api_key_id
        )
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="会话不存在或无权访问"
            )
        
        # 获取会话的所有消息
        messages = await get_conversation_messages(conversation_id)
        
        # 格式化消息
        formatted_messages = []
        for msg in messages:
            formatted_messages.append({
                "role": msg['role'],
                "content": msg['content'],
                "created_at": msg['created_at'].isoformat() if msg['created_at'] else ""
            })
        
        return ConversationDetailResponse(
            conversation_id=conversation['id'],
            title=conversation['title'],
            created_at=conversation['created_at'].isoformat() if conversation['created_at'] else "",
            updated_at=conversation['updated_at'].isoformat() if conversation.get('updated_at') else "",
            messages=formatted_messages
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取会话详情失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取会话详情失败: {str(e)}"
        )


@router.patch("/conversations/{conversation_id}", response_model=ConversationResponse)
async def update_conversation_endpoint(
    conversation_id: int,
    request: UpdateConversationRequest,
    user_info: dict = Depends(get_user_info)
):
    """
    更新会话标题
    """
    try:
        user_id = user_info.get('user_id')
        api_key_id = user_info.get('api_key_id')
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户信息不完整"
            )
        
        # 更新标题
        success = await update_conversation_title(
            conversation_id=conversation_id,
            title=request.title,
            user_id=user_id,
            api_key_id=api_key_id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="会话不存在或无权访问"
            )
        
        # 获取更新后的会话信息
        conversation = await get_conversation(conversation_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="会话不存在"
            )
        
        logger.info(f"更新会话标题成功: conversation_id={conversation_id}")
        
        return ConversationResponse(
            conversation_id=conversation['id'],
            title=conversation['title'],
            created_at=conversation['created_at'].isoformat() if conversation['created_at'] else "",
            updated_at=conversation['updated_at'].isoformat() if conversation.get('updated_at') else None
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新会话标题失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新会话标题失败: {str(e)}"
        )


@router.delete("/conversations/{conversation_id}", response_model=DeleteConversationResponse)
async def delete_conversation_endpoint(
    conversation_id: int,
    user_info: dict = Depends(get_user_info)
):
    """
    删除会话（级联删除所有消息）
    """
    try:
        user_id = user_info.get('user_id')
        api_key_id = user_info.get('api_key_id')
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户信息不完整"
            )
        
        # 删除会话
        success = await delete_conversation(
            conversation_id=conversation_id,
            user_id=user_id,
            api_key_id=api_key_id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="会话不存在或无权访问"
            )
        
        logger.info(f"删除会话成功: conversation_id={conversation_id}")
        
        return DeleteConversationResponse(
            success=True,
            message="会话已删除"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除会话失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除会话失败: {str(e)}"
        )

