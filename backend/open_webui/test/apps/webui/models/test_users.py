import random
import time
import uuid
from typing import Any

import pytest
from open_webui.internal.db_utils import AsyncDatabaseConnector
from open_webui.models.users import User, UserModel, UserSettings, UsersTable
from sqlalchemy import select

_user_attributes: dict[str, str | int] = {
    "id": str(uuid.uuid4()),
    "email": "test.bob@example.test",
    "name": "Test Bob",
    "profile_image_url": "http://image.profile",
    "role": "user",
    "oauth_sub": "oauth2_sub:test.bob@example.test",
    "domain": "example.test",
    "created_at": int(time.time()),
    "last_active_at": int(time.time()),
    "updated_at": int(time.time()),
}


class TestUsers:

    @pytest.mark.asyncio
    async def test_insert_new_user(
        self,
        users_table: UsersTable,
        db_connector: AsyncDatabaseConnector,
    ):
        usermodel = await users_table.insert_new_user(
            id=_user_attributes["id"],
            email=_user_attributes["email"],
            name=_user_attributes["name"],
            profile_image_url=_user_attributes["profile_image_url"],
            role=_user_attributes["role"],
            oauth_sub=_user_attributes["oauth_sub"],
            domain=_user_attributes["domain"],
        )
        assert usermodel

        async with db_connector.get_async_db() as session:
            user = await session.scalar(
                select(User).where(User.id == _user_attributes["id"])
            )

            assert user

            for k, v in usermodel.model_dump().items():
                assert getattr(user, k, None) == v

    @pytest.mark.asyncio
    async def test_get_user_by_id(
        self,
        users_table: UsersTable,
        db_connector: AsyncDatabaseConnector,
    ):
        async with db_connector.get_async_db() as db:

            user = User(**_user_attributes)
            db.add(user)
            await db.commit()
            await db.refresh(user)

            usermodel = await users_table.get_user_by_id(id=_user_attributes["id"])

            assert usermodel == UserModel(**_user_attributes)

    @pytest.mark.asyncio
    async def test_set_api_key_and_get_user_by_api_key(
        self,
        db_connector: AsyncDatabaseConnector,
        users_table: UsersTable,
    ):
        async with db_connector.get_async_db() as db:

            _model = UserModel(**_user_attributes)
            user = User(**_model.model_dump())
            db.add(user)
            await db.commit()
            await db.refresh(user)

            api_key = "apikey-1549785651231265"
            api_key_updated = await users_table.update_user_api_key_by_id(
                user.id, api_key=api_key
            )

            assert api_key_updated

            usermodel = await users_table.get_user_by_api_key(api_key=api_key)
            assert usermodel

            # Ensure users are identical
            _model.api_key = api_key
            assert usermodel == _model

    @pytest.mark.asyncio
    async def test_get_user_by_email(
        self,
        db_connector: AsyncDatabaseConnector,
        users_table: UsersTable,
    ):
        async with db_connector.get_async_db() as db:

            _model = UserModel(**_user_attributes)
            user = User(**_model.model_dump())
            db.add(user)
            await db.commit()
            await db.refresh(user)

            usermodel = await users_table.get_user_by_email(
                email=_user_attributes["email"]
            )
            assert usermodel

            # Ensure users are identical
            assert usermodel == _model

    @pytest.mark.asyncio
    async def test_get_all_users(
        self,
        db_connector: AsyncDatabaseConnector,
        users_table: UsersTable,
    ):
        async with db_connector.get_async_db() as db:

            _ums = [UserModel(**_user_attributes) for _ in range(5)]
            for index, user in enumerate(_ums):
                user.email = f"{index}_{user.email}"
                user.id += f"_{index}"
                user.oauth_sub = f"{user.oauth_sub}_{index}"

            _users = [User(**user.model_dump()) for user in _ums]
            db.add_all(_users)
            await db.commit()

            for user in _users:
                await db.refresh(user)

            users = await users_table.get_users()
            assert users and len(users) == len(_ums)

            # Ensure users are identical
            for index in range(len(users)):
                assert users[index] == _ums[index]

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "skip, limit",
        [
            (0, 0),
            (0, 2),
            (0, 3),
            (2, 0),
            (2, 1),
            (3, 0),
            (3, 2),
        ],
    )
    async def test_get_users_skip_and_limit(
        self,
        skip: int,
        limit: int,
        db_connector: AsyncDatabaseConnector,
        users_table: UsersTable,
    ):
        async with db_connector.get_async_db() as db:
            _ums = [UserModel(**_user_attributes) for _ in range(5)]
            for index, user in enumerate(_ums):
                user.email = f"{index}_{user.email}"
                user.id += f"_{index}"
                user.oauth_sub = f"{user.oauth_sub}_{index}"

            _users = [User(**user.model_dump()) for user in _ums]
            db.add_all(_users)
            await db.commit()

            for user in _users:
                await db.refresh(user)

            users = await users_table.get_users(
                skip=None if skip == 0 else skip,
                limit=None if limit == 0 else limit,
            )
            assert users and len(users) == (len(_ums) - skip) if limit == 0 else limit

            # Ensure users are identical
            users.sort(key=lambda u: u.id)
            for index in range(len(users)):
                assert users[index] == _ums[index + skip]

    @pytest.mark.asyncio
    async def test_get_users_by_user_ids(
        self,
        db_connector: AsyncDatabaseConnector,
        users_table: UsersTable,
    ):
        async with db_connector.get_async_db() as db:
            _ums = [UserModel(**_user_attributes) for _ in range(5)]
            for index, user in enumerate(_ums):
                user.email = f"{index}_{user.email}"
                user.id += f"_{index}"
                user.oauth_sub = f"{user.oauth_sub}_{index}"

            _users = [User(**user.model_dump()) for user in _ums]
            db.add_all(_users)
            await db.commit()

            for user in _users:
                await db.refresh(user)

            # Get some random IDs
            ids: set[str] = set()
            for _ in range(3):
                ids.add(_users[random.randrange(0, len(_users))].id)

            users = await users_table.get_users_by_user_ids(list(ids))

            assert len(ids) == len(users)

            for user in users:
                assert user in users

    @pytest.mark.asyncio
    async def test_get_user_domains(
        self,
        db_connector: AsyncDatabaseConnector,
        users_table: UsersTable,
    ):
        async with db_connector.get_async_db() as db:
            _ums = [UserModel(**_user_attributes) for _ in range(5)]
            for index, user in enumerate(_ums):
                user.email = f"{index}_{user.email}"
                user.id += f"_{index}"
                user.oauth_sub = f"{user.oauth_sub}_{index}"
                user.domain += f"_{index}"

            _users = [User(**user.model_dump()) for user in _ums]
            db.add_all(_users)
            await db.commit()

            for user in _users:
                await db.refresh(user)

            domains = await users_table.get_user_domains()

            _d = set([user.domain for user in _ums])
            assert len(domains) == len(_d)

            for domain in domains:
                assert domain in _d

    @pytest.mark.asyncio
    async def test_get_first_user(
        self,
        db_connector: AsyncDatabaseConnector,
        users_table: UsersTable,
    ):
        async with db_connector.get_async_db() as db:
            # Create 5 users and make the last one the earliest created_at
            _ums = [UserModel(**_user_attributes) for index in range(5)]
            for index, user in enumerate(_ums):
                user.email = f"{index}_{user.email}"
                user.id += f"_{index}"
                user.oauth_sub = f"{user.oauth_sub}_{index}"
                user.domain += f"_{index}"
                user.created_at -= index

            _users = [User(**user.model_dump()) for user in _ums]
            db.add_all(_users)
            await db.commit()

            for user in _users:
                await db.refresh(user)

            first_user = await users_table.get_first_user()

            assert first_user
            assert first_user == _ums[len(_ums) - 1]

    @pytest.mark.asyncio
    async def test_get_user_webhook_url_by_id(
        self,
        db_connector: AsyncDatabaseConnector,
        users_table: UsersTable,
    ):
        async with db_connector.get_async_db() as db:
            _model = UserModel(**_user_attributes)
            _w_url = "http://test.webhook.url"
            _model.settings = UserSettings(
                ui={"notifications": {"webhook_url": _w_url}}
            )
            user = User(**_model.model_dump())
            db.add(user)
            await db.commit()
            await db.refresh(user)

            webhook_url = await users_table.get_user_webhook_url_by_id(id=user.id)
            assert webhook_url

            # Ensure users are identical
            assert webhook_url == _w_url

    @pytest.mark.asyncio
    async def test_get_user_webhook_url_by_id_no_webhook(
        self,
        db_connector: AsyncDatabaseConnector,
        users_table: UsersTable,
    ):
        async with db_connector.get_async_db() as db:

            _model = UserModel(**_user_attributes)
            _model.settings = UserSettings(ui={"notifications": {}})
            user = User(**_model.model_dump())
            db.add(user)
            await db.commit()
            await db.refresh(user)

            webhook_url = await users_table.get_user_webhook_url_by_id(id=user.id)
            assert not webhook_url

    @pytest.mark.asyncio
    async def test_update_user_role_by_id(
        self,
        db_connector: AsyncDatabaseConnector,
        users_table: UsersTable,
    ):
        async with db_connector.get_async_db() as db:

            _model = UserModel(**_user_attributes)
            _model.settings = UserSettings(ui={"notifications": {}})
            user = User(**_model.model_dump())
            db.add(user)
            await db.commit()
            await db.refresh(user)

            _role = "test_role"
            updated_user = await users_table.update_user_role_by_id(
                id=user.id, role=_role
            )

            assert updated_user

            # Update user with latest role.
            await db.refresh(user)

            assert UserModel.model_validate(user) == updated_user

    @pytest.mark.asyncio
    async def test_update_user_profile_image_url_by_id(
        self,
        db_connector: AsyncDatabaseConnector,
        users_table: UsersTable,
    ):
        async with db_connector.get_async_db() as db:

            _model = UserModel(**_user_attributes)
            _model.settings = UserSettings(ui={"notifications": {}})
            user = User(**_model.model_dump())
            db.add(user)
            await db.commit()
            await db.refresh(user)

            _profile_image_url = "test_role"
            updated_user = await users_table.update_user_profile_image_url_by_id(
                id=user.id, profile_image_url=_profile_image_url
            )

            assert updated_user

            # Update user with latest profile_image_url.
            await db.refresh(user)

            assert UserModel.model_validate(user) == updated_user

    @pytest.mark.asyncio
    async def test_update_user_last_active_by_id(
        self,
        db_connector: AsyncDatabaseConnector,
        users_table: UsersTable,
    ):
        async with db_connector.get_async_db() as db:

            _model = UserModel(**_user_attributes)
            _model.settings = UserSettings(ui={"notifications": {}})
            user = User(**_model.model_dump())
            db.add(user)
            await db.commit()
            await db.refresh(user)

            updated_user = await users_table.update_user_last_active_by_id(id=user.id)

            assert updated_user
            assert UserModel.model_validate(user) != updated_user

            # Update user with last_active_at.
            await db.refresh(user)
            assert UserModel.model_validate(user) == updated_user

    @pytest.mark.parametrize(
        "days, domain",
        [
            (0, None),
            (1, None),
            (20, None),
            (0, f"{_user_attributes['domain']}"),
            (4, f"{_user_attributes['domain']}.4"),
            (20, f"{_user_attributes['domain']}.3"),
        ],
    )
    @pytest.mark.asyncio
    async def test_get_daily_users_number(
        self,
        days: int,
        domain: str | None,
        db_connector: AsyncDatabaseConnector,
        users_table: UsersTable,
    ):
        async with db_connector.get_async_db() as db:
            if days > 30:
                pytest.skip("Test built for a maximum number of days equal to 30.")

            _20_hours_in_seconds = 20 * 60 * 60

            _ums: list[UserModel] = list()
            for index_day in range(30):
                for index_user in range(index_day):
                    user = UserModel(**_user_attributes)
                    user.email = f"{index_day}_{index_user}_{user.email}.{index_day}"
                    user.id += f"_{index_day}_{index_user}"
                    user.domain = f"{user.domain}.{index_day}"
                    user.oauth_sub = f"{user.oauth_sub}_{index_day}_{index_user}"
                    user.last_active_at -= _20_hours_in_seconds * index_day
                    _ums.append(user)

            _users = [User(**user.model_dump()) for user in _ums]
            db.add_all(_users)
            await db.commit()

            for user in _users:
                await db.refresh(user)

            daily_users = await users_table.get_daily_users_number(
                days=days, domain=domain
            )

            assert daily_users is not None

            if domain is None:
                assert daily_users == sum(
                    1
                    for user in _users
                    if user.last_active_at >= int(time.time()) - (days * 24 * 60 * 60)
                )
            else:
                assert daily_users == sum(
                    1
                    for user in _users
                    if user.last_active_at >= int(time.time()) - (days * 24 * 60 * 60)
                    and user.domain == domain
                )

    @pytest.mark.asyncio
    async def test_update_user_oauth_sub_by_id(
        self,
        db_connector: AsyncDatabaseConnector,
        users_table: UsersTable,
    ):
        async with db_connector.get_async_db() as db:

            _model = UserModel(**_user_attributes)
            user = User(**_model.model_dump())
            db.add(user)
            await db.commit()
            await db.refresh(user)

            _oauth_sub = user.oauth_sub + "_updated_sub"
            updated_user = await users_table.update_user_oauth_sub_by_id(
                id=user.id, oauth_sub=_oauth_sub
            )

            assert updated_user
            assert updated_user.oauth_sub == _oauth_sub

            # Update user with latest oauth_sub.
            await db.refresh(user)

            assert UserModel.model_validate(user) == updated_user

    @pytest.mark.parametrize(
        "updates",
        [
            {"email": "new.email@bob.test.ca"},  # A proper field to update.
            {"bad_email": "new.email@bob.test.ca"},  # A field that doesn't belong.
            {
                "name": "Bobby Tester",
                "oauth_sub": str(uuid.uuid4()),
            },  # Multiple fields.
        ],
    )
    @pytest.mark.asyncio
    async def test_update_user_by_id(
        self,
        updates: dict[str, Any],
        db_connector: AsyncDatabaseConnector,
        users_table: UsersTable,
    ):
        async with db_connector.get_async_db() as db:

            _model = UserModel(**_user_attributes)
            user = User(**_model.model_dump())
            db.add(user)
            await db.commit()
            await db.refresh(user)

            updated_user = await users_table.update_user_by_id(
                id=user.id, updated=updates
            )

            assert updated_user

            # Update user with latest oauth_sub.
            await db.refresh(user)

            assert UserModel.model_validate(user) == updated_user
            assert UserModel(**(_user_attributes | updates)) == updated_user

    @pytest.mark.asyncio
    async def test_delete_user_by_id(
        self,
        db_connector: AsyncDatabaseConnector,
        users_table: UsersTable,
    ):
        async with db_connector.get_async_db() as db:

            _model = UserModel(**_user_attributes)
            user = User(**_model.model_dump())
            db.add(user)
            await db.commit()
            await db.refresh(user)

            is_deleted = await users_table.delete_user_by_id(id=user.id)

            assert is_deleted

            result = await db.scalar(select(User).where(User.id == _model.id))
            assert not result

    @pytest.mark.asyncio
    async def test_update_user_api_key_by_id(
        self,
        db_connector: AsyncDatabaseConnector,
        users_table: UsersTable,
    ):
        async with db_connector.get_async_db() as db:

            _model = UserModel(**_user_attributes)
            user = User(**_model.model_dump())
            db.add(user)
            await db.commit()
            await db.refresh(user)

            _api_key = "sk-test-asdsad-asdasd"
            updated_user = await users_table.update_user_api_key_by_id(
                id=user.id, api_key=_api_key
            )

            assert updated_user

            # Update user with latest oauth_sub.
            await db.refresh(user)

            assert user.api_key != _model.api_key

    @pytest.mark.asyncio
    async def test_update_user_api_key_by_id_no_id(
        self,
        users_table: UsersTable,
    ):

        _api_key = "sk-test-asdsad-asdasd"
        updated_user = await users_table.update_user_api_key_by_id(
            id=str(uuid.uuid4()), api_key=_api_key
        )

        assert not updated_user

    @pytest.mark.asyncio
    async def test_get_user_api_key_by_id(
        self,
        db_connector: AsyncDatabaseConnector,
        users_table: UsersTable,
    ):
        async with db_connector.get_async_db() as db:

            _api_key = "sk-test-asdsad-asdasd"
            _model = UserModel(**_user_attributes)
            _model.api_key = _api_key
            user = User(**_model.model_dump())
            db.add(user)
            await db.commit()
            await db.refresh(user)

            api_key = await users_table.get_user_api_key_by_id(id=user.id)

            assert api_key

            # Update user with latest oauth_sub.
            await db.refresh(user)

            assert user.api_key == api_key
            assert api_key == _api_key

    @pytest.mark.asyncio
    async def test_get_valid_user_ids(
        self,
        db_connector: AsyncDatabaseConnector,
        users_table: UsersTable,
    ):
        async with db_connector.get_async_db() as db:
            _ums = [UserModel(**_user_attributes) for _ in range(5)]
            for index, user in enumerate(_ums):
                user.email = f"{index}_{user.email}"
                user.id += f"_{index}"
                user.oauth_sub = f"{user.oauth_sub}_{index}"

            _users = [User(**user.model_dump()) for user in _ums]
            db.add_all(_users)
            await db.commit()

            for user in _users:
                await db.refresh(user)

            # Get some random IDs
            ids: set[str] = set()
            for _ in range(3):
                ids.add(_users[random.randrange(0, len(_users))].id)

            valid_ids = await users_table.get_valid_user_ids(list(ids))

            assert len(ids) == len(valid_ids)

            list_ids = list(ids)
            list_ids.sort()
            valid_ids.sort()
            assert list_ids == valid_ids
