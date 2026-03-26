import time
import uuid

from open_webui.internal.db_utils import AsyncDatabaseConnector
from open_webui.models.base import Base
from pydantic import BaseModel, ConfigDict
from sqlalchemy import JSON, BigInteger, Text, delete, select
from sqlalchemy.orm import Mapped, mapped_column

####################
# Message DB Schema
####################


class MessageReaction(Base):
    __tablename__ = "message_reaction"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    user_id: Mapped[str] = mapped_column(Text)
    message_id: Mapped[str] = mapped_column(Text)
    name: Mapped[str] = mapped_column(Text)
    created_at: Mapped[int] = mapped_column(BigInteger)


class MessageReactionModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    message_id: str
    name: str
    created_at: int  # timestamp in epoch


class Message(Base):
    __tablename__ = "message"
    id: Mapped[str] = mapped_column(Text, primary_key=True)

    user_id: Mapped[str] = mapped_column(Text)
    channel_id: Mapped[str | None] = mapped_column(Text, nullable=True)

    parent_id: Mapped[str | None] = mapped_column(Text, nullable=True)

    content: Mapped[str] = mapped_column(Text)
    data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[int] = mapped_column(BigInteger)  # time_ns
    updated_at: Mapped[int] = mapped_column(BigInteger)  # time_ns


class MessageModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    channel_id: str | None = None

    parent_id: str | None = None

    content: str
    data: dict | None = None
    meta: dict | None = None

    created_at: int  # timestamp in epoch
    updated_at: int  # timestamp in epoch


####################
# Forms
####################


class MessageForm(BaseModel):
    content: str
    parent_id: str | None = None
    data: dict | None = None
    meta: dict | None = None


class Reactions(BaseModel):
    name: str
    user_ids: list[str]
    count: int


class MessageResponse(MessageModel):
    latest_reply_at: int | None
    reply_count: int
    reactions: list[Reactions]


