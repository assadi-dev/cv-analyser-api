"""ChatMessage ORM model — one turn inside a chat conversation."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.chat_conversation import ChatConversation


class ChatMessage(BaseModel):
    """
    A single message in a conversation.

    `seq` — not `created_at` — is the ordering key: TimestampMixin uses
    server_default=func.now(), which in Postgres is the transaction start time,
    so the question and its answer would carry identical timestamps. The UUIDv4
    primary key is not sortable either, which would leave the transcript order
    undefined.

    There is deliberately no user_id here: ownership is resolved once, on the
    conversation, and every message query goes through that gate.
    """

    __tablename__ = "chat_messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    seq: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="0-based position of the message inside its conversation",
    )
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="user | assistant"
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_partial: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        comment="True when the client disconnected before the answer was complete",
    )

    conversation: Mapped["ChatConversation"] = relationship(
        "ChatConversation", back_populates="messages"
    )

    __table_args__ = (
        UniqueConstraint("conversation_id", "seq", name="uq_chat_messages_conv_seq"),
        Index("ix_chat_messages_conversation_seq", "conversation_id", "seq"),
    )

    def __repr__(self) -> str:
        return f"<ChatMessage id={self.id} seq={self.seq} role={self.role}>"
