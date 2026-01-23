import os
import uuid
import pytest
import redis.asyncio as redis

from pytest_mock import MockerFixture
from open_webui.session.models import UserSession
from open_webui.session.session_service_redis import (
    RedisJSONSessionService,
    RedisSessionServiceImpl,
)

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
REDIS_CLIENT: redis.Redis


@pytest.fixture(scope="session")
async def redis_client_fixture():
    try:
        REDIS_CLIENT = await redis.from_url(REDIS_URL)
        await REDIS_CLIENT.ping()
    except redis.ConnectionError:
        pytest.skip("No connection to Redis.")

    return REDIS_CLIENT


@pytest.mark.asyncio
async def test_redis_session_service(
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    redis_client_fixture: redis.Redis,
):
    user_id = str(uuid.uuid4())

    client = await redis_client_fixture
    session_storage = RedisSessionServiceImpl(client=client, session_lifetime=60)

    session = UserSession(user_id=user_id)
    assert await session_storage.update_session(session=session)

    session2 = await session_storage.get_session(user_id)
    assert session2

    await session_storage.remove_session(user_id)
    assert not await session_storage.get_session(user_id)


@pytest.mark.asyncio
async def test_redisjson_session_service(
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    redis_client_fixture: redis.Redis,
):
    client = await redis_client_fixture
    modules: list[dict[bytes, bytes]] = await client.module_list()

    contains_module = False
    for module in modules:
        name = module.get(b"name")
        if module.get(b"name") == b"ReJSON":
            contains_module = True
            break

    if not contains_module:
        pytest.skip("No ReJSON module loaded in Redis.")

    user_id = str(uuid.uuid4())

    session_storage = RedisJSONSessionService(client=client, session_lifetime=60)

    session = UserSession(user_id=user_id)
    assert await session_storage.update_session(session=session)

    session2 = await session_storage.get_session(user_id)
    assert session2

    await session_storage.remove_session(user_id)
    assert not await session_storage.get_session(user_id)
