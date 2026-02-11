import time
import uuid
import logging

from open_webui.env import SRC_LOG_LEVELS
from open_webui.internal.db import get_async_db
from open_webui.models.base import Base
from open_webui.models.tags import TagModel, Tags

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Boolean, String, Text, JSON
from sqlalchemy import delete, func, or_, and_, select, text, update
from sqlalchemy.orm import Mapped, mapped_column

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

####################
# Chat DB Schema
####################


class Chat(Base):
    __tablename__ = "chat"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(Text)
    chat: Mapped[dict] = mapped_column(JSON)

    created_at: Mapped[int] = mapped_column(BigInteger)
    updated_at: Mapped[int] = mapped_column(BigInteger)

    share_id: Mapped[str | None] = mapped_column(Text, unique=True, nullable=True)
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    pinned: Mapped[bool | None] = mapped_column(Boolean, default=False, nullable=True)

    meta: Mapped[dict] = mapped_column(JSON, server_default="{}")
    folder_id: Mapped[str | None] = mapped_column(Text, nullable=True)


class ChatModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    title: str
    chat: dict

    created_at: int  # timestamp in epoch
    updated_at: int  # timestamp in epoch

    share_id: str | None = None
    archived: bool = False
    pinned: bool | None = False

    meta: dict = {}
    folder_id: str | None = None


####################
# Forms
####################


class ChatForm(BaseModel):
    chat: dict


class ChatImportForm(ChatForm):
    meta: dict | None = {}
    pinned: bool | None = False
    folder_id: str | None = None


class ChatTitleMessagesForm(BaseModel):
    title: str
    messages: list[dict]


class ChatTitleForm(BaseModel):
    title: str


class ChatResponse(BaseModel):
    id: str
    user_id: str
    title: str
    chat: dict
    updated_at: int  # timestamp in epoch
    created_at: int  # timestamp in epoch
    share_id: str | None = None  # id of the chat to be shared
    archived: bool
    pinned: bool | None = False
    meta: dict = {}
    folder_id: str | None = None


class ChatTitleIdResponse(BaseModel):
    id: str
    title: str
    updated_at: int
    created_at: int


