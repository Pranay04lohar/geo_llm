"""
Chat History Models for Dynamic RAG System.

What: SQLAlchemy models for storing user chat conversations and messages
Why: Enable persistent chat history per user across sessions
How: SQLAlchemy ORM models with simple to_dict helpers
"""

from datetime import datetime
import uuid
from typing import Optional

from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    Boolean,
    ForeignKey,
)
from sqlalchemy.orm import relationship, declarative_base


# Local Base for this model module
Base = declarative_base()


class ChatConversation(Base):
    __tablename__ = "chat_conversations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(128), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, nullable=False, default=True)

    # Relationships
    messages = relationship(
        "ChatMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else str(self.created_at),
            "updated_at": self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else str(self.updated_at),
            "is_active": bool(self.is_active),
        }


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String(36), ForeignKey("chat_conversations.id"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # 'user' | 'assistant'
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    meta_data = Column(Text, nullable=True)  # JSON string (optional)

    # Relationship back to conversation
    conversation = relationship("ChatConversation", back_populates="messages")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "role": self.role,
            "content": self.content,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else str(self.created_at),
            "metadata": self.meta_data,
        }



