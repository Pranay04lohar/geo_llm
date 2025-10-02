"""
Chat History API Router (standalone service).
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from typing import List, Optional
from datetime import datetime
import json
import logging

from ..database import get_db
from ..models.chat_models import ChatConversation, ChatMessage
from auth.middleware.firebase_auth_middleware import get_current_user_uid
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()


class ChatConversationResponse(BaseModel):
    id: str
    user_id: str
    title: str
    created_at: str
    updated_at: str
    is_active: bool
    message_count: int


class ChatMessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    created_at: str
    metadata: Optional[str] = None


class CreateConversationRequest(BaseModel):
    title: str


class CreateMessageRequest(BaseModel):
    conversation_id: str
    role: str
    content: str
    metadata: Optional[dict] = None


class UpdateConversationRequest(BaseModel):
    title: Optional[str] = None
    is_active: Optional[bool] = None


@router.get(
    "/conversations",
    response_model=List[ChatConversationResponse],
    summary="Get user's chat conversations",
    description="Retrieve all chat conversations for the authenticated user, ordered by most recent first."
)
async def get_conversations(
    user_id: str = Depends(get_current_user_uid),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    try:
        result = await db.execute(
            select(ChatConversation)
            .where(ChatConversation.user_id == user_id)
            .where(ChatConversation.is_active == True)
            .order_by(desc(ChatConversation.updated_at))
            .limit(limit)
            .offset(offset)
        )
        conversations = result.scalars().all()

        response = []
        for conv in conversations:
            message_count_result = await db.execute(
                select(func.count(ChatMessage.id))
                .where(ChatMessage.conversation_id == conv.id)
            )
            message_count = message_count_result.scalar() or 0

            conv_dict = conv.to_dict()
            conv_dict["message_count"] = message_count
            response.append(ChatConversationResponse(**conv_dict))

        return response
    except Exception as e:
        logger.error(f"Error retrieving conversations for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve conversations")


@router.post(
    "/conversations",
    response_model=ChatConversationResponse,
    summary="Create new chat conversation",
    description="Create a new chat conversation for the authenticated user."
)
async def create_conversation(
    request: CreateConversationRequest,
    user_id: str = Depends(get_current_user_uid),
    db: AsyncSession = Depends(get_db)
):
    try:
        conversation = ChatConversation(
            user_id=user_id,
            title=request.title,
            is_active=True
        )

        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)

        conv_dict = conversation.to_dict()
        conv_dict["message_count"] = 0
        return ChatConversationResponse(**conv_dict)
    except Exception as e:
        logger.error(f"Error creating conversation for user {user_id}: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create conversation")


@router.get(
    "/conversations/{conversation_id}",
    response_model=ChatConversationResponse,
    summary="Get specific conversation",
    description="Retrieve a specific conversation by ID for the authenticated user."
)
async def get_conversation(
    conversation_id: str,
    user_id: str = Depends(get_current_user_uid),
    db: AsyncSession = Depends(get_db)
):
    try:
        result = await db.execute(
            select(ChatConversation)
            .where(ChatConversation.id == conversation_id)
            .where(ChatConversation.user_id == user_id)
        )
        conversation = result.scalar_one_or_none()

        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        message_count_result = await db.execute(
            select(func.count(ChatMessage.id))
            .where(ChatMessage.conversation_id == conversation_id)
        )
        message_count = message_count_result.scalar() or 0

        conv_dict = conversation.to_dict()
        conv_dict["message_count"] = message_count
        return ChatConversationResponse(**conv_dict)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving conversation {conversation_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve conversation")


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=List[ChatMessageResponse],
    summary="Get conversation messages",
    description="Retrieve all messages for a specific conversation."
)
async def get_conversation_messages(
    conversation_id: str,
    user_id: str = Depends(get_current_user_uid),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    try:
        conv_result = await db.execute(
            select(ChatConversation)
            .where(ChatConversation.id == conversation_id)
            .where(ChatConversation.user_id == user_id)
        )
        conversation = conv_result.scalar_one_or_none()

        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.conversation_id == conversation_id)
            .order_by(ChatMessage.created_at)
            .limit(limit)
            .offset(offset)
        )
        messages = result.scalars().all()

        return [ChatMessageResponse(**msg.to_dict()) for msg in messages]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving messages for conversation {conversation_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve messages")


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=ChatMessageResponse,
    summary="Add message to conversation",
    description="Add a new message to an existing conversation."
)
async def add_message(
    conversation_id: str,
    request: CreateMessageRequest,
    user_id: str = Depends(get_current_user_uid),
    db: AsyncSession = Depends(get_db)
):
    try:
        conv_result = await db.execute(
            select(ChatConversation)
            .where(ChatConversation.id == conversation_id)
            .where(ChatConversation.user_id == user_id)
        )
        conversation = conv_result.scalar_one_or_none()

        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        message = ChatMessage(
            conversation_id=conversation_id,
            role=request.role,
            content=request.content,
            meta_data=json.dumps(request.metadata) if request.metadata else None
        )

        db.add(message)
        conversation.updated_at = datetime.utcnow()

        await db.commit()
        await db.refresh(message)

        return ChatMessageResponse(**message.to_dict())
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding message to conversation {conversation_id}: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to add message")


@router.put(
    "/conversations/{conversation_id}",
    response_model=ChatConversationResponse,
    summary="Update conversation",
    description="Update conversation title or status."
)
async def update_conversation(
    conversation_id: str,
    request: UpdateConversationRequest,
    user_id: str = Depends(get_current_user_uid),
    db: AsyncSession = Depends(get_db)
):
    try:
        result = await db.execute(
            select(ChatConversation)
            .where(ChatConversation.id == conversation_id)
            .where(ChatConversation.user_id == user_id)
        )
        conversation = result.scalar_one_or_none()

        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        if request.title is not None:
            conversation.title = request.title
        if request.is_active is not None:
            conversation.is_active = request.is_active

        conversation.updated_at = datetime.utcnow()

        await db.commit()
        await db.refresh(conversation)

        message_count_result = await db.execute(
            select(func.count(ChatMessage.id))
            .where(ChatMessage.conversation_id == conversation_id)
        )
        message_count = message_count_result.scalar() or 0

        conv_dict = conversation.to_dict()
        conv_dict["message_count"] = message_count
        return ChatConversationResponse(**conv_dict)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating conversation {conversation_id}: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update conversation")


@router.delete(
    "/conversations/{conversation_id}",
    summary="Delete conversation",
    description="Soft delete a conversation (mark as inactive)."
)
async def delete_conversation(
    conversation_id: str,
    user_id: str = Depends(get_current_user_uid),
    db: AsyncSession = Depends(get_db)
):
    try:
        result = await db.execute(
            select(ChatConversation)
            .where(ChatConversation.id == conversation_id)
            .where(ChatConversation.user_id == user_id)
        )
        conversation = result.scalar_one_or_none()

        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        conversation.is_active = False
        conversation.updated_at = datetime.utcnow()

        await db.commit()
        return {"message": "Conversation deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting conversation {conversation_id}: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete conversation")