class MessageTable:

    __db: AsyncDatabaseConnector

    def __init__(self, db_connector: AsyncDatabaseConnector) -> None:
        self.__db = db_connector

    async def insert_new_message(
        self, form_data: MessageForm, channel_id: str, user_id: str
    ) -> MessageModel | None:
        async with self.__db.get_async_db() as db:
            id = str(uuid.uuid4())

            ts = int(time.time_ns())
            message = MessageModel(
                **{
                    "id": id,
                    "user_id": user_id,
                    "channel_id": channel_id,
                    "parent_id": form_data.parent_id,
                    "content": form_data.content,
                    "data": form_data.data,
                    "meta": form_data.meta,
                    "created_at": ts,
                    "updated_at": ts,
                }
            )

            result = Message(**message.model_dump())
            db.add(result)
            await db.commit()
            await db.refresh(result)
            return MessageModel.model_validate(result) if result else None

    async def get_message_by_id(self, id: str) -> MessageResponse | None:
        async with self.__db.get_async_db() as db:
            message = await db.get(Message, id)
            if not message:
                return None

            reactions = await self.get_reactions_by_message_id(id)
            replies = await self.get_replies_by_message_id(id)

            return MessageResponse(
                **{
                    **MessageModel.model_validate(message).model_dump(),
                    "latest_reply_at": replies[0].created_at if replies else None,
                    "reply_count": len(replies),
                    "reactions": reactions,
                }
            )

    async def get_replies_by_message_id(self, id: str) -> list[MessageModel]:
        async with self.__db.get_async_db() as db:
            all_messages = await db.scalars(
                select(Message)
                .where(Message.parent_id == id)
                .order_by(Message.created_at.desc())
            )

            return [
                MessageModel.model_validate(message) for message in all_messages.all()
            ]

    async def get_reply_user_ids_by_message_id(self, id: str) -> list[str]:
        async with self.__db.get_async_db() as db:
            ids = await db.scalars(
                select(Message.user_id).where(Message.parent_id == id)
            )
            return [id for id in ids.all()]

    async def get_messages_by_channel_id(
        self, channel_id: str, skip: int = 0, limit: int = 50
    ) -> list[MessageModel]:
        async with self.__db.get_async_db() as db:
            messages = await db.scalars(
                select(Message)
                .where(Message.channel_id == channel_id, Message.parent_id == None)
                .order_by(Message.created_at.desc())
                .offset(skip)
                .limit(limit)
            )
            return [MessageModel.model_validate(message) for message in messages.all()]

    async def get_messages_by_parent_id(
        self, channel_id: str, parent_id: str, skip: int = 0, limit: int = 50
    ) -> list[MessageModel]:
        async with self.__db.get_async_db() as db:
            parent_message = await db.get(Message, parent_id)

            if not parent_message:
                return []

            all_messages = await db.scalars(
                select(Message)
                .where(Message.channel_id == channel_id, Message.parent_id == parent_id)
                .order_by(Message.created_at.desc())
                .offset(skip)
                .limit(limit)
            )

            message_list = [
                MessageModel.model_validate(message) for message in all_messages.all()
            ]

            # If length of all_messages is less than limit, then add the parent message
            if len(message_list) < limit:
                message_list.append(MessageModel.model_validate(parent_message))

            return message_list

    async def update_message_by_id(
        self, id: str, form_data: MessageForm
    ) -> MessageModel | None:
        async with self.__db.get_async_db() as db:
            if message := await db.get(Message, id):
                message.content = form_data.content
                message.data = form_data.data
                message.meta = form_data.meta
                message.updated_at = int(time.time_ns())
                await db.commit()
                await db.refresh(message)
            return MessageModel.model_validate(message) if message else None

    async def add_reaction_to_message(
        self, id: str, user_id: str, name: str
    ) -> MessageReactionModel | None:
        async with self.__db.get_async_db() as db:
            reaction_id = str(uuid.uuid4())
            reaction = MessageReactionModel(
                id=reaction_id,
                user_id=user_id,
                message_id=id,
                name=name,
                created_at=int(time.time_ns()),
            )
            result = MessageReaction(**reaction.model_dump())
            db.add(result)
            await db.commit()
            await db.refresh(result)
            return MessageReactionModel.model_validate(result) if result else None

    async def get_reactions_by_message_id(self, id: str) -> list[Reactions]:
        async with self.__db.get_async_db() as db:
            all_reactions = await db.scalars(
                select(MessageReaction).where(MessageReaction.message_id == id)
            )

            reactions: dict[str, dict[str, str | list[str] | int]] = {}
            for reaction in all_reactions.all():
                if reaction.name not in reactions:
                    reactions[reaction.name] = {
                        "name": reaction.name,
                        "user_ids": [],
                        "count": 0,
                    }
                reactions[reaction.name]["user_ids"].append(reaction.user_id)
                reactions[reaction.name]["count"] += 1

            return [Reactions(**reaction) for reaction in reactions.values()]

    async def remove_reaction_by_id_and_user_id_and_name(
        self, id: str, user_id: str, name: str
    ) -> bool:
        async with self.__db.get_async_db() as db:
            _ = await db.execute(
                delete(MessageReaction).where(
                    MessageReaction.message_id == id,
                    MessageReaction.user_id == user_id,
                    MessageReaction.name == name,
                )
            )
            await db.commit()
            return True

    async def delete_reactions_by_id(self, id: str) -> bool:
        async with self.__db.get_async_db() as db:
            _ = await db.execute(
                delete(MessageReaction).where(
                    MessageReaction.message_id == id,
                )
            )
            await db.commit()
            return True

    async def delete_replies_by_id(self, id: str) -> bool:
        async with self.__db.get_async_db() as db:
            _ = await db.execute(
                delete(Message).where(
                    Message.parent_id == id,
                )
            )
            await db.commit()
            return True

    async def delete_message_by_id(self, id: str) -> bool:
        async with self.__db.get_async_db() as db:
            # Delete all reactions to this message
            _ = await db.execute(
                delete(MessageReaction).where(MessageReaction.message_id == id)
            )

            _ = await db.execute(delete(Message).where(Message.id == id))

            await db.commit()
            return True