class ChatTable:
    async def insert_new_chat(
        self, user_id: str, form_data: ChatForm
    ) -> ChatModel | None:
        async with get_async_db() as db:
            id = str(uuid.uuid4())
            chat = ChatModel(
                **{
                    "id": id,
                    "user_id": user_id,
                    "title": (
                        form_data.chat["title"]
                        if "title" in form_data.chat
                        else "New Chat"
                    ),
                    "chat": form_data.chat,
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )

            result = Chat(**chat.model_dump())
            db.add(result)
            await db.commit()
            await db.refresh(result)
            return ChatModel.model_validate(result) if result else None

    async def import_chat(
        self, user_id: str, form_data: ChatImportForm
    ) -> ChatModel | None:
        async with get_async_db() as db:
            id = str(uuid.uuid4())
            chat = ChatModel(
                **{
                    "id": id,
                    "user_id": user_id,
                    "title": (
                        form_data.chat["title"]
                        if "title" in form_data.chat
                        else "New Chat"
                    ),
                    "chat": form_data.chat,
                    "meta": form_data.meta,
                    "pinned": form_data.pinned,
                    "folder_id": form_data.folder_id,
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )

            result = Chat(**chat.model_dump())
            db.add(result)
            await db.commit()
            await db.refresh(result)
            return ChatModel.model_validate(result) if result else None

    async def update_chat_by_id(self, id: str, chat: dict) -> ChatModel | None:
        try:
            async with get_async_db() as db:
                if chat_item := await db.get(Chat, id):
                    chat_item.chat = chat
                    chat_item.title = chat["title"] if "title" in chat else "New Chat"
                    chat_item.updated_at = int(time.time())
                    await db.commit()
                    await db.refresh(chat_item)

                    return ChatModel.model_validate(chat_item)
                return None
        except Exception:
            return None

    async def update_chat_title_by_id(self, id: str, title: str) -> ChatModel | None:
        chat = await self.get_chat_by_id(id)
        if chat is None:
            return None

        chat = chat.chat
        chat["title"] = title

        return await self.update_chat_by_id(id, chat)

    async def update_chat_tags_by_id(
        self, id: str, tags: list[str], user
    ) -> ChatModel | None:
        chat = await self.get_chat_by_id(id)
        if chat is None:
            return None

        _ = await self.delete_all_tags_by_id_and_user_id(id, user.id)

        for tag in chat.meta.get("tags", []):
            if await self.count_chats_by_tag_name_and_user_id(tag, user.id) == 0:
                _ = await Tags.delete_tag_by_name_and_user_id(tag, user.id)

        for tag_name in tags:
            if tag_name.lower() == "none":
                continue

            _ = await self.add_chat_tag_by_id_and_user_id_and_tag_name(
                id, user.id, tag_name
            )
        return await self.get_chat_by_id(id)

    async def get_chat_title_by_id(self, id: str) -> str | None:
        chat = await self.get_chat_by_id(id)
        if chat is None:
            return None

        return chat.chat.get("title", "New Chat")

    async def get_messages_by_chat_id(self, id: str) -> dict | None:
        chat = await self.get_chat_by_id(id)
        if chat is None:
            return None

        return chat.chat.get("history", {}).get("messages", {}) or {}

    async def get_message_by_id_and_message_id(
        self, id: str, message_id: str
    ) -> dict | None:
        chat = await self.get_chat_by_id(id)
        if chat is None:
            return None

        return chat.chat.get("history", {}).get("messages", {}).get(message_id, {})

    async def upsert_message_to_chat_by_id_and_message_id(
        self, id: str, message_id: str, message: dict
    ) -> ChatModel | None:
        chat = await self.get_chat_by_id(id)
        if chat is None:
            return None

        chat = chat.chat
        history = chat.get("history", {})

        if message_id in history.get("messages", {}):
            history["messages"][message_id] = {
                **history["messages"][message_id],
                **message,
            }
        else:
            history["messages"][message_id] = message

        history["currentId"] = message_id

        chat["history"] = history
        return await self.update_chat_by_id(id, chat)

    async def add_message_status_to_chat_by_id_and_message_id(
        self, id: str, message_id: str, status: dict
    ) -> ChatModel | None:
        chat = await self.get_chat_by_id(id)
        if chat is None:
            return None

        chat = chat.chat
        history = chat.get("history", {})

        if message_id in history.get("messages", {}):
            status_history = history["messages"][message_id].get("statusHistory", [])
            status_history.append(status)
            history["messages"][message_id]["statusHistory"] = status_history

        chat["history"] = history
        return await self.update_chat_by_id(id, chat)

    async def insert_shared_chat_by_chat_id(self, chat_id: str) -> ChatModel | None:
        async with get_async_db() as db:
            # Get the existing chat to share
            if chat := await db.get(Chat, chat_id):
                # Check if the chat is already shared
                if chat.share_id:
                    return await self.get_chat_by_id_and_user_id(
                        chat.share_id, "shared"
                    )
                # Create a new chat with the same data, but with a new ID
                shared_chat = ChatModel(
                    **{
                        "id": str(uuid.uuid4()),
                        "user_id": f"shared-{chat_id}",
                        "title": chat.title,
                        "chat": chat.chat,
                        "created_at": chat.created_at,
                        "updated_at": int(time.time()),
                    }
                )
                shared_result = Chat(**shared_chat.model_dump())
                db.add(shared_result)
                await db.commit()
                await db.refresh(shared_result)

                # Update the original chat with the share_id
                chat.share_id = shared_chat.id
                await db.commit()
                await db.refresh(chat)
                return shared_chat if (shared_result and chat) else None
            return None

    async def update_shared_chat_by_chat_id(self, chat_id: str) -> ChatModel | None:
        try:
            async with get_async_db() as db:
                if chat := await db.get(Chat, chat_id):
                    shared_chat = await db.scalar(
                        select(Chat).where(Chat.user_id == f"shared-{chat_id}")
                    )

                    if shared_chat is None:
                        return await self.insert_shared_chat_by_chat_id(chat_id)

                    shared_chat.title = chat.title
                    shared_chat.chat = chat.chat

                    shared_chat.updated_at = int(time.time())
                    await db.commit()
                    await db.refresh(shared_chat)

                    return ChatModel.model_validate(shared_chat)
                return None
        except Exception:
            return None

    async def delete_shared_chat_by_chat_id(self, chat_id: str) -> bool:
        try:
            async with get_async_db() as db:
                _ = await db.execute(
                    delete(Chat).where(Chat.user_id == f"shared-{chat_id}")
                )
                await db.commit()

                return True
        except Exception:
            return False

    async def update_chat_share_id_by_id(
        self, id: str, share_id: str | None
    ) -> ChatModel | None:
        try:
            async with get_async_db() as db:
                if chat := await db.get(Chat, id):
                    chat.share_id = share_id
                    chat.updated_at = int(time.time())

                    await db.commit()
                    await db.refresh(chat)
                    return ChatModel.model_validate(chat)
                return None
        except Exception:
            return None

    async def toggle_chat_pinned_by_id(self, id: str) -> ChatModel | None:
        try:
            async with get_async_db() as db:
                if chat := await db.get(Chat, id):
                    chat.pinned = not chat.pinned
                    chat.updated_at = int(time.time())
                    await db.commit()
                    await db.refresh(chat)
                    return ChatModel.model_validate(chat)
                return None
        except Exception:
            return None

    async def toggle_chat_archive_by_id(self, id: str) -> ChatModel | None:
        try:
            async with get_async_db() as db:
                if chat := await db.get(Chat, id):
                    chat.archived = not chat.archived
                    chat.updated_at = int(time.time())
                    await db.commit()
                    await db.refresh(chat)
                    return ChatModel.model_validate(chat)
                return None
        except Exception:
            return None

    async def archive_all_chats_by_user_id(self, user_id: str) -> bool:
        try:
            async with get_async_db() as db:
                _ = await db.execute(
                    update(Chat).where(Chat.user_id == user_id).values(archived=True)
                )
                await db.commit()
                return True
        except Exception:
            return False

    async def get_archived_chat_list_by_user_id(
        self, user_id: str, skip: int = 0, limit: int = 50
    ) -> list[ChatModel]:
        async with get_async_db() as db:
            all_chats = (
                await (
                    db.scalars(
                        select(Chat)
                        .where(Chat.user_id == user_id, Chat.archived == True)
                        .order_by(Chat.updated_at.desc())
                    )
                    # .limit(limit).offset(skip)
                )
            )
            return [ChatModel.model_validate(chat) for chat in all_chats.all()]

    async def get_chat_list_by_user_id(
        self,
        user_id: str,
        include_archived: bool = False,
        skip: int = 0,
        limit: int = 50,
    ) -> list[ChatModel]:
        async with get_async_db() as db:
            query = select(Chat).where(Chat.user_id == user_id)
            if not include_archived:
                query = query.where(Chat.archived == False)

            query = query.order_by(Chat.updated_at.desc())

            if skip:
                query = query.offset(skip)
            if limit:
                query = query.limit(limit)

            all_chats = await db.scalars(query)
            return [ChatModel.model_validate(chat) for chat in all_chats.all()]

    async def get_chat_title_id_list_by_user_id(
        self,
        user_id: str,
        include_archived: bool = False,
        skip: int | None = None,
        limit: int | None = None,
    ) -> list[ChatTitleIdResponse]:
        async with get_async_db() as db:
            query = select(Chat.id, Chat.title, Chat.updated_at, Chat.created_at).where(
                Chat.user_id == user_id, Chat.folder_id == None
            )
            query = query.where(or_(Chat.pinned == False, Chat.pinned == None))

            if not include_archived:
                query = query.filter_by(archived=False)

            query = query.order_by(Chat.updated_at.desc())

            if skip:
                query = query.offset(skip)
            if limit:
                query = query.limit(limit)

            all_chats = await db.execute(query)

            return [
                ChatTitleIdResponse.model_validate(
                    {
                        "id": id,
                        "title": title,
                        "updated_at": updated_at,
                        "created_at": created_at,
                    }
                )
                for id, title, updated_at, created_at in all_chats.all()
            ]

    async def get_chat_list_by_chat_ids(
        self, chat_ids: list[str], skip: int = 0, limit: int = 50
    ) -> list[ChatModel]:
        async with get_async_db() as db:
            all_chats = await db.scalars(
                select(Chat)
                .where(Chat.id.in_(chat_ids), Chat.archived == False)
                .order_by(Chat.updated_at.desc())
            )
            return [ChatModel.model_validate(chat) for chat in all_chats.all()]

    async def get_chat_by_id(self, id: str) -> ChatModel | None:
        try:
            async with get_async_db() as db:
                chat = await db.get(Chat, id)
                return ChatModel.model_validate(chat)
        except Exception:
            return None

    async def get_chat_by_share_id(self, id: str) -> ChatModel | None:
        try:
            async with get_async_db() as db:
                # it is possible that the shared link was deleted. hence,
                # we check if the chat is still shared by checkng if a chat with the share_id exists
                chat = await db.scalar(select(Chat).where(Chat.share_id == id))

                return ChatModel.model_validate(chat) if chat else None
        except Exception:
            return None

    async def get_chat_by_id_and_user_id(
        self, id: str, user_id: str
    ) -> ChatModel | None:
        try:
            async with get_async_db() as db:
                if chat := await db.scalar(
                    select(Chat).where(Chat.id == id, Chat.user_id == user_id)
                ):
                    return ChatModel.model_validate(chat)
                return None
        except Exception:
            return None

    async def get_chats(self, skip: int = 0, limit: int = 50) -> list[ChatModel]:
        async with get_async_db() as db:
            all_chats = await db.scalars(
                select(Chat)
                # .limit(limit).offset(skip)
                .order_by(Chat.updated_at.desc())
            )
            return [ChatModel.model_validate(chat) for chat in all_chats.all()]

    async def get_chats_by_user_id(self, user_id: str) -> list[ChatModel]:
        async with get_async_db() as db:
            all_chats = await db.scalars(
                select(Chat)
                .where(Chat.user_id == user_id)
                .order_by(Chat.updated_at.desc())
            )
            return [ChatModel.model_validate(chat) for chat in all_chats.all()]

    async def get_pinned_chats_by_user_id(self, user_id: str) -> list[ChatModel]:
        async with get_async_db() as db:
            all_chats = await db.scalars(
                select(Chat)
                .where(
                    Chat.user_id == user_id, Chat.pinned == True, Chat.archived == False
                )
                .order_by(Chat.updated_at.desc())
            )
            return [ChatModel.model_validate(chat) for chat in all_chats.all()]

    async def get_archived_chats_by_user_id(self, user_id: str) -> list[ChatModel]:
        async with get_async_db() as db:
            all_chats = await db.scalars(
                select(Chat)
                .where(Chat.user_id == user_id, Chat.archived == True)
                .order_by(Chat.updated_at.desc())
            )
            return [ChatModel.model_validate(chat) for chat in all_chats.all()]

    async def get_chats_by_user_id_and_search_text(
        self,
        user_id: str,
        search_text: str,
        include_archived: bool = False,
        skip: int = 0,
        limit: int = 60,
    ) -> list[ChatModel]:
        """
        Filters chats based on a search query using Python, allowing pagination using skip and limit.
        """
        search_text = search_text.lower().strip()

        if not search_text:
            return await self.get_chat_list_by_user_id(
                user_id, include_archived, skip, limit
            )

        search_text_words = search_text.split(" ")

        # search_text might contain 'tag:tag_name' format so we need to extract the tag_name, split the search_text and remove the tags
        tag_ids = [
            word.replace("tag:", "").replace(" ", "_").lower()
            for word in search_text_words
            if word.startswith("tag:")
        ]

        search_text_words = [
            word for word in search_text_words if not word.startswith("tag:")
        ]

        search_text = " ".join(search_text_words)

        async with get_async_db() as db:
            query = select(Chat).where(Chat.user_id == user_id)

            if not include_archived:
                query = query.filter(Chat.archived == False)

            query = query.order_by(Chat.updated_at.desc())

            # Check if the database dialect is either 'sqlite' or 'postgresql'
            dialect_name = db.bind.dialect.name
            if dialect_name == "sqlite":
                # SQLite case: using JSON1 extension for JSON searching
                query = query.filter(
                    (Chat.title.ilike(f"%{search_text}%") | text("""
                            EXISTS (
                                SELECT 1
                                FROM json_each(Chat.chat, '$.messages') AS message
                                WHERE LOWER(message.value->>'content') LIKE '%' || :search_text || '%'
                            )
                            """)).params(  # Case-insensitive search in title
                        search_text=search_text
                    )
                )

                # Check if there are any tags to filter, it should have all the tags
                if "none" in tag_ids:
                    query = query.filter(text("""
                            NOT EXISTS (
                                SELECT 1
                                FROM json_each(Chat.meta, '$.tags') AS tag
                            )
                            """))
                elif tag_ids:
                    query = query.filter(
                        and_(
                            *[
                                text(f"""
                                    EXISTS (
                                        SELECT 1
                                        FROM json_each(Chat.meta, '$.tags') AS tag
                                        WHERE tag.value = :tag_id_{tag_idx}
                                    )
                                    """).params(**{f"tag_id_{tag_idx}": tag_id})
                                for tag_idx, tag_id in enumerate(tag_ids)
                            ]
                        )
                    )

            elif dialect_name == "postgresql":
                # PostgreSQL relies on proper JSON query for search
                query = query.filter(
                    (Chat.title.ilike(f"%{search_text}%") | text("""
                            EXISTS (
                                SELECT 1
                                FROM json_array_elements(Chat.chat->'messages') AS message
                                WHERE LOWER(message->>'content') LIKE '%' || :search_text || '%'
                            )
                            """)).params(  # Case-insensitive search in title
                        search_text=search_text
                    )
                )

                # Check if there are any tags to filter, it should have all the tags
                if "none" in tag_ids:
                    query = query.filter(text("""
                            NOT EXISTS (
                                SELECT 1
                                FROM json_array_elements_text(Chat.meta->'tags') AS tag
                            )
                            """))
                elif tag_ids:
                    query = query.filter(
                        and_(
                            *[
                                text(f"""
                                    EXISTS (
                                        SELECT 1
                                        FROM json_array_elements_text(Chat.meta->'tags') AS tag
                                        WHERE tag = :tag_id_{tag_idx}
                                    )
                                    """).params(**{f"tag_id_{tag_idx}": tag_id})
                                for tag_idx, tag_id in enumerate(tag_ids)
                            ]
                        )
                    )
            else:
                raise NotImplementedError(
                    f"Unsupported dialect: {db.bind.dialect.name}"
                )

            # Perform pagination at the SQL level
            all_chats = await db.scalars(query.offset(skip).limit(limit))

            # Validate and return chats
            return [ChatModel.model_validate(chat) for chat in all_chats.all()]

    async def get_chats_by_folder_id_and_user_id(
        self, folder_id: str, user_id: str
    ) -> list[ChatModel]:
        async with get_async_db() as db:
            query = select(Chat).where(
                Chat.folder_id == folder_id, Chat.user_id == user_id
            )
            query = query.where(or_(Chat.pinned == False, Chat.pinned == None))
            query = query.where(Chat.archived == False)

            query = query.order_by(Chat.updated_at.desc())

            all_chats = await db.scalars(query)
            return [ChatModel.model_validate(chat) for chat in all_chats.all()]

    async def get_chats_by_folder_ids_and_user_id(
        self, folder_ids: list[str], user_id: str
    ) -> list[ChatModel]:
        async with get_async_db() as db:
            query = select(Chat).where(
                Chat.folder_id.in_(folder_ids), Chat.user_id == user_id
            )
            query = query.where(or_(Chat.pinned == False, Chat.pinned == None))
            query = query.where(Chat.archived == False)

            query = query.order_by(Chat.updated_at.desc())

            all_chats = await db.scalars(query)
            return [ChatModel.model_validate(chat) for chat in all_chats.all()]

    async def update_chat_folder_id_by_id_and_user_id(
        self, id: str, user_id: str, folder_id: str
    ) -> ChatModel | None:
        try:
            async with get_async_db() as db:
                if chat := await db.get(Chat, id):
                    chat.folder_id = folder_id
                    chat.updated_at = int(time.time())
                    chat.pinned = False
                    await db.commit()
                    await db.refresh(chat)
                    return ChatModel.model_validate(chat)
                return None
        except Exception:
            return None

    async def get_chat_tags_by_id_and_user_id(
        self, id: str, user_id: str
    ) -> list[TagModel]:
        async with get_async_db() as db:
            if chat := await db.get(Chat, id):
                tags: list[str] = chat.meta.get("tags", [])
                return [
                    (await Tags.get_tag_by_name_and_user_id(tag, user_id))
                    for tag in tags
                    if tag
                ]
            return []

    async def get_chat_list_by_user_id_and_tag_name(
        self, user_id: str, tag_name: str, skip: int = 0, limit: int = 50
    ) -> list[ChatModel]:
        async with get_async_db() as db:
            query = select(Chat).where(Chat.user_id == user_id)
            tag_id = tag_name.replace(" ", "_").lower()

            print(db.bind.dialect.name)
            if db.bind.dialect.name == "sqlite":
                # SQLite JSON1 querying for tags within the meta JSON field
                query = query.filter(
                    text(
                        "EXISTS (SELECT 1 FROM json_each(Chat.meta, '$.tags') WHERE json_each.value = :tag_id)"
                    )
                ).params(tag_id=tag_id)
            elif db.bind.dialect.name == "postgresql":
                # PostgreSQL JSON query for tags within the meta JSON field (for `json` type)
                query = query.filter(
                    text(
                        "EXISTS (SELECT 1 FROM json_array_elements_text(Chat.meta->'tags') elem WHERE elem = :tag_id)"
                    )
                ).params(tag_id=tag_id)
            else:
                raise NotImplementedError(
                    f"Unsupported dialect: {db.bind.dialect.name}"
                )

            all_chats = await db.scalars(query)
            return [ChatModel.model_validate(chat) for chat in all_chats.all()]

    async def add_chat_tag_by_id_and_user_id_and_tag_name(
        self, id: str, user_id: str, tag_name: str
    ) -> ChatModel | None:
        tag = await Tags.get_tag_by_name_and_user_id(tag_name, user_id)
        if tag is None:
            tag = await Tags.insert_new_tag(tag_name, user_id)
        try:
            async with get_async_db() as db:
                if tag:
                    if chat := await db.get(Chat, id):
                        tag_id = tag.id
                        if tag_id not in chat.meta.get("tags", []):
                            chat.meta = {
                                **chat.meta,
                                "tags": list(set(chat.meta.get("tags", []) + [tag_id])),
                            }

                        await db.commit()
                        await db.refresh(chat)
                        return ChatModel.model_validate(chat)
                return None
        except Exception:
            return None

    async def count_chats_by_tag_name_and_user_id(
        self, tag_name: str, user_id: str
    ) -> int:
        async with get_async_db() as db:  # Assuming `get_db()` returns a session object
            query = (
                select(func.count())
                .select_from(Chat)
                .where(Chat.user_id == user_id, Chat.archived == False)
            )

            # Normalize the tag_name for consistency
            tag_id = tag_name.replace(" ", "_").lower()

            if db.bind.dialect.name == "sqlite":
                # SQLite JSON1 support for querying the tags inside the `meta` JSON field
                query = query.where(
                    text(
                        "EXISTS (SELECT 1 FROM json_each(Chat.meta, '$.tags') WHERE json_each.value = :tag_id)"
                    )
                ).params(tag_id=tag_id)

            elif db.bind.dialect.name == "postgresql":
                # PostgreSQL JSONB support for querying the tags inside the `meta` JSON field
                query = query.where(
                    text(
                        "EXISTS (SELECT 1 FROM json_array_elements_text(Chat.meta->'tags') elem WHERE elem = :tag_id)"
                    )
                ).params(tag_id=tag_id)

            else:
                raise NotImplementedError(
                    f"Unsupported dialect: {db.bind.dialect.name}"
                )

            # Get the count of matching records
            count = await db.scalar(query)
            count = count if count else 0
            # Debugging output for inspection
            print(f"Count of chats for tag '{tag_name}':", count)

            return count

    async def delete_tag_by_id_and_user_id_and_tag_name(
        self, id: str, user_id: str, tag_name: str
    ) -> bool:
        try:
            async with get_async_db() as db:
                chat = await db.get(Chat, id)
                tags = chat.meta.get("tags", [])
                tag_id = tag_name.replace(" ", "_").lower()

                tags = [tag for tag in tags if tag != tag_id]
                chat.meta = {
                    **chat.meta,
                    "tags": list(set(tags)),
                }
                await db.commit()
                return True
        except Exception:
            return False

    async def delete_all_tags_by_id_and_user_id(self, id: str, user_id: str) -> bool:
        try:
            async with get_async_db() as db:
                if chat := await db.get(Chat, id):
                    chat.meta = {
                        **chat.meta,
                        "tags": [],
                    }
                    await db.commit()

                    return True
                return False
        except Exception:
            return False

    async def delete_chat_by_id(self, id: str) -> bool:
        try:
            async with get_async_db() as db:
                _ = await db.execute(delete(Chat).where(Chat.id == id))
                await db.commit()

                return True and await self.delete_shared_chat_by_chat_id(id)
        except Exception:
            return False

    async def delete_chat_by_id_and_user_id(self, id: str, user_id: str) -> bool:
        try:
            async with get_async_db() as db:
                _ = await db.execute(
                    delete(Chat).where(Chat.id == id, Chat.user_id == user_id)
                )
                await db.commit()

                return True and await self.delete_shared_chat_by_chat_id(id)
        except Exception:
            return False

    async def delete_chats_by_user_id(self, user_id: str) -> bool:
        try:
            async with get_async_db() as db:
                await self.delete_shared_chats_by_user_id(user_id)

                _ = await db.execute(delete(Chat).where(Chat.user_id == user_id))
                await db.commit()

                return True
        except Exception:
            return False

    async def delete_chats_by_user_id_and_folder_id(
        self, user_id: str, folder_id: str
    ) -> bool:
        try:
            async with get_async_db() as db:
                _ = await db.execute(
                    delete(Chat).where(
                        Chat.user_id == user_id, Chat.folder_id == folder_id
                    )
                )
                await db.commit()

                return True
        except Exception:
            return False

    async def delete_shared_chats_by_user_id(self, user_id: str) -> bool:
        try:
            async with get_async_db() as db:

                chats_by_user = await db.scalars(
                    select(Chat).where(Chat.user_id == user_id)
                )
                shared_chat_ids = [f"shared-{chat.id}" for chat in chats_by_user.all()]

                _ = await db.execute(
                    delete(Chat).where(Chat.user_id.in_(shared_chat_ids))
                )
                await db.commit()

                return True
        except Exception:
            return False

    async def get_chats_for_cleanup(
        self,
        max_age_days: int | None = None,
        preserve_pinned: bool = True,
        preserve_archived: bool = False,
        batch_size: int = 100,
    ) -> list[ChatModel]:
        """
        Get chats for cleanup, optionally filtered by age.
        Uses pagination to handle large datasets efficiently.

        Args:
            max_age_days: Age threshold in days. If None, gets all chats regardless of age.
            preserve_pinned: If True, exclude pinned chats from cleanup
            preserve_archived: If True, exclude archived chats from cleanup

        Returns:
            List of ChatModel objects for cleanup
        """
        try:
            async with get_async_db() as db:
                statement = select(Chat)

                # Apply age filter if specified
                if max_age_days is not None:
                    cutoff_timestamp = int(time.time()) - (max_age_days * 24 * 60 * 60)
                    statement = statement.where(Chat.updated_at < cutoff_timestamp)

                # Apply preservation filters
                if preserve_pinned:
                    statement = statement.where(
                        or_(Chat.pinned == False, Chat.pinned.is_(None))
                    )

                if preserve_archived:
                    statement = statement.where(Chat.archived == False)

                # Exclude shared chats (user_id starting with "shared-")
                statement = statement.where(~Chat.user_id.like("shared-%"))

                # Order by created_at to ensure consistent pagination
                statement = statement.order_by(Chat.created_at.asc())

                offset = 0
                result_chats: list[ChatModel] = []

                log.info("Starting paginated chat cleanup query...")

                while True:
                    # Get batch of chats
                    batch = await db.scalars(statement.offset(offset).limit(batch_size))

                    if not batch:
                        break  # No more chats to process

                    # Convert batch to ChatModel objects
                    for chat in batch.all():
                        try:
                            chat_model = ChatModel.model_validate(chat)
                            result_chats.append(chat_model)
                        except Exception as e:
                            log.error(
                                f"Error converting chat {chat.id} to ChatModel: {e}"
                            )
                            continue

                    # Clear batch from memory
                    del batch
                    offset += batch_size

                    # Log progress every 1000 records
                    if offset % 1000 == 0:
                        log.info(
                            f"Processed {offset} chats so far, found {len(result_chats)} for cleanup"
                        )

                log.info(
                    f"Completed paginated chat cleanup query. Total chats for cleanup: {len(result_chats)}"
                )
                return result_chats

        except Exception as e:
            log.error(f"Error getting chats for cleanup: {e}")
            return []

    # Backward compatibility methods
    async def get_expired_chats(
        self,
        max_age_days: int,
        preserve_pinned: bool = True,
        preserve_archived: bool = False,
    ) -> list[ChatModel]:
        """
        Deprecated: Use get_chats_for_cleanup() instead.
        Get chats that are older than max_age_days.
        """
        return await self.get_chats_for_cleanup(
            max_age_days, preserve_pinned, preserve_archived
        )

    async def get_all_chats_for_cleanup(
        self, preserve_pinned: bool = True, preserve_archived: bool = False
    ) -> list[ChatModel]:
        """
        Deprecated: Use get_chats_for_cleanup() instead.
        Get all chats for cleanup (ignoring age restrictions).
        """
        return await self.get_chats_for_cleanup(
            None, preserve_pinned, preserve_archived
        )

    async def delete_chat_list(
        self, chat_ids: list[str], batch_size: int = 100
    ) -> dict:
        """
        Delete multiple chats by their IDs and return deletion summary.
        Uses batching for large datasets to prevent memory issues.

        Args:
            chat_ids: List of chat IDs to delete

        Returns:
            Dictionary with deletion results
        """
        try:
            result = {
                "deleted_count": 0,
                "failed_count": 0,
                "total_requested": len(chat_ids),
                "errors": [],
            }

            if not chat_ids:
                return result

            async with get_async_db() as db:
                for i in range(0, len(chat_ids), batch_size):
                    batch_ids = chat_ids[i : i + batch_size]
                    log.info(
                        f"Deleting chat batch {i//batch_size + 1}: {len(batch_ids)} chats"
                    )

                    try:
                        # Use bulk delete for better performance
                        deleted_count = await db.execute(
                            delete(Chat).where(Chat.id.in_(batch_ids))
                        )

                        result["deleted_count"] += deleted_count.first()

                        # Check if any in this batch weren't found
                        not_found_count = len(batch_ids) - deleted_count
                        if not_found_count > 0:
                            result["failed_count"] += not_found_count
                            result["errors"].append(
                                f"Batch {i//batch_size + 1}: {not_found_count} chats not found"
                            )

                        # Commit this batch
                        await db.commit()

                        log.debug(
                            f"Successfully deleted {deleted_count} chats in batch {i//batch_size + 1}"
                        )

                    except Exception as e:
                        # Handle batch failure
                        result["failed_count"] += len(batch_ids)
                        error_msg = (
                            f"Error deleting chat batch {i//batch_size + 1}: {str(e)}"
                        )
                        result["errors"].append(error_msg)
                        log.error(error_msg)

                        # Try to rollback this batch and continue
                        try:
                            await db.rollback()
                        except Exception:
                            pass

            log.info(
                f"Chat deletion completed. Deleted: {result['deleted_count']}, Failed: {result['failed_count']}"
            )
            return result

        except Exception as e:
            log.error(f"Error in bulk chat deletion: {e}")
            return {
                "deleted_count": 0,
                "failed_count": len(chat_ids),
                "total_requested": len(chat_ids),
                "errors": [f"Bulk deletion failed: {str(e)}"],
            }


Chats = ChatTable()
