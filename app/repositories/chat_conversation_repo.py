"""
Repository for chat conversations and their messages.

Messages are never manipulated outside of a conversation, so both live in this
single repository: the conversation is the aggregate root and the only place
where ownership is checked.
"""

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.chat_conversation import ChatConversation
from app.models.chat_message import ChatMessage
from app.repositories.base import BaseRepository


class ChatConversationRepository(BaseRepository[ChatConversation]):
    """Persistence for ChatConversation + ChatMessage."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(ChatConversation, db)

    # -------------------------------------------------------------------------
    # Conversations
    # -------------------------------------------------------------------------
    async def get_for_user(
        self, conversation_id: uuid.UUID, user_id: uuid.UUID
    ) -> ChatConversation | None:
        """
        Fetches a conversation owned by the user.

        This is the ONLY authorization gate for the whole feature — never use
        the inherited get_by_id, which has no ownership filter.
        """
        result = await self.db.execute(
            select(ChatConversation).where(
                ChatConversation.id == conversation_id,
                ChatConversation.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_for_user_with_messages(
        self, conversation_id: uuid.UUID, user_id: uuid.UUID
    ) -> ChatConversation | None:
        """Same as get_for_user, with the messages eagerly loaded (ordered by seq)."""
        result = await self.db.execute(
            select(ChatConversation)
            .where(
                ChatConversation.id == conversation_id,
                ChatConversation.user_id == user_id,
            )
            .options(selectinload(ChatConversation.messages))
        )
        return result.scalar_one_or_none()

    async def list_for_user(
        self,
        user_id: uuid.UUID,
        *,
        include_archived: bool = False,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[ChatConversation], int]:
        """Most recently active conversations first."""
        filters: list[Any] = [ChatConversation.user_id == user_id]
        if not include_archived:
            filters.append(ChatConversation.is_archived.is_(False))

        return await self.list_all(
            filters=filters,
            order_by=ChatConversation.last_message_at.desc(),
            offset=offset,
            limit=limit,
        )

    async def touch(
        self,
        conversation: ChatConversation,
        *,
        message_delta: int = 1,
    ) -> ChatConversation:
        """Bumps last_message_at and message_count. Does not commit."""
        conversation.last_message_at = func.now()
        conversation.message_count = (conversation.message_count or 0) + message_delta
        await self.db.flush()
        await self.db.refresh(conversation)
        return conversation

    async def apply_update(
        self,
        conversation: ChatConversation,
        *,
        title: str | None = None,
        is_archived: bool | None = None,
    ) -> ChatConversation:
        """
        Applies a PATCH.

        Assigns attributes directly instead of using BaseRepository.update,
        which skips None values and would therefore be unable to distinguish
        "not provided" from a real value in a partial update.
        """
        if title is not None:
            conversation.title = title
        if is_archived is not None:
            conversation.is_archived = is_archived

        await self.db.flush()
        await self.db.refresh(conversation)
        return conversation

    # -------------------------------------------------------------------------
    # Messages
    # -------------------------------------------------------------------------
    async def next_seq(self, conversation_id: uuid.UUID) -> int:
        """Next free position in the conversation (0 when it is empty)."""
        result = await self.db.execute(
            select(func.coalesce(func.max(ChatMessage.seq), -1) + 1).where(
                ChatMessage.conversation_id == conversation_id
            )
        )
        return int(result.scalar_one())

    async def add_message(
        self,
        conversation_id: uuid.UUID,
        *,
        role: str,
        content: str,
        is_partial: bool = False,
        message_id: uuid.UUID | None = None,
    ) -> ChatMessage:
        """
        Appends a message at the next free seq. Does not commit.

        message_id lets the caller pick the primary key in advance — the
        streaming path needs it, since every SSE frame carries the id of the
        message being written while the row is only inserted at the end. Same
        uuid4 the model would have generated at flush time, so no extra
        collision risk; the primary key still rejects a double insert.
        """
        message = ChatMessage(
            conversation_id=conversation_id,
            seq=await self.next_seq(conversation_id),
            role=role,
            content=content,
            is_partial=is_partial,
        )
        if message_id is not None:
            message.id = message_id
        self.db.add(message)
        await self.db.flush()
        await self.db.refresh(message)
        return message

    async def list_messages(
        self,
        conversation_id: uuid.UUID,
        *,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[ChatMessage], int]:
        """Chronological page of messages, ordered by seq."""
        query = (
            select(ChatMessage)
            .where(ChatMessage.conversation_id == conversation_id)
            .order_by(ChatMessage.seq.asc())
            .offset(offset)
            .limit(limit)
        )
        count_query = (
            select(func.count())
            .select_from(ChatMessage)
            .where(ChatMessage.conversation_id == conversation_id)
        )

        items_result = await self.db.execute(query)
        count_result = await self.db.execute(count_query)

        return list(items_result.scalars().all()), count_result.scalar_one()

    async def recent_messages(
        self,
        conversation_id: uuid.UUID,
        *,
        limit: int,
        before_seq: int | None = None,
    ) -> list[ChatMessage]:
        """
        The last `limit` messages, returned in ascending seq order.

        Used to build the prompt window: the whole transcript is injected into
        the system prompt alongside the CV and the job offer, so it has to be
        bounded. `before_seq` excludes the turn currently being answered.
        """
        query = select(ChatMessage).where(ChatMessage.conversation_id == conversation_id)
        if before_seq is not None:
            query = query.where(ChatMessage.seq < before_seq)

        result = await self.db.execute(
            query.order_by(ChatMessage.seq.desc()).limit(limit)
        )
        return list(reversed(result.scalars().all()))
