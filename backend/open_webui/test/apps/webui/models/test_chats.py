import random
import time
import uuid
from typing import Any

import pytest
from open_webui.internal.db_utils import AsyncDatabaseConnector
from open_webui.models.chats import (
    Chat,
    ChatForm,
    ChatImportForm,
    ChatModel,
    ChatTable,
    ChatTitleIdResponse,
)
from open_webui.models.tags import Tag, TagModel
from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.orm.exc import ObjectDeletedError
import contextlib


class TestChat:
    @pytest.mark.parametrize(
        "chat, title",
        [
            (
                {
                    "messages": {
                        "system": "Be a good system.",
                        "user": "What is the name of the moon.",
                        "agent": "Luna",
                    }
                },
                None,
            ),
            ({}, ""),
            ({}, "This is a test domain."),
        ],
    )
    @pytest.mark.asyncio
    async def test_insert_new_chat(
        self,
        chat: dict[Any, Any],
        title: str | None,
        chat_table: ChatTable,
        db_connector: AsyncDatabaseConnector,
    ):
        user_id = str(uuid.uuid4())

        new_chat = chat | {"title": title} if title is not None else chat
        chat_form = ChatForm(chat=new_chat)

        chat_model = await chat_table.insert_new_chat(
            user_id=user_id, form_data=chat_form
        )
        assert chat_model

        async with db_connector.get_async_db() as db:
            chat = await db.scalar(select(Chat).where(Chat.id == chat_model.id))

            assert chat

            assert chat.chat == new_chat
            assert ChatModel.model_validate(chat) and chat_model

    @pytest.mark.parametrize(
        "chat_import_form",
        [
            ChatImportForm(
                chat={},
                meta={},
                folder_id=None,
                pinned=True,
            ),
            ChatImportForm(
                chat={"messages": ["test", "test2"]},
                meta={
                    "stuff": "testing",
                },
                folder_id=str(uuid.uuid4()),
                pinned=True,
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_import_chat(
        self,
        chat_import_form: ChatImportForm,
        chat_table: ChatTable,
        db_connector: AsyncDatabaseConnector,
    ):
        user_id = str(uuid.uuid4())

        chat_model = await chat_table.import_chat(
            user_id=user_id, form_data=chat_import_form
        )
        assert chat_model

        async with db_connector.get_async_db() as db:
            chat = await db.scalar(select(Chat).where(Chat.id == chat_model.id))

            assert chat

            assert ChatModel.model_validate(chat) and chat_model

    @pytest.mark.asyncio
    async def test_update_chat_by_id(
        self,
        chat_table: ChatTable,
        db_connector: AsyncDatabaseConnector,
    ):
        current_time = int(time.time())
        chat = Chat(
            id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
            title="New Chat",
            chat={},
            created_at=current_time,
            updated_at=current_time,
            share_id=None,
            archived=False,
            pinned=None,
            meta={},
            folder_id=None,
        )

        new_chat = {
            "messages": ["Test", "Test2"],
            "title": "Updated Chat",
        }

        async with db_connector.get_async_db() as db:
            db.add(chat)
            await db.commit()
            await db.refresh(chat)

            c = await chat_table.update_chat_by_id(chat.id, new_chat)

            assert c
            assert c.chat == new_chat
            assert c.title == new_chat["title"]

            await db.refresh(chat)
            assert ChatModel.model_validate(chat) == c

    @pytest.mark.asyncio
    async def test_update_chat_title_by_id(
        self,
        chat_table: ChatTable,
        db_connector: AsyncDatabaseConnector,
    ):
        current_time = int(time.time())
        chat = Chat(
            id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
            title="New Chat",
            chat={},
            created_at=current_time,
            updated_at=current_time,
            share_id=None,
            archived=False,
            pinned=None,
            meta={},
            folder_id=None,
        )

        new_title = "This is the new title."

        async with db_connector.get_async_db() as db:
            db.add(chat)
            await db.commit()
            await db.refresh(chat)

            c = await chat_table.update_chat_title_by_id(id=chat.id, title=new_title)

            assert c
            assert c.chat.get("title", None) == new_title
            assert c.title == new_title

            await db.refresh(chat)
            assert ChatModel.model_validate(chat) == c

    @pytest.mark.asyncio
    async def test_get_chat_title_by_id(
        self,
        chat_table: ChatTable,
        db_connector: AsyncDatabaseConnector,
    ):
        current_time = int(time.time())
        title = "Test Chat for Unit Testing"
        chat = Chat(
            id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
            title=title,
            chat={"title": title},
            created_at=current_time,
            updated_at=current_time,
            share_id=None,
            archived=False,
            pinned=None,
            meta={},
            folder_id=None,
        )

        async with db_connector.get_async_db() as db:
            db.add(chat)
            await db.commit()
            await db.refresh(chat)

            t = await chat_table.get_chat_title_by_id(id=chat.id)

            assert t
            assert title == t

    @pytest.mark.asyncio
    async def test_get_chat_title_by_id_no_id(
        self,
        chat_table: ChatTable,
        db_connector: AsyncDatabaseConnector,
    ):
        current_time = int(time.time())
        title = "Test Chat for Unit Testing"
        chat = Chat(
            id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
            title=title,
            chat={"title": title},
            created_at=current_time,
            updated_at=current_time,
            share_id=None,
            archived=False,
            pinned=None,
            meta={},
            folder_id=None,
        )

        async with db_connector.get_async_db() as db:
            db.add(chat)
            await db.commit()
            await db.refresh(chat)

            t = await chat_table.get_chat_title_by_id(id="BadChatID")

            assert t is None

    class TestGetMessagesByChatId:

        @pytest.mark.asyncio
        async def test_valid_id(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
        ):
            current_time = int(time.time())
            title = "Test Chat for Unit Testing"
            message_id = "fd1bd5bf-25e6-45ff-ad30-9e1801ceab37"
            chat = Chat(
                id=str(uuid.uuid4()),
                user_id=str(uuid.uuid4()),
                title=title,
                chat={
                    "history": {
                        "messages": {
                            "0bc9697b-6972-4971-b135-d85be3778b0c": {
                                "id": "0bc9697b-6972-4971-b135-d85be3778b0c",
                                "parentId": None,
                                "childrenIds": [message_id],
                                "role": "user",
                                "content": "Blahblahblah",
                                "timestamp": 1771950743,
                                "models": ["Gemini Flash 2.5"],
                            },
                            message_id: {
                                "parentId": "0bc9697b-6972-4971-b135-d85be3778b0c",
                                "id": message_id,
                                "childrenIds": [],
                                "role": "assistant",
                                "content": "To do the following....",
                                "model": "Gemini Flash 2.5",
                                "modelName": "Gemini Flash 2.5",
                                "modelIdx": 0,
                                "userContext": None,
                                "timestamp": 1771950744,
                                "lastSentence": "So, if your PGPORT is 5432, you'll access PostgreSQL via localhost:5432.",
                                "usage": {
                                    "completion_tokens": 1042,
                                    "prompt_tokens": 549,
                                    "total_tokens": 1591,
                                    "completion_tokens_details": {
                                        "reasoning_tokens": 172,
                                        "text_tokens": 870,
                                    },
                                    "prompt_tokens_details": {"text_tokens": 549},
                                },
                                "done": True,
                            },
                        }
                    },
                    "title": title,
                },
                created_at=current_time,
                updated_at=current_time,
                share_id=None,
                archived=False,
                pinned=None,
                meta={},
                folder_id=None,
            )

            async with db_connector.get_async_db() as db:
                db.add(chat)
                await db.commit()
                await db.refresh(chat)

                messages = await chat_table.get_messages_by_chat_id(id=chat.id)

                assert messages
                assert messages == chat.chat["history"]["messages"]

        @pytest.mark.asyncio
        async def test_no_messages(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
        ):
            current_time = int(time.time())
            title = "Test Chat for Unit Testing"
            chat = Chat(
                id=str(uuid.uuid4()),
                user_id=str(uuid.uuid4()),
                title=title,
                chat={
                    "history": {"messages": {}},
                    "title": title,
                },
                created_at=current_time,
                updated_at=current_time,
                share_id=None,
                archived=False,
                pinned=None,
                meta={},
                folder_id=None,
            )

            async with db_connector.get_async_db() as db:
                db.add(chat)
                await db.commit()
                await db.refresh(chat)

                messages = await chat_table.get_messages_by_chat_id(id=chat.id)

                assert messages is not None and len(messages) == 0
                assert messages == chat.chat["history"]["messages"]

        @pytest.mark.asyncio
        async def test_no_id(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
        ):
            current_time = int(time.time())
            title = "Test Chat for Unit Testing"
            message_id = "fd1bd5bf-25e6-45ff-ad30-9e1801ceab37"
            chat = Chat(
                id=str(uuid.uuid4()),
                user_id=str(uuid.uuid4()),
                title=title,
                chat={
                    "history": {
                        "messages": {
                            "0bc9697b-6972-4971-b135-d85be3778b0c": {
                                "id": "0bc9697b-6972-4971-b135-d85be3778b0c",
                                "parentId": None,
                                "childrenIds": [message_id],
                                "role": "user",
                                "content": "Blahblahblah",
                                "timestamp": 1771950743,
                                "models": ["Gemini Flash 2.5"],
                            },
                            message_id: {
                                "parentId": "0bc9697b-6972-4971-b135-d85be3778b0c",
                                "id": message_id,
                                "childrenIds": [],
                                "role": "assistant",
                                "content": "To do the following....",
                                "model": "Gemini Flash 2.5",
                                "modelName": "Gemini Flash 2.5",
                                "modelIdx": 0,
                                "userContext": None,
                                "timestamp": 1771950744,
                                "lastSentence": "So, if your PGPORT is 5432, you'll access PostgreSQL via localhost:5432.",
                                "usage": {
                                    "completion_tokens": 1042,
                                    "prompt_tokens": 549,
                                    "total_tokens": 1591,
                                    "completion_tokens_details": {
                                        "reasoning_tokens": 172,
                                        "text_tokens": 870,
                                    },
                                    "prompt_tokens_details": {"text_tokens": 549},
                                },
                                "done": True,
                            },
                        }
                    },
                    "title": title,
                },
                created_at=current_time,
                updated_at=current_time,
                share_id=None,
                archived=False,
                pinned=None,
                meta={},
                folder_id=None,
            )

            async with db_connector.get_async_db() as db:
                db.add(chat)
                await db.commit()
                await db.refresh(chat)

                messages = await chat_table.get_messages_by_chat_id(id="BadChatID")

                assert messages is None

    class TestGetMessagesByChatIdAndMessageId:
        @pytest.mark.asyncio
        async def test_valid_ids(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
        ):
            current_time = int(time.time())
            title = "Test Chat for Unit Testing"
            message_id = "fd1bd5bf-25e6-45ff-ad30-9e1801ceab37"
            chat = Chat(
                id=str(uuid.uuid4()),
                user_id=str(uuid.uuid4()),
                title=title,
                chat={
                    "history": {
                        "messages": {
                            "0bc9697b-6972-4971-b135-d85be3778b0c": {
                                "id": "0bc9697b-6972-4971-b135-d85be3778b0c",
                                "parentId": None,
                                "childrenIds": [message_id],
                                "role": "user",
                                "content": "Blahblahblah",
                                "timestamp": 1771950743,
                                "models": ["Gemini Flash 2.5"],
                            },
                            message_id: {
                                "parentId": "0bc9697b-6972-4971-b135-d85be3778b0c",
                                "id": message_id,
                                "childrenIds": [],
                                "role": "assistant",
                                "content": "To do the following....",
                                "model": "Gemini Flash 2.5",
                                "modelName": "Gemini Flash 2.5",
                                "modelIdx": 0,
                                "userContext": None,
                                "timestamp": 1771950744,
                                "lastSentence": "So, if your PGPORT is 5432, you'll access PostgreSQL via localhost:5432.",
                                "usage": {
                                    "completion_tokens": 1042,
                                    "prompt_tokens": 549,
                                    "total_tokens": 1591,
                                    "completion_tokens_details": {
                                        "reasoning_tokens": 172,
                                        "text_tokens": 870,
                                    },
                                    "prompt_tokens_details": {"text_tokens": 549},
                                },
                                "done": True,
                            },
                        }
                    },
                    "title": title,
                },
                created_at=current_time,
                updated_at=current_time,
                share_id=None,
                archived=False,
                pinned=None,
                meta={},
                folder_id=None,
            )

            async with db_connector.get_async_db() as db:
                db.add(chat)
                await db.commit()
                await db.refresh(chat)

                message = await chat_table.get_message_by_id_and_message_id(
                    id=chat.id, message_id=message_id
                )

                assert message
                assert message == chat.chat["history"]["messages"][message_id]

        @pytest.mark.asyncio
        async def test_invalid_chat_id(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
        ):
            current_time = int(time.time())
            title = "Test Chat for Unit Testing"
            message_id = "fd1bd5bf-25e6-45ff-ad30-9e1801ceab37"
            chat = Chat(
                id=str(uuid.uuid4()),
                user_id=str(uuid.uuid4()),
                title=title,
                chat={
                    "history": {
                        "messages": {
                            "0bc9697b-6972-4971-b135-d85be3778b0c": {
                                "id": "0bc9697b-6972-4971-b135-d85be3778b0c",
                                "parentId": None,
                                "childrenIds": [message_id],
                                "role": "user",
                                "content": "Blahblahblah",
                                "timestamp": 1771950743,
                                "models": ["Gemini Flash 2.5"],
                            },
                            message_id: {
                                "parentId": "0bc9697b-6972-4971-b135-d85be3778b0c",
                                "id": message_id,
                                "childrenIds": [],
                                "role": "assistant",
                                "content": "To do the following....",
                                "model": "Gemini Flash 2.5",
                                "modelName": "Gemini Flash 2.5",
                                "modelIdx": 0,
                                "userContext": None,
                                "timestamp": 1771950744,
                                "lastSentence": "So, if your PGPORT is 5432, you'll access PostgreSQL via localhost:5432.",
                                "usage": {
                                    "completion_tokens": 1042,
                                    "prompt_tokens": 549,
                                    "total_tokens": 1591,
                                    "completion_tokens_details": {
                                        "reasoning_tokens": 172,
                                        "text_tokens": 870,
                                    },
                                    "prompt_tokens_details": {"text_tokens": 549},
                                },
                                "done": True,
                            },
                        }
                    },
                    "title": title,
                },
                created_at=current_time,
                updated_at=current_time,
                share_id=None,
                archived=False,
                pinned=None,
                meta={},
                folder_id=None,
            )

            async with db_connector.get_async_db() as db:
                db.add(chat)
                await db.commit()
                await db.refresh(chat)

                message = await chat_table.get_message_by_id_and_message_id(
                    id="BadChatID", message_id=message_id
                )

                assert message is None

        @pytest.mark.asyncio
        async def test_invalid_message_id(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
        ):
            current_time = int(time.time())
            title = "Test Chat for Unit Testing"
            message_id = "fd1bd5bf-25e6-45ff-ad30-9e1801ceab37"
            chat = Chat(
                id=str(uuid.uuid4()),
                user_id=str(uuid.uuid4()),
                title=title,
                chat={
                    "history": {
                        "messages": {
                            "0bc9697b-6972-4971-b135-d85be3778b0c": {
                                "id": "0bc9697b-6972-4971-b135-d85be3778b0c",
                                "parentId": None,
                                "childrenIds": [message_id],
                                "role": "user",
                                "content": "Blahblahblah",
                                "timestamp": 1771950743,
                                "models": ["Gemini Flash 2.5"],
                            },
                            message_id: {
                                "parentId": "0bc9697b-6972-4971-b135-d85be3778b0c",
                                "id": message_id,
                                "childrenIds": [],
                                "role": "assistant",
                                "content": "To do the following....",
                                "model": "Gemini Flash 2.5",
                                "modelName": "Gemini Flash 2.5",
                                "modelIdx": 0,
                                "userContext": None,
                                "timestamp": 1771950744,
                                "lastSentence": "So, if your PGPORT is 5432, you'll access PostgreSQL via localhost:5432.",
                                "usage": {
                                    "completion_tokens": 1042,
                                    "prompt_tokens": 549,
                                    "total_tokens": 1591,
                                    "completion_tokens_details": {
                                        "reasoning_tokens": 172,
                                        "text_tokens": 870,
                                    },
                                    "prompt_tokens_details": {"text_tokens": 549},
                                },
                                "done": True,
                            },
                        }
                    },
                    "title": title,
                },
                created_at=current_time,
                updated_at=current_time,
                share_id=None,
                archived=False,
                pinned=None,
                meta={},
                folder_id=None,
            )

            async with db_connector.get_async_db() as db:
                db.add(chat)
                await db.commit()
                await db.refresh(chat)

                message = await chat_table.get_message_by_id_and_message_id(
                    id=chat.id, message_id="BadMessageID"
                )

                assert message is not None and len(message) == 0

    class TestUpsertMessageToChatByIdAndMessageId:
        @pytest.mark.asyncio
        async def test_valid_ids_existing_message(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
        ):
            current_time = int(time.time())
            title = "Test Chat for Unit Testing"
            message_id = "fd1bd5bf-25e6-45ff-ad30-9e1801ceab37"
            chat = Chat(
                id=str(uuid.uuid4()),
                user_id=str(uuid.uuid4()),
                title=title,
                chat={
                    "history": {
                        "messages": {
                            "0bc9697b-6972-4971-b135-d85be3778b0c": {
                                "id": "0bc9697b-6972-4971-b135-d85be3778b0c",
                                "parentId": None,
                                "childrenIds": [message_id],
                                "role": "user",
                                "content": "Blahblahblah",
                                "timestamp": 1771950743,
                                "models": ["Gemini Flash 2.5"],
                            },
                            message_id: {
                                "parentId": "0bc9697b-6972-4971-b135-d85be3778b0c",
                                "id": message_id,
                                "childrenIds": [],
                                "role": "assistant",
                                "content": "To do the following....",
                                "model": "Gemini Flash 2.5",
                                "modelName": "Gemini Flash 2.5",
                                "modelIdx": 0,
                                "userContext": None,
                                "timestamp": 1771950744,
                                "lastSentence": "So, if your PGPORT is 5432, you'll access PostgreSQL via localhost:5432.",
                                "usage": {
                                    "completion_tokens": 1042,
                                    "prompt_tokens": 549,
                                    "total_tokens": 1591,
                                    "completion_tokens_details": {
                                        "reasoning_tokens": 172,
                                        "text_tokens": 870,
                                    },
                                    "prompt_tokens_details": {"text_tokens": 549},
                                },
                                "done": True,
                            },
                        }
                    },
                    "title": title,
                },
                created_at=current_time,
                updated_at=current_time,
                share_id=None,
                archived=False,
                pinned=None,
                meta={},
                folder_id=None,
            )

            async with db_connector.get_async_db() as db:
                db.add(chat)
                await db.commit()
                await db.refresh(chat)

                message = chat.chat["history"]["messages"][message_id]
                message |= {
                    "content": "This is update content.",
                    "timestamp": int(time.time()),
                }

                chat_model = (
                    await chat_table.upsert_message_to_chat_by_id_and_message_id(
                        id=chat.id, message_id=message_id, message=message
                    )
                )
                assert chat_model

                await db.refresh(chat)
                assert ChatModel.model_validate(chat) == chat_model

        @pytest.mark.asyncio
        async def test_valid_ids_new_message(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
        ):
            current_time = int(time.time())
            title = "Test Chat for Unit Testing"
            chat = Chat(
                id=str(uuid.uuid4()),
                user_id=str(uuid.uuid4()),
                title=title,
                chat={
                    "history": {
                        "messages": {
                            "0bc9697b-6972-4971-b135-d85be3778b0c": {
                                "id": "0bc9697b-6972-4971-b135-d85be3778b0c",
                                "parentId": None,
                                "childrenIds": ["fd1bd5bf-25e6-45ff-ad30-9e1801ceab37"],
                                "role": "user",
                                "content": "Blahblahblah",
                                "timestamp": 1771950743,
                                "models": ["Gemini Flash 2.5"],
                            },
                            "fd1bd5bf-25e6-45ff-ad30-9e1801ceab37": {
                                "parentId": "0bc9697b-6972-4971-b135-d85be3778b0c",
                                "id": "fd1bd5bf-25e6-45ff-ad30-9e1801ceab37",
                                "childrenIds": [],
                                "role": "assistant",
                                "content": "To do the following....",
                                "model": "Gemini Flash 2.5",
                                "modelName": "Gemini Flash 2.5",
                                "modelIdx": 0,
                                "userContext": None,
                                "timestamp": 1771950744,
                                "lastSentence": "So, if your PGPORT is 5432, you'll access PostgreSQL via localhost:5432.",
                                "usage": {
                                    "completion_tokens": 1042,
                                    "prompt_tokens": 549,
                                    "total_tokens": 1591,
                                    "completion_tokens_details": {
                                        "reasoning_tokens": 172,
                                        "text_tokens": 870,
                                    },
                                    "prompt_tokens_details": {"text_tokens": 549},
                                },
                                "done": True,
                            },
                        }
                    },
                    "title": title,
                },
                created_at=current_time,
                updated_at=current_time,
                share_id=None,
                archived=False,
                pinned=None,
                meta={},
                folder_id=None,
            )

            async with db_connector.get_async_db() as db:
                db.add(chat)
                await db.commit()
                await db.refresh(chat)

                message_id = str(uuid.uuid4())
                message: dict[str, Any] = {
                    "parentId": "fd1bd5bf-25e6-45ff-ad30-9e1801ceab37",
                    "id": message_id,
                    "childrenIds": [],
                    "role": "assistant",
                    "content": "The contents of a new message..",
                    "model": "Gemini Flash 2.5",
                    "modelName": "Gemini Flash 2.5",
                    "modelIdx": 0,
                    "userContext": None,
                    "timestamp": int(time.time()),
                    "lastSentence": "So, if your PGPORT is 5432, you'll access PostgreSQL via localhost:5432.",
                    "usage": {
                        "completion_tokens": 1042,
                        "prompt_tokens": 549,
                        "total_tokens": 1591,
                        "completion_tokens_details": {
                            "reasoning_tokens": 172,
                            "text_tokens": 870,
                        },
                        "prompt_tokens_details": {"text_tokens": 549},
                    },
                    "done": True,
                }

                chat_model = (
                    await chat_table.upsert_message_to_chat_by_id_and_message_id(
                        id=chat.id, message_id=message_id, message=message
                    )
                )
                assert chat_model

                await db.refresh(chat)
                assert ChatModel.model_validate(chat) == chat_model

        @pytest.mark.asyncio
        async def test_invalid_chat_id(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
        ):
            current_time = int(time.time())
            title = "Test Chat for Unit Testing"
            chat = Chat(
                id=str(uuid.uuid4()),
                user_id=str(uuid.uuid4()),
                title=title,
                chat={
                    "history": {
                        "messages": {
                            "0bc9697b-6972-4971-b135-d85be3778b0c": {
                                "id": "0bc9697b-6972-4971-b135-d85be3778b0c",
                                "parentId": None,
                                "childrenIds": ["fd1bd5bf-25e6-45ff-ad30-9e1801ceab37"],
                                "role": "user",
                                "content": "Blahblahblah",
                                "timestamp": 1771950743,
                                "models": ["Gemini Flash 2.5"],
                            },
                            "fd1bd5bf-25e6-45ff-ad30-9e1801ceab37": {
                                "parentId": "0bc9697b-6972-4971-b135-d85be3778b0c",
                                "id": "fd1bd5bf-25e6-45ff-ad30-9e1801ceab37",
                                "childrenIds": [],
                                "role": "assistant",
                                "content": "To do the following....",
                                "model": "Gemini Flash 2.5",
                                "modelName": "Gemini Flash 2.5",
                                "modelIdx": 0,
                                "userContext": None,
                                "timestamp": 1771950744,
                                "lastSentence": "So, if your PGPORT is 5432, you'll access PostgreSQL via localhost:5432.",
                                "usage": {
                                    "completion_tokens": 1042,
                                    "prompt_tokens": 549,
                                    "total_tokens": 1591,
                                    "completion_tokens_details": {
                                        "reasoning_tokens": 172,
                                        "text_tokens": 870,
                                    },
                                    "prompt_tokens_details": {"text_tokens": 549},
                                },
                                "done": True,
                            },
                        }
                    },
                    "title": title,
                },
                created_at=current_time,
                updated_at=current_time,
                share_id=None,
                archived=False,
                pinned=None,
                meta={},
                folder_id=None,
            )

            async with db_connector.get_async_db() as db:
                db.add(chat)
                await db.commit()
                await db.refresh(chat)

                message_id = str(uuid.uuid4())
                message: dict[str, Any] = {
                    "parentId": "fd1bd5bf-25e6-45ff-ad30-9e1801ceab37",
                    "id": message_id,
                    "childrenIds": [],
                    "role": "assistant",
                    "content": "The contents of a new message..",
                    "model": "Gemini Flash 2.5",
                    "modelName": "Gemini Flash 2.5",
                    "modelIdx": 0,
                    "userContext": None,
                    "timestamp": int(time.time()),
                    "lastSentence": "So, if your PGPORT is 5432, you'll access PostgreSQL via localhost:5432.",
                    "usage": {
                        "completion_tokens": 1042,
                        "prompt_tokens": 549,
                        "total_tokens": 1591,
                        "completion_tokens_details": {
                            "reasoning_tokens": 172,
                            "text_tokens": 870,
                        },
                        "prompt_tokens_details": {"text_tokens": 549},
                    },
                    "done": True,
                }

                chat_model = (
                    await chat_table.upsert_message_to_chat_by_id_and_message_id(
                        id="InvalidChatID", message_id=message_id, message=message
                    )
                )
                assert chat_model is None

    class TestAddMessageStatusToChatByIdAndMessageId:
        @pytest.mark.asyncio
        async def test_valid_ids_existing_message(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
        ):
            current_time = int(time.time())
            title = "Test Chat for Unit Testing"
            message_id = "fd1bd5bf-25e6-45ff-ad30-9e1801ceab37"
            chat = Chat(
                id=str(uuid.uuid4()),
                user_id=str(uuid.uuid4()),
                title=title,
                chat={
                    "history": {
                        "messages": {
                            "0bc9697b-6972-4971-b135-d85be3778b0c": {
                                "id": "0bc9697b-6972-4971-b135-d85be3778b0c",
                                "parentId": None,
                                "childrenIds": [message_id],
                                "role": "user",
                                "content": "Blahblahblah",
                                "timestamp": 1771950743,
                                "models": ["Gemini Flash 2.5"],
                            },
                            message_id: {
                                "parentId": "0bc9697b-6972-4971-b135-d85be3778b0c",
                                "id": message_id,
                                "childrenIds": [],
                                "role": "assistant",
                                "content": "To do the following....",
                                "model": "Gemini Flash 2.5",
                                "modelName": "Gemini Flash 2.5",
                                "modelIdx": 0,
                                "userContext": None,
                                "timestamp": 1771950744,
                                "lastSentence": "So, if your PGPORT is 5432, you'll access PostgreSQL via localhost:5432.",
                                "usage": {
                                    "completion_tokens": 1042,
                                    "prompt_tokens": 549,
                                    "total_tokens": 1591,
                                    "completion_tokens_details": {
                                        "reasoning_tokens": 172,
                                        "text_tokens": 870,
                                    },
                                    "prompt_tokens_details": {"text_tokens": 549},
                                },
                                "done": True,
                            },
                        }
                    },
                    "title": title,
                },
                created_at=current_time,
                updated_at=current_time,
                share_id=None,
                archived=False,
                pinned=None,
                meta={},
                folder_id=None,
            )

            async with db_connector.get_async_db() as db:
                db.add(chat)
                await db.commit()
                await db.refresh(chat)

                status = {
                    "status": "Ready",
                    "phase": "unit tests",
                }

                chat_model = (
                    await chat_table.add_message_status_to_chat_by_id_and_message_id(
                        id=chat.id, message_id=message_id, status=status
                    )
                )
                assert chat_model

                await db.refresh(chat)
                assert ChatModel.model_validate(chat) == chat_model

        @pytest.mark.asyncio
        async def test_valid_id_non_existing_message(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
        ):
            current_time = int(time.time())
            title = "Test Chat for Unit Testing"
            message_id = "fd1bd5bf-25e6-45ff-ad30-9e1801ceab37"
            chat = Chat(
                id=str(uuid.uuid4()),
                user_id=str(uuid.uuid4()),
                title=title,
                chat={
                    "history": {
                        "messages": {
                            "0bc9697b-6972-4971-b135-d85be3778b0c": {
                                "id": "0bc9697b-6972-4971-b135-d85be3778b0c",
                                "parentId": None,
                                "childrenIds": [message_id],
                                "role": "user",
                                "content": "Blahblahblah",
                                "timestamp": 1771950743,
                                "models": ["Gemini Flash 2.5"],
                            },
                            message_id: {
                                "parentId": "0bc9697b-6972-4971-b135-d85be3778b0c",
                                "id": message_id,
                                "childrenIds": [],
                                "role": "assistant",
                                "content": "To do the following....",
                                "model": "Gemini Flash 2.5",
                                "modelName": "Gemini Flash 2.5",
                                "modelIdx": 0,
                                "userContext": None,
                                "timestamp": 1771950744,
                                "lastSentence": "So, if your PGPORT is 5432, you'll access PostgreSQL via localhost:5432.",
                                "usage": {
                                    "completion_tokens": 1042,
                                    "prompt_tokens": 549,
                                    "total_tokens": 1591,
                                    "completion_tokens_details": {
                                        "reasoning_tokens": 172,
                                        "text_tokens": 870,
                                    },
                                    "prompt_tokens_details": {"text_tokens": 549},
                                },
                                "done": True,
                            },
                        }
                    },
                    "title": title,
                },
                created_at=current_time,
                updated_at=current_time,
                share_id=None,
                archived=False,
                pinned=None,
                meta={},
                folder_id=None,
            )

            async with db_connector.get_async_db() as db:
                db.add(chat)
                await db.commit()
                await db.refresh(chat)

                status = {
                    "status": "Ready",
                    "phase": "unit tests",
                }

                chat_model = (
                    await chat_table.add_message_status_to_chat_by_id_and_message_id(
                        id=chat.id, message_id="InvalidMessageID", status=status
                    )
                )
                assert chat_model

                # No changes database, no need for a refresh.
                assert ChatModel.model_validate(chat) == chat_model

        @pytest.mark.asyncio
        async def test_invalid_id(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
        ):
            current_time = int(time.time())
            title = "Test Chat for Unit Testing"
            message_id = "fd1bd5bf-25e6-45ff-ad30-9e1801ceab37"
            chat = Chat(
                id=str(uuid.uuid4()),
                user_id=str(uuid.uuid4()),
                title=title,
                chat={
                    "history": {
                        "messages": {
                            "0bc9697b-6972-4971-b135-d85be3778b0c": {
                                "id": "0bc9697b-6972-4971-b135-d85be3778b0c",
                                "parentId": None,
                                "childrenIds": [message_id],
                                "role": "user",
                                "content": "Blahblahblah",
                                "timestamp": 1771950743,
                                "models": ["Gemini Flash 2.5"],
                            },
                            message_id: {
                                "parentId": "0bc9697b-6972-4971-b135-d85be3778b0c",
                                "id": message_id,
                                "childrenIds": [],
                                "role": "assistant",
                                "content": "To do the following....",
                                "model": "Gemini Flash 2.5",
                                "modelName": "Gemini Flash 2.5",
                                "modelIdx": 0,
                                "userContext": None,
                                "timestamp": 1771950744,
                                "lastSentence": "So, if your PGPORT is 5432, you'll access PostgreSQL via localhost:5432.",
                                "usage": {
                                    "completion_tokens": 1042,
                                    "prompt_tokens": 549,
                                    "total_tokens": 1591,
                                    "completion_tokens_details": {
                                        "reasoning_tokens": 172,
                                        "text_tokens": 870,
                                    },
                                    "prompt_tokens_details": {"text_tokens": 549},
                                },
                                "done": True,
                            },
                        }
                    },
                    "title": title,
                },
                created_at=current_time,
                updated_at=current_time,
                share_id=None,
                archived=False,
                pinned=None,
                meta={},
                folder_id=None,
            )

            async with db_connector.get_async_db() as db:
                db.add(chat)
                await db.commit()
                await db.refresh(chat)

                status = {
                    "status": "Ready",
                    "phase": "unit tests",
                }

                chat_model = (
                    await chat_table.add_message_status_to_chat_by_id_and_message_id(
                        id="InvalidChatID", message_id=message_id, status=status
                    )
                )
                assert chat_model is None

    class TestInsertSharedChatByChatID:
        @pytest.mark.asyncio
        async def test_valid_id(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
        ):
            current_time = int(time.time())
            title = "Test Chat for Unit Testing"
            chat = Chat(
                id=str(uuid.uuid4()),
                user_id=str(uuid.uuid4()),
                title=title,
                chat={
                    "history": {
                        "messages": {
                            "0bc9697b-6972-4971-b135-d85be3778b0c": {
                                "id": "0bc9697b-6972-4971-b135-d85be3778b0c",
                                "parentId": None,
                                "childrenIds": [],
                                "role": "user",
                                "content": "Blahblahblah",
                                "timestamp": 1771950743,
                                "models": ["Gemini Flash 2.5"],
                            },
                        }
                    },
                    "title": title,
                },
                created_at=current_time,
                updated_at=current_time,
                share_id=None,
                archived=False,
                pinned=None,
                meta={},
                folder_id=None,
            )

            async with db_connector.get_async_db() as db:
                db.add(chat)
                await db.commit()
                await db.refresh(chat)

                shared_chat_model = await chat_table.insert_shared_chat_by_chat_id(
                    chat_id=chat.id
                )
                assert shared_chat_model

                assert chat.user_id != shared_chat_model.user_id
                assert shared_chat_model.user_id == f"shared-{chat.id}"
                assert chat.chat == shared_chat_model.chat
                assert chat.created_at == shared_chat_model.created_at
                assert chat.title == shared_chat_model.title

                await db.refresh(chat)
                assert chat.share_id is not None

        @pytest.mark.asyncio
        async def test_valid_id_existing_chat(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
        ):
            current_time = int(time.time())
            title = "Test Chat for Unit Testing"
            chat = Chat(
                id=str(uuid.uuid4()),
                user_id=str(uuid.uuid4()),
                title=title,
                chat={
                    "history": {
                        "messages": {
                            "0bc9697b-6972-4971-b135-d85be3778b0c": {
                                "id": "0bc9697b-6972-4971-b135-d85be3778b0c",
                                "parentId": None,
                                "childrenIds": [],
                                "role": "user",
                                "content": "Blahblahblah",
                                "timestamp": 1771950743,
                                "models": ["Gemini Flash 2.5"],
                            },
                        }
                    },
                    "title": title,
                },
                created_at=current_time,
                updated_at=current_time,
                share_id=None,
                archived=False,
                pinned=None,
                meta={},
                folder_id=None,
            )

            async with db_connector.get_async_db() as db:
                db.add(chat)
                await db.commit()
                await db.refresh(chat)

                shared_chat_model = await chat_table.insert_shared_chat_by_chat_id(
                    chat_id=chat.id
                )
                assert shared_chat_model

                assert chat.user_id != shared_chat_model.user_id
                assert shared_chat_model.user_id == f"shared-{chat.id}"
                assert chat.chat == shared_chat_model.chat
                assert chat.created_at == shared_chat_model.created_at
                assert chat.title == shared_chat_model.title

                await db.refresh(chat)
                assert chat.share_id is not None

                existing_shared_model = await chat_table.insert_shared_chat_by_chat_id(
                    chat_id=chat.id
                )

                assert existing_shared_model
                assert existing_shared_model == shared_chat_model

        @pytest.mark.asyncio
        async def test_valid_id_existing_shared_id_no_shared_chat(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
        ):
            current_time = int(time.time())
            title = "Test Chat for Unit Testing"
            chat = Chat(
                id=str(uuid.uuid4()),
                user_id=str(uuid.uuid4()),
                title=title,
                chat={
                    "history": {
                        "messages": {
                            "0bc9697b-6972-4971-b135-d85be3778b0c": {
                                "id": "0bc9697b-6972-4971-b135-d85be3778b0c",
                                "parentId": None,
                                "childrenIds": [],
                                "role": "user",
                                "content": "Blahblahblah",
                                "timestamp": 1771950743,
                                "models": ["Gemini Flash 2.5"],
                            },
                        }
                    },
                    "title": title,
                },
                created_at=current_time,
                updated_at=current_time,
                share_id=str(uuid.uuid4()),
                archived=False,
                pinned=None,
                meta={},
                folder_id=None,
            )

            async with db_connector.get_async_db() as db:
                db.add(chat)
                await db.commit()
                await db.refresh(chat)

                shared_chat_model = await chat_table.insert_shared_chat_by_chat_id(
                    chat_id=chat.id
                )
                assert shared_chat_model is None

        @pytest.mark.asyncio
        async def test_invalid_id(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
        ):
            current_time = int(time.time())
            title = "Test Chat for Unit Testing"
            chat = Chat(
                id=str(uuid.uuid4()),
                user_id=str(uuid.uuid4()),
                title=title,
                chat={
                    "history": {
                        "messages": {
                            "0bc9697b-6972-4971-b135-d85be3778b0c": {
                                "id": "0bc9697b-6972-4971-b135-d85be3778b0c",
                                "parentId": None,
                                "childrenIds": [],
                                "role": "user",
                                "content": "Blahblahblah",
                                "timestamp": 1771950743,
                                "models": ["Gemini Flash 2.5"],
                            },
                        }
                    },
                    "title": title,
                },
                created_at=current_time,
                updated_at=current_time,
                share_id=str(uuid.uuid4()),
                archived=False,
                pinned=None,
                meta={},
                folder_id=None,
            )

            async with db_connector.get_async_db() as db:
                db.add(chat)
                await db.commit()
                await db.refresh(chat)

                shared_chat_model = await chat_table.insert_shared_chat_by_chat_id(
                    chat_id="InvalidChatID"
                )
                assert shared_chat_model is None

    class TestUpdateSharedChatByChatId:
        @pytest.mark.asyncio
        async def test_valid_id_no_shared_chat(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
        ):
            current_time = int(time.time())
            title = "Test Chat for Unit Testing"
            chat = Chat(
                id=str(uuid.uuid4()),
                user_id=str(uuid.uuid4()),
                title=title,
                chat={
                    "history": {
                        "messages": {
                            "0bc9697b-6972-4971-b135-d85be3778b0c": {
                                "id": "0bc9697b-6972-4971-b135-d85be3778b0c",
                                "parentId": None,
                                "childrenIds": [],
                                "role": "user",
                                "content": "Blahblahblah",
                                "timestamp": 1771950743,
                                "models": ["Gemini Flash 2.5"],
                            },
                        }
                    },
                    "title": title,
                },
                created_at=current_time,
                updated_at=current_time,
                share_id=None,
                archived=False,
                pinned=None,
                meta={},
                folder_id=None,
            )

            async with db_connector.get_async_db() as db:
                db.add(chat)
                await db.commit()
                await db.refresh(chat)

                shared_chat_model = await chat_table.update_shared_chat_by_chat_id(
                    chat_id=chat.id
                )
                assert shared_chat_model

                assert chat.user_id != shared_chat_model.user_id
                assert shared_chat_model.user_id == f"shared-{chat.id}"
                assert chat.chat == shared_chat_model.chat
                assert chat.created_at == shared_chat_model.created_at
                assert chat.title == shared_chat_model.title

                await db.refresh(chat)
                assert chat.share_id is not None

        @pytest.mark.asyncio
        async def test_valid_id_existing_chat(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
        ):
            current_time = int(time.time())
            title = "Test Chat for Unit Testing"
            chat = Chat(
                id=str(uuid.uuid4()),
                user_id=str(uuid.uuid4()),
                title=title,
                chat={
                    "history": {
                        "messages": {
                            "0bc9697b-6972-4971-b135-d85be3778b0c": {
                                "id": "0bc9697b-6972-4971-b135-d85be3778b0c",
                                "parentId": None,
                                "childrenIds": [],
                                "role": "user",
                                "content": "Blahblahblah",
                                "timestamp": 1771950743,
                                "models": ["Gemini Flash 2.5"],
                            },
                        }
                    },
                    "title": title,
                },
                created_at=current_time,
                updated_at=current_time,
                share_id=None,
                archived=False,
                pinned=None,
                meta={},
                folder_id=None,
            )

            async with db_connector.get_async_db() as db:
                db.add(chat)
                await db.commit()
                await db.refresh(chat)

                shared_chat_model = await chat_table.insert_shared_chat_by_chat_id(
                    chat_id=chat.id
                )
                assert shared_chat_model

                assert chat.user_id != shared_chat_model.user_id
                assert shared_chat_model.user_id == f"shared-{chat.id}"
                assert chat.chat == shared_chat_model.chat
                assert chat.created_at == shared_chat_model.created_at
                assert chat.title == shared_chat_model.title

                await db.refresh(chat)
                assert chat.share_id is not None

                # Update chat
                chat.title = "Chat Title Updated for Unit Testing"
                new_message_id = str(uuid.uuid4())
                chat.chat["history"]["messages"][new_message_id] = {
                    "id": new_message_id,
                    "parentId": None,
                    "childrenIds": [],
                    "role": "user",
                    "content": "UnitTest",
                    "timestamp": int(time.time()),
                    "models": ["Command A"],
                }
                flag_modified(chat, "chat")
                await db.commit()

                # Update the shared chat
                updated_shared_model = await chat_table.update_shared_chat_by_chat_id(
                    chat_id=chat.id
                )
                assert updated_shared_model

                # shared_chat_models should not be equal.
                assert updated_shared_model != shared_chat_model

                assert updated_shared_model.user_id == f"shared-{chat.id}"
                assert chat.chat == updated_shared_model.chat
                assert chat.created_at == updated_shared_model.created_at
                assert chat.title == updated_shared_model.title

        @pytest.mark.asyncio
        async def test_invalid_id(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
        ):
            current_time = int(time.time())
            title = "Test Chat for Unit Testing"
            chat = Chat(
                id=str(uuid.uuid4()),
                user_id=str(uuid.uuid4()),
                title=title,
                chat={
                    "history": {
                        "messages": {
                            "0bc9697b-6972-4971-b135-d85be3778b0c": {
                                "id": "0bc9697b-6972-4971-b135-d85be3778b0c",
                                "parentId": None,
                                "childrenIds": [],
                                "role": "user",
                                "content": "Blahblahblah",
                                "timestamp": 1771950743,
                                "models": ["Gemini Flash 2.5"],
                            },
                        }
                    },
                    "title": title,
                },
                created_at=current_time,
                updated_at=current_time,
                share_id=str(uuid.uuid4()),
                archived=False,
                pinned=None,
                meta={},
                folder_id=None,
            )

            async with db_connector.get_async_db() as db:
                db.add(chat)
                await db.commit()
                await db.refresh(chat)

                shared_chat_model = await chat_table.insert_shared_chat_by_chat_id(
                    chat_id="InvalidChatID"
                )
                assert shared_chat_model is None

    class TestDeleteSharedChatByChatId:
        @pytest.mark.asyncio
        async def test_valid_id(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
        ):
            current_time = int(time.time())
            title = "Test Chat for Unit Testing"
            chat = Chat(
                id=str(uuid.uuid4()),
                user_id=str(uuid.uuid4()),
                title=title,
                chat={
                    "history": {
                        "messages": {
                            "0bc9697b-6972-4971-b135-d85be3778b0c": {
                                "id": "0bc9697b-6972-4971-b135-d85be3778b0c",
                                "parentId": None,
                                "childrenIds": [],
                                "role": "user",
                                "content": "Blahblahblah",
                                "timestamp": 1771950743,
                                "models": ["Gemini Flash 2.5"],
                            },
                        }
                    },
                    "title": title,
                },
                created_at=current_time,
                updated_at=current_time,
                share_id=None,
                archived=False,
                pinned=None,
                meta={},
                folder_id=None,
            )

            async with db_connector.get_async_db() as db:
                db.add(chat)
                await db.commit()
                await db.refresh(chat)

                # Create shared chat.
                shared_chat_model = await chat_table.insert_shared_chat_by_chat_id(
                    chat_id=chat.id
                )
                assert shared_chat_model

                shared = await db.scalar(
                    select(Chat).where(Chat.user_id == f"shared-{chat.id}")
                )
                assert shared

                shared_chat_model = await chat_table.delete_shared_chat_by_chat_id(
                    chat_id=chat.id
                )
                assert shared_chat_model

                shared = await db.scalar(
                    select(Chat).where(Chat.user_id == f"shared-{chat.id}")
                )
                assert shared is None

    class TestUpdateChatShareIdById:
        @pytest.mark.asyncio
        @pytest.mark.parametrize(
            argnames="share_id", argvalues=["shareid-34646556", None]
        )
        async def test_valid_id(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
            share_id: str | None,
        ):
            current_time = int(time.time())
            title = "Test Chat for Unit Testing"
            chat = Chat(
                id=str(uuid.uuid4()),
                user_id=str(uuid.uuid4()),
                title=title,
                chat={
                    "history": {
                        "messages": {
                            "0bc9697b-6972-4971-b135-d85be3778b0c": {
                                "id": "0bc9697b-6972-4971-b135-d85be3778b0c",
                                "parentId": None,
                                "childrenIds": [],
                                "role": "user",
                                "content": "Blahblahblah",
                                "timestamp": 1771950743,
                                "models": ["Gemini Flash 2.5"],
                            },
                        }
                    },
                    "title": title,
                },
                created_at=current_time,
                updated_at=current_time,
                share_id="Original-SharedID",
                archived=False,
                pinned=None,
                meta={},
                folder_id=None,
            )

            async with db_connector.get_async_db() as db:
                db.add(chat)
                await db.commit()
                await db.refresh(chat)

                chat_model = await chat_table.update_chat_share_id_by_id(
                    id=chat.id, share_id=share_id
                )
                assert chat_model

                await db.refresh(chat)

                assert chat.share_id == chat_model.share_id
                assert ChatModel.model_validate(chat) == chat_model

        @pytest.mark.asyncio
        async def test_invalid_id(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
        ):
            current_time = int(time.time())
            title = "Test Chat for Unit Testing"
            chat = Chat(
                id=str(uuid.uuid4()),
                user_id=str(uuid.uuid4()),
                title=title,
                chat={
                    "history": {
                        "messages": {
                            "0bc9697b-6972-4971-b135-d85be3778b0c": {
                                "id": "0bc9697b-6972-4971-b135-d85be3778b0c",
                                "parentId": None,
                                "childrenIds": [],
                                "role": "user",
                                "content": "Blahblahblah",
                                "timestamp": 1771950743,
                                "models": ["Gemini Flash 2.5"],
                            },
                        }
                    },
                    "title": title,
                },
                created_at=current_time,
                updated_at=current_time,
                share_id="Original-SharedID",
                archived=False,
                pinned=None,
                meta={},
                folder_id=None,
            )

            async with db_connector.get_async_db() as db:
                db.add(chat)
                await db.commit()
                await db.refresh(chat)

                chat_model = await chat_table.update_chat_share_id_by_id(
                    id="InvalidChatID", share_id=None
                )
                assert chat_model is None

    class TestToggleChatPinnedById:
        @pytest.mark.parametrize(argnames="is_pinned", argvalues=[True, False, None])
        @pytest.mark.asyncio
        async def test_valid_id(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
            is_pinned: None | bool,
        ):
            current_time = int(time.time())
            title = "Test Chat for Unit Testing"
            chat = Chat(
                id=str(uuid.uuid4()),
                user_id=str(uuid.uuid4()),
                title=title,
                chat={
                    "history": {
                        "messages": {
                            "0bc9697b-6972-4971-b135-d85be3778b0c": {
                                "id": "0bc9697b-6972-4971-b135-d85be3778b0c",
                                "parentId": None,
                                "childrenIds": [],
                                "role": "user",
                                "content": "Blahblahblah",
                                "timestamp": 1771950743,
                                "models": ["Gemini Flash 2.5"],
                            },
                        }
                    },
                    "title": title,
                },
                created_at=current_time,
                updated_at=current_time,
                share_id="Original-SharedID",
                archived=False,
                pinned=is_pinned,
                meta={},
                folder_id=None,
            )

            async with db_connector.get_async_db() as db:
                db.add(chat)
                await db.commit()
                await db.refresh(chat)

                chat_model = await chat_table.toggle_chat_pinned_by_id(id=chat.id)
                assert chat_model

                match is_pinned:
                    case False | None:
                        assert chat_model.pinned == True
                    case True:
                        assert chat_model.pinned == False

                await db.refresh(chat)
                assert ChatModel.model_validate(chat) == chat_model

        @pytest.mark.asyncio
        async def test_valid_id_pinned_nulled(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
        ):
            current_time = int(time.time())
            title = "Test Chat for Unit Testing"
            chat = Chat(
                id=str(uuid.uuid4()),
                user_id=str(uuid.uuid4()),
                title=title,
                chat={
                    "history": {
                        "messages": {
                            "0bc9697b-6972-4971-b135-d85be3778b0c": {
                                "id": "0bc9697b-6972-4971-b135-d85be3778b0c",
                                "parentId": None,
                                "childrenIds": [],
                                "role": "user",
                                "content": "Blahblahblah",
                                "timestamp": 1771950743,
                                "models": ["Gemini Flash 2.5"],
                            },
                        }
                    },
                    "title": title,
                },
                created_at=current_time,
                updated_at=current_time,
                share_id="Original-SharedID",
                archived=False,
                pinned=None,  # Default value in the DB is False, not Null on creation.
                meta={},
                folder_id=None,
            )

            async with db_connector.get_async_db() as db:
                db.add(chat)
                await db.commit()
                await db.refresh(chat)

                # Explicitly set the value in the DB to null.
                chat.pinned = None
                await db.commit()
                await db.refresh(chat)

                chat_model = await chat_table.toggle_chat_pinned_by_id(id=chat.id)
                assert chat_model

                await db.refresh(chat)
                assert chat.pinned == True
                assert chat_model.pinned == True
                assert ChatModel.model_validate(chat) == chat_model

        @pytest.mark.asyncio
        async def test_invalid_id(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
        ):
            current_time = int(time.time())
            title = "Test Chat for Unit Testing"
            chat = Chat(
                id=str(uuid.uuid4()),
                user_id=str(uuid.uuid4()),
                title=title,
                chat={
                    "history": {
                        "messages": {
                            "0bc9697b-6972-4971-b135-d85be3778b0c": {
                                "id": "0bc9697b-6972-4971-b135-d85be3778b0c",
                                "parentId": None,
                                "childrenIds": [],
                                "role": "user",
                                "content": "Blahblahblah",
                                "timestamp": 1771950743,
                                "models": ["Gemini Flash 2.5"],
                            },
                        }
                    },
                    "title": title,
                },
                created_at=current_time,
                updated_at=current_time,
                share_id="Original-SharedID",
                archived=False,
                pinned=None,
                meta={},
                folder_id=None,
            )

            async with db_connector.get_async_db() as db:
                db.add(chat)
                await db.commit()
                await db.refresh(chat)

                chat_model = await chat_table.toggle_chat_pinned_by_id(
                    id="InvalidChatID"
                )
                assert chat_model is None

    class TestToggleChatArchiveById:
        @pytest.mark.parametrize(argnames="is_archived", argvalues=[True, False])
        @pytest.mark.asyncio
        async def test_valid_id(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
            is_archived: None | bool,
        ):
            current_time = int(time.time())
            title = "Test Chat for Unit Testing"
            chat = Chat(
                id=str(uuid.uuid4()),
                user_id=str(uuid.uuid4()),
                title=title,
                chat={
                    "history": {
                        "messages": {
                            "0bc9697b-6972-4971-b135-d85be3778b0c": {
                                "id": "0bc9697b-6972-4971-b135-d85be3778b0c",
                                "parentId": None,
                                "childrenIds": [],
                                "role": "user",
                                "content": "Blahblahblah",
                                "timestamp": 1771950743,
                                "models": ["Gemini Flash 2.5"],
                            },
                        }
                    },
                    "title": title,
                },
                created_at=current_time,
                updated_at=current_time,
                share_id="Original-SharedID",
                archived=is_archived,
                pinned=None,
                meta={},
                folder_id=None,
            )

            async with db_connector.get_async_db() as db:
                db.add(chat)
                await db.commit()
                await db.refresh(chat)

                chat_model = await chat_table.toggle_chat_archive_by_id(id=chat.id)
                assert chat_model

                assert chat_model != is_archived

                await db.refresh(chat)
                assert ChatModel.model_validate(chat) == chat_model

        @pytest.mark.asyncio
        async def test_invalid_id(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
        ):
            current_time = int(time.time())
            title = "Test Chat for Unit Testing"
            chat = Chat(
                id=str(uuid.uuid4()),
                user_id=str(uuid.uuid4()),
                title=title,
                chat={
                    "history": {
                        "messages": {
                            "0bc9697b-6972-4971-b135-d85be3778b0c": {
                                "id": "0bc9697b-6972-4971-b135-d85be3778b0c",
                                "parentId": None,
                                "childrenIds": [],
                                "role": "user",
                                "content": "Blahblahblah",
                                "timestamp": 1771950743,
                                "models": ["Gemini Flash 2.5"],
                            },
                        }
                    },
                    "title": title,
                },
                created_at=current_time,
                updated_at=current_time,
                share_id="Original-SharedID",
                archived=False,
                pinned=None,
                meta={},
                folder_id=None,
            )

            async with db_connector.get_async_db() as db:
                db.add(chat)
                await db.commit()
                await db.refresh(chat)

                chat_model = await chat_table.toggle_chat_archive_by_id(
                    id="InvalidChatID"
                )
                assert chat_model is None

    class TestArchiveAllChatsByUserId:
        @pytest.mark.asyncio
        async def test_valid_id(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
        ):
            user_id = str(uuid.uuid4())
            current_time = int(time.time())

            chats = [
                Chat(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    title="New Chat",
                    chat={},
                    created_at=current_time,
                    updated_at=current_time,
                    share_id=None,
                    archived=False,
                    pinned=None,
                    meta={"tags": ["news", "bob"]},
                    folder_id=None,
                ),
                Chat(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    title="New Chat",
                    chat={},
                    created_at=current_time,
                    updated_at=current_time,
                    share_id=None,
                    archived=False,
                    pinned=None,
                    meta={"tags": ["news", "bob"]},
                    folder_id=None,
                ),
                Chat(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    title="New Chat",
                    chat={},
                    created_at=current_time,
                    updated_at=current_time,
                    share_id=None,
                    archived=False,
                    pinned=None,
                    meta={"tags": ["news", "bob"]},
                    folder_id=None,
                ),
                Chat(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    title="New Chat",
                    chat={},
                    created_at=current_time,
                    updated_at=current_time,
                    share_id=None,
                    archived=True,
                    pinned=None,
                    meta={"tags": ["news", "bob"]},
                    folder_id=None,
                ),
            ]

            async with db_connector.get_async_db() as db:
                for chat in chats:
                    db.add(chat)
                await db.commit()

                are_archived = await chat_table.archive_all_chats_by_user_id(
                    user_id=user_id
                )

                assert are_archived

                for chat in chats:
                    await db.refresh(chat)
                    assert chat.archived == True

    class TestGetArchivedChatListByUserId:
        @pytest.mark.asyncio
        async def test_valid_id(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
        ):
            user_id = str(uuid.uuid4())
            current_time = int(time.time())

            chats = [
                Chat(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    title="New Chat",
                    chat={},
                    created_at=current_time,
                    updated_at=current_time,
                    share_id=None,
                    archived=True,
                    pinned=None,
                    meta={"tags": ["news", "bob"]},
                    folder_id=None,
                ),
                Chat(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    title="New Chat",
                    chat={},
                    created_at=current_time,
                    updated_at=current_time,
                    share_id=None,
                    archived=False,
                    pinned=None,
                    meta={"tags": ["news", "bob"]},
                    folder_id=None,
                ),
                Chat(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    title="New Chat",
                    chat={},
                    created_at=current_time,
                    updated_at=current_time,
                    share_id=None,
                    archived=False,
                    pinned=None,
                    meta={"tags": ["news", "bob"]},
                    folder_id=None,
                ),
                Chat(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    title="New Chat",
                    chat={},
                    created_at=current_time,
                    updated_at=current_time,
                    share_id=None,
                    archived=True,
                    pinned=None,
                    meta={"tags": ["news", "bob"]},
                    folder_id=None,
                ),
            ]

            async with db_connector.get_async_db() as db:
                for chat in chats:
                    db.add(chat)
                await db.commit()

                archived_chat_models = (
                    await chat_table.get_archived_chat_list_by_user_id(user_id=user_id)
                )
                assert len(archived_chat_models) == 2

                archived_chats = [
                    ChatModel.model_validate(chat) for chat in chats if chat.archived
                ]
                archived_chats.sort(key=lambda chat: chat.updated_at)

                assert archived_chat_models == archived_chats

    class TestGetChatListByUserId:
        @pytest.mark.parametrize(
            argnames="skip, limit, include_archived",
            argvalues=[
                (0, 0, False),
                (0, 0, True),
                (1, 1, False),
                (1, 1, True),
                (2, 10, False),
                (2, 10, True),
                (10, 100, False),
                (10, 100, True),
                # (2, 10, False),
                # (2, 10, True),
            ],
        )
        @pytest.mark.asyncio
        async def test_valid(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
            skip: int,
            limit: int,
            include_archived: bool,
        ):
            user_id = str(uuid.uuid4())
            current_time = int(time.time())

            initial_chats = [
                Chat(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    title=f"New Chat {i}",
                    chat={},
                    created_at=current_time + i + 100,
                    updated_at=current_time + i + 100,
                    share_id=None,
                    archived=i % 2 == 0,
                    pinned=i % 2 == 0,
                    meta={"tags": ["news", "bob", str(i)]},
                    folder_id=None,
                )
                for i in range(1, 30)
            ]
            initial_chats.sort(key=lambda chat: chat.updated_at, reverse=True)

            async with db_connector.get_async_db() as db:
                for chat in initial_chats:
                    db.add(chat)
                await db.commit()

                chat_models = await chat_table.get_chat_list_by_user_id(
                    user_id=user_id,
                    skip=skip,
                    limit=limit,
                    include_archived=include_archived,
                )
                assert chat_models

                stop_limit = None
                if limit != 0:
                    stop_limit = skip + limit

                expected_chats = [
                    ChatModel.model_validate(chat)
                    for chat in initial_chats
                    if not chat.archived or include_archived
                ][skip:stop_limit]
                assert chat_models == expected_chats

    class TestGetChatTitleIdListByUserId:
        @pytest.mark.parametrize(
            argnames="skip, limit, include_archived",
            argvalues=[
                (None, None, False),
                (None, None, True),
                (0, 0, False),
                (0, 0, True),
                (1, 1, False),
                (1, 1, True),
                (2, 10, False),
                (2, 10, True),
                (10, 100, False),
                (10, 100, True),
            ],
        )
        @pytest.mark.asyncio
        async def test_valid(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
            skip: int | None,
            limit: int | None,
            include_archived: bool,
        ):
            user_id = str(uuid.uuid4())
            current_time = int(time.time())

            initial_chats = [
                Chat(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    title=f"New Chat {i}",
                    chat={},
                    created_at=current_time + i + 100,
                    updated_at=current_time + i + 100 * random.randrange(2, 50),
                    share_id=None,
                    archived=i % 2 == 0,
                    pinned=i % 2 == 0,
                    meta={"tags": ["news", "bob", str(i)]},
                    folder_id=None,
                )
                for i in range(1, 30)
            ]
            initial_chats.sort(key=lambda chat: chat.updated_at, reverse=True)

            async with db_connector.get_async_db() as db:
                for chat in initial_chats:
                    db.add(chat)
                await db.commit()

                chat_titles = await chat_table.get_chat_title_id_list_by_user_id(
                    user_id=user_id,
                    skip=skip,
                    limit=limit,
                    include_archived=include_archived,
                )
                assert chat_titles

                # Swap Nones to 0 to allow for slicing.
                if limit is None:
                    limit = 0
                if skip is None:
                    skip = 0

                stop_limit = None
                if limit != 0:
                    stop_limit = skip + limit

                expected_chats = [
                    ChatTitleIdResponse.model_validate(
                        {
                            "id": chat.id,
                            "title": chat.title,
                            "updated_at": chat.updated_at,
                            "created_at": chat.created_at,
                        }
                    )
                    for chat in initial_chats
                    if (not chat.archived or include_archived)
                    and (chat.pinned is None or not chat.pinned)
                ][skip:stop_limit]
                assert chat_titles == expected_chats

    class TestGetChatListByChatIds:
        # TODO: Implement skip and limit tests if implemented in function.
        # @pytest.mark.parametrize(
        #     argnames="skip, limit",
        #     argvalues=[
        #         (0, 0),
        #         (0, 0),
        #         (1, 1),
        #         (1, 1),
        #         (2, 10),
        #         (2, 10),
        #         (10, 100),
        #         (10, 100),
        #     ],
        # )
        @pytest.mark.asyncio
        async def test_valid(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
            # skip: int,
            # limit: int,
        ):
            current_time = int(time.time())
            initial_chats = [
                Chat(
                    id=str(uuid.uuid4()),
                    user_id=str(uuid.uuid4()),
                    title=f"New Chat {i}",
                    chat={},
                    created_at=current_time + i + 100,
                    updated_at=current_time + i + 100 * random.randrange(2, 50),
                    share_id=None,
                    archived=i % 2 == 0,
                    pinned=i % 2 == 0,
                    meta={"tags": ["news", "bob", str(i)]},
                    folder_id=None,
                )
                for i in range(1, 30)
            ]

            random_chats = random.choices(initial_chats, k=10)
            random_ids = list(set([chat.id for chat in random_chats]))

            async with db_connector.get_async_db() as db:
                for chat in initial_chats:
                    db.add(chat)
                await db.commit()

                for chat in initial_chats:
                    await db.refresh(chat)

                chat_models = await chat_table.get_chat_list_by_chat_ids(
                    chat_ids=random_ids,
                    # skip=skip,
                    # limit=limit,
                )
                assert chat_models

                # stop_limit = None
                # if limit != 0:
                #     stop_limit = skip + limit

                # Create a list with unique chat elements.
                added_to_expected: set[str] = set()
                expected_chats: list[ChatModel] = []
                for chat in random_chats:
                    if (
                        not chat.archived
                        and chat.id in random_ids
                        and chat.id not in added_to_expected
                    ):
                        added_to_expected.add(chat.id)
                        expected_chats.append(ChatModel.model_validate(chat))

                expected_chats.sort(key=lambda chat: chat.updated_at, reverse=True)
                assert chat_models == expected_chats

    class TestGetChatById:
        @pytest.mark.asyncio
        async def test_valid_id(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
        ):
            chat = Chat(
                id=str(uuid.uuid4()),
                user_id=str(uuid.uuid4()),
                title="New Chat",
                chat={},
                created_at=int(time.time()),
                updated_at=int(time.time()),
                share_id=None,
                archived=False,
                pinned=False,
                meta={
                    "tags": [
                        "news",
                        "bob",
                    ]
                },
                folder_id=None,
            )

            async with db_connector.get_async_db() as db:
                db.add(chat)
                await db.commit()
                await db.refresh(chat)

                chat_model = await chat_table.get_chat_by_id(id=chat.id)
                assert chat_model

                assert ChatModel.model_validate(chat) == chat_model

        @pytest.mark.asyncio
        async def test_invalid_id(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
        ):
            chat = Chat(
                id=str(uuid.uuid4()),
                user_id=str(uuid.uuid4()),
                title="New Chat",
                chat={},
                created_at=int(time.time()),
                updated_at=int(time.time()),
                share_id=None,
                archived=False,
                pinned=False,
                meta={
                    "tags": [
                        "news",
                        "bob",
                    ]
                },
                folder_id=None,
            )

            async with db_connector.get_async_db() as db:
                db.add(chat)
                await db.commit()
                await db.refresh(chat)

                chat_model = await chat_table.get_chat_by_id(id="InvalidChatID")
                assert chat_model is None

    class TestGetChatByShareId:
        @pytest.mark.asyncio
        async def test_valid_id(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
        ):
            chat = Chat(
                id=str(uuid.uuid4()),
                user_id=str(uuid.uuid4()),
                title="New Chat",
                chat={},
                created_at=int(time.time()),
                updated_at=int(time.time()),
                share_id=str(uuid.uuid4()),
                archived=False,
                pinned=False,
                meta={
                    "tags": [
                        "news",
                        "bob",
                    ]
                },
                folder_id=None,
            )

            async with db_connector.get_async_db() as db:
                db.add(chat)
                await db.commit()
                await db.refresh(chat)

                chat_model = await chat_table.get_chat_by_share_id(id=chat.share_id)
                assert chat_model

                assert ChatModel.model_validate(chat) == chat_model

        @pytest.mark.asyncio
        async def test_invalid_id(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
        ):
            chat = Chat(
                id=str(uuid.uuid4()),
                user_id=str(uuid.uuid4()),
                title="New Chat",
                chat={},
                created_at=int(time.time()),
                updated_at=int(time.time()),
                share_id=str(uuid.uuid4()),
                archived=False,
                pinned=False,
                meta={
                    "tags": [
                        "news",
                        "bob",
                    ]
                },
                folder_id=None,
            )

            async with db_connector.get_async_db() as db:
                db.add(chat)
                await db.commit()
                await db.refresh(chat)

                chat_model = await chat_table.get_chat_by_share_id(id="InvalidShareID")
                assert chat_model is None

    class TestGetChatByIdAndUserId:
        @pytest.mark.asyncio
        async def test_valid_id(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
        ):
            chat = Chat(
                id=str(uuid.uuid4()),
                user_id=str(uuid.uuid4()),
                title="New Chat",
                chat={},
                created_at=int(time.time()),
                updated_at=int(time.time()),
                share_id=str(uuid.uuid4()),
                archived=False,
                pinned=False,
                meta={
                    "tags": [
                        "news",
                        "bob",
                    ]
                },
                folder_id=None,
            )

            async with db_connector.get_async_db() as db:
                db.add(chat)
                await db.commit()
                await db.refresh(chat)

                chat_model = await chat_table.get_chat_by_id_and_user_id(
                    id=chat.id, user_id=chat.user_id
                )
                assert chat_model

                assert ChatModel.model_validate(chat) == chat_model

        @pytest.mark.asyncio
        async def test_invalid_chat_id(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
        ):
            chat = Chat(
                id=str(uuid.uuid4()),
                user_id=str(uuid.uuid4()),
                title="New Chat",
                chat={},
                created_at=int(time.time()),
                updated_at=int(time.time()),
                share_id=str(uuid.uuid4()),
                archived=False,
                pinned=False,
                meta={
                    "tags": [
                        "news",
                        "bob",
                    ]
                },
                folder_id=None,
            )

            async with db_connector.get_async_db() as db:
                db.add(chat)
                await db.commit()
                await db.refresh(chat)

                chat_model = await chat_table.get_chat_by_id_and_user_id(
                    id="InvalidChatID", user_id=chat.user_id
                )
                assert chat_model is None

        @pytest.mark.asyncio
        async def test_invalid_user_id(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
        ):
            chat = Chat(
                id=str(uuid.uuid4()),
                user_id=str(uuid.uuid4()),
                title="New Chat",
                chat={},
                created_at=int(time.time()),
                updated_at=int(time.time()),
                share_id=str(uuid.uuid4()),
                archived=False,
                pinned=False,
                meta={
                    "tags": [
                        "news",
                        "bob",
                    ]
                },
                folder_id=None,
            )

            async with db_connector.get_async_db() as db:
                db.add(chat)
                await db.commit()
                await db.refresh(chat)

                chat_model = await chat_table.get_chat_by_id_and_user_id(
                    id=chat.id, user_id="InvalidUserID"
                )
                assert chat_model is None

    class TestGetChats:
        @pytest.mark.asyncio
        async def test_valid(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
            # skip: int,
            # limit: int,
        ):
            current_time = int(time.time())
            initial_chats = [
                Chat(
                    id=str(uuid.uuid4()),
                    user_id=str(uuid.uuid4()),
                    title=f"New Chat {i}",
                    chat={},
                    created_at=current_time + i + 100,
                    updated_at=current_time + i + 100,
                    share_id=None,
                    archived=i % 2 == 0,
                    pinned=i % 2 == 0,
                    meta={"tags": ["news", "bob", str(i)]},
                    folder_id=None,
                )
                for i in range(1, 30)
            ]

            async with db_connector.get_async_db() as db:
                for chat in initial_chats:
                    db.add(chat)
                await db.commit()

                for chat in initial_chats:
                    await db.refresh(chat)

                chat_models = await chat_table.get_chats()
                assert chat_models

                # Sort updated_at in descending order.
                initial_chats.sort(key=lambda chat: chat.updated_at, reverse=True)

                assert chat_models == [
                    ChatModel.model_validate(chat) for chat in initial_chats
                ]

    class TestGetChatsByUserId:
        @pytest.mark.asyncio
        async def test_valid_user_id(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
        ):
            current_time = int(time.time())

            # Create 5 user_ids
            user_ids = [str(uuid.uuid4()) for _ in range(5)]

            initial_chats = [
                Chat(
                    id=str(uuid.uuid4()),
                    user_id=random.choice(user_ids),
                    title=f"New Chat {i}",
                    chat={},
                    created_at=current_time + i + 100,
                    updated_at=current_time + i + 100 * random.randrange(2, 50),
                    share_id=None,
                    archived=i % 2 == 0,
                    pinned=i % 2 == 0,
                    meta={"tags": ["news", "bob", str(i)]},
                    folder_id=None,
                )
                for i in range(1, 51)
            ]

            user_id = random.choice(user_ids)
            # Get another user_id for the chance that it was never randomly picked.
            while not any(user_id == chat.user_id for chat in initial_chats):
                user_id = random.choice(user_ids)

            async with db_connector.get_async_db() as db:
                for chat in initial_chats:
                    db.add(chat)
                await db.commit()

                chat_models = await chat_table.get_chats_by_user_id(user_id=user_id)
                assert chat_models

                # Sort updated_at in descending order.
                users_chat_models = [
                    ChatModel.model_validate(chat)
                    for chat in initial_chats
                    if chat.user_id == user_id
                ]
                users_chat_models.sort(key=lambda chat: chat.updated_at, reverse=True)

                assert chat_models == users_chat_models

        @pytest.mark.asyncio
        async def test_invalid_user_id(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
        ):
            current_time = int(time.time())

            # Create 5 user_ids
            user_ids = [str(uuid.uuid4()) for _ in range(5)]

            initial_chats = [
                Chat(
                    id=str(uuid.uuid4()),
                    user_id=random.choice(user_ids),
                    title=f"New Chat {i}",
                    chat={},
                    created_at=current_time + i + 100,
                    updated_at=current_time + i + 100 * random.randrange(2, 50),
                    share_id=None,
                    archived=i % 2 == 0,
                    pinned=i % 2 == 0,
                    meta={"tags": ["news", "bob", str(i)]},
                    folder_id=None,
                )
                for i in range(1, 51)
            ]

            async with db_connector.get_async_db() as db:
                for chat in initial_chats:
                    db.add(chat)
                await db.commit()

                chat_models = await chat_table.get_chats_by_user_id(
                    user_id="InvalidUserId"
                )
                assert not chat_models

    class TestGetPinnedChatsByUserId:
        @pytest.mark.asyncio
        async def test_valid_user_id(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
        ):
            current_time = int(time.time())
            user_id = str(uuid.uuid4())
            initial_chats = [
                Chat(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    title=f"New Chat {i}",
                    chat={},
                    created_at=current_time + i + 100,
                    updated_at=current_time + i + 100 * random.randrange(2, 50),
                    share_id=None,
                    archived=False,
                    pinned=i % 2 == 0,
                    meta={"tags": ["news", "bob", str(i)]},
                    folder_id=None,
                )
                for i in range(1, 31)
            ]

            async with db_connector.get_async_db() as db:
                for chat in initial_chats:
                    db.add(chat)
                await db.commit()

                chat_models = await chat_table.get_pinned_chats_by_user_id(
                    user_id=user_id
                )
                assert chat_models

                # Sort updated_at in descending order.
                initial_chats.sort(key=lambda chat: chat.updated_at, reverse=True)

                assert chat_models == [
                    ChatModel.model_validate(chat)
                    for chat in initial_chats
                    if chat.pinned == True and chat.archived == False
                ]

        @pytest.mark.asyncio
        async def test_invalid_user_id(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
        ):
            current_time = int(time.time())
            user_id = str(uuid.uuid4())
            initial_chats = [
                Chat(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    title=f"New Chat {i}",
                    chat={},
                    created_at=current_time + i + 100,
                    updated_at=current_time + i + 100 * random.randrange(2, 50),
                    share_id=None,
                    archived=False,
                    pinned=i % 2 == 0,
                    meta={"tags": ["news", "bob", str(i)]},
                    folder_id=None,
                )
                for i in range(1, 31)
            ]

            async with db_connector.get_async_db() as db:
                for chat in initial_chats:
                    db.add(chat)
                await db.commit()

                chat_models = await chat_table.get_pinned_chats_by_user_id(
                    user_id="InvalidUserId"
                )
                assert not chat_models

    class TestGetArchivedChatsByUserId:
        @pytest.mark.asyncio
        async def test_valid_user_id(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
        ):
            current_time = int(time.time())
            user_id = str(uuid.uuid4())
            initial_chats = [
                Chat(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    title=f"New Chat {i}",
                    chat={},
                    created_at=current_time + i + 100,
                    updated_at=current_time + i + 100 * random.randrange(2, 50),
                    share_id=None,
                    archived=i % 2 == 0,
                    pinned=i % 2 == 0,
                    meta={"tags": ["news", "bob", str(i)]},
                    folder_id=None,
                )
                for i in range(1, 31)
            ]

            async with db_connector.get_async_db() as db:
                for chat in initial_chats:
                    db.add(chat)
                await db.commit()

                chat_models = await chat_table.get_archived_chats_by_user_id(
                    user_id=user_id
                )
                assert chat_models

                # Sort updated_at in descending order.
                initial_chats.sort(key=lambda chat: chat.updated_at, reverse=True)

                assert chat_models == [
                    ChatModel.model_validate(chat)
                    for chat in initial_chats
                    if chat.archived == True
                ]

        @pytest.mark.asyncio
        async def test_invalid_user_id(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
        ):
            current_time = int(time.time())
            user_id = str(uuid.uuid4())
            initial_chats = [
                Chat(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    title=f"New Chat {i}",
                    chat={},
                    created_at=current_time + i + 100,
                    updated_at=current_time + i + 100 * random.randrange(2, 50),
                    share_id=None,
                    archived=i % 2 == 0,
                    pinned=i % 2 == 0,
                    meta={"tags": ["news", "bob", str(i)]},
                    folder_id=None,
                )
                for i in range(1, 31)
            ]

            async with db_connector.get_async_db() as db:
                for chat in initial_chats:
                    db.add(chat)
                await db.commit()

                chat_models = await chat_table.get_archived_chats_by_user_id(
                    user_id="InvalidUserId"
                )
                assert not chat_models

    class TestGetChatsByUserIdAndSearchText:
        @pytest.mark.asyncio
        async def test_simple(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
        ):
            current_time = int(time.time())
            initial_chat = Chat(
                id=str(uuid.uuid4()),
                user_id=str(uuid.uuid4()),
                title="New Chat",
                chat={
                    "history": {
                        "messages": {
                            "0bc9697b-6972-4971-b135-d85be3778b0c": {
                                "id": "0bc9697b-6972-4971-b135-d85be3778b0c",
                                "parentId": None,
                                "childrenIds": ["fd1bd5bf-25e6-45ff-ad30-9e1801ceab37"],
                                "role": "user",
                                "content": "Blahblahblah",
                                "timestamp": 1771950743,
                                "models": ["Gemini Flash 2.5"],
                            },
                            "fd1bd5bf-25e6-45ff-ad30-9e1801ceab37": {
                                "parentId": "0bc9697b-6972-4971-b135-d85be3778b0c",
                                "id": "fd1bd5bf-25e6-45ff-ad30-9e1801ceab37",
                                "childrenIds": [],
                                "role": "assistant",
                                "content": "To do the following....",
                                "model": "Gemini Flash 2.5",
                                "modelName": "Gemini Flash 2.5",
                                "modelIdx": 0,
                                "userContext": None,
                                "timestamp": 1771950744,
                                "lastSentence": "So, if your PGPORT is 5432, you'll access PostgreSQL via localhost:5432.",
                                "usage": {
                                    "completion_tokens": 1042,
                                    "prompt_tokens": 549,
                                    "total_tokens": 1591,
                                    "completion_tokens_details": {
                                        "reasoning_tokens": 172,
                                        "text_tokens": 870,
                                    },
                                    "prompt_tokens_details": {"text_tokens": 549},
                                },
                                "done": True,
                            },
                        }
                    },
                    "messages": [
                        {
                            "id": "0bc9697b-6972-4971-b135-d85be3778b0c",
                            "parentId": None,
                            "childrenIds": ["fd1bd5bf-25e6-45ff-ad30-9e1801ceab37"],
                            "role": "user",
                            "content": "Blahblahblah apple",
                            "timestamp": 1771950743,
                            "models": ["Gemini Flash 2.5"],
                        },
                        {
                            "parentId": "0bc9697b-6972-4971-b135-d85be3778b0c",
                            "id": "fd1bd5bf-25e6-45ff-ad30-9e1801ceab37",
                            "childrenIds": [],
                            "role": "assistant",
                            "content": "To do the following....",
                            "model": "Gemini Flash 2.5",
                            "modelName": "Gemini Flash 2.5",
                            "modelIdx": 0,
                            "userContext": None,
                            "timestamp": 1771950744,
                            "lastSentence": "So, if your PGPORT is 5432, you'll access PostgreSQL via localhost:5432.",
                            "usage": {
                                "completion_tokens": 1042,
                                "prompt_tokens": 549,
                                "total_tokens": 1591,
                                "completion_tokens_details": {
                                    "reasoning_tokens": 172,
                                    "text_tokens": 870,
                                },
                                "prompt_tokens_details": {"text_tokens": 549},
                            },
                            "done": True,
                        },
                    ],
                    "title": "New Chat",
                },
                created_at=current_time,
                updated_at=current_time,
                share_id=None,
                archived=False,
                pinned=False,
                meta={"tags": ["apple"]},
                folder_id=None,
            )

            async with db_connector.get_async_db() as db:
                db.add(initial_chat)
                await db.commit()

                chat_models = await chat_table.get_chats_by_user_id_and_search_text(
                    user_id=initial_chat.user_id,
                    search_text="apple",
                )

                initial_chats: list[ChatModel] = list()
                initial_chats.append(ChatModel.model_validate(initial_chat))

                assert chat_models == initial_chats

        @pytest.mark.asyncio
        async def test_invalid_user_id(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
        ):
            current_time = int(time.time())
            initial_chat = Chat(
                id=str(uuid.uuid4()),
                user_id=str(uuid.uuid4()),
                title="New Chat",
                chat={
                    "history": {
                        "messages": {
                            "0bc9697b-6972-4971-b135-d85be3778b0c": {
                                "id": "0bc9697b-6972-4971-b135-d85be3778b0c",
                                "parentId": None,
                                "childrenIds": ["fd1bd5bf-25e6-45ff-ad30-9e1801ceab37"],
                                "role": "user",
                                "content": "Blahblahblah",
                                "timestamp": 1771950743,
                                "models": ["Gemini Flash 2.5"],
                            },
                            "fd1bd5bf-25e6-45ff-ad30-9e1801ceab37": {
                                "parentId": "0bc9697b-6972-4971-b135-d85be3778b0c",
                                "id": "fd1bd5bf-25e6-45ff-ad30-9e1801ceab37",
                                "childrenIds": [],
                                "role": "assistant",
                                "content": "To do the following....",
                                "model": "Gemini Flash 2.5",
                                "modelName": "Gemini Flash 2.5",
                                "modelIdx": 0,
                                "userContext": None,
                                "timestamp": 1771950744,
                                "lastSentence": "So, if your PGPORT is 5432, you'll access PostgreSQL via localhost:5432.",
                                "usage": {
                                    "completion_tokens": 1042,
                                    "prompt_tokens": 549,
                                    "total_tokens": 1591,
                                    "completion_tokens_details": {
                                        "reasoning_tokens": 172,
                                        "text_tokens": 870,
                                    },
                                    "prompt_tokens_details": {"text_tokens": 549},
                                },
                                "done": True,
                            },
                        }
                    },
                    "messages": [
                        {
                            "id": "0bc9697b-6972-4971-b135-d85be3778b0c",
                            "parentId": None,
                            "childrenIds": ["fd1bd5bf-25e6-45ff-ad30-9e1801ceab37"],
                            "role": "user",
                            "content": "Blahblahblah apple",
                            "timestamp": 1771950743,
                            "models": ["Gemini Flash 2.5"],
                        },
                        {
                            "parentId": "0bc9697b-6972-4971-b135-d85be3778b0c",
                            "id": "fd1bd5bf-25e6-45ff-ad30-9e1801ceab37",
                            "childrenIds": [],
                            "role": "assistant",
                            "content": "To do the following....",
                            "model": "Gemini Flash 2.5",
                            "modelName": "Gemini Flash 2.5",
                            "modelIdx": 0,
                            "userContext": None,
                            "timestamp": 1771950744,
                            "lastSentence": "So, if your PGPORT is 5432, you'll access PostgreSQL via localhost:5432.",
                            "usage": {
                                "completion_tokens": 1042,
                                "prompt_tokens": 549,
                                "total_tokens": 1591,
                                "completion_tokens_details": {
                                    "reasoning_tokens": 172,
                                    "text_tokens": 870,
                                },
                                "prompt_tokens_details": {"text_tokens": 549},
                            },
                            "done": True,
                        },
                    ],
                    "title": "New Chat",
                },
                created_at=current_time,
                updated_at=current_time,
                share_id=None,
                archived=False,
                pinned=False,
                meta={"tags": ["apple"]},
                folder_id=None,
            )

            async with db_connector.get_async_db() as db:
                db.add(initial_chat)
                await db.commit()

                chat_models = await chat_table.get_chats_by_user_id_and_search_text(
                    user_id="InvalidUserId",
                    search_text="apple",
                )

                assert len(chat_models) == 0

        @pytest.mark.parametrize(
            argnames="search_text, skip, limit, include_archived",
            argvalues=[
                ("apple", 0, 60, False),
                ("apple", 0, 60, True),
                ("apple hippo", 0, 60, False),
                ("apple hippo", 0, 60, True),
                ("apple tag:finance", 0, 60, False),
                ("apple tag:finance", 0, 60, True),
                ("tag:finance", 0, 60, False),
                ("tag:finance", 0, 60, True),
                ("tag:finance tag:art", 0, 60, False),
                ("tag:finance tag:art", 0, 60, True),
                ("apple tag:finance", 1, 1, False),
                ("apple tag:finance", 1, 1, True),
                ("apple", 2, 10, False),
                ("apple", 2, 10, True),
                ("apple", 10, 100, False),
                ("apple", 10, 100, True),
                ("apple", 100, 100, False),
                ("apple", 100, 100, True),
                ("", 2, 10, False),
                ("", 2, 10, True),
                ("", 10, 100, False),
                ("", 10, 100, True),
                ("", 100, 100, False),
                ("", 100, 100, True),
            ],
        )
        @pytest.mark.asyncio
        async def test_valid_user_id(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
            search_text: str,
            skip: int,
            limit: int,
            include_archived: bool,
        ):
            current_time = int(time.time())

            # Create 5 user_ids
            user_ids = [str(uuid.uuid4()) for _ in range(2)]
            search_terms = [
                "apple",
                "banana",
                "blueberry",
                "mouse",
                "hippo",
                "cat",
                "dog",
                "puppy",
                "rose",
                "violet",
                "vermillion",
                "indigo",
            ]

            search_tags = [
                "finance",
                "coding",
                "art",
                "cooking",
                "government",
                "technology",
            ]

            initial_chats = [
                Chat(
                    id=str(uuid.uuid4()),
                    user_id=random.choice(user_ids),
                    title=f"New Chat {i}",
                    chat={
                        "messages": [
                            {
                                "content": f"Blahblahblah {' '.join(random.choices(search_terms, k=random.randint(1, 3)))}",
                            },
                            {
                                "content": f"To do the following.... {' '.join(random.choices(search_terms, k=random.randint(1, 3)))}",
                            },
                        ],
                        "title": f"New Chat {i}",
                    },
                    created_at=current_time + i + 100,
                    updated_at=current_time + i + 100 * random.randrange(2, 50),
                    share_id=None,
                    archived=random.randint(0, 1) % 2 == 0,
                    pinned=i % 2 == 0,
                    meta={"tags": random.choices(search_tags, k=random.randint(0, 3))},
                    folder_id=None,
                )
                for i in range(1, 51)
            ]

            user_id = random.choice(user_ids)
            # Get another user_id for the chance that it was never randomly picked.
            while not any(user_id == chat.user_id for chat in initial_chats):
                user_id = random.choice(user_ids)

            async with db_connector.get_async_db() as db:
                for chat in initial_chats:
                    db.add(chat)
                await db.commit()

                chat_models = await chat_table.get_chats_by_user_id_and_search_text(
                    user_id=user_id,
                    search_text=search_text,
                    skip=skip,
                    limit=limit,
                    include_archived=include_archived,
                )

                text_to_search = " ".join(
                    [
                        text
                        for text in search_text.lower().split(" ")
                        if not text.startswith("tag:")
                    ]
                )

                tags_to_search = [
                    text.split("tag:")[1]
                    for text in search_text.lower().split(" ")
                    if text.startswith("tag:")
                ]

                def contains_search_terms(chat: Chat) -> bool:
                    """
                    Quick convenience funtion to get find chats that have the search terms we're looking for.

                    Checks for an occurrence of the split search_text
                    """

                    # Empty search term returns all.
                    if not text_to_search:
                        return True

                    messages: list[dict[str, str | int | None]] = chat.chat.get(
                        "messages", []
                    )

                    for message_dict in messages:
                        if (
                            text_to_search
                            in str(message_dict.get("content", "")).lower().strip()
                        ):
                            return True

                    return False

                def contains_all_tags(chat: Chat) -> bool:
                    return all(
                        tag in chat.meta.get("tags", []) for tag in tags_to_search
                    )

                users_chat_models = [
                    ChatModel.model_validate(chat)
                    for chat in initial_chats
                    if chat.user_id == user_id
                    and (not chat.archived or include_archived)
                    and (contains_search_terms(chat) and contains_all_tags(chat))
                ]
                users_chat_models.sort(key=lambda chat: chat.updated_at, reverse=True)

                assert (
                    chat_models
                    == users_chat_models[skip : skip + limit if limit != 0 else 0]
                )

    class TestUpdateChatFolderIdByChatIdAndUserId:
        @pytest.mark.asyncio
        async def test_valid_ids(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
        ):
            current_time = int(time.time())
            chat = Chat(
                id=str(uuid.uuid4()),
                user_id=str(uuid.uuid4()),
                title="New Chat",
                chat={},
                created_at=current_time,
                updated_at=current_time,
                share_id=None,
                archived=False,
                pinned=None,
                meta={},
                folder_id=None,
            )
            folder_id = str(uuid.uuid4())

            async with db_connector.get_async_db() as db:
                db.add(chat)
                await db.commit()
                await db.refresh(chat)

                c = await chat_table.update_chat_folder_id_by_id_and_user_id(
                    id=chat.id, user_id=chat.user_id, folder_id=folder_id
                )

                assert c
                assert c.folder_id == folder_id

                await db.refresh(chat)
                assert ChatModel.model_validate(chat) == c

        @pytest.mark.asyncio
        async def test_invalid_user_id(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
        ):
            current_time = int(time.time())
            chat = Chat(
                id=str(uuid.uuid4()),
                user_id=str(uuid.uuid4()),
                title="New Chat",
                chat={},
                created_at=current_time,
                updated_at=current_time,
                share_id=None,
                archived=False,
                pinned=None,
                meta={},
                folder_id=None,
            )
            folder_id = str(uuid.uuid4())

            async with db_connector.get_async_db() as db:
                db.add(chat)
                await db.commit()
                await db.refresh(chat)

                c = await chat_table.update_chat_folder_id_by_id_and_user_id(
                    id=chat.id, user_id="BadUserID", folder_id=folder_id
                )

                assert c is None

        @pytest.mark.asyncio
        async def test_invalid_chat_id(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
        ):
            current_time = int(time.time())
            chat = Chat(
                id=str(uuid.uuid4()),
                user_id=str(uuid.uuid4()),
                title="New Chat",
                chat={},
                created_at=current_time,
                updated_at=current_time,
                share_id=None,
                archived=False,
                pinned=None,
                meta={},
                folder_id=None,
            )
            folder_id = str(uuid.uuid4())

            async with db_connector.get_async_db() as db:
                db.add(chat)
                await db.commit()
                await db.refresh(chat)

                c = await chat_table.update_chat_folder_id_by_id_and_user_id(
                    id="BadChatID", user_id=chat.user_id, folder_id=folder_id
                )

                assert c is None

    class TestGetChatTagsByIdAndUserId:
        @pytest.mark.asyncio
        async def test_valid_chat_id_and_valid_user_id(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
        ):
            current_time = int(time.time())
            user_id = str(uuid.uuid4())

            tag_names = ["Test First", "Investments", "This is a test"]

            tags = [
                Tag(
                    id=tag.replace(" ", "_").lower(), name=tag, user_id=user_id, meta={}
                )
                for tag in tag_names
            ]

            chat = Chat(
                id=str(uuid.uuid4()),
                user_id=user_id,
                title="New Chat",
                chat={},
                created_at=current_time,
                updated_at=current_time,
                share_id=None,
                archived=False,
                pinned=None,
                meta={"tags": [tag.id for tag in tags]},
                folder_id=None,
            )

            async with db_connector.get_async_db() as db:
                for tag in tags:
                    db.add(tag)

                db.add(chat)
                await db.commit()
                for tag in tags:
                    await db.refresh(tag)
                await db.refresh(chat)

                tag_models = await chat_table.get_chat_tags_by_id_and_user_id(
                    id=chat.id, user_id=chat.user_id
                )

                assert len(tag_models) == len(tags)
                assert [TagModel.model_validate(tag) for tag in tags] == tag_models

        @pytest.mark.asyncio
        async def test_valid_chat_id_and_invalid_user_id(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
        ):
            current_time = int(time.time())
            user_id = str(uuid.uuid4())

            tag_names = ["Test First", "Investments", "This is a test"]

            tags = [
                Tag(
                    id=tag.replace(" ", "_").lower(), name=tag, user_id=user_id, meta={}
                )
                for tag in tag_names
            ]

            chat = Chat(
                id=str(uuid.uuid4()),
                user_id=user_id,
                title="New Chat",
                chat={},
                created_at=current_time,
                updated_at=current_time,
                share_id=None,
                archived=False,
                pinned=None,
                meta={"tags": [tag.id for tag in tags]},
                folder_id=None,
            )

            async with db_connector.get_async_db() as db:
                for tag in tags:
                    db.add(tag)

                db.add(chat)
                await db.commit()
                for tag in tags:
                    await db.refresh(tag)
                await db.refresh(chat)

                tag_models = await chat_table.get_chat_tags_by_id_and_user_id(
                    id=chat.id, user_id="BadUserID"
                )

                assert len(tag_models) == 0

    class TestGetChatListByUserIdAndTagName:
        # TODO: Add tests for skip and limit.
        @pytest.mark.asyncio
        async def test_valid_user_id_and_tag_name(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
        ):
            tag_name = "first_tag"
            user_id = str(uuid.uuid4())
            current_time = int(time.time())

            chats = [
                Chat(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    title="New Chat",
                    chat={},
                    created_at=current_time,
                    updated_at=current_time,
                    share_id=None,
                    archived=False,
                    pinned=None,
                    meta={"tags": [tag_name, "news", "bob"]},
                    folder_id=None,
                ),
                Chat(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    title="New Chat",
                    chat={},
                    created_at=current_time,
                    updated_at=current_time,
                    share_id=None,
                    archived=False,
                    pinned=None,
                    meta={"tags": ["news", "bob"]},
                    folder_id=None,
                ),
                Chat(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    title="New Chat",
                    chat={},
                    created_at=current_time,
                    updated_at=current_time,
                    share_id=None,
                    archived=False,
                    pinned=None,
                    meta={"tags": [tag_name, "news", "bob"]},
                    folder_id=None,
                ),
                Chat(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    title="New Chat",
                    chat={},
                    created_at=current_time,
                    updated_at=current_time,
                    share_id=None,
                    archived=True,
                    pinned=None,
                    meta={"tags": [tag_name, "news", "bob"]},
                    folder_id=None,
                ),
            ]

            async with db_connector.get_async_db() as db:
                for chat in chats:
                    db.add(chat)
                await db.commit()

                c = await chat_table.get_chat_list_by_user_id_and_tag_name(
                    user_id=user_id, tag_name="first_tag"
                )

                assert len(c) == 3

        # TODO: Add tests for skip and limit.
        @pytest.mark.asyncio
        async def test_invalid_user_id_and_valid_tag_name(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
        ):
            tag_name = "first_tag"
            user_id = str(uuid.uuid4())
            current_time = int(time.time())

            chats = [
                Chat(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    title="New Chat",
                    chat={},
                    created_at=current_time,
                    updated_at=current_time,
                    share_id=None,
                    archived=False,
                    pinned=None,
                    meta={"tags": [tag_name, "news", "bob"]},
                    folder_id=None,
                ),
                Chat(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    title="New Chat",
                    chat={},
                    created_at=current_time,
                    updated_at=current_time,
                    share_id=None,
                    archived=False,
                    pinned=None,
                    meta={"tags": ["news", "bob"]},
                    folder_id=None,
                ),
                Chat(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    title="New Chat",
                    chat={},
                    created_at=current_time,
                    updated_at=current_time,
                    share_id=None,
                    archived=False,
                    pinned=None,
                    meta={"tags": [tag_name, "news", "bob"]},
                    folder_id=None,
                ),
                Chat(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    title="New Chat",
                    chat={},
                    created_at=current_time,
                    updated_at=current_time,
                    share_id=None,
                    archived=True,
                    pinned=None,
                    meta={"tags": [tag_name, "news", "bob"]},
                    folder_id=None,
                ),
            ]

            async with db_connector.get_async_db() as db:
                for chat in chats:
                    db.add(chat)
                await db.commit()

                c = await chat_table.get_chat_list_by_user_id_and_tag_name(
                    user_id="InvalidUserId", tag_name="first_tag"
                )

                assert len(c) == 0

        # TODO: Add tests for skip and limit.
        @pytest.mark.asyncio
        async def test_valid_user_id_and_invalid_tag_name(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
        ):
            tag_name = "first_tag"
            user_id = str(uuid.uuid4())
            current_time = int(time.time())

            chats = [
                Chat(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    title="New Chat",
                    chat={},
                    created_at=current_time,
                    updated_at=current_time,
                    share_id=None,
                    archived=False,
                    pinned=None,
                    meta={"tags": [tag_name, "news", "bob"]},
                    folder_id=None,
                ),
                Chat(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    title="New Chat",
                    chat={},
                    created_at=current_time,
                    updated_at=current_time,
                    share_id=None,
                    archived=False,
                    pinned=None,
                    meta={"tags": ["news", "bob"]},
                    folder_id=None,
                ),
                Chat(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    title="New Chat",
                    chat={},
                    created_at=current_time,
                    updated_at=current_time,
                    share_id=None,
                    archived=False,
                    pinned=None,
                    meta={"tags": [tag_name, "news", "bob"]},
                    folder_id=None,
                ),
                Chat(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    title="New Chat",
                    chat={},
                    created_at=current_time,
                    updated_at=current_time,
                    share_id=None,
                    archived=True,
                    pinned=None,
                    meta={"tags": [tag_name, "news", "bob"]},
                    folder_id=None,
                ),
            ]

            async with db_connector.get_async_db() as db:
                for chat in chats:
                    db.add(chat)
                await db.commit()

                c = await chat_table.get_chat_list_by_user_id_and_tag_name(
                    user_id=user_id, tag_name="InvalidTagName"
                )

                assert len(c) == 0

    class TestAddChatTagByIdAndUserIdAndTagName:
        @pytest.mark.asyncio
        async def test_valid_chat_id_and_user_id_and_tag_name(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
        ):
            current_time = int(time.time())
            chat = Chat(
                id=str(uuid.uuid4()),
                user_id=str(uuid.uuid4()),
                title="New Chat",
                chat={},
                created_at=current_time,
                updated_at=current_time,
                share_id=None,
                archived=False,
                pinned=None,
                meta={"tags": ["test_tag", "tag_2", "last_tag"]},
                folder_id=None,
            )

            new_tag = "This is the new Tag."

            async with db_connector.get_async_db() as db:
                db.add(chat)
                await db.commit()
                await db.refresh(chat)

                c = await chat_table.add_chat_tag_by_id_and_user_id_and_tag_name(
                    id=chat.id, user_id=chat.user_id, tag_name=new_tag
                )

                assert c
                assert new_tag.replace(" ", "_").lower() in c.meta.get("tags", [])

                await db.refresh(chat)
                assert ChatModel.model_validate(chat) == c

        @pytest.mark.asyncio
        async def test_invalid_chat_id_and_valid_user_id_and_tag_name(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
        ):
            current_time = int(time.time())
            chat = Chat(
                id=str(uuid.uuid4()),
                user_id=str(uuid.uuid4()),
                title="New Chat",
                chat={},
                created_at=current_time,
                updated_at=current_time,
                share_id=None,
                archived=False,
                pinned=None,
                meta={"tags": ["test_tag", "tag_2", "last_tag"]},
                folder_id=None,
            )

            new_tag = "This is the new Tag."

            async with db_connector.get_async_db() as db:
                db.add(chat)
                await db.commit()
                await db.refresh(chat)

                c = await chat_table.add_chat_tag_by_id_and_user_id_and_tag_name(
                    id="BadChatID", user_id=chat.user_id, tag_name=new_tag
                )

                assert c is None

        @pytest.mark.asyncio
        async def test_invalid_user_id_and_valid_chat_id_and_tag_name(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
        ):
            current_time = int(time.time())
            chat = Chat(
                id=str(uuid.uuid4()),
                user_id=str(uuid.uuid4()),
                title="New Chat",
                chat={},
                created_at=current_time,
                updated_at=current_time,
                share_id=None,
                archived=False,
                pinned=None,
                meta={"tags": ["test_tag", "tag_2", "last_tag"]},
                folder_id=None,
            )

            new_tag = "This is the new Tag."

            async with db_connector.get_async_db() as db:
                db.add(chat)
                await db.commit()
                await db.refresh(chat)

                c = await chat_table.add_chat_tag_by_id_and_user_id_and_tag_name(
                    id=chat.id, user_id="InvalidUserId", tag_name=new_tag
                )

                assert c is None

        @pytest.mark.asyncio
        async def test_valid_chat_id_and_user_id_and_empty_tag_name(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
        ):
            current_time = int(time.time())
            chat = Chat(
                id=str(uuid.uuid4()),
                user_id=str(uuid.uuid4()),
                title="New Chat",
                chat={},
                created_at=current_time,
                updated_at=current_time,
                share_id=None,
                archived=False,
                pinned=None,
                meta={"tags": ["test_tag", "tag_2", "last_tag"]},
                folder_id=None,
            )

            async with db_connector.get_async_db() as db:
                db.add(chat)
                await db.commit()
                await db.refresh(chat)

                c = await chat_table.add_chat_tag_by_id_and_user_id_and_tag_name(
                    id=chat.id, user_id=chat.user_id, tag_name=""
                )

                assert c is None

    class TestCountChatsByTagNameAndUserId:

        @pytest.mark.asyncio
        async def test_valid_tag_and_user_id(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
        ):
            tag_name = "first_tag"
            user_id = str(uuid.uuid4())
            current_time = int(time.time())

            chats = [
                Chat(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    title="New Chat",
                    chat={},
                    created_at=current_time,
                    updated_at=current_time,
                    share_id=None,
                    archived=False,
                    pinned=None,
                    meta={"tags": [tag_name, "news", "bob"]},
                    folder_id=None,
                ),
                Chat(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    title="New Chat",
                    chat={},
                    created_at=current_time,
                    updated_at=current_time,
                    share_id=None,
                    archived=False,
                    pinned=None,
                    meta={"tags": ["news", "bob"]},
                    folder_id=None,
                ),
                Chat(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    title="New Chat",
                    chat={},
                    created_at=current_time,
                    updated_at=current_time,
                    share_id=None,
                    archived=False,
                    pinned=None,
                    meta={"tags": [tag_name, "news", "bob"]},
                    folder_id=None,
                ),
                Chat(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    title="New Chat",
                    chat={},
                    created_at=current_time,
                    updated_at=current_time,
                    share_id=None,
                    archived=True,
                    pinned=None,
                    meta={"tags": [tag_name, "news", "bob"]},
                    folder_id=None,
                ),
            ]

            async with db_connector.get_async_db() as db:
                for chat in chats:
                    db.add(chat)
                await db.commit()

                c = await chat_table.count_chats_by_tag_name_and_user_id(
                    user_id=user_id, tag_name="first_tag"
                )

                assert c == 2

        @pytest.mark.asyncio
        async def test_valid_tag_and_invalid_user_id(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
        ):
            tag_name = "first_tag"
            user_id = str(uuid.uuid4())
            current_time = int(time.time())

            chats = [
                Chat(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    title="New Chat",
                    chat={},
                    created_at=current_time,
                    updated_at=current_time,
                    share_id=None,
                    archived=False,
                    pinned=None,
                    meta={"tags": [tag_name, "news", "bob"]},
                    folder_id=None,
                ),
                Chat(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    title="New Chat",
                    chat={},
                    created_at=current_time,
                    updated_at=current_time,
                    share_id=None,
                    archived=False,
                    pinned=None,
                    meta={"tags": ["news", "bob"]},
                    folder_id=None,
                ),
                Chat(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    title="New Chat",
                    chat={},
                    created_at=current_time,
                    updated_at=current_time,
                    share_id=None,
                    archived=False,
                    pinned=None,
                    meta={"tags": [tag_name, "news", "bob"]},
                    folder_id=None,
                ),
                Chat(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    title="New Chat",
                    chat={},
                    created_at=current_time,
                    updated_at=current_time,
                    share_id=None,
                    archived=True,
                    pinned=None,
                    meta={"tags": [tag_name, "news", "bob"]},
                    folder_id=None,
                ),
            ]

            async with db_connector.get_async_db() as db:
                for chat in chats:
                    db.add(chat)
                await db.commit()

                c = await chat_table.count_chats_by_tag_name_and_user_id(
                    user_id="InvalidUserId", tag_name="first_tag"
                )

                assert c == 0

        @pytest.mark.asyncio
        async def test_unknown_tag_and_user_id(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
        ):
            tag_name = "first_tag"
            user_id = str(uuid.uuid4())
            current_time = int(time.time())

            chats = [
                Chat(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    title="New Chat",
                    chat={},
                    created_at=current_time,
                    updated_at=current_time,
                    share_id=None,
                    archived=False,
                    pinned=None,
                    meta={"tags": [tag_name, "news", "bob"]},
                    folder_id=None,
                ),
                Chat(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    title="New Chat",
                    chat={},
                    created_at=current_time,
                    updated_at=current_time,
                    share_id=None,
                    archived=False,
                    pinned=None,
                    meta={"tags": ["news", "bob"]},
                    folder_id=None,
                ),
                Chat(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    title="New Chat",
                    chat={},
                    created_at=current_time,
                    updated_at=current_time,
                    share_id=None,
                    archived=False,
                    pinned=None,
                    meta={"tags": [tag_name, "news", "bob"]},
                    folder_id=None,
                ),
                Chat(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    title="New Chat",
                    chat={},
                    created_at=current_time,
                    updated_at=current_time,
                    share_id=None,
                    archived=True,
                    pinned=None,
                    meta={"tags": [tag_name, "news", "bob"]},
                    folder_id=None,
                ),
            ]

            async with db_connector.get_async_db() as db:
                for chat in chats:
                    db.add(chat)
                await db.commit()

                c = await chat_table.count_chats_by_tag_name_and_user_id(
                    user_id=user_id, tag_name=""
                )

                assert c == 0

    class TestDeleteTagByIdAndUserIdAndTagName:

        @pytest.mark.asyncio
        async def test_valid_chat_id_and_user_id_and_tag_name(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
        ):
            tag_to_remove = "first_tag"
            current_time = int(time.time())
            chat = Chat(
                id=str(uuid.uuid4()),
                user_id=str(uuid.uuid4()),
                title="New Chat",
                chat={},
                created_at=current_time,
                updated_at=current_time,
                share_id=None,
                archived=False,
                pinned=None,
                meta={"tags": [tag_to_remove, "news", "bob"]},
                folder_id=None,
            )

            async with db_connector.get_async_db() as db:
                db.add(chat)
                await db.commit()
                await db.refresh(chat)

                assert tag_to_remove in chat.meta.get("tags", [])

                c = await chat_table.delete_tag_by_id_and_user_id_and_tag_name(
                    id=chat.id, user_id=chat.user_id, tag_name="first_tag"
                )

                assert c

                await db.refresh(chat)
                assert chat.meta.get("tags", None)
                assert tag_to_remove not in chat.meta.get("tags", [])

        @pytest.mark.asyncio
        async def test_valid_chat_id_and_tag_name_and_invalid_user_id(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
        ):
            tag_to_remove = "first_tag"
            current_time = int(time.time())
            chat = Chat(
                id=str(uuid.uuid4()),
                user_id=str(uuid.uuid4()),
                title="New Chat",
                chat={},
                created_at=current_time,
                updated_at=current_time,
                share_id=None,
                archived=False,
                pinned=None,
                meta={"tags": [tag_to_remove, "news", "bob"]},
                folder_id=None,
            )

            async with db_connector.get_async_db() as db:
                db.add(chat)
                await db.commit()
                await db.refresh(chat)

                assert tag_to_remove in chat.meta.get("tags", [])

                c = await chat_table.delete_tag_by_id_and_user_id_and_tag_name(
                    id=chat.id, user_id="InvalidUserID", tag_name="first_tag"
                )

                assert not c

        @pytest.mark.asyncio
        async def test_valid_user_id_and_tag_name_and_invalid_chat_id(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
        ):
            tag_to_remove = "first_tag"
            current_time = int(time.time())
            chat = Chat(
                id=str(uuid.uuid4()),
                user_id=str(uuid.uuid4()),
                title="New Chat",
                chat={},
                created_at=current_time,
                updated_at=current_time,
                share_id=None,
                archived=False,
                pinned=None,
                meta={"tags": [tag_to_remove, "news", "bob"]},
                folder_id=None,
            )

            async with db_connector.get_async_db() as db:
                db.add(chat)
                await db.commit()
                await db.refresh(chat)

                assert tag_to_remove in chat.meta.get("tags", [])

                c = await chat_table.delete_tag_by_id_and_user_id_and_tag_name(
                    id="InvalidChatId", user_id=chat.user_id, tag_name="first_tag"
                )

                assert not c

    class TestDeleteAllTagsByIdAndUserId:

        @pytest.mark.asyncio
        async def test_valid_ids(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
        ):
            current_time = int(time.time())
            chat = Chat(
                id=str(uuid.uuid4()),
                user_id=str(uuid.uuid4()),
                title="New Chat",
                chat={},
                created_at=current_time,
                updated_at=current_time,
                share_id=None,
                archived=False,
                pinned=None,
                meta={"tags": ["FirstTag", "News", "Bob"]},
                folder_id=None,
            )

            async with db_connector.get_async_db() as db:
                db.add(chat)
                await db.commit()
                await db.refresh(chat)

                c = await chat_table.delete_all_tags_by_id_and_user_id(
                    id=chat.id, user_id=chat.user_id
                )

                assert c

                await db.refresh(chat)
                assert chat.meta.get("tags", None) == []

    class TestDeleteChatsById:

        @pytest.mark.asyncios
        async def test_valid_id(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
        ):
            current_time = int(time.time())
            chat = Chat(
                id=str(uuid.uuid4()),
                user_id=str(uuid.uuid4()),
                title="Test Chat for Unit Testing",
                chat={},
                created_at=current_time,
                updated_at=current_time,
                share_id=None,
                archived=False,
                pinned=None,
                meta={},
                folder_id=None,
            )

            async with db_connector.get_async_db() as db:
                db.add(chat)
                await db.commit()
                await db.refresh(chat)

                is_deleted = await chat_table.delete_chat_by_id(id=chat.id)
                assert is_deleted

                c = await db.scalar(select(Chat).where(Chat.id == chat.id))
                assert c is None

    class TestDeleteChatsByIdAndUserId:

        @pytest.mark.asyncios
        async def test_valid_ids(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
        ):
            current_time = int(time.time())
            chat = Chat(
                id=str(uuid.uuid4()),
                user_id=str(uuid.uuid4()),
                title="Test Chat for Unit Testing",
                chat={},
                created_at=current_time,
                updated_at=current_time,
                share_id=None,
                archived=False,
                pinned=None,
                meta={},
                folder_id=None,
            )

            async with db_connector.get_async_db() as db:
                db.add(chat)
                await db.commit()
                await db.refresh(chat)

                is_deleted = await chat_table.delete_chat_by_id_and_user_id(
                    id=chat.id, user_id=chat.user_id
                )
                assert is_deleted

                c = await db.scalar(
                    select(Chat).where(Chat.id == chat.id, Chat.user_id == chat.user_id)
                )
                assert c is None

    class TestDeleteChatsByUserId:

        @pytest.mark.asyncios
        async def test_valid_id(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
        ):
            current_time = int(time.time())
            user_id = str(uuid.uuid4())
            chats = [
                Chat(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    title="Test Chat for Unit Testing",
                    chat={},
                    created_at=current_time,
                    updated_at=current_time,
                    share_id=None,
                    archived=False,
                    pinned=None,
                    meta={},
                    folder_id=None,
                )
                for _ in range(5)
            ]

            async with db_connector.get_async_db() as db:
                for chat in chats:
                    db.add(chat)
                await db.commit()
                for chat in chats:
                    await db.refresh(chat)

                chats_in_db = await db.execute(
                    select(Chat).where(Chat.user_id == user_id)
                )
                assert len(chats_in_db.fetchall()) == len(chats)

                is_deleted = await chat_table.delete_chats_by_user_id(user_id=user_id)
                assert is_deleted

                c = await db.execute(select(Chat).where(Chat.user_id == user_id))
                assert len(c.fetchall()) == 0

    class TestDeleteChatsByUserIdAndFolderId:

        @pytest.mark.asyncios
        async def test_valid_ids(
            self,
            chat_table: ChatTable,
            db_connector: AsyncDatabaseConnector,
        ):
            current_time = int(time.time())
            user_id = str(uuid.uuid4())
            folder_ids = [str(uuid.uuid4()) for _ in range(3)]

            chats = [
                Chat(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    title="Test Chat for Unit Testing",
                    chat={},
                    created_at=current_time,
                    updated_at=current_time,
                    share_id=None,
                    archived=False,
                    pinned=None,
                    meta={},
                    folder_id=random.choice(folder_ids),
                )
                for _ in range(10)
            ]

            async with db_connector.get_async_db() as db:
                for chat in chats:
                    db.add(chat)
                await db.commit()
                for chat in chats:
                    await db.refresh(chat)

                # Choose a folder_id
                folder_id = random.choice(folder_ids)
                chats_in_folder = [
                    chat.id for chat in chats if chat.folder_id == folder_id
                ]
                while len(chats_in_folder) == 0:
                    folder_id = random.choice(folder_ids)
                    chats_in_folder = [
                        chat.id for chat in chats if chat.folder_id == folder_id
                    ]

                chats_in_folder_db = await db.execute(
                    select(Chat).where(
                        Chat.user_id == user_id, Chat.folder_id == folder_id
                    )
                )
                assert len(chats_in_folder_db.fetchall()) == len(chats_in_folder)

                is_deleted = await chat_table.delete_chats_by_user_id_and_folder_id(
                    user_id=user_id, folder_id=folder_id
                )
                assert is_deleted

                c = await db.execute(
                    select(Chat).where(
                        Chat.user_id == user_id, Chat.folder_id == folder_id
                    )
                )
                assert len(c.fetchall()) == 0
