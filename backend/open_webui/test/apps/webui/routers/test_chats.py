import uuid

import pytest

from open_webui.test.util.abstract_integration_test import AbstractPostgresTest
from open_webui.test.util.mock_user import mock_webui_user


class TestChats(AbstractPostgresTest):
    BASE_PATH = "/api/v1/chats/"

    @classmethod
    def setup_class(cls):
        super().setup_class()
        from open_webui.models.chats import ChatForm
        from open_webui.models.db_services import CHATS, USERS

        cls.chats = CHATS
        cls.chat_form = ChatForm
        cls.users = USERS

    async def setup_method(self):
        await super().setup_method()

        _ = await self.users.insert_new_user(
            "1", "User 1", "user1@example.com", "/user1.png", "user"
        )
        _ = await self.users.insert_new_user(
            "2", "User 2", "user2@example.com", "/user2.png", "user"
        )
        _ = await self.chats.insert_new_chat(
            "2",
            self.chat_form(
                **{
                    "chat": {
                        "name": "chat1",
                        "description": "chat1 description",
                        "tags": ["tag1", "tag2"],
                        "history": {"currentId": "1", "messages": []},
                    }
                }
            ),
        )

    def test_get_session_user_chat_list(self):
        with mock_webui_user(id="2"):
            response = self.fast_api_client.get(self.create_url("/"))
        assert response.status_code == 200
        first_chat = response.json()[0]
        assert first_chat["id"] is not None
        assert first_chat["title"] == "New Chat"
        assert first_chat["created_at"] is not None
        assert first_chat["updated_at"] is not None

    @pytest.mark.asyncio
    async def test_delete_all_user_chats(self):
        with mock_webui_user(id="2"):
            response = self.fast_api_client.delete(self.create_url("/"))
        assert response.status_code == 200
        assert len(await self.chats.get_chats()) == 0

    @pytest.mark.asyncio
    def test_get_user_chat_list_by_user_id(self):
        with mock_webui_user(id="3"):
            response = self.fast_api_client.get(self.create_url("/list/user/2"))
        assert response.status_code == 200
        first_chat = response.json()[0]
        assert first_chat["id"] is not None
        assert first_chat["title"] == "New Chat"
        assert first_chat["created_at"] is not None
        assert first_chat["updated_at"] is not None

    @pytest.mark.asyncio
    async def test_create_new_chat(self):
        with mock_webui_user(id="2"):
            response = self.fast_api_client.post(
                self.create_url("/new"),
                json={
                    "chat": {
                        "name": "chat2",
                        "description": "chat2 description",
                        "tags": ["tag1", "tag2"],
                    }
                },
            )
        assert response.status_code == 200
        data = response.json()
        assert data["archived"] is False
        assert data["chat"] == {
            "name": "chat2",
            "description": "chat2 description",
            "tags": ["tag1", "tag2"],
        }
        assert data["user_id"] == "2"
        assert data["id"] is not None
        assert data["share_id"] is None
        assert data["title"] == "New Chat"
        assert data["updated_at"] is not None
        assert data["created_at"] is not None
        assert len(await self.chats.get_chats()) == 2

    def test_get_user_chats(self):
        self.test_get_session_user_chat_list()

    @pytest.mark.asyncio
    async def test_get_user_archived_chats(self):
        await self.chats.archive_all_chats_by_user_id("2")
        from open_webui.internal.db import DB_SESSION

        DB_SESSION.commit()
        with mock_webui_user(id="2"):
            response = self.fast_api_client.get(self.create_url("/all/archived"))
        assert response.status_code == 200
        first_chat = response.json()[0]
        assert first_chat["id"] is not None
        assert first_chat["title"] == "New Chat"
        assert first_chat["created_at"] is not None
        assert first_chat["updated_at"] is not None

    def test_get_all_user_chats_in_db(self):
        with mock_webui_user(id="4"):
            response = self.fast_api_client.get(self.create_url("/all/db"))
        assert response.status_code == 200
        assert len(response.json()) == 1

    @pytest.mark.asyncio
    async def test_get_archived_session_user_chat_list(self):
        await self.test_get_user_archived_chats()

    @pytest.mark.asyncio
    async def test_archive_all_chats(self):
        with mock_webui_user(id="2"):
            response = self.fast_api_client.post(self.create_url("/archive/all"))
        assert response.status_code == 200
        assert len(await self.chats.get_archived_chats_by_user_id("2")) == 1

    @pytest.mark.asyncio
    async def test_get_shared_chat_by_id(self):
        chat_id = (await self.chats.get_chats())[0].id
        await self.chats.update_chat_share_id_by_id(chat_id, chat_id)
        with mock_webui_user(id="2"):
            response = self.fast_api_client.get(self.create_url(f"/share/{chat_id}"))
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == chat_id
        assert data["chat"] == {
            "name": "chat1",
            "description": "chat1 description",
            "tags": ["tag1", "tag2"],
            "history": {"currentId": "1", "messages": []},
        }
        assert data["id"] == chat_id
        assert data["share_id"] == chat_id
        assert data["title"] == "New Chat"

    @pytest.mark.asyncio
    async def test_get_chat_by_id(self):
        chat_id = (await self.chats.get_chats())[0].id
        with mock_webui_user(id="2"):
            response = self.fast_api_client.get(self.create_url(f"/{chat_id}"))
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == chat_id
        assert data["chat"] == {
            "name": "chat1",
            "description": "chat1 description",
            "tags": ["tag1", "tag2"],
            "history": {"currentId": "1", "messages": []},
        }
        assert data["share_id"] is None
        assert data["title"] == "New Chat"
        assert data["user_id"] == "2"

    @pytest.mark.asyncio
    async def test_update_chat_by_id(self):
        chat_id = (await self.chats.get_chats())[0].id
        with mock_webui_user(id="2"):
            response = self.fast_api_client.post(
                self.create_url(f"/{chat_id}"),
                json={
                    "chat": {
                        "name": "chat2",
                        "description": "chat2 description",
                        "tags": ["tag2", "tag4"],
                        "title": "Just another title",
                    }
                },
            )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == chat_id
        assert data["chat"] == {
            "name": "chat2",
            "title": "Just another title",
            "description": "chat2 description",
            "tags": ["tag2", "tag4"],
            "history": {"currentId": "1", "messages": []},
        }
        assert data["share_id"] is None
        assert data["title"] == "Just another title"
        assert data["user_id"] == "2"

    @pytest.mark.asyncio
    async def test_delete_chat_by_id(self):
        chat_id = (await self.chats.get_chats())[0].id
        with mock_webui_user(id="2"):
            response = self.fast_api_client.delete(self.create_url(f"/{chat_id}"))
        assert response.status_code == 200
        assert response.json() is True

    @pytest.mark.asyncio
    async def test_clone_chat_by_id(self):
        chat_id = (await self.chats.get_chats())[0].id
        with mock_webui_user(id="2"):
            response = self.fast_api_client.post(
                self.create_url(f"/{chat_id}/clone"), json={}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] != chat_id
        assert data["chat"]["name"] == "chat1"
        assert data["chat"]["title"] == "Clone of New Chat"
        assert data["share_id"] is None
        assert data["title"] == "Clone of New Chat"
        assert data["user_id"] == "2"

    @pytest.mark.asyncio
    async def test_archive_chat_by_id(self):
        chat_id = (await self.chats.get_chats())[0].id
        with mock_webui_user(id="2"):
            response = self.fast_api_client.post(self.create_url(f"/{chat_id}/archive"))
        assert response.status_code == 200

        chat = await self.chats.get_chat_by_id(chat_id)
        assert chat is not None and chat.archived is True

    @pytest.mark.asyncio
    async def test_share_chat_by_id(self):
        chat_id = (await self.chats.get_chats())[0].id
        with mock_webui_user(id="2"):
            response = self.fast_api_client.post(self.create_url(f"/{chat_id}/share"))
        assert response.status_code == 200

        chat = await self.chats.get_chat_by_id(chat_id)
        assert chat is not None and chat.share_id is not None

    @pytest.mark.asyncio
    async def test_delete_shared_chat_by_id(self):
        chat_id = (await self.chats.get_chats())[0].id
        share_id = str(uuid.uuid4())
        await self.chats.update_chat_share_id_by_id(chat_id, share_id)
        with mock_webui_user(id="2"):
            response = self.fast_api_client.delete(self.create_url(f"/{chat_id}/share"))
        assert response.status_code

        chat = await self.chats.get_chat_by_id(chat_id)
        assert chat is not None and chat.share_id is None
